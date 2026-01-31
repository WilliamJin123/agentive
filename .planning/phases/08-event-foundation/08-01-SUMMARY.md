---
phase: 08-event-foundation
plan: 01
subsystem: events
tags: [pydantic, asyncio, event-bus, async-generator, discriminated-union]

# Dependency graph
requires:
  - phase: 07-cli-core
    provides: CLI foundation and observability module
provides:
  - Pydantic event models for all HFS lifecycle stages
  - EventBus with wildcard pattern subscriptions
  - EventStream async generator for event consumption
  - Bounded queues with backpressure support
affects: [09-state-manager, 10-ui-core, 11-textual-widgets, 12-otel-bridge]

# Tech tracking
tech-stack:
  added: []  # All stdlib or existing deps
  patterns:
    - Discriminated unions with Literal event_type
    - Async generator protocol for event streams
    - Bounded queue with timeout for backpressure

key-files:
  created:
    - hfs/events/models.py
    - hfs/events/bus.py
    - hfs/events/stream.py
    - hfs/events/__init__.py
  modified: []

key-decisions:
  - "Minimal payloads (IDs only) - consumers query StateManager for details"
  - "fnmatch for wildcard patterns - no hand-rolled regex"
  - "1s timeout per subscriber on emit - drops if slow consumer"
  - "Default queue maxsize 100 - configurable per subscription"

patterns-established:
  - "Event naming: category.action (agent.started, negotiation.resolved)"
  - "All events inherit from HFSEvent base with timestamp, run_id, event_type"
  - "Subscription via async generator: async for event in bus.subscribe('pattern')"
  - "One-shot via once(): await bus.once('run.ended', timeout=30.0)"

# Metrics
duration: 3min
completed: 2026-01-31
---

# Phase 8 Plan 1: Event Models and Bus Summary

**Pydantic event models with discriminated union and async EventBus with wildcard subscriptions for HFS lifecycle events**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-31T05:50:56Z
- **Completed:** 2026-01-31T05:53:32Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments
- Created 11 typed Pydantic event models covering all HFS lifecycle stages
- Built EventBus with wildcard pattern matching (agent.*, negotiation.*, *)
- Implemented EventStream async generator with proper cancellation
- Added once() method for one-shot subscriptions with timeout

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic event models** - `0db8e06` (feat)
2. **Task 2: Create EventBus and EventStream** - `9c95110` (feat)

## Files Created/Modified
- `hfs/events/models.py` - Pydantic event models with AnyHFSEvent discriminated union
- `hfs/events/bus.py` - EventBus with subscribe(), emit(), once(), unsubscribe()
- `hfs/events/stream.py` - Subscription dataclass and EventStream async generator
- `hfs/events/__init__.py` - Public module exports

## Decisions Made
- Used Literal types for event_type discriminator enabling efficient Pydantic validation
- fnmatch.fnmatch() for pattern matching per RESEARCH.md recommendation
- 1 second timeout on queue.put() to prevent slow consumers from blocking emitters
- Default maxsize=100 for subscription queues (covers typical UI render cycles)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Event models and bus ready for Phase 9 (StateManager) integration
- EventStream ready for Phase 10+ (Textual widgets) consumption
- OTel bridge will use these events in Phase 8 Plan 2

---
*Phase: 08-event-foundation*
*Completed: 2026-01-31*
