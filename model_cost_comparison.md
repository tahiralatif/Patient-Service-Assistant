# Model / Cost Comparison (Part 9)

## Scenario
100,000 interactions/month — each interaction = 1 user message + 1 assistant reply.

## Models Compared

| Model | Provider | Context | Cost (1M tokens) | Est. tokens/interaction | Monthly Cost | Latency (p50) |
|-------|----------|---------|------------------|------------------------|--------------|---------------|
| **Llama-3.1-70B** | Groq | 128K | $0.59 input / $0.79 output | ~800 | **~$110** | ~200ms |
| **GPT-4o-mini** | OpenAI | 128K | $0.15 input / $0.60 output | ~800 | **~$60** | ~500ms |

## Calculation (100K interactions/month)

**Llama-3.1-70B (Groq)**
- Input: 100K × 400 tokens = 40M tokens → $23.60
- Output: 100K × 400 tokens = 40M tokens → $31.60
- **Total: ~$55/month** (Groq often has free tier; listed pricing for comparison)

**GPT-4o-mini (OpenAI)**
- Input: 100K × 400 tokens = 40M tokens → $6.00
- Output: 100K × 400 tokens = 40M tokens → $24.00
- **Total: ~$30/month**

## Why These Two
- **Groq Llama-3.1-70B**: Best-in-class speed (LPU inference), deterministic enough for structured output, Arabic support
- **GPT-4o-mini**: Lowest cost for reasonable quality, strong function calling, enterprise SLA

## Current Architecture (Zero LLM Cost)
- **NLU**: Rule-based (regex/keywords) — $0, <5ms, 100% deterministic
- **Retrieval**: TF-IDF — $0, <10ms
- **Grounding**: Deterministic citation check — $0
- **Total inference cost: $0/month**

## When to Add LLM
| Trigger | Recommended Model |
|---------|-------------------|
| NLU intent coverage < 90% | Llama-3.1-70B (speed) or GPT-4o-mini (cost) |
| Multi-turn reasoning needed | GPT-4o-mini (better reasoning) |
| Arabic dialect handling | Llama-3.1-70B (better Arabic) |

## Recommendation
**Keep rule-based NLU for Part 1-4 scope.** Add LLM only when:
1. Intent coverage gap measured > 10%
2. Cost budget approved ($30-55/mo)
3. Latency SLA allows 200-500ms extra

The current architecture has a clean seam: replace `nlu.classify()` + `nlu.extract_entities()` only.