"""Checks run BEFORE any intent handling. They block prompt-injection
attempts, requests for other people's data, and medical advice/records.
Emergencies are checked first in main.py, so they are never blocked here.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    code: str
    reply: str


_INJECTION = re.compile(
    r"ignore (?:\w+ ){0,3}(?:instructions|rules|prompts?)"
    r"|disregard (?:\w+ ){0,3}(?:instructions|rules|prompts?)"
    r"|system prompt|developer mode|jailbreak"
    r"|reveal (?:\w+ ){0,2}(?:prompt|instructions|rules)"
    r"|you are now|pretend (?:to be|you)",
    re.I,
)
_OTHER_PATIENT = re.compile(
    r"(?:someone else|another patient|other patient|wife|husband|mother|father|son"
    r"|daughter|brother|sister|friend|neighbou?r|colleague)(?:'s|s')? "
    r"(?:appointment|records?|results?|details|file)",
    re.I,
)
_MEDICAL = re.compile(
    r"medical records?|lab results?|diagnos\w*|prescri\w*"
    r"|what (?:medicine|medication|dose|dosage)|should i take|side effects?|is it serious",
    re.I,
)

_REPLIES = {
    "prompt_injection": (
        "I can't change how I work or follow instructions that override my rules. "
        "I can help with booking, rescheduling, cancelling, availability, preparation "
        "and general clinic questions."
    ),
    "other_patient_data": (
        "I can only help with your own appointments. I can't share or change "
        "another person's information."
    ),
    "medical_advice": (
        "I can't give medical advice or access medical records or results here. "
        "Please contact your clinician or the clinic directly. If it is urgent, "
        "contact emergency services."
    ),
}


def check_message(message: str) -> Block | None:
    for code, pattern in (
        ("prompt_injection", _INJECTION),
        ("other_patient_data", _OTHER_PATIENT),
        ("medical_advice", _MEDICAL),
    ):
        if pattern.search(message):
            return Block(code, _REPLIES[code])
    return None