# Phase 9: State & Query Layer - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean API that returns inspection data as JSON-serializable Pydantic models. StateManager computes snapshots from events (Phase 8), and a query interface provides agent tree structure, negotiation state, token usage breakdown, and trace timeline. This layer sits between the event bus and Textual UI — it's the abstraction both CLI and future web UI will consume.

</domain>

<decisions>
## Implementation Decisions

### Query Granularity
- **Both patterns**: Composite `get_snapshot()` for full picture, plus focused getters for lightweight queries
- **Parameterized queries**: Full getters plus filtered variants for common access patterns (e.g., `get_agent(agent_id)`, `get_usage_by_phase(phase_name)`)
- **Class instance pattern**: `QueryInterface(state_manager)` — testable, mockable, explicit dependencies, consistent with StateManager pattern

### State Freshness
- **Hybrid approach**: Maintain state from events as they arrive, but can rebuild from event history if needed
- **Version number**: Each state change increments version — widgets can skip re-render if version unchanged
- **Optional persistence**: Can dump/load event history for debugging, but not required for normal operation

### Data Shape Conventions
- **Agent tree**: Both views — hierarchical for tree display, flat index for lookups
- **Agent status**: Simple status enum (`idle`, `working`, `blocked`, `complete`) plus optional detail fields (current action, progress, last activity, blocking reason)
- **Negotiation state**: Section-centric — list of sections, each with owner, claimants, contest history

### Update Semantics
- **Both available**: Polling via queries for simple widgets, subscriptions for real-time panels
- **Diff capability**: `get_changes_since(version)` for efficient incremental updates

### Claude's Discretion
- Nested composable models vs single RunSnapshot model — choose appropriate Pydantic structure
- Query blocking behavior during state transitions — choose based on Textual widget needs
- Token usage granularity — determine appropriate breakdown level
- Notification granularity for subscriptions — coarse vs fine-grained events
- Throttling/debouncing of rapid updates — implement if needed for performance

</decisions>

<specifics>
## Specific Ideas

- Query interface should be class-based for testability — widgets become testable by mocking the interface
- Version numbers enable efficient cache invalidation — widgets check version before re-rendering
- Both polling and subscription patterns support different widget needs — status bar can poll, agent tree can subscribe

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-state-query-layer*
*Context gathered: 2026-01-31*
