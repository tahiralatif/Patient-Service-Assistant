# Production Architecture (Part 10)

## Current Take-Home Architecture

```mermaid
graph TD
    Client[Client] --> API[FastAPI /assistant/message]
    API --> NLU[NLU: classify + extract_entities]
    NLU --> Handlers[handlers.py]
    Handlers --> Tools[tools.py]
    Handlers --> KB[retrieval.py + grounding.py]
    Tools --> Store[(In-Memory Store)]
    KB --> Chunks[(Knowledge Chunks)]
    Store --> Response[AssistantResponse]
    KB --> Response
```

## Production Architecture

```mermaid
graph TD
    Client[Client App] --> Gateway[API Gateway / Kong]
    Gateway --> Auth[Auth Service\nValidate JWT\nExtract patient_id]
    Auth --> API[FastAPI Pods xN]
    API --> NLU[NLU Service\nRule-based v1\nLLM v2 behind flag]
    NLU --> Orchestrator[Workflow Orchestrator\nTemporal / custom]
    Orchestrator --> Tools[Tool Layer\nTimeouts, Retries, Idempotency]
    Tools --> DB[(PostgreSQL\nAppointments, Slots, Patients)]
    Tools --> Cache[(Redis\nAvailability Cache)]
    Tools --> Queue[Async Queue\nEscalations, Notifications]
    Orchestrator --> KB[KB Service\nVector Search + Grounding]
    KB --> VectorDB[(pgvector / Qdrant)]
    KB --> ObjectStore[(S3\nMarkdown Source)]
    API --> Metrics[Prometheus + Grafana]
    API --> Logs[Loki / ELK]
    API --> Traces[Jaeger]
```

## What Changes from Take-Home

| Layer | Take-Home | Production |
|-------|-----------|------------|
| **Auth** | `patient_id` in request body | JWT validation, session management, RBAC |
| **Store** | In-memory dict | PostgreSQL + row-level security, advisory locks for concurrency |
| **Availability** | Computed on-demand | Materialized view + Redis cache (TTL 30s) |
| **Tools** | Sync functions | Async with timeouts (5s), retries (3x), idempotency keys |
| **Workflow** | In-memory `_FLOWS` dict | Temporal / durable execution (survives restarts) |
| **KB** | TF-IDF on chunks | Hybrid: BM25 + embeddings (bge-m3), reranker, grounding v2 |
| **NLU** | Rule-based only | Rule-based v1 + LLM v2 behind feature flag, A/B test |
| **Observability** | `logging.info` | Structured logs, metrics, traces, alerts |
| **Deployment** | Single container | K8s: HPA, PodDisruptionBudget, blue/green |
| **Secrets** | None | Vault / SealedSecrets, rotation |
| **Compliance** | None | PDPL (Saudi), audit logs, data residency (KSA region) |

## Saudi-Specific Considerations

- **Data residency**: All PHI in KSA region (STC, AWS Bahrah, Azure KSA, Google Dammam)
- **PDPL compliance**: Consent, purpose limitation, retention policy, DPO appointed
- **Language**: Arabic-first UI; NLU must handle Najdi, Hejazi, Gulf dialects
- **Calendar**: Hijri date support alongside Gregorian
- **Prayer times**: Slot availability excludes prayer windows
- **Gender segregation**: Specialty/doctor assignment rules

## Migration Path

1. **Phase 1** (Week 1-2): PostgreSQL + Redis + auth + observability
2. **Phase 2** (Week 3-4): Tool layer with timeouts/retries + idempotency
3. **Phase 3** (Week 5-6): Durable workflow engine (Temporal)
4. **Phase 4** (Week 7-8): Vector KB + hybrid retrieval + LLM NLU behind flag
5. **Phase 5** (Week 9-10): Load test, chaos engineering, compliance audit