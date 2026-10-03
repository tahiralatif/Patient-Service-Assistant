"""The only functions the assistant may use to touch appointments.
Each tool validates its input, calls the store, and returns a ToolResult.
RULE: ok=True is created only AFTER the store call returned. Any error,
including an unexpected one or a timeout, becomes ok=False, so no reply
can claim success without confirmed tool output.
"""
import logging
import re
from dataclasses import dataclass
from datetime import date as _date
from typing import Any, Callable

from app.store import (
    SPECIALTIES, AlreadyCancelled, AppointmentNotFound, AppointmentStore,
    InvalidSlot, SlotUnavailable,
)

log = logging.getLogger(__name__)

_PATIENT_RE = re.compile(r"^P\d{4}$")
_APPT_RE = re.compile(r"^APT-\d{4}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_REASON_RE = re.compile(r"^[a-z_]{3,40}$")


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    code: str = "ok"          # ok | invalid_input | not_found | slot_unavailable | ...
    message: str = ""         # safe text, never contains raw user message
    data: dict[str, Any] | None = None


def _fail(code: str, message: str) -> ToolResult:
    return ToolResult(ok=False, code=code, message=message)


# ---------- input validation ----------
def _check_patient_id(v):
    if not isinstance(v, str) or not _PATIENT_RE.match(v):
        return "patient_id must look like P1234"

def _check_appointment_id(v):
    if not isinstance(v, str) or not _APPT_RE.match(v):
        return "appointment_id must look like APT-1234"

def _check_specialty(v):
    if v not in SPECIALTIES:
        return "specialty must be one of: " + ", ".join(SPECIALTIES)

def _check_date(v):
    try:
        _date.fromisoformat(v)
    except (TypeError, ValueError):
        return "date must be a real date in YYYY-MM-DD format"

def _check_time(v):
    if not isinstance(v, str) or not _TIME_RE.match(v):
        return "time must be HH:MM in 24-hour format"

def _check_reason(v):
    if not isinstance(v, str) or not _REASON_RE.match(v):
        return "reason must be a short code like no_verified_answer"

_CHECKS = {
    "patient_id": _check_patient_id,
    "appointment_id": _check_appointment_id,
    "specialty": _check_specialty,
    "date": _check_date,
    "time": _check_time,
    "reason": _check_reason,
}


def _validate(**fields) -> ToolResult | None:
    for name, value in fields.items():
        problem = _CHECKS[name](value)
        if problem:
            return _fail("invalid_input", problem)
    return None


def _guarded(fn: Callable[[], ToolResult]) -> ToolResult:
    """Run a store call; turn every failure into ok=False."""
    try:
        return fn()
    except AppointmentNotFound:
        return _fail("not_found", "No appointment matches that appointment ID and patient ID.")
    except AlreadyCancelled:
        return _fail("already_cancelled", "That appointment is already cancelled.")
    except SlotUnavailable:
        return _fail("slot_unavailable", "That slot is not available.")
    except InvalidSlot as exc:
        return _fail("invalid_slot", exc.reason)
    except Exception:
        # Includes timeouts: we do NOT know if the action happened.
        log.exception("tool failed unexpectedly")
        return _fail("tool_failure",
                     "The system could not confirm this action, so nothing is confirmed.")


# ---------- the six tools ----------
def check_availability(store: AppointmentStore, specialty: str,
                       on_date: str | None = None) -> ToolResult:
    bad = _validate(specialty=specialty)
    if not bad and on_date is not None:
        bad = _validate(date=on_date)
    if bad:
        return bad
    return _guarded(lambda: ToolResult(
        ok=True, data={"slots": store.list_available(specialty, on_date=on_date)}))


def book_appointment(store: AppointmentStore, patient_id: str, specialty: str,
                     date: str, time: str) -> ToolResult:
    bad = _validate(patient_id=patient_id, specialty=specialty, date=date, time=time)
    if bad:
        return bad

    def run() -> ToolResult:
        appt = store.book(patient_id, specialty, date, time)
        return ToolResult(ok=True, data={"appointment": appt.as_dict()})
    return _guarded(run)


def reschedule_appointment(store: AppointmentStore, appointment_id: str,
                           patient_id: str, date: str, time: str) -> ToolResult:
    bad = _validate(appointment_id=appointment_id, patient_id=patient_id,
                    date=date, time=time)
    if bad:
        return bad

    def run() -> ToolResult:
        appt = store.reschedule(appointment_id, patient_id, date, time)
        return ToolResult(ok=True, data={"appointment": appt.as_dict()})
    return _guarded(run)


def cancel_appointment(store: AppointmentStore, appointment_id: str,
                       patient_id: str) -> ToolResult:
    bad = _validate(appointment_id=appointment_id, patient_id=patient_id)
    if bad:
        return bad

    def run() -> ToolResult:
        appt = store.cancel(appointment_id, patient_id)
        return ToolResult(ok=True, data={"appointment": appt.as_dict()})
    return _guarded(run)


def lookup_appointment(store: AppointmentStore, appointment_id: str,
                       patient_id: str) -> ToolResult:
    bad = _validate(appointment_id=appointment_id, patient_id=patient_id)
    if bad:
        return bad

    def run() -> ToolResult:
        appt = store.get_owned(appointment_id, patient_id)
        return ToolResult(ok=True, data={"appointment": appt.as_dict()})
    return _guarded(run)


def escalate_to_human(store: AppointmentStore, reason: str,
                      patient_id: str | None = None) -> ToolResult:
    bad = _validate(reason=reason)
    if not bad and patient_id is not None:
        bad = _validate(patient_id=patient_id)
    if bad:
        return bad

    def run() -> ToolResult:
        ticket = store.create_escalation(reason, patient_id)
        return ToolResult(ok=True, data={"ticket": ticket})
    return _guarded(run)