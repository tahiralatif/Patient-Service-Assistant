from types import SimpleNamespace

import pytest

from app import workflow
from app.store import AppointmentStore
from app.tools.tools import book_appointment, check_availability, lookup_appointment


@pytest.fixture(autouse=True)
def _clear():
    workflow._FLOWS.clear()


def E(**kw):
    base = dict(patient_id=None, appointment_id=None, date=None, time=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _setup(store, patient="P1001"):
    slots = check_availability(store, "cardiology").data["slots"]
    a, b = slots[0], slots[1]
    appt = book_appointment(store, patient, "cardiology", a["date"], a["time"]).data["appointment"]
    return appt["appointment_id"], a, b


def test_missing_fields_are_asked_not_guessed():
    r = workflow.step("s1", E(patient_id="P1001"), "reschedule", AppointmentStore())
    assert r.status.value == "needs_clarification"
    assert "appointment_id" in r.missing_fields


def test_full_flow_changes_appointment_only_after_yes():
    store = AppointmentStore()
    appt_id, a, b = _setup(store)
    ask = workflow.step("s2", E(patient_id="P1001", appointment_id=appt_id,
                                date=b["date"], time=b["time"]), "move it", store)
    assert ask.status.value == "needs_clarification"
    still = lookup_appointment(store, appt_id, "P1001").data["appointment"]
    assert still["time"] == a["time"]            # nothing changed before confirmation
    done = workflow.step("s2", E(), "yes", store)
    assert done.status.value == "completed"
    now = lookup_appointment(store, appt_id, "P1001").data["appointment"]
    assert (now["date"], now["time"]) == (b["date"], b["time"])


def test_no_keeps_appointment():
    store = AppointmentStore()
    appt_id, a, b = _setup(store)
    workflow.step("s3", E(patient_id="P1001", appointment_id=appt_id,
                          date=b["date"], time=b["time"]), "move", store)
    workflow.step("s3", E(), "no", store)
    now = lookup_appointment(store, appt_id, "P1001").data["appointment"]
    assert now["time"] == a["time"]


def test_wrong_patient_is_refused():
    store = AppointmentStore()
    appt_id, a, b = _setup(store)
    r = workflow.step("s4", E(patient_id="P1002", appointment_id=appt_id,
                              date=b["date"], time=b["time"]), "move", store)
    assert r.status.value == "not_possible"
    assert not workflow.is_active("s4")


def test_taken_slot_offers_alternatives():
    store = AppointmentStore()
    appt_id, a, b = _setup(store)
    book_appointment(store, "P1002", "cardiology", b["date"], b["time"])
    r = workflow.step("s5", E(patient_id="P1001", appointment_id=appt_id,
                              date=b["date"], time=b["time"]), "move", store)
    assert r.status.value == "needs_clarification"
    assert "not available" in r.reply


def test_timeout_during_execution_is_not_reported_as_success():
    store = AppointmentStore()
    appt_id, a, b = _setup(store)
    workflow.step("s6", E(patient_id="P1001", appointment_id=appt_id,
                          date=b["date"], time=b["time"]), "move", store)

    def broken(*args, **kwargs):
        raise TimeoutError("simulated")
    store.reschedule = broken
    r = workflow.step("s6", E(), "yes", store)
    assert r.status.value == "not_possible"
    assert "is now on" not in r.reply