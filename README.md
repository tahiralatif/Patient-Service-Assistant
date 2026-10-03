# Patient Service Assistant — Apex AI Arabia Assessment

FastAPI backend for a Saudi healthcare patient-service assistant. Answers trusted questions from a knowledge base and safely executes appointment operations.

## Quick Start

```bash
# Local (uv)
uv sync --frozen
uv run uvicorn main:app --reload

# Docker
docker build -t apex-assistant .
docker run -p 8000:8000 apex-assistant
```

## API

- `GET /health` → `{"status":"ok"}`
- `POST /assistant/message`

```json
{
  "message": "Book cardiology on 2026-10-07 at 10:00",
  "patient_id": "P1001",
  "session_id": "optional-for-reschedule"
}
```

Response:
```json
{
  "request_id": "abc123",
  "intent": "book_appointment",
  "status": "completed",
  "reply": "Your cardiology appointment is confirmed: APT-1003 on 2026-10-07 at 10:00.",
  "missing_fields": [],
  "data": {"appointment": {...}}
}
```

## Intents Supported

| Intent | Description |
|--------|-------------|
| `book_appointment` | Book new appointment (needs patient_id, specialty, date, time) |
| `reschedule_appointment` | Multi-step: clarify → verify → check slot → **confirm** → execute |
| `cancel_appointment` | Cancel own appointment (needs patient_id, appointment_id) |
| `check_availability` | List open slots for specialty/date |
| `preparation_instructions` | KB-backed prep instructions per specialty |
| `insurance_general_info` | KB-backed insurance/hours questions |
| `escalate_to_human` | Emergency or unknown → human ticket |

## Run Tests

```bash
# Unit tests (38)
uv run pytest -v

# Evaluation cases (15, Part 6)
uv run python -m evals.run_evals
```

## Project Structure

```
app/
  nlu.py           # Rule-based intent classification + entity extraction
  kb.py            # Loads knowledge/*.md with frontmatter
  retrieval.py     # TF-IDF retriever (coverage ≥ 0.5, top 3)
  grounding.py     # Citation enforcement: answer_from_kb() + ground()
  store.py         # In-memory mock clinic scheduler
  tools/tools.py   # 6 validated tools (input validation + _guarded errors)
  workflow.py      # Multi-step reschedule flow (session-based)
  handlers.py      # Intent handlers → tools/KB
  schemas.py       # Pydantic request/response contracts
main.py            # FastAPI entrypoint
evals/run_evals.py # 15 evaluation cases (Part 6)
tests/             # 38 unit tests
knowledge/         # 4 markdown docs (insurance, hours, cancellation, prep)
```

## Key Design Decisions

- **Controlled workflow** (not autonomous agent) — Part 11 requirement
- **Tools** — every action goes through `tools.py`; `ok=True` only after store confirms
- **Grounding** — KB answers must cite retrieved chunks; invented sources rejected
- **Safety** — emergencies escalate immediately; timeout → `tool_failure` (never claims success)
- **Privacy** — no PII in logs; patient_id from auth context, not free text

## Assessment Deliverables

| Part | File |
|------|------|
| 6 | `evals/run_evals.py` + `evals/RESULTS.md` |
| 8 | `Dockerfile` + this README |
| 9 | `model_cost_comparison.md` |
| 10 | `production_architecture.md` |
| 11 | `workflow_vs_agent.md` |
| 12 | `debugging_case.md` |
| 13 | `business_communication.md` |
| Final | `assessment_summary.md`, `assumptions.md`, `ai_tools_disclosure.md` |