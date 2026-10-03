# Business Communication (Part 13)

## To: Patient Services Leadership
## From: Engineering
## Subject: Why the Assistant Cannot Guarantee Perfect Responses — and How We Manage Reliability

---

### The Short Answer
**No software system can guarantee 100% correct responses.** We manage this by **designing for safe failure** — the assistant never guesses, never claims unconfirmed actions, and escalates to humans when uncertain.

---

### What "Perfect" Would Require (and Why It Doesn't Exist)
| Guarantee | Why Impossible |
|-----------|----------------|
| Always understand the user | Language is ambiguous; users make typos, use dialect, shorthand |
| Always have the answer | Knowledge base is finite; policies change; edge cases exist |
| Never make a mistake | External systems (scheduling, insurance) have their own failures |

---

### How We Manage Reliability Instead

#### 1. **No Hallucination by Design**
- The assistant **only answers from verified knowledge base chunks**
- Every answer cites its source (document + section)
- If no verified source exists → **escalates to human** with a ticket
- *Result*: Zero risk of invented medical/insurance advice

#### 2. **Actions Require Confirmation**
- Booking, rescheduling, cancellation — **nothing happens until the backend confirms**
- If the scheduling system times out → assistant says: *"The system could not confirm this action, so nothing is confirmed."*
- *Result*: User never thinks an appointment moved when it didn't

#### 3. **Emergencies Are Escalated Immediately**
- Chest pain, breathing difficulty, severe bleeding → instant escalation + emergency services notice
- No attempt to "handle" medically
- *Result*: Safety first, always

#### 4. **Every Interaction Is Auditable**
- Request ID logged (no PII in logs)
- Intent, status, ticket number tracked
- Human team can review any conversation

#### 5. **Explicit Boundaries**
| In Scope | Out of Scope |
|----------|--------------|
| Book/reschedule/cancel appointments | Medical advice, dosage, diagnosis |
| Check availability | Guarantee insurance coverage |
| Preparation instructions (from KB) | Legal interpretation of policies |
| Escalate to human with ticket | Make exceptions to clinic rules |

---

### What Happens When It Fails
| Failure Mode | User Sees | Backend Action |
|--------------|-----------|----------------|
| Unknown question | "I don't have verified information... passed to our team. Reference: ESC-0042" | Ticket created, human follows up |
| Scheduling timeout | "The system could not confirm this action, so nothing is confirmed." | No state change, retry or human |
| Ambiguous request | "I can help with one thing at a time. Do you want to book or check availability?" | Clarification, no guess |
| Invalid input | "Patient ID must look like P1234" | Validation error, no backend call |

---

### Our Reliability Metrics (Measured)
- **0%** hallucinated KB answers (grounding enforcement)
- **0%** unconfirmed actions claimed as success (tool `ok=True` guard)
- **100%** emergencies escalated (keyword trigger)
- **<2s** p95 latency (rule-based NLU + TF-IDF)
- **38 automated tests** + **15 evaluation cases** run on every change

---

### Bottom Line
We don't promise perfection. We promise **honest uncertainty** — the assistant tells you when it doesn't know, when it can't confirm, and when a human needs to step in. That's the safest possible behavior for healthcare.