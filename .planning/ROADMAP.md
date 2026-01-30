# Roadmap: Agno + Keycycle Integration

## Overview

Transform HFS from a mock-powered demo into a real LLM-powered multi-agent negotiation system. Starting with Keycycle for key rotation, we build up Agno tools, convert triads to Agno Teams, add configurable model tiers with adaptive escalation, wire in observability, and finally remove the mock client to force real API usage.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Keycycle Foundation** - Multi-provider key rotation with TiDB persistence
- [x] **Phase 2: Agno Tools** - HFS-specific tools as Agno @tool decorators
- [x] **Phase 3: Agno Teams** - Triads implemented as Agno Teams with async execution
- [x] **Phase 4: Shared State** - Markdown-based coordination layer with async locking
- [ ] **Phase 5: Model Tiers** - Role-based model selection with adaptive escalation
- [ ] **Phase 6: Observability** - OpenTelemetry tracing and usage metrics
- [ ] **Phase 7: Cleanup** - Remove MockLLMClient, require real API keys

## Phase Details

### Phase 1: Keycycle Foundation
**Goal**: HFS can obtain rotating Agno models from Keycycle with usage tracked to TiDB
**Depends on**: Nothing (first phase)
**Requirements**: KEYC-01, KEYC-02
**Success Criteria** (what must be TRUE):
  1. MultiProviderWrapper.get_model() returns a working Agno model
  2. Key rotation occurs automatically when rate limits hit
  3. Usage statistics persist to TiDB after API calls
  4. All four providers (Cerebras, Groq, Gemini, OpenRouter) configured
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md - ProviderManager and model factory setup
- [x] 01-02-PLAN.md - Integration tests and verification

### Phase 2: Agno Tools
**Goal**: HFS operations available as Agno tools that agents can invoke
**Depends on**: Phase 1
**Requirements**: AGNO-02
**Success Criteria** (what must be TRUE):
  1. register_claim tool can register a section claim on the spec
  2. negotiate_response tool can respond with CONCEDE/REVISE/HOLD
  3. generate_code tool can produce code artifacts
  4. Tools validate inputs and return structured responses
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md - HFSToolkit with Pydantic validation and 5 tool methods

### Phase 3: Agno Teams
**Goal**: Triads execute as Agno Teams with 3 agent members and conversation history
**Depends on**: Phase 2
**Requirements**: AGNO-01, AGNO-03, AGNO-04
**Success Criteria** (what must be TRUE):
  1. HierarchicalTriad creates Team with orchestrator + 2 workers
  2. DialecticTriad creates Team with proposer + critic + synthesizer
  3. ConsensusTriad creates Team with 3 equal peers
  4. team.arun() executes triad operations asynchronously
  5. Conversation history preserved across deliberate/negotiate/execute phases
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md - Base infrastructure (AgnoTriad, schemas, error handling)
- [x] 03-02-PLAN.md - HierarchicalAgnoTriad with orchestrator-directed delegation
- [x] 03-03-PLAN.md - DialecticAgnoTriad with synthesizer summaries
- [x] 03-04-PLAN.md - ConsensusAgnoTriad with parallel dispatch

### Phase 4: Shared State
**Goal**: Markdown-based coordination layer enabling multi-agent collaboration with async locking
**Depends on**: Phase 3
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. Markdown state files created/updated by tools
  2. Read tools return current state without locks
  3. Write tools queue edits and resolve in order
  4. IP markers prevent duplicate work across agents
  5. Agents can query "what's available" vs "what's claimed"
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md - Core state infrastructure (SharedStateManager, schemas, parser)
- [x] 04-02-PLAN.md - SharedStateToolkit with 4 tools and unit tests

### Phase 5: Model Tiers
**Goal**: Model selection driven by role, phase, and failure-adaptive escalation
**Depends on**: Phase 4
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04
**Success Criteria** (what must be TRUE):
  1. YAML config specifies model tiers per role (orchestrator, worker, arbiter)
  2. Phase-specific model overrides work (execution phase can use different tier)
  3. Code execution always uses Cerebras GLM-4.7 or OSS-120b
  4. Failed executions over time causes self-improvement to shift to better models
**Plans**: 6 plans

Plans:
- [x] 05-01-PLAN.md - Pydantic config models and YAML tier schema
- [x] 05-02-PLAN.md - ModelSelector with tier resolution and provider fallback
- [x] 05-03-PLAN.md - EscalationTracker with permanent config updates
- [x] 05-04-PLAN.md - Wire ModelSelector/EscalationTracker into AgnoTriad base class (gap closure)
- [x] 05-05-PLAN.md - Update AgnoTriad subclasses to use ModelSelector (gap closure)
- [ ] 05-06-PLAN.md - Wire ModelSelector/EscalationTracker into HFSOrchestrator (gap closure)

### Phase 6: Observability
**Goal**: Full visibility into agent runs, token usage, and phase timing
**Depends on**: Phase 5
**Requirements**: OBSV-01, OBSV-02, OBSV-03
**Success Criteria** (what must be TRUE):
  1. OpenTelemetry tracing captures agent runs and tool executions
  2. Token usage tracked and reported per agent, phase, and run
  3. Phase timing metrics captured for all 9 HFS pipeline phases
  4. Trace data viewable via configured backend (TiDB or file)
**Plans**: TBD

Plans:
- [ ] 06-01: OpenTelemetry tracing setup
- [ ] 06-02: Token and timing metrics

### Phase 7: Cleanup
**Goal**: MockLLMClient removed, HFS requires real API keys to run
**Depends on**: Phase 6
**Requirements**: CLEN-01
**Success Criteria** (what must be TRUE):
  1. MockLLMClient class deleted from codebase
  2. HFS CLI fails gracefully with clear error when API keys missing
  3. All tests either use real APIs or are marked as integration tests
**Plans**: TBD

Plans:
- [ ] 07-01: Remove MockLLMClient and update CLI

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Keycycle Foundation | 2/2 | Complete | 2026-01-29 |
| 2. Agno Tools | 1/1 | Complete | 2026-01-29 |
| 3. Agno Teams | 4/4 | Complete | 2026-01-29 |
| 4. Shared State | 2/2 | Complete | 2026-01-30 |
| 5. Model Tiers | 5/6 | In progress | - |
| 6. Observability | 0/2 | Not started | - |
| 7. Cleanup | 0/1 | Not started | - |
