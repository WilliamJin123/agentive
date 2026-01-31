# Phase 8: Event Foundation - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

HFS emits typed events that UI components can subscribe to in real-time. This phase establishes the event bus, Pydantic event models, and OTel bridge. Consumers are Textual widgets (Phase 10+) and the StateManager (Phase 9). This is internal infrastructure — no user-facing behavior.

</domain>

<decisions>
## Implementation Decisions

### Event Granularity
- Lifecycle + negotiation events (run, phase, agent, claim, contest, arbiter decisions)
- NOT token-level streaming — that's separate from the event bus
- Payloads are minimal IDs only (run_id, agent_id, phase_id, triad_id) — consumers query StateManager for details
- End events include timestamp + duration since corresponding start

### Subscription Model
- Wildcard pattern filtering: `agent.*`, `negotiation.*`, `*` for all
- Bounded buffer with backpressure — slow down emitters if subscriber is slow
- No replay — events are fire-and-forget; StateManager handles "current state" queries
- Support both persistent subscriptions and one-shot (`once()`) for waiting on single events

### OTel Bridge Behavior
- Emit events on both span start AND span end (UI needs in-progress state)
- Named spans only — filter by prefix (hfs.*, agent.*, negotiation.*), not all spans
- Prefix list is configurable so users can tune what emits events
- Include allowlisted attributes: agent_id, phase_id, triad_id, role, status
- Errors emit separate `error.*` events with exception details

### Consumer API Shape
- Primary pattern: async generators — `async for event in bus.subscribe("agent.*")`
- Unsubscribing: both break-from-loop and explicit `cancel()` work
- Class per event type: AgentStartedEvent, NegotiationClaimedEvent, etc.
- Common base class: HFSEvent with timestamp, run_id, event_type fields

### Claude's Discretion
- Token streaming mechanism (separate async iterator vs event bus)
- Event delivery ordering guarantees
- Exact buffer sizes for backpressure
- Internal implementation patterns

</decisions>

<specifics>
## Specific Ideas

- "Both persistent and one-shot subscriptions would be useful" — support both patterns
- Prefix filtering should be user-configurable for flexibility
- Pattern matching with `match/case` on typed event classes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-event-foundation*
*Context gathered: 2026-01-30*
