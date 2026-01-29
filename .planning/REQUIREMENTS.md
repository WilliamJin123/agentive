# Requirements: Agno + Keycycle Integration

**Defined:** 2026-01-29
**Core Value:** Real LLM-powered multi-agent negotiation with automatic key rotation and failure-adaptive model escalation

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Agno Integration

- [ ] **AGNO-01**: Each HFS triad is implemented as an Agno Team with 3 agent members
- [ ] **AGNO-02**: HFS-specific tools defined as Agno @tool decorators (register_claim, negotiate_response, generate_code)
- [ ] **AGNO-03**: Triad operations use async execution via team.arun()
- [ ] **AGNO-04**: Agent conversation history preserved via add_history_to_context=True

### Keycycle Integration

- [ ] **KEYC-01**: MultiProviderWrapper configured for Cerebras (51 keys), Groq (16), Gemini (110), OpenRouter (31)
- [ ] **KEYC-02**: Usage statistics persisted to TiDB via TIDB_DB_URL

### Model Configuration

- [ ] **MODL-01**: Role-based model tiers configurable in YAML (orchestrator, worker, arbiter defaults)
- [ ] **MODL-02**: Phase-based model selection (deliberation, negotiation, execution can use different tiers)
- [ ] **MODL-03**: Code execution always uses high-quality models (GLM-4.7, OSS-120b via Cerebras)
- [ ] **MODL-04**: Adaptive model escalation when execution fails (auto-upgrade to better tier)

### Observability

- [ ] **OBSV-01**: OpenTelemetry tracing integrated for agent runs and tool executions
- [ ] **OBSV-02**: Token usage tracked per agent, phase, and run
- [ ] **OBSV-03**: Phase timing metrics captured for HFS pipeline phases

### Cleanup

- [ ] **CLEN-01**: MockLLMClient removed entirely (no fallback, require real API keys)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Features

- **ADVN-01**: Provider fallback (switch providers when one exhausted)
- **ADVN-02**: Learning mode for agent improvement over time
- **ADVN-03**: Session persistence across HFS runs
- **ADVN-04**: Trace data persisted to TiDB (not just usage stats)

### Scaling

- **SCAL-01**: Parallel triad execution within phases
- **SCAL-02**: Distributed triad execution across workers

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Human-in-the-loop approval | Not needed for v1, adds latency |
| Web/mobile UI | CLI-only for now, UI is separate project |
| Custom model fine-tuning | Out of scope, use existing models |
| Real-time streaming responses | Batch mode sufficient for triad operations |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGNO-01 | TBD | Pending |
| AGNO-02 | TBD | Pending |
| AGNO-03 | TBD | Pending |
| AGNO-04 | TBD | Pending |
| KEYC-01 | TBD | Pending |
| KEYC-02 | TBD | Pending |
| MODL-01 | TBD | Pending |
| MODL-02 | TBD | Pending |
| MODL-03 | TBD | Pending |
| MODL-04 | TBD | Pending |
| OBSV-01 | TBD | Pending |
| OBSV-02 | TBD | Pending |
| OBSV-03 | TBD | Pending |
| CLEN-01 | TBD | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 0
- Unmapped: 14 ⚠️

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 after initial definition*
