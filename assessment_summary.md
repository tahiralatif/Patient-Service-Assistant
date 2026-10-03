# What Works, What Does Not, What I Would Build Next

## What Works

### Core Implementation (Parts 1-5)
- **POST `/assistant/message`** — FastAPI endpoint with Pydantic validation, 7 intents supported
- **Rule-based NLU** — deterministic, no API key, swappable for LLM (`nlu.classify` + `nlu.extract_entities`)
- **Knowledge Base** — 4 markdown docs with frontmatter, split into 8+ chunks with metadata (doc_id, section, owner, last_reviewed)
- **TF-IDF Retrieval** — coverage threshold (0.5), top-3, finds right sections, returns empty for unknown topics
- **Grounding** — `answer_from_kb()` returns chunk text verbatim; `ground()` verifies citations ⊆ retrieved; invented sources rejected
- **Tool Layer** — 6 validated tools (`book_appointment`, `reschedule_appointment`, `cancel_appointment`, `check_availability`, `lookup_appointment`, `escalate_to_human`); `_guarded` wrapper converts **any** exception to `ok=False, code=tool_failure`
- **Multi-step Workflow** — reschedule: clarify → verify ownership → check slot → **confirm** → execute; in-memory per `session_id`; emergency exits flow
- **Safety** — emergencies escalate instantly; unknown KB → escalate; timeout → never claims success; no PII in logs; patient_id from auth context

### Testing & Evaluation (Parts 6-7)
- **38 unit tests** — all pass, cover happy paths, failures, guardrails, timeout safety
- **15 evaluation cases** (exceeds 12 required) — all pass, cover booking, double-book, closed day, missing fields, ownership, confirmation gate, timeout, KB answer, unknown KB, prompt injection, medical advice, emergency, invalid ID, ambiguous intent
- **Docker** — multi-stage build with uv, non-root user, healthcheck-ready

---

## What Does Not Work / Known Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **In-memory store** | Not scalable, no persistence, race conditions on concurrent booking | Replace with PostgreSQL + advisory locks (see Production Architecture) |
| **In-memory workflow state** (`_FLOWS` dict) | Lost on restart, no TTL cleanup, single-process only | Durable workflow engine (Temporal) or Redis + TTL |
| **TF-IDF retrieval** | No semantic understanding; misses paraphrases, Arabic dialect variations | Hybrid BM25 + embeddings (bge-m3) + reranker |
| **Rule-based NLU** | Limited coverage for paraphrases, typos, Arabic dialects | LLM-based NLU behind feature flag (clean seam at `nlu.classify`/`extract_entities`) |
| **No auth integration** | `patient_id` passed in request body | JWT validation, session management, RBAC |
| **No observability** | Only basic logging | Structured logs, metrics (Prometheus), traces (Jaeger), alerts |
| **No rate limiting / abuse protection** | Vulnerable to spam, DoS | API Gateway (Kong) + rate limits |
| **Python 3.14 in pyproject.toml** | Doesn't exist yet | Change to `>=3.11` |
| **Test isolation** | `test_part1_smoke.py` leaks `_FLOWS` | Add `tests/conftest.py` with autouse fixture |
| **No CI/CD** | Manual test/run | GitHub Actions: lint, typecheck, test, build, deploy |

---

## What I Would Build Next (Priority Order)

### 1. Production Hardening (Weeks 1-3)
- PostgreSQL + Redis + advisory locks for concurrency
- JWT auth + session management
- Temporal workflow engine (durable `_FLOWS`)
- Structured observability (logs, metrics, traces)
- Rate limiting, API Gateway
- CI/CD pipeline

### 2. KB v2 — Semantic Search (Weeks 3-5)
- Embeddings (bge-m3 for Arabic/English)
- Hybrid retrieval: BM25 + vector + cross-encoder reranker
- Chunking strategy optimization (overlap, size)
- Evaluation harness: retrieval recall@k, grounding precision

### 3. LLM NLU Behind Flag (Weeks 5-7)
- Swap `nlu.classify`/`extract_entities` only
- Few-shot prompt with intent definitions + examples
- Structured output (Pydantic) for entities
- A/B test: rule-based vs LLM on intent F1, entity F1, latency
- Fallback to rule-based on LLM failure

### 4. Arabic-First Enhancements (Weeks 7-9)
- Hijri calendar support
- Prayer-time slot blocking
- Dialect-aware NLU (Najdi, Hejazi, Gulf)
- Gender-segregation rules for specialty assignment

### 5. Compliance & Audit (Weeks 9-10)
- PDPL compliance: consent, retention, DPO, data residency (KSA region)
- Immutable audit log for every appointment action
- Penetration testing, chaos engineering
- MOH/SFDA alignment review

---

## Highest-Risk Uncovered Behavior
**Concurrent booking race condition** — two requests for same slot simultaneously both pass availability check, both proceed to book. In-memory store has no locking. Fix: PostgreSQL `SELECT ... FOR UPDATE` or advisory lock in tool layer.