# Architecture Research: HFS CLI Abstraction Layer

**Domain:** Event/state/query abstraction for multi-UI support
**Researched:** 2026-01-30
**Confidence:** HIGH (based on existing codebase analysis + established Python patterns)

## Executive Summary

The HFS system already has robust OpenTelemetry instrumentation with a 4-level span hierarchy (Run > Phase > Triad > Agent). The abstraction layer should **tap into this existing telemetry** rather than duplicate event emission, while adding a pub/sub event bus for real-time streaming and a query interface for inspection data.

The recommended architecture follows the **event sourcing lite** pattern: events are emitted during execution, captured into state snapshots, and queryable via a clean API. All three concerns (events, state, queries) share the same Pydantic model hierarchy for JSON serialization.

---

## Event System

### Recommended Pattern: Async Event Bus with Typed Events

Use an in-process async event bus with typed Pydantic events. This provides:
- Type safety via Pydantic models
- Multiple subscribers (CLI, future web UI, logging)
- Async-native with asyncio
- No external dependencies (Redis, etc.) for the core use case

### Event Categories

```
HFSEvent (base)
├── LifecycleEvent
│   ├── RunStarted
│   ├── RunCompleted
│   ├── RunFailed
│   └── PhaseTransition
├── AgentEvent
│   ├── TriadSpawned
│   ├── AgentStarted
│   ├── AgentResponse (streaming chunks)
│   ├── AgentCompleted
│   └── AgentError
├── NegotiationEvent
│   ├── ClaimRegistered
│   ├── NegotiationRoundStarted
│   ├── NegotiationResponse
│   ├── SectionResolved
│   └── EscalationTriggered
└── UsageEvent
    ├── TokensUsed
    └── ProviderSelected
```

### Event Bus Implementation

```python
from typing import Callable, Dict, List, Type, TypeVar
from pydantic import BaseModel
import asyncio

T = TypeVar('T', bound='HFSEvent')

class HFSEvent(BaseModel):
    """Base event with timestamp and trace context."""
    timestamp: float
    run_id: str
    trace_id: str | None = None  # OpenTelemetry trace ID for correlation
    span_id: str | None = None

class EventBus:
    """Async event bus for HFS events."""

    def __init__(self):
        self._subscribers: Dict[Type[HFSEvent], List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable[[HFSEvent], None]) -> None:
        """Subscribe to all events (wildcard)."""
        self._wildcard_subscribers.append(handler)

    async def emit(self, event: HFSEvent) -> None:
        """Emit event to all matching subscribers."""
        # Type-specific subscribers
        for event_type, handlers in self._subscribers.items():
            if isinstance(event, event_type):
                for handler in handlers:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)

        # Wildcard subscribers
        for handler in self._wildcard_subscribers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
```

### Streaming via Async Generators

For CLI live streaming, expose an async generator interface:

```python
class EventStream:
    """Async generator wrapper for event streaming."""

    def __init__(self, bus: EventBus, event_types: List[Type[HFSEvent]] | None = None):
        self._queue: asyncio.Queue[HFSEvent] = asyncio.Queue()
        self._bus = bus

        # Subscribe to requested types or all
        if event_types:
            for et in event_types:
                bus.subscribe(et, self._queue.put_nowait)
        else:
            bus.subscribe_all(self._queue.put_nowait)

    async def __aiter__(self):
        return self

    async def __anext__(self) -> HFSEvent:
        return await self._queue.get()
```

### OpenTelemetry Integration

Events should **correlate with existing spans**, not replace them:

1. **Span context propagation**: Each event carries `trace_id` and `span_id` from the current OpenTelemetry context
2. **Event-to-span mapping**: `AgentStarted` events correspond to `hfs.agent.{role}` spans
3. **Dual emission**: Critical events are also recorded as span events via `span.add_event()`

```python
from opentelemetry import trace

def emit_with_trace_context(bus: EventBus, event: HFSEvent) -> None:
    """Emit event with OpenTelemetry context attached."""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        ctx = current_span.get_span_context()
        event.trace_id = format(ctx.trace_id, '032x')
        event.span_id = format(ctx.span_id, '016x')

        # Also record as span event for OTLP export
        current_span.add_event(
            event.__class__.__name__,
            attributes=event.model_dump(exclude={'timestamp'})
        )

    asyncio.create_task(bus.emit(event))
```

### Why Not External Message Queue?

For v1.1 (CLI + future web), an in-process event bus is sufficient because:
- Single process execution (no distributed workers)
- Real-time streaming, not durable queuing
- Web UI will connect via WebSocket to the same process

If HFS scales to distributed execution, consider Redis Pub/Sub or Apache Kafka.

---

## State Management

### Philosophy: Computed Views, Not Persisted State

The abstraction layer should **compute state from events and existing OpenTelemetry data**, not maintain separate state stores. This ensures consistency and avoids synchronization bugs.

### State Snapshots

```python
class RunSnapshot(BaseModel):
    """Point-in-time snapshot of a run."""
    run_id: str
    status: Literal["pending", "running", "completed", "failed"]
    current_phase: str | None
    phase_history: List[PhaseSnapshot]
    triads: Dict[str, TriadSnapshot]
    spec: SpecSnapshot
    timing: TimingSnapshot
    usage: UsageSnapshot

class TriadSnapshot(BaseModel):
    """Snapshot of a triad's state."""
    triad_id: str
    preset: str
    current_phase: str | None
    agents: Dict[str, AgentSnapshot]
    claims: List[str]
    owned_sections: List[str]

class AgentSnapshot(BaseModel):
    """Snapshot of an agent's state."""
    role: str
    model: str
    provider: str
    status: Literal["idle", "running", "completed", "error"]
    last_response: str | None
    token_usage: TokenUsage

class TokenUsage(BaseModel):
    """Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
```

### State Computation

State is computed on-demand from:

1. **Event history**: Accumulated from event bus
2. **OpenTelemetry spans**: Current trace context
3. **Orchestrator internals**: `HFSOrchestrator` instance state

```python
class StateManager:
    """Manages state snapshots computed from events."""

    def __init__(self, orchestrator: HFSOrchestrator):
        self._orchestrator = orchestrator
        self._events: List[HFSEvent] = []
        self._usage_accumulator = UsageAccumulator()

    def record_event(self, event: HFSEvent) -> None:
        """Record event for state computation."""
        self._events.append(event)

        # Update accumulators for specific event types
        if isinstance(event, TokensUsed):
            self._usage_accumulator.add(event)

    def get_snapshot(self) -> RunSnapshot:
        """Compute current state snapshot."""
        return RunSnapshot(
            run_id=self._orchestrator._run_id,
            status=self._compute_status(),
            current_phase=self._compute_current_phase(),
            phase_history=self._compute_phase_history(),
            triads=self._compute_triads(),
            spec=self._compute_spec(),
            timing=self._compute_timing(),
            usage=self._usage_accumulator.get_snapshot(),
        )
```

### What State is Captured vs Computed

| Data | Source | Lifecycle |
|------|--------|-----------|
| Run ID | Generated at start | Immutable |
| Current phase | Event stream | Live updated |
| Phase history | Event accumulation | Append-only |
| Triad state | Orchestrator + events | Live computed |
| Agent responses | Event stream | Append-only |
| Token usage | Events (TokensUsed) | Accumulated |
| Spec sections | `Spec` instance | Live reference |
| Timing | Events + spans | Computed |

---

## Query Interface

### Design Principles

1. **UI-agnostic**: Returns Pydantic models, not formatted strings
2. **Sync and async**: Both sync (polling) and async (streaming) access
3. **Granular**: Query specific data without loading everything
4. **JSON-ready**: All return types are `model_dump()` serializable

### Query API

```python
class HFSQueryInterface:
    """Query interface for HFS inspection data."""

    def __init__(self, state_manager: StateManager, orchestrator: HFSOrchestrator):
        self._state = state_manager
        self._orchestrator = orchestrator

    # === Agent Tree Queries ===

    def get_agent_tree(self) -> AgentTreeResponse:
        """Get hierarchical agent structure."""
        return AgentTreeResponse(
            run_id=self._orchestrator._run_id,
            triads=[
                TriadNode(
                    triad_id=tid,
                    preset=t.config.preset.value,
                    agents=[
                        AgentNode(role=role, model=self._get_model_info(t, role))
                        for role in t.agents.keys()
                    ]
                )
                for tid, t in self._orchestrator.triads.items()
            ]
        )

    def get_agent_status(self, triad_id: str, role: str) -> AgentSnapshot:
        """Get specific agent's current status."""
        snapshot = self._state.get_snapshot()
        return snapshot.triads[triad_id].agents[role]

    # === Trace Timeline Queries ===

    def get_trace_timeline(self) -> TraceTimelineResponse:
        """Get chronological trace of all events."""
        return TraceTimelineResponse(
            run_id=self._state._orchestrator._run_id,
            events=[
                TimelineEvent(
                    timestamp=e.timestamp,
                    event_type=e.__class__.__name__,
                    summary=self._summarize_event(e),
                    trace_id=e.trace_id,
                    span_id=e.span_id,
                )
                for e in self._state._events
            ]
        )

    def get_phase_timeline(self) -> List[PhaseTimeline]:
        """Get timeline grouped by phase."""
        snapshot = self._state.get_snapshot()
        return snapshot.phase_history

    # === Token/Cost Queries ===

    def get_usage_breakdown(self) -> UsageBreakdownResponse:
        """Get token usage breakdown by triad/agent/phase."""
        return UsageBreakdownResponse(
            total=self._state._usage_accumulator.get_total(),
            by_triad=self._state._usage_accumulator.get_by_triad(),
            by_phase=self._state._usage_accumulator.get_by_phase(),
            by_provider=self._state._usage_accumulator.get_by_provider(),
        )

    def get_cost_estimate(self) -> CostEstimate:
        """Get estimated cost based on token usage."""
        usage = self._state._usage_accumulator.get_total()
        return CostEstimate(
            total_tokens=usage.total_tokens,
            estimated_cost_usd=self._calculate_cost(usage),
            breakdown=self._get_cost_breakdown(),
        )

    # === Spec Queries ===

    def get_spec_status(self) -> SpecSnapshot:
        """Get current spec state."""
        spec = self._orchestrator.spec
        return SpecSnapshot(
            temperature=spec.temperature,
            round=spec.round,
            status=spec.status,
            sections={
                name: SectionSnapshot(
                    status=s.status.value,
                    owner=s.owner,
                    claims=list(s.claims),
                    content_preview=s.content[:200] if s.content else None,
                )
                for name, s in spec.sections.items()
            }
        )

    def get_section_detail(self, section_name: str) -> SectionDetail:
        """Get detailed info for a specific section."""
        section = self._orchestrator.spec.sections[section_name]
        return SectionDetail(
            name=section_name,
            status=section.status.value,
            owner=section.owner,
            claims=list(section.claims),
            proposals=dict(section.proposals),
            content=section.content,
        )
```

### Response Models

All query responses are Pydantic models:

```python
class AgentTreeResponse(BaseModel):
    """Response for agent tree query."""
    run_id: str
    triads: List[TriadNode]

class TriadNode(BaseModel):
    """Node in agent tree representing a triad."""
    triad_id: str
    preset: str
    agents: List[AgentNode]

class AgentNode(BaseModel):
    """Node representing an agent."""
    role: str
    model: ModelInfo

class ModelInfo(BaseModel):
    """Model information for an agent."""
    provider: str
    model_id: str
    tier: str

class TraceTimelineResponse(BaseModel):
    """Response for trace timeline query."""
    run_id: str
    events: List[TimelineEvent]

class TimelineEvent(BaseModel):
    """Event in the trace timeline."""
    timestamp: float
    event_type: str
    summary: str
    trace_id: str | None
    span_id: str | None

class UsageBreakdownResponse(BaseModel):
    """Response for usage breakdown query."""
    total: TokenUsage
    by_triad: Dict[str, TokenUsage]
    by_phase: Dict[str, TokenUsage]
    by_provider: Dict[str, TokenUsage]
```

---

## OpenTelemetry Integration

### Current State

The existing observability module provides:
- 4-level span hierarchy: `hfs.run` > `hfs.phase.{name}` > `hfs.triad.{id}` > `hfs.agent.{role}`
- Duration histograms with LLM-tuned buckets
- Token counters (`hfs.tokens.prompt`, `hfs.tokens.completion`)
- Console + OTLP export

### Integration Strategy

**Do not duplicate what OpenTelemetry already captures.** Instead:

1. **Extract data from spans**: Use span attributes for timeline reconstruction
2. **Correlate events with spans**: Every event carries trace/span IDs
3. **Augment spans with events**: Record significant events as span events

### Span-to-Event Mapping

| Span Name | Corresponding Events |
|-----------|---------------------|
| `hfs.run` | `RunStarted`, `RunCompleted`, `RunFailed` |
| `hfs.phase.{name}` | `PhaseTransition` |
| `hfs.triad.{id}` | `TriadSpawned`, events for all child agents |
| `hfs.agent.{role}` | `AgentStarted`, `AgentResponse`, `AgentCompleted` |

### Custom SpanProcessor for Event Emission

To automatically emit events when spans complete:

```python
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan

class EventEmittingSpanProcessor(SpanProcessor):
    """Emit HFS events when spans complete."""

    def __init__(self, event_bus: EventBus):
        self._bus = event_bus

    def on_end(self, span: ReadableSpan) -> None:
        """Emit event when span ends."""
        name = span.name
        attrs = span.attributes or {}

        if name == "hfs.run":
            event = self._create_run_event(span, attrs)
        elif name.startswith("hfs.phase."):
            event = self._create_phase_event(span, attrs)
        elif name.startswith("hfs.triad."):
            event = self._create_triad_event(span, attrs)
        elif name.startswith("hfs.agent."):
            event = self._create_agent_event(span, attrs)
        else:
            return

        asyncio.create_task(self._bus.emit(event))
```

---

## Build Order

### Dependency Graph

```
                    ┌─────────────────┐
                    │  Event Models   │ (Pydantic)
                    │  (HFSEvent, *)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌─────────────┐  ┌──────────────┐
     │  EventBus  │  │ StateManager │  │ QueryModels  │
     │ (pub/sub)  │  │ (snapshots)  │  │ (responses)  │
     └──────┬─────┘  └──────┬──────┘  └──────┬───────┘
            │               │                │
            └───────────────┼────────────────┘
                            ▼
                   ┌────────────────┐
                   │ QueryInterface │
                   │   (unified)    │
                   └────────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     ┌────────────┐  ┌─────────────┐  ┌──────────────┐
     │  OTel      │  │ Orchestrator│  │    CLI       │
     │ Processor  │  │ Integration │  │  Consumer    │
     └────────────┘  └─────────────┘  └──────────────┘
```

### Recommended Implementation Phases

#### Phase 1: Event Foundation (No external dependencies)

**Tasks:**
1. Define `HFSEvent` base model and all event types
2. Implement `EventBus` with subscribe/emit
3. Implement `EventStream` async generator
4. Unit tests for event bus

**Output:** `hfs/abstraction/events/` with models and bus

#### Phase 2: State Layer

**Tasks:**
1. Define snapshot models (`RunSnapshot`, `TriadSnapshot`, etc.)
2. Implement `StateManager` with event recording
3. Implement usage accumulator
4. Wire state manager to event bus

**Output:** `hfs/abstraction/state/` with manager and models

#### Phase 3: Query Interface

**Tasks:**
1. Define response models for all queries
2. Implement `HFSQueryInterface`
3. Add sync and async query methods
4. Unit tests for queries

**Output:** `hfs/abstraction/queries/` with interface and models

#### Phase 4: OpenTelemetry Integration

**Tasks:**
1. Implement `EventEmittingSpanProcessor`
2. Add trace context propagation to events
3. Register processor in `setup_tracing()`
4. Verify correlation in tests

**Output:** `hfs/abstraction/otel.py` with processor

#### Phase 5: Orchestrator Integration

**Tasks:**
1. Add event emission points to `HFSOrchestrator`
2. Expose query interface from orchestrator
3. Add streaming endpoint to CLI
4. Integration tests

**Output:** Modified `hfs/core/orchestrator.py`, new CLI commands

### Phase Dependencies

| Phase | Depends On | Can Start After |
|-------|------------|-----------------|
| 1. Events | None | Immediately |
| 2. State | Phase 1 | Phase 1 complete |
| 3. Queries | Phase 2 | Phase 2 complete |
| 4. OTel | Phase 1 | Phase 1 complete (parallel with 2-3) |
| 5. Integration | Phases 3, 4 | All prior complete |

---

## Directory Structure

```
hfs/
├── abstraction/              # NEW: Abstraction layer
│   ├── __init__.py
│   ├── events/
│   │   ├── __init__.py
│   │   ├── models.py         # HFSEvent and all event types
│   │   ├── bus.py            # EventBus implementation
│   │   └── stream.py         # EventStream async generator
│   ├── state/
│   │   ├── __init__.py
│   │   ├── models.py         # Snapshot models
│   │   ├── manager.py        # StateManager
│   │   └── accumulators.py   # Usage accumulators
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── models.py         # Response models
│   │   └── interface.py      # HFSQueryInterface
│   └── otel.py               # OpenTelemetry integration
├── core/
│   └── orchestrator.py       # MODIFIED: Add event emission
├── cli/
│   └── main.py               # MODIFIED: Add streaming commands
└── observability/
    └── tracing.py            # MODIFIED: Register EventEmittingSpanProcessor
```

---

## Anti-Patterns to Avoid

### 1. Duplicating OpenTelemetry Data

**Wrong:** Creating parallel timing/metrics tracking
**Right:** Extract from existing spans and metrics

### 2. Synchronous Event Handlers Blocking Pipeline

**Wrong:** `await handler(event)` in emit loop
**Right:** Use `asyncio.create_task()` for non-critical handlers

### 3. State Mutation from Multiple Sources

**Wrong:** Events modify state, orchestrator also modifies state
**Right:** State is computed from events + orchestrator (single source of truth)

### 4. Over-Engineering Event Persistence

**Wrong:** Writing events to database for CLI use
**Right:** In-memory event log, persistence only if explicitly needed

### 5. Tight Coupling to CLI

**Wrong:** Event handlers format strings for terminal output
**Right:** Events are data models, CLI transforms for display

---

## Future Considerations

### Web UI Integration (v1.2+)

The abstraction layer is designed for future web UI:

1. **WebSocket endpoint**: Stream events to browser via `EventStream`
2. **REST API**: Expose `HFSQueryInterface` as REST endpoints
3. **Real-time updates**: Browser subscribes to event stream

### Distributed Execution (v2+)

If HFS scales to distributed workers:

1. Replace in-process `EventBus` with Redis Pub/Sub
2. Add event persistence for replay
3. Consider event sourcing for full state reconstruction

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Event System | HIGH | Standard asyncio pub/sub, well-documented patterns |
| State Management | HIGH | Computed from existing data, no new persistence |
| Query Interface | HIGH | Pydantic models already used throughout codebase |
| OTel Integration | HIGH | Existing spans provide foundation, just add processor |
| Build Order | HIGH | Clear dependencies, no circular references |

## Sources

- [aiopubsub](https://github.com/qntln/aiopubsub) - Asyncio pub/sub pattern
- [Building an Event Bus in Python with asyncio](https://www.joeltok.com/posts/2021-03-building-an-event-bus-in-python/)
- [bubus](https://github.com/browser-use/bubus) - Production-ready Python event bus
- [OpenTelemetry Python Instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [OpenTelemetry Span Events](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.span.html)
- [Pydantic Serialization](https://docs.pydantic.dev/latest/concepts/serialization/)
- [Building Reactive Python Apps with Async Generators](https://blog.naveenpn.com/building-reactive-python-apps-with-async-generators-and-streams)
