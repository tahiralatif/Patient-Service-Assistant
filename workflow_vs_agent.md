# Workflow vs Agent (Part 11)

## Position
**Controlled workflow is preferable** for this healthcare appointment use case.

## Why Controlled Workflow Wins Here

### 1. Regulatory & Safety Requirements
- **Saudi PDPL / MOH guidelines**: Every action must be auditable, attributable, reversible
- **Medical liability**: "The AI said it was booked" is not a defense — confirmed tool output is
- **Current code**: `ok=True` ONLY after store returns; timeout → `tool_failure` → never claims success

### 2. Deterministic Behavior Required
| Scenario | Workflow | Agent |
|----------|----------|-------|
| Double-book attempt | Explicit `slot_unavailable` code | LLM might hallucinate "confirmed" |
| Timeout during reschedule | Proven `not_possible`, appointment unchanged | LLM might say "rescheduled" |
| Prompt injection | Rule-based NLU ignores it | Agent follows injected instruction |
| Audit trail | Every step logged with request_id | Opaque reasoning trace |

### 3. Testability & Reproducibility
- **38 unit tests + 15 evals** — all deterministic, run in CI in <2s
- Agent: flaky, non-deterministic, requires eval frameworks, human review

### 4. Scope Matches Workflow
The use case has **bounded, well-defined operations**:
1. Check availability (read)
2. Book (write + confirm)
3. Reschedule (read + verify + write + confirm)
4. Cancel (verify + write)
5. Answer from KB (retrieve + cite)

No open-ended reasoning, no tool discovery, no planning — just a fixed menu.

### 5. Escalation Is a Feature, Not Failure
- Unknown KB question → escalate with ticket (not guess)
- Emergency → escalate + emergency services notice
- Ambiguous intent → ask for clarification
This is **explicit control flow**, not "agent couldn't figure it out."

## When an Agent Would Be Appropriate
- Unbounded user goals ("Plan my healthcare journey")
- Dynamic tool discovery (new integrations weekly)
- Multi-step reasoning with unknown intermediate steps
- Negotiation / persuasion required

## Our Architecture Enables Future Agent Layer
The current design **does not prevent** adding an agent later:
- `nlu.classify()` + `nlu.extract_entities()` are the **only** LLM swap points
- Tools, workflow, grounding, store remain unchanged
- Feature flag can route: rule-based v1 vs LLM v2 (A/B test)

## Conclusion
For a **Saudi healthcare patient-service assistant** with:
- Regulatory audit requirements
- Safety-critical operations (appointments, emergencies)
- Bounded, well-defined scope
- Need for 100% reproducibility in tests

**Controlled workflow is the correct engineering choice.** An autonomous agent adds risk without value for this scope.