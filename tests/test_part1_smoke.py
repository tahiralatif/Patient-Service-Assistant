"""Part 1 smoke tests. Part 7 expands these into the full suite."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from main import app, get_store
from app.store import AppointmentStore

TODAY = date(2026, 10, 4)  # a Sunday; Fri 2026-10-09 is a closed day


@pytest.fixture
def client():
    store = AppointmentStore(today=TODAY)
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def send(client, message, patient_id=None):
    body = {"message": message}
    if patient_id:
        body["patient_id"] = patient_id
    return client.post("/assistant/message", json=body)


def test_blank_message_rejected(client):
    assert send(client, "   ").status_code == 422


def test_bad_patient_id_rejected(client):
    assert send(client, "hi", patient_id="12345").status_code == 422


def test_availability(client):
    body = send(client, "Any cardiology slots available?").json()
    assert body["intent"] == "check_availability"
    assert body["status"] == "completed"
    assert body["data"]["slots"]


def test_book_missing_fields_asks_for_them(client):
    body = send(client, "I want to book a cardiology appointment").json()
    assert body["status"] == "needs_clarification"
    assert set(body["missing_fields"]) == {"patient_id", "date", "time"}


def test_book_then_double_book(client):
    msg = "Book cardiology on 2026-10-07 at 11:00"
    first = send(client, msg, patient_id="P2000").json()
    assert first["status"] == "completed"
    second = send(client, msg, patient_id="P3000").json()
    assert second["status"] == "not_possible"
    assert second["data"]["alternatives"]


def test_book_on_closed_day(client):
    body = send(client, "Book dermatology on 2026-10-09 at 10:00", patient_id="P2000").json()
    assert body["status"] == "not_possible"
    assert "closed" in body["reply"]


def test_reschedule_own_appointment(client):
    body = send(client, "Reschedule APT-1001 to 2026-10-08 at 14:00", patient_id="P1001").json()
    assert body["status"] == "completed"
    assert body["data"]["appointment"]["time"] == "14:00"


def test_cancel_other_patients_appointment_is_refused(client):
    body = send(client, "Cancel APT-1001", patient_id="P9999").json()
    assert body["status"] == "not_possible"
    assert body["data"] is None


def test_emergency_escalates(client):
    body = send(client, "I have chest pain").json()
    assert body["status"] == "escalated"
    assert "emergency services" in body["reply"]
    assert body["data"]["ticket"].startswith("ESC-")


def test_unknown_info_escalates_instead_of_guessing(client):
    body = send(client, "Where is the parking?").json()
    assert body["status"] == "escalated"


def test_known_info_answers(client):
    body = send(client, "Is insurance accepted?").json()
    assert body["status"] == "completed"


def test_ambiguous_request_asks(client):
    body = send(client, "Is cardiology available and is it covered by insurance?").json()
    assert body["status"] == "needs_clarification"
