"""Intent classification and entity extraction.

Part 1 is deliberately rule-based: deterministic, no API key, easy to explain
and test. `classify` / `extract_entities` are the only functions the rest of
the app calls, so an LLM-based classifier can replace them later without
touching handlers or the API layer.
"""
import re
from dataclasses import dataclass

from .schemas import Intent


@dataclass(frozen=True)
class Entities:
    patient_id: str | None = None
    appointment_id: str | None = None
    specialty: str | None = None
    date: str | None = None   # raw YYYY-MM-DD string; validated in the store
    time: str | None = None   # normalised HH:MM


_EMERGENCY = ("emergency", "chest pain", "cannot breathe", "can't breathe", "severe bleeding")
_ESCALATION = _EMERGENCY + (
    "human", "real person", "representative", "complaint", "complain",
    "speak to someone", "talk to someone",
)

_INTENT_RULES: dict[Intent, tuple[str, ...]] = {
    Intent.CANCEL: ("cancel",),
    Intent.RESCHEDULE: ("reschedule", "postpone", "move my appointment",
                        "change my appointment", "change the time"),
    Intent.BOOK: ("book", "schedule", "make an appointment", "need an appointment",
                  "see a doctor"),
    Intent.AVAILABILITY: ("available", "availability", "slot", "slots",
                          "free slot", "open slot", "when can i"),
    Intent.PREPARATION: ("prepare", "preparation", "fasting", "what should i bring",
                         "before my appointment"),
    Intent.INFO: ("insurance", "coverage", "covered", "copay", "opening hours",
                  "working hours", "parking", "address"),
}

_SPECIALTY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cardiology": ("cardiology", "cardiologist", "heart"),
    "dermatology": ("dermatology", "dermatologist", "skin"),
    "general practice": ("general practice", "gp", "family doctor", "general practitioner"),
}

_APPOINTMENT_ID = re.compile(r"\bAPT-\d{4}\b", re.IGNORECASE)
_PATIENT_ID = re.compile(r"\bP\d{4}\b", re.IGNORECASE)
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TIME = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def is_emergency(message: str) -> bool:
    text = message.lower()
    return any(_contains(text, p) for p in _EMERGENCY)


def classify(message: str) -> tuple[Intent, list[Intent]]:
    """Return (intent, candidates).

    - Escalation phrases always win (safety first).
    - Exactly one matching intent -> that intent.
    - BOOK + AVAILABILITY together -> BOOK (booking checks availability anyway).
    - Several different intents -> UNKNOWN, with `candidates` so the handler can ask.
    - No match -> UNKNOWN with no candidates.
    """
    text = message.lower()
    if any(_contains(text, p) for p in _ESCALATION):
        return Intent.ESCALATE, []

    matches = [
        intent for intent, phrases in _INTENT_RULES.items()
        if any(_contains(text, p) for p in phrases)
    ]
    if len(matches) == 1:
        return matches[0], matches
    if set(matches) == {Intent.BOOK, Intent.AVAILABILITY}:
        return Intent.BOOK, matches
    return Intent.UNKNOWN, matches


def extract_entities(message: str, patient_id: str | None = None) -> Entities:
    text = message.lower()

    appointment = _APPOINTMENT_ID.search(message)
    date = _DATE.search(message)
    time = _TIME.search(message)

    # patient_id from the request body (authenticated context) beats free text.
    if patient_id is None:
        found = _PATIENT_ID.search(message)
        patient_id = found.group(0) if found else None

    specialty = next(
        (name for name, words in _SPECIALTY_KEYWORDS.items()
         if any(_contains(text, w) for w in words)),
        None,
    )

    normalised_time = None
    if time:
        hours, minutes = time.group(0).split(":")
        normalised_time = f"{int(hours):02d}:{minutes}"

    return Entities(
        patient_id=patient_id.upper() if patient_id else None,
        appointment_id=appointment.group(0).upper() if appointment else None,
        specialty=specialty,
        date=date.group(0) if date else None,
        time=normalised_time,
    )
