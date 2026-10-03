"""One handler per intent. Each returns a Result; the API layer wraps it into
the validated AssistantResponse.

Rules followed everywhere:
- Every action goes through app/tools/tools.py, never straight to the store.
- A reply may only say an action happened if the tool returned ok=True.
- Rescheduling is NOT handled here: it needs a confirmation step, so main.py
  routes it to workflow.py.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.tools.tools import (
    ToolResult, book_appointment, cancel_appointment,
    check_availability, escalate_to_human,
)

from .grounding import answer_from_kb
from .nlu import Entities, is_emergency
from .retrieval import Retriever
from .schemas import Intent, Status
from .store import SPECIALTIES, AppointmentStore


@dataclass
class Result:
    status: Status
    reply: str
    missing_fields: list[str] = field(default_factory=list)
    data: dict[str, Any] | None = None


_FIELD_HELP = {
    "patient_id": "your patient ID (e.g. P1001)",
    "appointment_id": "your appointment ID (e.g. APT-1001)",
    "specialty": "the specialty (" + ", ".join(SPECIALTIES) + ")",
    "date": "the date (YYYY-MM-DD)",
    "time": "the time (HH:MM, 24-hour)",
}


@lru_cache
def _get_retriever() -> Retriever:
    return Retriever()


def _clarify(intro: str, missing: list[str]) -> Result:
    needs = "; ".join(_FIELD_HELP[m] for m in missing)
    return Result(Status.NEEDS_CLARIFICATION, f"{intro}: {needs}.", missing_fields=missing)


def _missing(entities: Entities, required: list[str]) -> list[str]:
    return [name for name in required if getattr(entities, name) is None]


def _fmt_slots(slots: list[dict]) -> str:
    return ", ".join(f"{s['date']} {s['time']}" for s in slots)


def _fail(res: ToolResult) -> Result:
    status = Status.NEEDS_CLARIFICATION if res.code == "invalid_input" else Status.NOT_POSSIBLE
    return Result(status, res.message)


def _ticket(store: AppointmentStore, reason: str, patient_id: str | None) -> str | None:
    res = escalate_to_human(store, reason, patient_id)
    return res.data["ticket"] if res.ok else None


def _ref(ticket: str | None) -> str:
    return f" Reference: {ticket}." if ticket else ""


def _book(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["patient_id", "specialty", "date", "time"])
    if missing:
        return _clarify("To book an appointment I still need", missing)
    res = book_appointment(store, e.patient_id, e.specialty, e.date, e.time)
    if not res.ok:
        if res.code == "slot_unavailable":
            alt = check_availability(store, e.specialty)
            alts = alt.data["slots"][:3] if alt.ok else []
            hint = f" Next available {e.specialty} slots: {_fmt_slots(alts)}." if alts else ""
            return Result(Status.NOT_POSSIBLE, res.message + hint, data={"alternatives": alts})
        return _fail(res)
    appt = res.data["appointment"]
    return Result(
        Status.COMPLETED,
        f"Your {appt['specialty']} appointment is confirmed: {appt['appointment_id']} "
        f"on {appt['date']} at {appt['time']}.",
        data=res.data,
    )


def _cancel(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["patient_id", "appointment_id"])
    if missing:
        return _clarify("To cancel I still need", missing)
    res = cancel_appointment(store, e.appointment_id, e.patient_id)
    if not res.ok:
        return _fail(res)
    appt = res.data["appointment"]
    return Result(Status.COMPLETED, f"Appointment {appt['appointment_id']} has been cancelled.",
                  data=res.data)


def _availability(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["specialty"])
    if missing:
        return _clarify("To check availability I still need", missing)
    res = check_availability(store, e.specialty, e.date)
    if not res.ok:
        return _fail(res)
    slots = res.data["slots"]
    if slots:
        return Result(Status.COMPLETED, f"Available {e.specialty} slots: {_fmt_slots(slots)}.",
                      data={"slots": slots})
    nxt_res = check_availability(store, e.specialty)
    nxt = nxt_res.data["slots"][:3] if nxt_res.ok else []
    if e.date:
        hint = f" Next available: {_fmt_slots(nxt)}." if nxt else ""
        return Result(Status.NOT_POSSIBLE, f"No {e.specialty} slots on {e.date}." + hint,
                      data={"slots": nxt})
    return Result(Status.NOT_POSSIBLE, f"There are no {e.specialty} slots in the next 14 days.",
                  data={"slots": []})


def _preparation(e: Entities, store: AppointmentStore) -> Result:
    if e.specialty is None:
        return _clarify("To give preparation instructions I still need", ["specialty"])
    answer = answer_from_kb(f"prepare for {e.specialty} appointment", _get_retriever())
    if not answer.grounded:
        ticket = _ticket(store, "no_verified_answer", e.patient_id)
        return Result(Status.ESCALATED, answer.reply + _ref(ticket), data={"ticket": ticket})
    return Result(Status.COMPLETED, answer.reply,
                  data={"specialty": e.specialty, "sources": answer.sources})


def _info(e: Entities, store: AppointmentStore, message: str) -> Result:
    answer = answer_from_kb(message, _get_retriever())
    if answer.grounded:
        return Result(Status.COMPLETED, answer.reply, data={"sources": answer.sources})
    # Nothing verified to answer with: do NOT guess, hand over to a human.
    ticket = _ticket(store, "no_verified_answer", e.patient_id)
    return Result(Status.ESCALATED, answer.reply + _ref(ticket), data={"ticket": ticket})


def _escalate(e: Entities, store: AppointmentStore, message: str) -> Result:
    emergency = is_emergency(message)
    ticket = _ticket(store, "possible_emergency" if emergency else "user_requested", e.patient_id)
    if emergency:
        reply = ("If this is a medical emergency, please contact emergency services immediately "
                 "and do not wait for this chat. I've also flagged your message to our team."
                 + _ref(ticket))
    else:
        reply = "I've passed this to a member of our team, who will follow up." + _ref(ticket)
    return Result(Status.ESCALATED, reply, data={"ticket": ticket})


def _unknown(candidates: list[Intent]) -> Result:
    if len(candidates) > 1:
        names = " or ".join(c.value.replace("_", " ") for c in candidates)
        return Result(Status.NEEDS_CLARIFICATION,
                      f"I can help with one thing at a time. Do you want to: {names}?")
    return Result(
        Status.NEEDS_CLARIFICATION,
        "I can help with booking, rescheduling or cancelling appointments, checking availability, "
        "preparation instructions, and insurance or general questions. What would you like to do?",
    )


def handle(intent: Intent, candidates: list[Intent], entities: Entities,
           message: str, store: AppointmentStore) -> Result:
    if intent is Intent.BOOK:
        return _book(entities, store)
    if intent is Intent.CANCEL:
        return _cancel(entities, store)
    if intent is Intent.AVAILABILITY:
        return _availability(entities, store)
    if intent is Intent.PREPARATION:
        return _preparation(entities, store)
    if intent is Intent.INFO:
        return _info(entities, store, message)
    if intent is Intent.ESCALATE:
        return _escalate(entities, store, message)
    # RESCHEDULE is routed to workflow.py by main.py (it needs confirmation).
    return _unknown(candidates)