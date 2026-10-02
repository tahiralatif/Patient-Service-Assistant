"""In-memory mock of the clinic's scheduling system.

Part 1 handlers call this directly. In Part 3 these operations get wrapped as
"tools" with timeouts, retries and explicit success/failure results.

Mock clinic rules (assumptions, see README):
- Open Sunday-Thursday (Fri/Sat closed), five fixed slots per day.
- One doctor per specialty -> one appointment per specialty/date/time.
- Bookings open from tomorrow up to 14 days ahead.
"""
from dataclasses import asdict, dataclass
from datetime import date, timedelta

SLOT_TIMES = ("09:00", "10:00", "11:00", "14:00", "15:00")
SPECIALTIES = ("cardiology", "dermatology", "general practice")
CLOSED_WEEKDAYS = {4, 5}  # Friday, Saturday (date.weekday())
BOOKING_HORIZON_DAYS = 14


class StoreError(Exception):
    pass


class InvalidSlot(StoreError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class SlotUnavailable(StoreError):
    pass


class AppointmentNotFound(StoreError):
    """Raised for unknown IDs AND for IDs owned by another patient, so the
    caller cannot learn whether someone else's appointment exists."""


class AlreadyCancelled(StoreError):
    pass


@dataclass
class Appointment:
    appointment_id: str
    patient_id: str
    specialty: str
    date: str
    time: str
    status: str = "confirmed"  # confirmed | cancelled

    def as_dict(self) -> dict:
        return asdict(self)


class AppointmentStore:
    def __init__(self, today: date | None = None):
        # Assumption: server date. Production should use Asia/Riyadh.
        self.today = today or date.today()
        self._appointments: dict[str, Appointment] = {}
        self._escalations: list[dict] = []
        self._next_id = 1001
        self._seed()

    # ---- seed data -------------------------------------------------------
    def _seed(self) -> None:
        day = self.today + timedelta(days=2)
        while day.weekday() in CLOSED_WEEKDAYS:
            day += timedelta(days=1)
        self._create("P1001", "cardiology", day.isoformat(), "10:00")
        self._create("P1002", "dermatology", day.isoformat(), "09:00")

    def _create(self, patient_id: str, specialty: str, date_str: str, time_str: str) -> Appointment:
        appt = Appointment(f"APT-{self._next_id}", patient_id, specialty, date_str, time_str)
        self._next_id += 1
        self._appointments[appt.appointment_id] = appt
        return appt

    # ---- helpers ---------------------------------------------------------
    def _validate_slot(self, specialty: str, date_str: str, time_str: str) -> None:
        if specialty not in SPECIALTIES:
            raise InvalidSlot("Unknown specialty.")
        try:
            day = date.fromisoformat(date_str)
        except ValueError:
            raise InvalidSlot("The date must be a real date in YYYY-MM-DD format.")
        if day <= self.today:
            raise InvalidSlot("Appointments can only be made for a future date.")
        if day > self.today + timedelta(days=BOOKING_HORIZON_DAYS):
            raise InvalidSlot(f"Bookings open up to {BOOKING_HORIZON_DAYS} days ahead.")
        if day.weekday() in CLOSED_WEEKDAYS:
            raise InvalidSlot("The clinic is closed on Fridays and Saturdays.")
        if time_str not in SLOT_TIMES:
            raise InvalidSlot("Appointment times are: " + ", ".join(SLOT_TIMES) + ".")

    def _is_taken(self, specialty: str, date_str: str, time_str: str,
                  ignore_id: str | None = None) -> bool:
        return any(
            a.status == "confirmed" and a.appointment_id != ignore_id
            and (a.specialty, a.date, a.time) == (specialty, date_str, time_str)
            for a in self._appointments.values()
        )

    def get_owned(self, appointment_id: str, patient_id: str) -> Appointment:
        appt = self._appointments.get(appointment_id)
        if appt is None or appt.patient_id != patient_id:
            raise AppointmentNotFound(appointment_id)
        return appt

    # ---- operations ------------------------------------------------------
    def list_available(self, specialty: str, on_date: str | None = None,
                       limit: int = 5) -> list[dict]:
        if specialty not in SPECIALTIES:
            raise InvalidSlot("Unknown specialty.")
        if on_date is not None:
            try:
                days = [date.fromisoformat(on_date)]
            except ValueError:
                raise InvalidSlot("The date must be a real date in YYYY-MM-DD format.")
        else:
            days = [self.today + timedelta(days=i) for i in range(1, BOOKING_HORIZON_DAYS + 1)]

        slots: list[dict] = []
        for day in days:
            if (day <= self.today or day > self.today + timedelta(days=BOOKING_HORIZON_DAYS)
                    or day.weekday() in CLOSED_WEEKDAYS):
                continue
            for time_str in SLOT_TIMES:
                if not self._is_taken(specialty, day.isoformat(), time_str):
                    slots.append({"date": day.isoformat(), "time": time_str})
                    if len(slots) >= limit:
                        return slots
        return slots

    def book(self, patient_id: str, specialty: str, date_str: str, time_str: str) -> Appointment:
        self._validate_slot(specialty, date_str, time_str)
        if self._is_taken(specialty, date_str, time_str):
            raise SlotUnavailable()
        return self._create(patient_id, specialty, date_str, time_str)

    def reschedule(self, appointment_id: str, patient_id: str,
                   date_str: str, time_str: str) -> Appointment:
        appt = self.get_owned(appointment_id, patient_id)
        if appt.status == "cancelled":
            raise AlreadyCancelled()
        self._validate_slot(appt.specialty, date_str, time_str)
        if self._is_taken(appt.specialty, date_str, time_str, ignore_id=appointment_id):
            raise SlotUnavailable()
        appt.date, appt.time = date_str, time_str
        return appt

    def cancel(self, appointment_id: str, patient_id: str) -> Appointment:
        appt = self.get_owned(appointment_id, patient_id)
        if appt.status == "cancelled":
            raise AlreadyCancelled()
        appt.status = "cancelled"
        return appt

    def create_escalation(self, reason: str, patient_id: str | None) -> str:
        # Stores the reason code only, never the raw message (privacy).
        ticket = f"ESC-{len(self._escalations) + 1:04d}"
        self._escalations.append({"ticket": ticket, "reason": reason, "patient_id": patient_id})
        return ticket
