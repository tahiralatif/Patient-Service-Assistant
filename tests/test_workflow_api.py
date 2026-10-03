from fastapi.testclient import TestClient

from app import workflow
from app.store import AppointmentStore
from app.tools.tools import book_appointment, check_availability, lookup_appointment
from main import app, get_store


def _client(store):
    workflow._FLOWS.clear()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_reschedule_over_two_messages_via_api():
    store = AppointmentStore()
    slots = check_availability(store, "cardiology").data["slots"]
    a, b = slots[0], slots[1]
    appt_id = book_appointment(store, "P1001", "cardiology", a["date"], a["time"]
                               ).data["appointment"]["appointment_id"]
    client = _client(store)
    try:
        r1 = client.post("/assistant/message", json={
            "message": f"reschedule {appt_id} to {b['date']} at {b['time']}",
            "patient_id": "P1001", "session_id": "sess-1"}).json()
        assert r1["status"] == "needs_clarification"
        unchanged = lookup_appointment(store, appt_id, "P1001").data["appointment"]
        assert unchanged["time"] == a["time"]

        r2 = client.post("/assistant/message", json={
            "message": "yes", "patient_id": "P1001", "session_id": "sess-1"}).json()
        assert r2["status"] == "completed"
        moved = lookup_appointment(store, appt_id, "P1001").data["appointment"]
        assert (moved["date"], moved["time"]) == (b["date"], b["time"])
    finally:
        app.dependency_overrides.clear()


def test_reschedule_without_session_id_asks_for_one():
    client = _client(AppointmentStore())
    try:
        r = client.post("/assistant/message", json={
            "message": "I want to reschedule my appointment"}).json()
        assert r["status"] == "needs_clarification"
        assert "session_id" in r["missing_fields"]
    finally:
        app.dependency_overrides.clear()