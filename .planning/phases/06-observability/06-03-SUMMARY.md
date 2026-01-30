---
phase: 06
plan: 03
subsystem: observability
tags: [opentelemetry, tracing, metrics, tokens]

dependency-graph:
  requires:
    - "06-01 (tracing/metrics foundation)"
    - "06-02 (orchestrator spans)"
  provides:
    - "triad-level span instrumentation"
    - "agent-level span helper"
    - "token usage recording"
    - "4-level span hierarchy complete"
  affects:
    - "future: cost tracking dashboard"
    - "future: performance debugging"

tech-stack:
  added: []
  patterns:
    - "lazy tracer/meter initialization"
    - "context manager for agent spans"
    - "token extraction from LLM responses"

file-tracking:
  key-files:
    created:
      - hfs/tests/test_observability_agents.py
    modified:
      - hfs/agno/teams/base.py

decisions:
  - id: "lazy-init-pattern"
    choice: "module-level lazy initialization for tracer/meter"
    rationale: "Consistent with 06-02 orchestrator pattern, avoids import-time side effects"
  - id: "token-extraction-fallback"
    choice: "Check response.usage first, then response.messages[-1].usage"
    rationale: "Agno may store usage in different locations depending on operation"
  - id: "agent-span-contextmanager"
    choice: "Return contextmanager from _create_agent_span_context"
    rationale: "Clean API for subclasses that need finer-grained tracing"

metrics:
  duration: 7 min
  completed: 2026-01-30
---

# Phase 6 Plan 03: Triad and Agent Instrumentation Summary

Triad-level spans with token tracking, agent-level span helper, completing 4-level hierarchy (Run -> Phase -> Triad -> Agent).

## One-liner

Triad spans wrap `_run_with_error_handling()` with token usage extraction from LLM responses; agent span helper enables subclass instrumentation.

## Accomplishments

### Task 1: Triad-level spans to AgnoTriad base class

Added OpenTelemetry instrumentation to `hfs/agno/teams/base.py`:

- Imported `get_tracer`, `get_meter`, `truncate_prompt` from `hfs.observability`
- Added lazy-initialized module-level tracer and metrics (consistent with orchestrator pattern)
- Wrapped `_run_with_error_handling()` in `hfs.triad.{id}` span with attributes:
  - `hfs.triad.id`, `hfs.triad.type`, `hfs.triad.phase`
  - `hfs.triad.prompt_snippet` (truncated to 200 chars)
  - `hfs.triad.duration_s`, `hfs.triad.success`
  - `hfs.triad.agent_roles` (list of agent role names)
  - `hfs.triad.tier` (from model_selector if available)
- Token usage extracted and recorded:
  - `hfs.tokens.prompt`, `hfs.tokens.completion`, `hfs.tokens.total`
  - Metrics: `hfs.triad.duration` histogram, `hfs.tokens.prompt`/`completion` counters

### Task 2: Agent-level span support

Added `_create_agent_span_context()` method for subclass use:

- Returns context manager that creates `hfs.agent.{role}` span
- Records attributes: `role`, `triad_id`, `model`, `provider`, `duration_s`, `success`
- Records `hfs.agent.duration` histogram metric
- Error handling: records exception and sets ERROR status

### Task 3: Agent observability tests

Created `hfs/tests/test_observability_agents.py` with 13 tests:

- Triad span creation and attributes
- Agent roles recorded in span
- Tier from model_selector recorded
- Token usage extraction from `response.usage`
- Token usage extraction from `response.messages[-1].usage`
- Graceful handling of missing token data
- Error handling with ERROR status
- Agent span helper functionality
- Duration recording on success and failure
- Prompt snippet truncation

## Verification Results

```
pytest hfs/tests/test_observability_agents.py -v
============================= 13 passed in 0.97s ==============================
```

## Key Files Modified

| File | Change Type | Purpose |
|------|-------------|---------|
| `hfs/agno/teams/base.py` | Modified | Triad/agent span instrumentation |
| `hfs/tests/test_observability_agents.py` | Created | Test coverage for tracing |

## Decisions Made

1. **Lazy initialization pattern** - Module-level `_get_tracer()` and `_get_agent_metrics()` functions lazily initialize tracer/meter, consistent with orchestrator instrumentation.

2. **Token extraction fallback** - Check `response.usage` first, then `response.messages[-1].usage` for flexibility with different Agno response formats.

3. **Agent span as context manager** - `_create_agent_span_context()` returns a context manager, providing clean API for subclasses that need finer-grained tracing.

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Phase 6 Complete** - Observability phase is now complete with:
- 06-01: TracerProvider/MeterProvider setup
- 06-02: Orchestrator run/phase spans
- 06-03: Triad/agent spans with token tracking

The 4-level span hierarchy is complete: `hfs.run` -> `hfs.phase.*` -> `hfs.triad.*` -> `hfs.agent.*`

**Ready for Phase 7** (if it exists in ROADMAP).

---

*Generated: 2026-01-30*
*Duration: 7 min*
*Commits: fd3a627, a5c401a, c6eb8b1*
