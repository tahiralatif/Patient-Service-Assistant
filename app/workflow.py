"""Multi-step reschedule workflow:
clarify -> verify ownership -> check slot -> ask confirmation -> execute -> reply.
State is kept per session_id in code. A reply says 'done' only if the
reschedule tool returned ok=True.
"""
from dataclasses import dataclass, field

from app.handlers import Result
from app.schemas import Status
from app.store import AppointmentStore
from app.tools.tools import (
    check_availability, lookup_appointment, reschedule_appointment,
)

REQUIRED = ["patient_id", "appointment_id", "date", "time"]
_ASK = {
    "patient_id": "your patient ID (e.g. P1001)",
    "appointment_id": "your appointment ID (e.g. APT-1001)",
    "date": "the new date (YYYY-MM-DD)",
    "time": "the new time (HH:MM, 24-hour)",
}
_YES = {"yes", "y", "confirm", "ok", "okay", "haan", "han", "ji"}
_NO = {"no", "n", "nahi", "nahin", "stop", "cancel"}


@dataclass
class Flow:
    fields: dict[str, str] = field(default_factory=dict)
    awaiting_confirm: bool = False


_FLOWS: dict[str, Flow] = {}


def is_active(session_id: str) -> bool:
    return session_id in _FLOWS

def reset(session_id: str) -> None:
    _FLOWS.pop(session_id, None)


def _merge(flow: Flow, entities) -> None:
    for name in REQUIRED:
        value = getattr(entities, name, None)
        if value:
            flow.fields[name] = value


def _confirm(session_id: str, flow: Flow, message: str, store: AppointmentStore) -> Result:
    answer = message.strip().lower().rstrip(".! ")
    if answer in _YES:
        f = flow.fields
        _FLOWS.pop(session_id, None)
        res = reschedule_appointment(
            store, f["appointment_id"], f["patient_id"], f["date"], f["time"])
        if not res.ok:
            # Includes tool_failure/timeouts: nothing is confirmed, so we say so.
            return Result(Status.NOT_POSSIBLE, res.message)
        appt = res.data["appointment"]
        return Result(
            Status.COMPLETED,
            f"Appointment {appt['appointment_id']} is now on {appt['date']} at {appt['time']}.",
            data=res.data)
    if answer in _NO:
        _FLOWS.pop(session_id, None)
        return Result(Status.COMPLETED, "No problem, your appointment was not changed.")
    return Result(Status.NEEDS_CLARIFICATION,
                  "Please reply yes to confirm the change, or no to keep your current appointment.")


def step(session_id: str, entities, message: str, store: AppointmentStore) -> Result:
    flow = _FLOWS.setdefault(session_id, Flow())
    if flow.awaiting_confirm:
        return _confirm(session_id, flow, message, store)

    _merge(flow, entities)
    missing = [n for n in REQUIRED if n not in flow.fields]
    if missing:
        needs = "; ".join(_ASK[m] for m in missing)
        return Result(Status.NEEDS_CLARIFICATION,
                      f"To reschedule I still need: {needs}.", missing_fields=missing)

    f = flow.fields
    found = lookup_appointment(store, f["appointment_id"], f["patient_id"])
    if not found.ok:
        _FLOWS.pop(session_id, None)
        return Result(Status.NOT_POSSIBLE, found.message)
    current = found.data["appointment"]

    avail = check_availability(store, current["specialty"], on_date=f["date"])
    if not avail.ok:
        _FLOWS.pop(session_id, None)
        return Result(Status.NOT_POSSIBLE, avail.message)
    if not any(s["time"] == f["time"] for s in avail.data["slots"]):
        alts = check_availability(store, current["specialty"])
        options = ", ".join(f"{s['date']} {s['time']}" for s in alts.data["slots"][:3]) \
            if alts.ok else ""
        del flow.fields["date"], flow.fields["time"]   # ask for a new date/time
        hint = f" Next available: {options}." if options else ""
        return Result(Status.NEEDS_CLARIFICATION,
                      "That slot is not available." + hint + " Which new date and time would you like?",
                      missing_fields=["date", "time"])

    flow.awaiting_confirm = True
    return Result(
        Status.NEEDS_CLARIFICATION,
        f"Move {current['appointment_id']} ({current['specialty']}) from "
        f"{current['date']} {current['time']} to {f['date']} {f['time']}? "
        "Reply yes to confirm or no to cancel this change.",
        data={"pending_change": {"from": [current["date"], current["time"]],
                                 "to": [f["date"], f["time"]]}})