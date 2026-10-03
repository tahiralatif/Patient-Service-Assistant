# """FastAPI entrypoint: POST /assistant/message."""
# import logging
# import uuid
# from functools import lru_cache

# from fastapi import Depends, FastAPI

# from app.handlers import handle
# from app.nlu import classify, extract_entities
# from app.schemas import AssistantRequest, AssistantResponse
# from app.store import AppointmentStore

# logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# logger = logging.getLogger("assistant")

# app = FastAPI(title="Patient Service Assistant", version="0.1.0")


# @lru_cache
# def get_store() -> AppointmentStore:
#     return AppointmentStore()


# @app.get("/health")
# def health() -> dict:
#     return {"status": "ok"}


# @app.post("/assistant/message", response_model=AssistantResponse)
# def assistant_message(
#     req: AssistantRequest, store: AppointmentStore = Depends(get_store)
# ) -> AssistantResponse:
#     request_id = uuid.uuid4().hex[:12]
#     intent, candidates = classify(req.message)
#     entities = extract_entities(req.message, req.patient_id)
#     result = handle(intent, candidates, entities, req.message, store)

#     # Log metadata only: message text can contain personal health information.
#     logger.info("request_id=%s intent=%s status=%s", request_id, intent.value, result.status.value)

#     return AssistantResponse(
#         request_id=request_id,
#         intent=intent,
#         status=result.status,
#         reply=result.reply,
#         missing_fields=result.missing_fields,
#         data=result.data,
#     )


"""FastAPI entrypoint: POST /assistant/message."""
import logging
import uuid
from functools import lru_cache

from fastapi import Depends, FastAPI

from app import workflow
from app.handlers import Result, handle
from app.nlu import classify, extract_entities, is_emergency
from app.schemas import AssistantRequest, AssistantResponse, Intent, Status
from app.store import AppointmentStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("assistant")

app = FastAPI(title="Patient Service Assistant", version="0.1.0")


@lru_cache
def get_store() -> AppointmentStore:
    return AppointmentStore()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/assistant/message", response_model=AssistantResponse)
def assistant_message(
    req: AssistantRequest, store: AppointmentStore = Depends(get_store)
) -> AssistantResponse:
    request_id = uuid.uuid4().hex[:12]
    intent, candidates = classify(req.message)
    entities = extract_entities(req.message, req.patient_id)
    sid = req.session_id

    # An emergency always leaves any running workflow and goes to escalation.
    if sid and is_emergency(req.message):
        workflow.reset(sid)
        intent = Intent.ESCALATE

    if sid and workflow.is_active(sid):
        # Mid-conversation: "yes" or "2026-10-05" is not classifiable on its own.
        intent = Intent.RESCHEDULE
        result = workflow.step(sid, entities, req.message, store)
    elif intent is Intent.RESCHEDULE:
        if not sid:
            result = Result(
                Status.NEEDS_CLARIFICATION,
                "To reschedule step by step I need a session_id so I can remember "
                "our conversation. Please send one with your next message.",
                missing_fields=["session_id"],
            )
        else:
            result = workflow.step(sid, entities, req.message, store)
    else:
        result = handle(intent, candidates, entities, req.message, store)

    # Log metadata only: message text can contain personal health information.
    logger.info("request_id=%s intent=%s status=%s", request_id, intent.value, result.status.value)

    return AssistantResponse(
        request_id=request_id,
        intent=intent,
        status=result.status,
        reply=result.reply,
        missing_fields=result.missing_fields,
        data=result.data,
    )