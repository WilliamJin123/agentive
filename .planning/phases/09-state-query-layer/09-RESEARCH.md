# Phase 9: State & Query Layer - Research

**Researched:** 2026-01-31
**Domain:** Event-driven state management, Pydantic models, Textual UI integration
**Confidence:** HIGH

## Summary

This phase builds the StateManager and QueryInterface that sit between the event bus (Phase 8) and UI widgets (Phase 10+). The StateManager computes RunSnapshot from incoming events combined with orchestrator state, while QueryInterface provides clean Pydantic models for all queries. The locked decisions specify a hybrid approach (maintain state from events, can rebuild if needed), version tracking for efficient widget updates, both polling and subscription patterns, and parameterized query methods.

The standard approach uses Pydantic v2 composable models with `computed_field` for derived values, `model_dump(mode='json')` for serialization, and a class instance pattern (`QueryInterface(state_manager)`) for testability. The version number pattern enables widgets to skip re-render when state hasn't changed. For Textual integration, widgets use reactive attributes with watch methods - our QueryInterface should complement this with efficient delta queries (`get_changes_since(version)`).

**Primary recommendation:** Use nested Pydantic models with composable structure - separate models for AgentNode, TriadInfo, NegotiationState, TokenUsage, and TraceTimeline that compose into RunSnapshot. StateManager subscribes to all events and maintains indexed state. QueryInterface wraps StateManager with typed query methods.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.x | Data models and serialization | Already used throughout codebase, native JSON support |
| asyncio | stdlib | Async event handling | Already used in EventBus, native Python |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing | stdlib | Type hints | All model definitions |
| enum | stdlib | Status enums | AgentStatus, etc. |
| dataclasses | stdlib | Simple containers | Internal state if not needing validation |
| datetime | stdlib | Timestamps | Phase durations, event timing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic | dataclasses | No validation, no JSON schema, less safe |
| dict state | ORM/DB | Too heavy for in-memory snapshot state |
| custom serializer | msgpack | JSON is required by ABS-08, web UI compat |

**Installation:**
Already in dependencies via existing Pydantic usage. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── state/                    # NEW: Phase 9 module
│   ├── __init__.py           # Public exports
│   ├── models.py             # Pydantic snapshot models
│   ├── manager.py            # StateManager class
│   └── query.py              # QueryInterface class
├── events/                   # Phase 8 (existing)
│   ├── models.py             # Event models
│   ├── bus.py                # EventBus
│   └── ...
└── core/                     # Existing
    └── orchestrator.py       # Provides spec/triad state
```

### Pattern 1: Composable Pydantic Models
**What:** Nested models that compose into larger structures
**When to use:** Always for Phase 9 data shapes
**Example:**
```python
# Source: Pydantic docs + codebase patterns
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from datetime import datetime
from typing import Optional

class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    COMPLETE = "complete"

class AgentNode(BaseModel):
    """Single agent in the tree."""
    agent_id: str
    triad_id: str
    role: str
    status: AgentStatus = AgentStatus.IDLE
    current_action: Optional[str] = None
    progress: Optional[float] = None
    last_activity: Optional[datetime] = None
    blocking_reason: Optional[str] = None

class TriadInfo(BaseModel):
    """Triad with its agents."""
    triad_id: str
    preset: str  # hierarchical, dialectic, consensus
    agents: list[AgentNode] = Field(default_factory=list)

class AgentTree(BaseModel):
    """Both hierarchical and flat views."""
    triads: list[TriadInfo] = Field(default_factory=list)

    @computed_field
    @property
    def agent_index(self) -> dict[str, AgentNode]:
        """Flat lookup by agent_id."""
        return {
            agent.agent_id: agent
            for triad in self.triads
            for agent in triad.agents
        }
```

### Pattern 2: Event-Sourced State with Version Tracking
**What:** StateManager subscribes to events and maintains versioned state
**When to use:** For maintaining current state from event stream
**Example:**
```python
# Source: Event sourcing patterns + project CONTEXT.md decisions
class StateManager:
    def __init__(self, event_bus: EventBus, orchestrator: Optional[HFSOrchestrator] = None):
        self._event_bus = event_bus
        self._orchestrator = orchestrator
        self._version: int = 0
        self._event_history: list[HFSEvent] = []

        # Indexed state (computed from events)
        self._agents: dict[str, AgentNode] = {}
        self._triads: dict[str, TriadInfo] = {}
        self._phases: dict[str, PhaseInfo] = {}
        self._usage: TokenUsageTracker = TokenUsageTracker()
        self._negotiations: NegotiationTracker = NegotiationTracker()

    async def start(self) -> None:
        """Subscribe to all events and start processing."""
        self._stream = await self._event_bus.subscribe("*")
        asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        async for event in self._stream:
            self._apply_event(event)
            self._version += 1
            self._event_history.append(event)

    def _apply_event(self, event: HFSEvent) -> None:
        """Update internal state based on event type."""
        # Dispatch to handlers based on event_type
        match event.event_type:
            case "agent.started":
                self._handle_agent_started(event)
            case "agent.ended":
                self._handle_agent_ended(event)
            # ... etc
```

### Pattern 3: QueryInterface with Parameterized Methods
**What:** Clean API wrapping StateManager with typed returns
**When to use:** All external access to state
**Example:**
```python
# Source: Project CONTEXT.md decisions
class QueryInterface:
    def __init__(self, state_manager: StateManager):
        self._state = state_manager

    @property
    def version(self) -> int:
        """Current state version for cache invalidation."""
        return self._state._version

    def get_snapshot(self) -> RunSnapshot:
        """Full snapshot for complete view."""
        return RunSnapshot(
            version=self.version,
            agent_tree=self.get_agent_tree(),
            negotiation=self.get_negotiation_state(),
            usage=self.get_token_usage(),
            timeline=self.get_trace_timeline(),
        )

    # Focused getters
    def get_agent_tree(self) -> AgentTree:
        """Tree structure of all agents."""
        ...

    def get_agent(self, agent_id: str) -> Optional[AgentNode]:
        """Single agent lookup."""
        ...

    # Filtered variants
    def get_usage_by_phase(self, phase_name: str) -> PhaseTokenUsage:
        """Token usage for specific phase."""
        ...

    def get_usage_by_agent(self, agent_id: str) -> AgentTokenUsage:
        """Token usage for specific agent."""
        ...

    # Delta queries for efficient updates
    def get_changes_since(self, version: int) -> StateChanges:
        """Changes since given version for incremental updates."""
        ...
```

### Pattern 4: Subscription Support for Real-time Updates
**What:** Notification when state changes for real-time widgets
**When to use:** Agent tree panel, negotiation status
**Example:**
```python
# Source: Textual reactivity + project decisions
class StateManager:
    def __init__(self, ...):
        self._subscribers: list[Callable[[StateChange], None]] = []

    def subscribe(self, callback: Callable[[StateChange], None]) -> None:
        """Subscribe to state changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[StateChange], None]) -> None:
        """Unsubscribe from state changes."""
        self._subscribers.remove(callback)

    def _notify_subscribers(self, change: StateChange) -> None:
        """Notify all subscribers of state change."""
        for callback in self._subscribers:
            try:
                callback(change)
            except Exception:
                pass  # Don't let one subscriber break others
```

### Anti-Patterns to Avoid
- **Storing redundant data:** Don't store what can be computed. Use `computed_field`.
- **Blocking queries:** Don't hold locks during queries. Use copy-on-read or immutable snapshots.
- **Tight UI coupling:** QueryInterface must not import Textual. UI adapts to models, not vice versa.
- **Over-notification:** Don't notify on every micro-change. Batch or throttle if needed.
- **Mutable return values:** Always return copies or frozen models to prevent accidental mutation.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom dict conversion | Pydantic `model_dump(mode='json')` | Handles datetime, enums, nested models |
| Field validation | Manual type checks | Pydantic validators | Consistent, declarative, tested |
| Enum serialization | Custom `to_json()` | `str, Enum` base class | Auto-serializes to string value |
| Computed fields | Manual dict building | `@computed_field` decorator | Included in serialization automatically |
| Optional handling | Null checks everywhere | Pydantic `Optional[T]` with defaults | Type-safe, explicit |
| Version comparison | Custom timestamp logic | Integer version counter | Simpler, no clock sync issues |

**Key insight:** Pydantic v2's serialization is comprehensive. Don't duplicate what `model_dump()` already does. Use `computed_field` for derived values that should appear in JSON.

## Common Pitfalls

### Pitfall 1: Circular Import Between State and Events
**What goes wrong:** StateManager imports event models, event models reference state types
**Why it happens:** Natural desire to type-hint everything
**How to avoid:** Keep event models minimal (IDs only per CONTEXT.md). State models reference event models, not vice versa. Use `TYPE_CHECKING` guards.
**Warning signs:** Import errors, slow startup

### Pitfall 2: Blocking Event Processing
**What goes wrong:** Event handler does expensive work, backs up event queue
**Why it happens:** Processing logic in event handler
**How to avoid:** Event handlers only update indexes. Expensive computation happens in query methods on demand.
**Warning signs:** EventBus queue fills up, 1s timeout triggers

### Pitfall 3: Stale State from Orchestrator
**What goes wrong:** QueryInterface returns outdated orchestrator state
**Why it happens:** Orchestrator state not synced with events
**How to avoid:** StateManager is authoritative for current state. Only query orchestrator for static config (sections, triads config). All runtime state from events.
**Warning signs:** UI shows wrong status, state doesn't update

### Pitfall 4: Non-JSON-Serializable Models
**What goes wrong:** `model_dump_json()` fails on datetime or custom types
**Why it happens:** Forgot to use `mode='json'` or custom types without serializers
**How to avoid:** Test every model with `model_dump(mode='json')`. Use `datetime` (auto-handled). For custom types, add `@field_serializer`.
**Warning signs:** TypeError on serialization, web UI can't parse response

### Pitfall 5: Version Skew in Delta Queries
**What goes wrong:** Widget requests changes since version N, but StateManager already garbage-collected that history
**Why it happens:** Unbounded event history growth
**How to avoid:** Keep recent history (e.g., last 100 events or 60 seconds). If requested version too old, return full snapshot instead of delta.
**Warning signs:** Memory growth, missing changes in UI

### Pitfall 6: Race Condition in Subscription Notifications
**What goes wrong:** Subscriber callback modifies state being iterated
**Why it happens:** Synchronous callback in async context
**How to avoid:** Copy subscriber list before iterating. Consider async notifications via queue.
**Warning signs:** RuntimeError during iteration, inconsistent state

## Code Examples

Verified patterns from official sources:

### Pydantic v2 Model with Computed Field and JSON Serialization
```python
# Source: https://docs.pydantic.dev/latest/concepts/serialization/
from pydantic import BaseModel, Field, computed_field
from datetime import datetime
from typing import Optional
from enum import Enum

class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    COMPLETE = "complete"

class AgentNode(BaseModel):
    """Agent state model, JSON-serializable."""
    agent_id: str
    triad_id: str
    role: str
    status: AgentStatus = AgentStatus.IDLE
    current_action: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    @computed_field
    @property
    def duration_ms(self) -> Optional[float]:
        """Duration if agent has ended."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None

# Usage:
agent = AgentNode(agent_id="a1", triad_id="t1", role="orchestrator")
print(agent.model_dump(mode='json'))
# {'agent_id': 'a1', 'triad_id': 't1', 'role': 'orchestrator',
#  'status': 'idle', 'current_action': None, 'started_at': None,
#  'ended_at': None, 'duration_ms': None}
```

### Textual-Compatible Query Pattern
```python
# Source: https://textual.textualize.io/guide/reactivity/ + project patterns
class QueryInterface:
    """Clean API for widget consumption."""

    def __init__(self, state_manager: StateManager):
        self._state = state_manager

    @property
    def version(self) -> int:
        """Current version for Textual reactive comparison."""
        return self._state.version

    def get_agent_tree(self) -> AgentTree:
        """Returns AgentTree with both hierarchical and flat views.

        Textual widgets use:
        - tree.triads for Tree widget
        - tree.agent_index for lookups by ID
        """
        return self._state.build_agent_tree()

    def get_changes_since(self, version: int) -> StateChanges:
        """Efficient incremental update for Textual watch methods.

        Widget pattern:
            def watch_version(self, old: int, new: int) -> None:
                if new > old:
                    changes = query.get_changes_since(old)
                    self.apply_changes(changes)
        """
        return self._state.compute_changes_since(version)
```

### Subscription Pattern for Real-time Updates
```python
# Source: Project CONTEXT.md + asyncio patterns
import asyncio
from typing import Callable, Awaitable

class StateManager:
    """Supports both polling and subscription."""

    def __init__(self):
        self._subscribers: list[Callable[[StateChange], Awaitable[None]]] = []

    async def subscribe_async(
        self,
        callback: Callable[[StateChange], Awaitable[None]]
    ) -> Callable[[], None]:
        """Subscribe for async notifications.

        Returns unsubscribe function.
        """
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

    async def _notify(self, change: StateChange) -> None:
        """Notify subscribers without blocking event processing."""
        # Copy list to avoid mutation during iteration
        for callback in list(self._subscribers):
            asyncio.create_task(callback(change))
```

### Token Usage Tracking Model
```python
# Source: Pydantic nested models + requirements ABS-05
class AgentTokenUsage(BaseModel):
    """Token usage for a single agent."""
    agent_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

class PhaseTokenUsage(BaseModel):
    """Token usage for a phase."""
    phase_name: str
    agents: list[AgentTokenUsage] = Field(default_factory=list)

    @computed_field
    @property
    def total_tokens(self) -> int:
        return sum(a.total_tokens for a in self.agents)

class TokenUsageSummary(BaseModel):
    """Complete token breakdown per ABS-05."""
    by_phase: list[PhaseTokenUsage] = Field(default_factory=list)
    by_agent: list[AgentTokenUsage] = Field(default_factory=list)

    @computed_field
    @property
    def total_tokens(self) -> int:
        return sum(p.total_tokens for p in self.by_phase)
```

### Negotiation State Model
```python
# Source: Requirements ABS-04 + existing spec.py patterns
class SectionNegotiationState(BaseModel):
    """Negotiation state for a single section."""
    section_name: str
    status: str  # unclaimed, contested, claimed, frozen
    owner: Optional[str] = None
    claimants: list[str] = Field(default_factory=list)
    contest_history: list[ContestEvent] = Field(default_factory=list)

class ContestEvent(BaseModel):
    """Single contest event in history."""
    round: int
    claimants: list[str]
    resolution: Optional[str] = None  # concede, arbiter
    winner: Optional[str] = None

class NegotiationSnapshot(BaseModel):
    """Full negotiation state per ABS-04."""
    temperature: float
    round: int
    sections: list[SectionNegotiationState] = Field(default_factory=list)

    @computed_field
    @property
    def contested_count(self) -> int:
        return sum(1 for s in self.sections if s.status == "contested")
```

### Trace Timeline Model
```python
# Source: Requirements ABS-06
class PhaseTimeline(BaseModel):
    """Single phase in timeline."""
    phase_name: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    @computed_field
    @property
    def duration_ms(self) -> Optional[float]:
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None

    @computed_field
    @property
    def is_complete(self) -> bool:
        return self.ended_at is not None

class TraceTimeline(BaseModel):
    """Full trace timeline per ABS-06."""
    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    phases: list[PhaseTimeline] = Field(default_factory=list)

    @computed_field
    @property
    def total_duration_ms(self) -> Optional[float]:
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dict` for serialization | Pydantic `model_dump(mode='json')` | Pydantic v2 (2023) | Native JSON mode, no manual conversion |
| Manual computed fields | `@computed_field` decorator | Pydantic v2 (2023) | Auto-included in serialization and schema |
| `Optional[T] = None` implicit | Explicit default required | Pydantic v2 (2023) | Must specify `= None` for optional fields |
| `.dict()` method | `.model_dump()` method | Pydantic v2 (2023) | New naming convention |

**Deprecated/outdated:**
- `.dict()`: Replaced by `.model_dump()` in Pydantic v2
- `.json()`: Replaced by `.model_dump_json()` in Pydantic v2
- `@validator`: Replaced by `@field_validator` in Pydantic v2
- Implicit `None` default for `Optional`: Must be explicit in v2

## Open Questions

Things that couldn't be fully resolved:

1. **Throttling/debouncing rapid updates**
   - What we know: Textual handles rapid updates well, but many events in tight loop could cause issues
   - What's unclear: Whether throttling is needed, optimal throttle interval
   - Recommendation: Implement without throttling initially, add if performance testing shows need

2. **Event history retention**
   - What we know: Need some history for `get_changes_since(version)`
   - What's unclear: Optimal retention window (time-based? count-based?)
   - Recommendation: Start with last 1000 events or 5 minutes, make configurable

3. **Query blocking during state transitions**
   - What we know: Need to prevent torn reads during multi-event updates
   - What's unclear: Whether lock is needed or copy-on-read suffices
   - Recommendation: Use copy-on-read pattern (return snapshot copies), simpler than locks

## Sources

### Primary (HIGH confidence)
- [Pydantic Serialization Docs](https://docs.pydantic.dev/latest/concepts/serialization/) - model_dump, computed_field, JSON mode
- [Pydantic Fields Docs](https://docs.pydantic.dev/latest/concepts/fields/) - Field configuration, Optional handling
- [Textual Reactivity Guide](https://textual.textualize.io/guide/reactivity/) - reactive attributes, watch methods, data binding

### Secondary (MEDIUM confidence)
- [Pydantic nested models best practices](https://dev.to/mechcloud_academy/going-deeper-with-pydantic-nested-models-and-data-structures-4e24) - composable model patterns
- [Event sourcing Python library](https://eventsourcing.readthedocs.io/) - event sourcing patterns (adapted for simpler use case)

### Tertiary (LOW confidence)
- [reaktiv library](https://dev.to/buiapp/reaktiv-reactive-state-management-for-python-2k52) - signals pattern reference (not using directly)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing Pydantic, well-documented
- Architecture: HIGH - Patterns verified against project codebase and Pydantic docs
- Pitfalls: MEDIUM - Based on general async/Pydantic experience, some project-specific

**Research date:** 2026-01-31
**Valid until:** 30 days (Pydantic v2 stable, Textual stable)

## Recommendations for Claude's Discretion Items

Based on research, here are recommendations for items left to Claude's discretion in CONTEXT.md:

### Nested composable models vs single RunSnapshot model
**Recommendation:** Use nested composable models.

Rationale:
- Pydantic docs recommend composable models for maintainability
- Individual models (AgentTree, NegotiationSnapshot, TokenUsageSummary, TraceTimeline) can be queried independently
- RunSnapshot composes these for full view
- Easier testing - each model testable in isolation

### Query blocking behavior during state transitions
**Recommendation:** Copy-on-read pattern (no blocking).

Rationale:
- Textual widgets are non-blocking by design
- Locks would complicate async code and risk deadlocks
- Copy models on read ensures consistent snapshot
- Performance impact minimal for expected state sizes

### Token usage granularity
**Recommendation:** Three-level breakdown: total, by-phase, by-agent.

Rationale:
- ABS-05 requires "per agent, phase, and total"
- Use computed_field for totals (no storage duplication)
- Phase-level breakdown from PhaseStarted/PhaseEnded events
- Agent-level breakdown from UsageEvent with agent_id

### Notification granularity for subscriptions
**Recommendation:** Coarse-grained (state category changed).

Rationale:
- Fine-grained (every field change) would overwhelm subscribers
- Categories: agent_tree_changed, negotiation_changed, usage_changed, timeline_changed
- Subscribers filter by category of interest
- Version number still allows checking if any change occurred

### Throttling/debouncing of rapid updates
**Recommendation:** No throttling initially, monitor performance.

Rationale:
- Textual optimizes rendering (batches multiple reactive changes)
- Event bus already has 1s timeout for slow consumers
- Add throttling only if performance testing shows need
- Keep architecture simple first
