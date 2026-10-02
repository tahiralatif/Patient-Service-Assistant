"""Request / response contracts for POST /assistant/message.

Every reply the service returns is validated against AssistantResponse, so
clients always get the same shape regardless of which intent was handled.
"""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Intent(str, Enum):
    BOOK = "book_appointment"
    RESCHEDULE = "reschedule_appointment"
    CANCEL = "cancel_appointment"
    AVAILABILITY = "check_availability"
    PREPARATION = "preparation_instructions"
    INFO = "insurance_general_info"
    ESCALATE = "escalate_to_human"
    UNKNOWN = "unknown"


class Status(str, Enum):
    COMPLETED = "completed"                      # action done / question answered
    NEEDS_CLARIFICATION = "needs_clarification"  # required details are missing
    NOT_POSSIBLE = "not_possible"                # understood, but cannot be done
    ESCALATED = "escalated"                      # handed to a human (ticket created)


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    # Assumption: in production this comes from the authenticated session,
    # not from the free-text message.
    patient_id: str | None = Field(default=None, pattern=r"^P\d{4}$")
    session_id: str | None = Field(default=None, max_length=64)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class AssistantResponse(BaseModel):
    request_id: str
    intent: Intent
    status: Status
    reply: str
    missing_fields: list[str] = Field(default_factory=list)
    data: dict[str, Any] | None = None
