# Requirements: Agno + Keycycle Integration

**Defined:** 2026-01-29
**Core Value:** Real LLM-powered multi-agent negotiation with automatic key rotation and failure-adaptive model escalation

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Agno Integration

- [ ] **AGNO-01**: Each HFS triad is implemented as an Agno Team with 3 agent members
- [x] **AGNO-02**: HFS-specific tools defined as Agno @tool decorators (register_claim, negotiate_response, generate_code)
- [ ] **AGNO-03**: Triad operations use async execution via team.arun()
- [ ] **AGNO-04**: Agent conversation history preserved via add_history_to_context=True

### Keycycle Integration

- [x] **KEYC-01**: MultiProviderWrapper configured for Cerebras (51 keys), Groq (16), Gemini (110), OpenRouter (31)
- [x] **KEYC-02**: Usage statistics persisted to TiDB via TIDB_DB_URL

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
| KEYC-01 | Phase 1 | Complete |
| KEYC-02 | Phase 1 | Complete |
| AGNO-02 | Phase 2 | Complete |
| AGNO-01 | Phase 3 | Pending |
| AGNO-03 | Phase 3 | Pending |
| AGNO-04 | Phase 3 | Pending |
| MODL-01 | Phase 4 | Pending |
| MODL-02 | Phase 4 | Pending |
| MODL-03 | Phase 4 | Pending |
| MODL-04 | Phase 4 | Pending |
| OBSV-01 | Phase 5 | Pending |
| OBSV-02 | Phase 5 | Pending |
| OBSV-03 | Phase 5 | Pending |
| CLEN-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 after roadmap creation*
