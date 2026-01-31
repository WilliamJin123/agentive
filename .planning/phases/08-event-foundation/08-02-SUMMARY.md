---
phase: 08-event-foundation
plan: 02
subsystem: events
tags: [opentelemetry, span-processor, otel-bridge, async-events]

# Dependency graph
requires:
  - phase: 08-01
    provides: Event models and bus for event emission
provides:
  - EventBridgeSpanProcessor bridging OTel spans to HFS events
  - Automatic event emission from traced code
  - Configurable span prefix filtering
affects: [09-state-manager, 10-ui-core, 11-textual-widgets]

# Tech tracking
tech-stack:
  added: []  # Uses existing opentelemetry-sdk
  patterns:
    - Custom SpanProcessor for span-to-event bridge
    - Thread-safe async dispatch via loop.call_soon_threadsafe
    - Optional processor injection in setup_tracing

key-files:
  created:
    - hfs/events/otel_bridge.py
  modified:
    - hfs/observability/tracing.py
    - hfs/events/__init__.py

key-decisions:
  - "Get event loop at init time, not emit time - avoids worker thread issues"
  - "Filter by span name prefix (hfs.*, agent.*, negotiation.*) per CONTEXT.md"
  - "Silent drop on loop closed - graceful shutdown behavior"
  - "Generic HFSEvent fallback for unrecognized span categories"

patterns-established:
  - "Span naming -> event type: hfs.phase.X -> phase.started/ended"
  - "Attribute extraction with hfs. prefix stripping"
  - "Error spans emit separate ErrorEvent with span description"
  - "Optional event bridge via setup_tracing(event_bus=bus)"

# Metrics
duration: 3min
completed: 2026-01-31
---

# Phase 8 Plan 2: OTel SpanProcessor Bridge Summary

**Custom SpanProcessor that bridges OpenTelemetry spans to HFS events with prefix filtering and thread-safe async emission**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-31T05:55:00Z
- **Completed:** 2026-01-31T05:58:30Z
- **Tasks:** 2
- **Files created:** 1
- **Files modified:** 2

## Accomplishments
- Created EventBridgeSpanProcessor implementing OTel SpanProcessor interface
- Configurable prefix filtering (default: hfs.*, agent.*, negotiation.*)
- Thread-safe event emission via loop.call_soon_threadsafe for worker threads
- Error spans emit separate ErrorEvent with exception details
- Integrated into setup_tracing() with optional event_bus parameter
- Backward compatible - existing code without event_bus unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EventBridgeSpanProcessor** - `7ecab9b` (feat)
2. **Task 2: Integrate SpanProcessor into tracing setup** - `3d696d9` (feat)

## Files Created/Modified
- `hfs/events/otel_bridge.py` - EventBridgeSpanProcessor class with span filtering and async emission
- `hfs/observability/tracing.py` - Added event_bus, run_id, event_prefixes params to setup_tracing()
- `hfs/events/__init__.py` - Export EventBridgeSpanProcessor

## Decisions Made
- Event loop captured at processor init time (CRITICAL per RESEARCH.md pitfall #4) to handle worker threads
- Span name to event type conversion: extract category from "hfs.{category}.{name}" pattern
- Allowed attributes list: agent_id, phase_id, triad_id, role, status - extracted with hfs. prefix
- Generic HFSEvent returned for unrecognized event types to allow extensibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Event foundation complete (models, bus, stream, OTel bridge)
- Ready for Phase 9 (StateManager) which will subscribe to events and track state
- Ready for Phase 10+ (Textual widgets) which will consume events for real-time UI
- All spans with hfs.*, agent.*, negotiation.* prefix automatically emit events when event_bus provided

---
*Phase: 08-event-foundation*
*Completed: 2026-01-31*
