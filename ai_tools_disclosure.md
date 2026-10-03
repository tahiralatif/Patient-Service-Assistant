# AI Tools Disclosure

## Tools Used
| Tool | Purpose | What It Accelerated | What I Verified Independently |
|------|---------|---------------------|-------------------------------|
| **GitHub Copilot** | Code completion, boilerplate | FastAPI routes, Pydantic models, test scaffolding, regex patterns | All business logic, error handling, security decisions |
| **ChatGPT (GPT-4o)** | Design discussion, markdown drafting | Architecture diagrams (mermaid), deliverable templates, wording | All technical decisions, code correctness, test design |
| **Claude (Sonnet)** | Code review, edge case analysis | Bug pattern recognition (timeout handling), test coverage gaps | All fixes, production architecture tradeoffs |

## What AI Did NOT Do
- ❌ Choose the architecture (controlled workflow vs agent) — **my judgment per Part 11**
- ❌ Design the grounding/citation enforcement — **my design to prevent hallucination**
- ❌ Define the tool contract (`ok=True` only after store confirms) — **my safety requirement**
- ❌ Write the evaluation cases — **my test design based on assessment requirements**
- ❌ Decide on TF-IDF vs embeddings — **my call for scope/simplicity**
- ❌ Create the multi-step workflow state machine — **my design for confirmation gate**

## Human Judgments (Material Decisions)
1. **Controlled workflow over autonomous agent** — assessed against Part 11, regulatory needs, testability
2. **Tool layer with `_guarded` converting all exceptions to `tool_failure`** — safety-first, proven by tests
3. **Grounding via citation verification** — not LLM judge, deterministic, zero hallucination
4. **Rule-based NLU as default** — deterministic, testable, swappable; LLM only when coverage gap measured
5. **In-memory store for take-home** — explicit assumption; production design documented separately
6. **15 evaluation cases** — designed to exceed Part 6 minimum, cover all guardrails
7. **Docker multi-stage with uv** — reproducible, fast, non-root

## Verification Process
- All AI-suggested code **read, understood, and modified** before commit
- All tests **written by me** to encode expected behavior
- All deliverables **drafted by me**, AI used only for formatting/wording
- Live defense preparation: **I can explain every line** without AI assistance

## Compliance
- No confidential data shared with AI tools
- No fabricated sources, metrics, or claims
- All code is original or adapted from my own prior patterns