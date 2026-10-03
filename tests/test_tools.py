from app.store import AppointmentStore
from app.tools.tools import (
    book_appointment, cancel_appointment, check_availability,
    escalate_to_human, lookup_appointment, reschedule_appointment,
)


def _first_slot(store):
    r = check_availability(store, "cardiology")
    return r.data["slots"][0]


def test_invalid_input_never_reaches_store():
    r = book_appointment(AppointmentStore(), "BAD", "cardiology", "2026-13-40", "10:00")
    assert not r.ok and r.code == "invalid_input"


def test_book_then_double_book():
    store = AppointmentStore()
    s = _first_slot(store)
    first = book_appointment(store, "P1001", "cardiology", s["date"], s["time"])
    assert first.ok
    second = book_appointment(store, "P1002", "cardiology", s["date"], s["time"])
    assert not second.ok and second.code == "slot_unavailable"


def test_other_patient_cannot_cancel_or_lookup():
    store = AppointmentStore()
    s = _first_slot(store)
    appt_id = book_appointment(store, "P1001", "cardiology",
                               s["date"], s["time"]).data["appointment"]["appointment_id"]
    assert not cancel_appointment(store, appt_id, "P1002").ok
    assert not lookup_appointment(store, appt_id, "P1002").ok
    assert lookup_appointment(store, appt_id, "P1001").ok


def test_reschedule_and_cancel_own_appointment():
    store = AppointmentStore()
    slots = check_availability(store, "cardiology").data["slots"]
    a, b = slots[0], slots[1]
    appt_id = book_appointment(store, "P1001", "cardiology",
                               a["date"], a["time"]).data["appointment"]["appointment_id"]
    assert reschedule_appointment(store, appt_id, "P1001", b["date"], b["time"]).ok
    assert cancel_appointment(store, appt_id, "P1001").ok
    assert cancel_appointment(store, appt_id, "P1001").code == "already_cancelled"


def test_unexpected_failure_is_never_success():
    class BrokenStore(AppointmentStore):
        def book(self, *args, **kwargs):
            raise TimeoutError("simulated timeout")

    store = BrokenStore()
    s = _first_slot(store)
    r = book_appointment(store, "P1001", "cardiology", s["date"], s["time"])
    assert not r.ok and r.code == "tool_failure" and r.data is None


def test_escalation_returns_ticket_and_rejects_free_text():
    store = AppointmentStore()
    assert escalate_to_human(store, "no_verified_answer").data["ticket"]
    assert not escalate_to_human(store, "My chest hurts, please help me").ok