"""One handler per intent. Each returns a Result; the API layer wraps it into
the validated AssistantResponse.

Rule followed everywhere: a reply may only say an action happened if the store
call actually returned successfully.
"""
from dataclasses import dataclass, field
from typing import Any
from functools import lru_cache
from .grounding import answer_from_kb
from .retrieval import Retriever
from .nlu import Entities, is_emergency
from .schemas import Intent, Status
from .store import (
    SPECIALTIES, AlreadyCancelled, AppointmentNotFound, AppointmentStore,
    InvalidSlot, SlotUnavailable,
)


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


def _book(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["patient_id", "specialty", "date", "time"])
    if missing:
        return _clarify("To book an appointment I still need", missing)
    try:
        appt = store.book(e.patient_id, e.specialty, e.date, e.time)
    except SlotUnavailable:
        alts = store.list_available(e.specialty, limit=3)
        hint = f" Next available {e.specialty} slots: {_fmt_slots(alts)}." if alts else ""
        return Result(Status.NOT_POSSIBLE, "That slot is not available." + hint,
                      data={"alternatives": alts})
    except InvalidSlot as exc:
        return Result(Status.NOT_POSSIBLE, exc.reason)
    return Result(
        Status.COMPLETED,
        f"Your {appt.specialty} appointment is confirmed: {appt.appointment_id} "
        f"on {appt.date} at {appt.time}.",
        data={"appointment": appt.as_dict()},
    )


def _reschedule(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["patient_id", "appointment_id", "date", "time"])
    if missing:
        return _clarify("To reschedule I still need", missing)
    try:
        appt = store.reschedule(e.appointment_id, e.patient_id, e.date, e.time)
    except AppointmentNotFound:
        return Result(Status.NOT_POSSIBLE,
                      "I couldn't find an appointment matching that appointment ID and patient ID.")
    except AlreadyCancelled:
        return Result(Status.NOT_POSSIBLE, "That appointment was already cancelled, so it can't be moved.")
    except SlotUnavailable:
        current = store.get_owned(e.appointment_id, e.patient_id)
        alts = store.list_available(current.specialty, limit=3)
        hint = f" Next available slots: {_fmt_slots(alts)}." if alts else ""
        return Result(Status.NOT_POSSIBLE, "That new slot is not available." + hint,
                      data={"alternatives": alts})
    except InvalidSlot as exc:
        return Result(Status.NOT_POSSIBLE, exc.reason)
    return Result(
        Status.COMPLETED,
        f"Appointment {appt.appointment_id} is now on {appt.date} at {appt.time}.",
        data={"appointment": appt.as_dict()},
    )


def _cancel(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["patient_id", "appointment_id"])
    if missing:
        return _clarify("To cancel I still need", missing)
    try:
        appt = store.cancel(e.appointment_id, e.patient_id)
    except AppointmentNotFound:
        return Result(Status.NOT_POSSIBLE,
                      "I couldn't find an appointment matching that appointment ID and patient ID.")
    except AlreadyCancelled:
        return Result(Status.NOT_POSSIBLE, "That appointment is already cancelled.")
    return Result(Status.COMPLETED, f"Appointment {appt.appointment_id} has been cancelled.",
                  data={"appointment": appt.as_dict()})


def _availability(e: Entities, store: AppointmentStore) -> Result:
    missing = _missing(e, ["specialty"])
    if missing:
        return _clarify("To check availability I still need", missing)
    try:
        slots = store.list_available(e.specialty, on_date=e.date)
    except InvalidSlot as exc:
        return Result(Status.NOT_POSSIBLE, exc.reason)
    if slots:
        return Result(Status.COMPLETED, f"Available {e.specialty} slots: {_fmt_slots(slots)}.",
                      data={"slots": slots})
    if e.date:
        nxt = store.list_available(e.specialty, limit=3)
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
        ticket = store.create_escalation("no_verified_answer", e.patient_id)
        return Result(Status.ESCALATED, f"{answer.reply} Reference: {ticket}.",
                      data={"ticket": ticket})
    return Result(Status.COMPLETED, answer.reply,
                  data={"specialty": e.specialty, "sources": answer.sources})

def _info(e: Entities, store: AppointmentStore, message: str) -> Result:
    answer = answer_from_kb(message, _get_retriever())
    if answer.grounded:
        return Result(Status.COMPLETED, answer.reply, data={"sources": answer.sources})
    # Nothing verified to answer with: do NOT guess, hand over to a human.
    ticket = store.create_escalation("no_verified_answer", e.patient_id)
    return Result(Status.ESCALATED, f"{answer.reply} Reference: {ticket}.",
                  data={"ticket": ticket})


def _escalate(e: Entities, store: AppointmentStore, message: str) -> Result:
    emergency = is_emergency(message)
    ticket = store.create_escalation("possible_emergency" if emergency else "user_requested", e.patient_id)
    if emergency:
        reply = ("If this is a medical emergency, please contact emergency services immediately "
                 "and do not wait for this chat. I've also flagged your message to our team. "
                 f"Reference: {ticket}.")
    else:
        reply = f"I've passed this to a member of our team, who will follow up. Reference: {ticket}."
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
    if intent is Intent.RESCHEDULE:
        return _reschedule(entities, store)
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
    return _unknown(candidates)
