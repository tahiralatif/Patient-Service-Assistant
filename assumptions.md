# Assumptions (Explicit)

## Clinic Operations
1. **Operating days**: Sunday–Thursday (Friday/Saturday closed)
2. **Slot times**: 09:00, 10:00, 11:00, 14:00, 15:00 (fixed, no configuration)
3. **One doctor per specialty** → one appointment per specialty/date/time
4. **Specialties**: cardiology, dermatology, general practice (fixed list)
5. **Booking window**: tomorrow to 14 days ahead (not today, not past)
6. **Patient ID format**: `P` + 4 digits (e.g., P1001)
7. **Appointment ID format**: `APT-` + 4 digits (e.g., APT-1001)

## Data & Privacy
8. **No real PHI** — all data is synthetic/sample
9. **Patient ID comes from authenticated session** — not from free-text message (extraction is fallback only)
10. **Logs contain no PII** — only request_id, intent, status
11. **Escalation tickets store reason code only** — never raw user message

## Knowledge Base
12. **KB is the single source of truth** for preparation, insurance, hours, cancellation
13. **Preparation instructions are general** — doctor-specific overrides not modeled
14. **Insurance acceptance cannot be confirmed** — assistant never says "we accept X insurer"
15. **KB documents have frontmatter** with `doc_id`, `title`, `owner`, `last_reviewed`, `searchable`

## Technical
16. **Single-process, in-memory** — no horizontal scaling, no persistence
17. **Server date = `date.today()`** — production should use Asia/Riyadh timezone
18. **No authentication** — `patient_id` and `session_id` accepted from request body
19. **No rate limiting, no quotas** — assessment scope only
20. **Rule-based NLU is sufficient for scope** — LLM not required for 7 intents
21. **TF-IDF retrieval is sufficient for 4 small docs** — no vector DB needed
22. **Grounding = citation enforcement** — no LLM judge, no semantic similarity threshold

## Evaluation
23. **15 evaluation cases cover critical paths** — not exhaustive, but representative
24. **Timeout simulated by monkey-patching store** — real timeout handling needs infrastructure
25. **Prompt injection tested via adversarial message** — not a full red-team exercise

## Out of Scope (Would Need Validation)
- Saudi PDPL / MOH / SFDA regulatory compliance
- Real insurance integration (eligibility, pre-auth)
- Multi-clinic, multi-doctor scheduling
- Patient portal / mobile app
- WhatsApp / voice channel integration
- Hijri calendar, prayer times, gender segregation
- Arabic dialect NLU
- Disaster recovery, backup, HA