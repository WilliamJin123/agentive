# Roadmap: Agno + Keycycle Integration

## Overview

Transform HFS from a mock-powered demo into a real LLM-powered multi-agent negotiation system. Starting with Keycycle for key rotation, we build up Agno tools, convert triads to Agno Teams, add configurable model tiers with adaptive escalation, wire in observability, and finally remove the mock client to force real API usage.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Keycycle Foundation** - Multi-provider key rotation with TiDB persistence
- [ ] **Phase 2: Agno Tools** - HFS-specific tools as Agno @tool decorators
- [ ] **Phase 3: Agno Teams** - Triads implemented as Agno Teams with async execution
- [ ] **Phase 4: Model Tiers** - Role-based model selection with adaptive escalation
- [ ] **Phase 5: Observability** - OpenTelemetry tracing and usage metrics
- [ ] **Phase 6: Cleanup** - Remove MockLLMClient, require real API keys

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
**Plans**: TBD

Plans:
- [ ] 01-01: Multi-provider wrapper setup
- [ ] 01-02: TiDB persistence integration

### Phase 2: Agno Tools
**Goal**: HFS operations available as Agno tools that agents can invoke
**Depends on**: Phase 1
**Requirements**: AGNO-02
**Success Criteria** (what must be TRUE):
  1. register_claim tool can register a section claim on the spec
  2. negotiate_response tool can respond with CONCEDE/REVISE/HOLD
  3. generate_code tool can produce code artifacts
  4. Tools validate inputs and return structured responses
**Plans**: TBD

Plans:
- [ ] 02-01: Define HFS tools with @tool decorators

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
**Plans**: TBD

Plans:
- [ ] 03-01: Hierarchical triad as Agno Team
- [ ] 03-02: Dialectic triad as Agno Team
- [ ] 03-03: Consensus triad as Agno Team
- [ ] 03-04: Orchestrator integration with Agno triads

### Phase 4: Model Tiers
**Goal**: Model selection driven by role, phase, and failure-adaptive escalation
**Depends on**: Phase 3
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04
**Success Criteria** (what must be TRUE):
  1. YAML config specifies model tiers per role (orchestrator, worker, arbiter)
  2. Phase-specific model overrides work (execution phase can use different tier)
  3. Code execution always uses Cerebras GLM-4.7 or OSS-120b
  4. Failed execution automatically escalates to better model tier
**Plans**: TBD

Plans:
- [ ] 04-01: YAML model tier configuration
- [ ] 04-02: Phase-based model selection
- [ ] 04-03: Adaptive escalation on failure

### Phase 5: Observability
**Goal**: Full visibility into agent runs, token usage, and phase timing
**Depends on**: Phase 4
**Requirements**: OBSV-01, OBSV-02, OBSV-03
**Success Criteria** (what must be TRUE):
  1. OpenTelemetry tracing captures agent runs and tool executions
  2. Token usage tracked and reported per agent, phase, and run
  3. Phase timing metrics captured for all 9 HFS pipeline phases
  4. Trace data viewable via configured backend (TiDB or file)
**Plans**: TBD

Plans:
- [ ] 05-01: OpenTelemetry tracing setup
- [ ] 05-02: Token and timing metrics

### Phase 6: Cleanup
**Goal**: MockLLMClient removed, HFS requires real API keys to run
**Depends on**: Phase 5
**Requirements**: CLEN-01
**Success Criteria** (what must be TRUE):
  1. MockLLMClient class deleted from codebase
  2. HFS CLI fails gracefully with clear error when API keys missing
  3. All tests either use real APIs or are marked as integration tests
**Plans**: TBD

Plans:
- [ ] 06-01: Remove MockLLMClient and update CLI

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Keycycle Foundation | 0/2 | Not started | - |
| 2. Agno Tools | 0/1 | Not started | - |
| 3. Agno Teams | 0/4 | Not started | - |
| 4. Model Tiers | 0/3 | Not started | - |
| 5. Observability | 0/2 | Not started | - |
| 6. Cleanup | 0/1 | Not started | - |
