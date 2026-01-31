# Phase 8: Event Foundation - Research

**Researched:** 2026-01-30
**Domain:** Python async event bus, Pydantic event models, OpenTelemetry SpanProcessor bridge
**Confidence:** HIGH

## Summary

This research investigates how to build an async event bus that emits typed events for HFS lifecycle stages, enabling real-time UI updates. The approach combines Python's native asyncio primitives (bounded queues, async generators) with Pydantic v2 discriminated unions for type-safe event models, and a custom OpenTelemetry SpanProcessor to bridge tracing spans to events.

The recommended architecture is a **custom in-process event bus** rather than using a third-party library. This is justified because:
1. The requirements are specific (wildcard patterns, bounded buffers, OTel bridge) and simpler than production event bus libraries
2. Dependencies should be minimal for a library (HFS core)
3. The complexity is manageable with asyncio.Queue and async generators

The OTel bridge uses a custom SpanProcessor that intercepts `on_start` and `on_end` callbacks, filters by span name prefix, and emits corresponding events to the bus.

**Primary recommendation:** Build a lightweight event bus using `asyncio.Queue` with `maxsize` for backpressure, `fnmatch` for wildcard subscriptions, Pydantic discriminated unions for typed events, and a custom SpanProcessor that emits events on span start/end.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio | stdlib | Event loop, Queue, async generators | Built into Python, no dependencies |
| pydantic | >=2.0 | Event models with discriminated unions | Already in project, type-safe validation |
| opentelemetry-sdk | >=1.20 | SpanProcessor interface | Already integrated for tracing |
| fnmatch | stdlib | Wildcard pattern matching | Built-in, simple, fast |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| weakref | stdlib | Clean subscriber references | Prevent memory leaks on orphaned subscriptions |
| dataclasses | stdlib | Internal subscription state | Lightweight internal models |
| typing | stdlib | Generic type annotations | Type hints for bus generics |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom bus | bubus | More features (WAL, nesting) but heavy dependency |
| Custom bus | tinybus | Clean API but Python 3.12+ only |
| Custom bus | lahja | Inter-process support but overkill for in-process |
| fnmatch | regex | More powerful but slower, overkill for simple wildcards |
| asyncio.Queue | trio.MemoryChannel | Better backpressure semantics but adds dependency |

**Installation:**
```bash
# No new dependencies - all are already in project or stdlib
pip install pydantic>=2.0 opentelemetry-sdk>=1.20
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── events/                # NEW: Event foundation module
│   ├── __init__.py        # Public exports
│   ├── models.py          # Pydantic event models
│   ├── bus.py             # EventBus class
│   ├── stream.py          # EventStream async generator wrapper
│   └── otel_bridge.py     # SpanProcessor that emits events
└── observability/         # EXISTING
    ├── tracing.py         # Setup, tracer access
    └── ...
```

### Pattern 1: Bounded Queue with Backpressure
**What:** Use `asyncio.Queue(maxsize=N)` to create backpressure when subscribers are slow
**When to use:** All event subscriptions by default
**Example:**
```python
# Source: Python docs asyncio-queue
class Subscription:
    def __init__(self, pattern: str, maxsize: int = 100):
        self.pattern = pattern
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)

    async def put(self, event: HFSEvent) -> None:
        """Put event, blocking if queue full (backpressure)."""
        await self.queue.put(event)

    def put_nowait_or_drop(self, event: HFSEvent) -> bool:
        """Non-blocking put, returns False if dropped."""
        try:
            self.queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            return False
```

### Pattern 2: Async Generator for Consumption
**What:** Wrap queue consumption in an async generator for clean `async for` syntax
**When to use:** Primary consumer pattern per CONTEXT.md decisions
**Example:**
```python
# Source: PEP 525, Python async generators
class EventStream:
    """Async generator wrapper for event subscription."""

    def __init__(self, subscription: Subscription):
        self._subscription = subscription
        self._cancelled = False

    def __aiter__(self):
        return self

    async def __anext__(self) -> HFSEvent:
        if self._cancelled:
            raise StopAsyncIteration
        try:
            event = await self._subscription.queue.get()
            self._subscription.queue.task_done()
            return event
        except asyncio.CancelledError:
            raise StopAsyncIteration

    def cancel(self):
        """Explicit cancellation."""
        self._cancelled = True

# Usage:
async for event in bus.subscribe("agent.*"):
    handle(event)
```

### Pattern 3: Discriminated Union for Event Types
**What:** Use Pydantic discriminated unions with Literal type field for efficient validation
**When to use:** All HFS event types
**Example:**
```python
# Source: Pydantic docs - unions
from typing import Literal, Union, Annotated
from pydantic import BaseModel, Field
from datetime import datetime

class HFSEvent(BaseModel):
    """Base event with common fields."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: str
    event_type: str  # Discriminator

class AgentStartedEvent(HFSEvent):
    event_type: Literal["agent.started"] = "agent.started"
    agent_id: str
    triad_id: str
    role: str

class AgentEndedEvent(HFSEvent):
    event_type: Literal["agent.ended"] = "agent.ended"
    agent_id: str
    triad_id: str
    role: str
    duration_ms: float

# Discriminated union for efficient parsing
AnyHFSEvent = Annotated[
    Union[AgentStartedEvent, AgentEndedEvent, ...],
    Field(discriminator="event_type")
]
```

### Pattern 4: Wildcard Pattern Matching
**What:** Use `fnmatch.fnmatch()` for Unix shell-style wildcard matching
**When to use:** Subscription filtering (e.g., `agent.*`, `negotiation.*`)
**Example:**
```python
# Source: Python docs fnmatch
import fnmatch

class EventBus:
    def _matches(self, event_type: str, pattern: str) -> bool:
        """Check if event_type matches subscription pattern."""
        if pattern == "*":
            return True
        return fnmatch.fnmatch(event_type, pattern)

    async def emit(self, event: HFSEvent) -> None:
        """Emit event to all matching subscribers."""
        for subscription in self._subscriptions:
            if self._matches(event.event_type, subscription.pattern):
                await subscription.put(event)
```

### Pattern 5: Custom SpanProcessor for OTel Bridge
**What:** Subclass SpanProcessor to intercept span lifecycle and emit events
**When to use:** Bridging OpenTelemetry spans to event bus
**Example:**
```python
# Source: OpenTelemetry Python SDK docs
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.trace import Span

class EventBridgeSpanProcessor(SpanProcessor):
    """SpanProcessor that emits events on span start/end."""

    ALLOWED_PREFIXES = ("hfs.", "agent.", "negotiation.")
    ALLOWED_ATTRIBUTES = ("agent_id", "phase_id", "triad_id", "role", "status")

    def __init__(self, event_bus: EventBus, prefixes: list[str] = None):
        self.event_bus = event_bus
        self.prefixes = prefixes or list(self.ALLOWED_PREFIXES)
        self._spans: dict[int, float] = {}  # span_id -> start_time

    def on_start(self, span: Span, parent_context=None) -> None:
        """Called synchronously when span starts - must not block."""
        if not self._should_emit(span.name):
            return

        # Store start time for duration calc
        self._spans[span.get_span_context().span_id] = time.time()

        # Emit start event (non-blocking)
        event = self._create_start_event(span)
        asyncio.create_task(self.event_bus.emit(event))

    def on_end(self, span: ReadableSpan) -> None:
        """Called synchronously when span ends - must not block."""
        if not self._should_emit(span.name):
            return

        # Calculate duration
        start_time = self._spans.pop(span.get_span_context().span_id, None)
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0

        # Emit end event
        event = self._create_end_event(span, duration_ms)
        asyncio.create_task(self.event_bus.emit(event))

        # Emit error event if span has error status
        if span.status.is_ok is False:
            error_event = self._create_error_event(span)
            asyncio.create_task(self.event_bus.emit(error_event))

    def _should_emit(self, span_name: str) -> bool:
        """Filter by prefix."""
        return any(span_name.startswith(p) for p in self.prefixes)

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
```

### Anti-Patterns to Avoid
- **Unbounded queues:** Always use `maxsize` to prevent memory exhaustion when consumers are slow
- **Blocking in SpanProcessor:** `on_start`/`on_end` are called synchronously; use `asyncio.create_task` for async operations
- **Full event replay:** Per CONTEXT.md - events are fire-and-forget; don't implement replay
- **Complex event hierarchies:** Keep event models flat with minimal IDs; consumers query StateManager for details
- **Thread-unsafe access:** `asyncio.Queue` is not thread-safe; if OTel callbacks come from threads, use `loop.call_soon_threadsafe`

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pattern matching | Custom regex matcher | `fnmatch.fnmatch()` | Edge cases in glob patterns, caching built-in |
| Async iteration | Manual queue polling | `__aiter__`/`__anext__` | Clean syntax, proper cancellation handling |
| Event validation | Manual type checking | Pydantic discriminated unions | Fast (Rust-based), schema generation |
| Bounded buffer | Custom ring buffer | `asyncio.Queue(maxsize=N)` | Thread-safe, proper backpressure semantics |
| Thread-safe emit | Locks/mutexes | `loop.call_soon_threadsafe` | Built-in asyncio pattern for thread bridging |

**Key insight:** The asyncio stdlib has sophisticated primitives for this exact use case. Rolling custom implementations of queues, pattern matching, or async iteration introduces subtle bugs around cancellation, memory management, and edge cases.

## Common Pitfalls

### Pitfall 1: SpanProcessor Blocking the Trace
**What goes wrong:** Slow event emission blocks the traced operation
**Why it happens:** `on_start`/`on_end` are synchronous; any `await` in them blocks the calling thread
**How to avoid:** Use `asyncio.create_task()` or `loop.call_soon_threadsafe()` for async work
**Warning signs:** Traced operations become slower after adding event bridge

### Pitfall 2: Memory Leak from Orphaned Subscriptions
**What goes wrong:** Subscribers that break from loop without explicit cancel leak queue resources
**Why it happens:** Queue and subscription objects kept alive by internal references
**How to avoid:** Use weak references for subscription tracking; implement `__del__` cleanup; add `cancel()` method
**Warning signs:** Memory growth over time, especially with many short-lived subscriptions

### Pitfall 3: Lost Events During High Load
**What goes wrong:** Events are silently dropped when queues are full
**Why it happens:** Using `put_nowait()` without tracking dropped events
**How to avoid:** Either block with `await put()` (backpressure) or log/metric dropped events
**Warning signs:** UI shows gaps in event timeline during bursts

### Pitfall 4: Wrong Event Loop in SpanProcessor
**What goes wrong:** `asyncio.create_task()` fails because no event loop running
**Why it happens:** SpanProcessor callbacks may run on non-asyncio threads (e.g., BatchSpanProcessor worker)
**How to avoid:** Get loop reference at init time; use `loop.call_soon_threadsafe()` from other threads
**Warning signs:** `RuntimeError: no running event loop` in span processor

### Pitfall 5: Event Type String Mismatch
**What goes wrong:** Events don't match subscriptions due to typos in event_type strings
**Why it happens:** String-based event types without centralized constants
**How to avoid:** Define event types as Literal types in a single module; use IDE autocomplete
**Warning signs:** Subscriptions never receive events, no errors thrown

### Pitfall 6: Async Generator Not Properly Closed
**What goes wrong:** Resources leak when consumer stops iterating without explicit close
**Why it happens:** Async generators need `aclose()` called for cleanup
**How to avoid:** Use `async with` context manager wrapper or `try/finally` in consumer
**Warning signs:** Warnings about unawaited async generator finalizer

## Code Examples

Verified patterns from official sources:

### Complete Event Bus Implementation
```python
# Source: asyncio docs, Pydantic docs, fnmatch docs
import asyncio
import fnmatch
from typing import Optional, AsyncIterator
from datetime import datetime
from pydantic import BaseModel, Field
from weakref import WeakSet

class HFSEvent(BaseModel):
    """Base event model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: str
    event_type: str

class Subscription:
    """Single subscription with bounded queue."""

    def __init__(self, pattern: str, maxsize: int = 100):
        self.pattern = pattern
        self.queue: asyncio.Queue[HFSEvent] = asyncio.Queue(maxsize=maxsize)
        self._cancelled = False

    async def put(self, event: HFSEvent) -> bool:
        """Put event with backpressure. Returns False if cancelled."""
        if self._cancelled:
            return False
        try:
            await asyncio.wait_for(self.queue.put(event), timeout=1.0)
            return True
        except asyncio.TimeoutError:
            return False  # Dropped due to slow consumer

    def cancel(self):
        self._cancelled = True

class EventStream:
    """Async iterator for consuming events."""

    def __init__(self, subscription: Subscription):
        self._sub = subscription

    def __aiter__(self) -> AsyncIterator[HFSEvent]:
        return self

    async def __anext__(self) -> HFSEvent:
        if self._sub._cancelled:
            raise StopAsyncIteration
        try:
            event = await self._sub.queue.get()
            self._sub.queue.task_done()
            return event
        except asyncio.CancelledError:
            raise StopAsyncIteration

    def cancel(self):
        """Explicit cancellation - also works to break from loop."""
        self._sub.cancel()

class EventBus:
    """Async event bus with wildcard subscriptions."""

    def __init__(self):
        self._subscriptions: list[Subscription] = []
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        pattern: str = "*",
        maxsize: int = 100
    ) -> EventStream:
        """Subscribe to events matching pattern."""
        sub = Subscription(pattern, maxsize)
        async with self._lock:
            self._subscriptions.append(sub)
        return EventStream(sub)

    async def unsubscribe(self, stream: EventStream) -> None:
        """Remove subscription."""
        stream.cancel()
        async with self._lock:
            if stream._sub in self._subscriptions:
                self._subscriptions.remove(stream._sub)

    async def emit(self, event: HFSEvent) -> int:
        """Emit event to all matching subscribers. Returns count delivered."""
        delivered = 0
        async with self._lock:
            subs = list(self._subscriptions)  # Copy to avoid mutation

        for sub in subs:
            if fnmatch.fnmatch(event.event_type, sub.pattern):
                if await sub.put(event):
                    delivered += 1

        return delivered

    async def once(
        self,
        pattern: str,
        timeout: Optional[float] = None
    ) -> Optional[HFSEvent]:
        """Wait for a single event matching pattern."""
        stream = await self.subscribe(pattern, maxsize=1)
        try:
            if timeout:
                return await asyncio.wait_for(stream.__anext__(), timeout)
            return await stream.__anext__()
        except (asyncio.TimeoutError, StopAsyncIteration):
            return None
        finally:
            await self.unsubscribe(stream)
```

### Event Model Hierarchy
```python
# Source: Pydantic discriminated unions docs
from typing import Literal, Union, Annotated
from pydantic import BaseModel, Field
from datetime import datetime

class HFSEvent(BaseModel):
    """Base event with common fields per CONTEXT.md."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: str
    event_type: str

# Run lifecycle
class RunStartedEvent(HFSEvent):
    event_type: Literal["run.started"] = "run.started"

class RunEndedEvent(HFSEvent):
    event_type: Literal["run.ended"] = "run.ended"
    duration_ms: float

# Phase lifecycle
class PhaseStartedEvent(HFSEvent):
    event_type: Literal["phase.started"] = "phase.started"
    phase_id: str
    phase_name: str

class PhaseEndedEvent(HFSEvent):
    event_type: Literal["phase.ended"] = "phase.ended"
    phase_id: str
    phase_name: str
    duration_ms: float

# Agent lifecycle
class AgentStartedEvent(HFSEvent):
    event_type: Literal["agent.started"] = "agent.started"
    agent_id: str
    triad_id: str
    role: str

class AgentEndedEvent(HFSEvent):
    event_type: Literal["agent.ended"] = "agent.ended"
    agent_id: str
    triad_id: str
    role: str
    duration_ms: float

# Negotiation events
class NegotiationClaimedEvent(HFSEvent):
    event_type: Literal["negotiation.claimed"] = "negotiation.claimed"
    triad_id: str
    section_name: str

class NegotiationContestedEvent(HFSEvent):
    event_type: Literal["negotiation.contested"] = "negotiation.contested"
    section_name: str
    claimants: list[str]

class NegotiationResolvedEvent(HFSEvent):
    event_type: Literal["negotiation.resolved"] = "negotiation.resolved"
    section_name: str
    winner: str
    resolution_type: Literal["concede", "arbiter"]

# Error events
class ErrorEvent(HFSEvent):
    event_type: Literal["error.occurred"] = "error.occurred"
    error_type: str
    message: str
    triad_id: Optional[str] = None
    agent_id: Optional[str] = None

# Usage tracking
class UsageEvent(HFSEvent):
    event_type: Literal["usage.recorded"] = "usage.recorded"
    triad_id: str
    prompt_tokens: int
    completion_tokens: int
    model: str

# Discriminated union for parsing any event
AnyHFSEvent = Annotated[
    Union[
        RunStartedEvent, RunEndedEvent,
        PhaseStartedEvent, PhaseEndedEvent,
        AgentStartedEvent, AgentEndedEvent,
        NegotiationClaimedEvent, NegotiationContestedEvent, NegotiationResolvedEvent,
        ErrorEvent, UsageEvent,
    ],
    Field(discriminator="event_type")
]
```

### OTel Bridge SpanProcessor
```python
# Source: OpenTelemetry Python SDK docs
import asyncio
import time
from typing import Optional
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.trace import Span, Status, StatusCode

class EventBridgeSpanProcessor(SpanProcessor):
    """Bridges OTel spans to HFS event bus."""

    DEFAULT_PREFIXES = ["hfs.", "agent.", "negotiation."]
    ALLOWED_ATTRIBUTES = ["agent_id", "phase_id", "triad_id", "role", "status"]

    def __init__(
        self,
        event_bus: "EventBus",
        run_id: str,
        prefixes: Optional[list[str]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.event_bus = event_bus
        self.run_id = run_id
        self.prefixes = prefixes or self.DEFAULT_PREFIXES
        self._loop = loop or asyncio.get_event_loop()
        self._span_starts: dict[int, float] = {}

    def on_start(self, span: Span, parent_context=None) -> None:
        """Emit start event - called synchronously, must not block."""
        name = span.name
        if not self._should_emit(name):
            return

        span_id = span.get_span_context().span_id
        self._span_starts[span_id] = time.time()

        # Extract allowed attributes
        attrs = self._extract_attributes(span)

        # Determine event type from span name
        event_type = self._span_to_event_type(name, is_end=False)

        # Create and emit event
        event = self._create_event(event_type, attrs)
        self._emit_async(event)

    def on_end(self, span: ReadableSpan) -> None:
        """Emit end event - called synchronously, must not block."""
        name = span.name
        if not self._should_emit(name):
            return

        span_id = span.get_span_context().span_id
        start_time = self._span_starts.pop(span_id, None)
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0

        attrs = self._extract_attributes(span)
        attrs["duration_ms"] = duration_ms

        event_type = self._span_to_event_type(name, is_end=True)
        event = self._create_event(event_type, attrs)
        self._emit_async(event)

        # Emit error event if span has error
        if span.status and span.status.status_code == StatusCode.ERROR:
            error_event = ErrorEvent(
                run_id=self.run_id,
                event_type="error.occurred",
                error_type="span_error",
                message=span.status.description or "Unknown error",
                **{k: v for k, v in attrs.items() if k in ["triad_id", "agent_id"]}
            )
            self._emit_async(error_event)

    def _should_emit(self, span_name: str) -> bool:
        return any(span_name.startswith(p) for p in self.prefixes)

    def _span_to_event_type(self, span_name: str, is_end: bool) -> str:
        """Convert span name to event type."""
        # hfs.phase.deliberation -> phase.started / phase.ended
        # hfs.agent.orchestrator -> agent.started / agent.ended
        parts = span_name.split(".")
        if len(parts) >= 2:
            category = parts[1]  # phase, agent, triad, etc.
            suffix = "ended" if is_end else "started"
            return f"{category}.{suffix}"
        return f"unknown.{'ended' if is_end else 'started'}"

    def _extract_attributes(self, span) -> dict:
        """Extract allowed attributes from span."""
        result = {}
        if hasattr(span, 'attributes') and span.attributes:
            for key in self.ALLOWED_ATTRIBUTES:
                full_key = f"hfs.{key}"
                if full_key in span.attributes:
                    result[key] = span.attributes[full_key]
        return result

    def _create_event(self, event_type: str, attrs: dict) -> HFSEvent:
        """Create appropriate event based on type."""
        # Factory logic based on event_type
        # This would use the appropriate Pydantic model
        return HFSEvent(run_id=self.run_id, event_type=event_type, **attrs)

    def _emit_async(self, event: HFSEvent) -> None:
        """Emit event without blocking."""
        # Thread-safe emit to async event bus
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self.event_bus.emit(event))
        )

    def shutdown(self) -> None:
        self._span_starts.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Callback-based events | Async generators | Python 3.6 (PEP 525) | Cleaner consumer code, proper cancellation |
| Untyped event dicts | Pydantic discriminated unions | Pydantic 2.0 (2023) | Type safety, fast validation, JSON schema |
| SimpleSpanProcessor | BatchSpanProcessor + custom | OTel 1.0 | Non-blocking, better performance |
| Union validation (smart mode) | Discriminated unions | Pydantic 2.0 | 10-100x faster validation |

**Deprecated/outdated:**
- **asyncio.ensure_future():** Use `asyncio.create_task()` instead (cleaner API)
- **Pydantic v1 unions:** Migrate to v2 discriminated unions for performance
- **SimpleSpanProcessor:** Blocks the trace; always use BatchSpanProcessor for production

## Open Questions

Things that couldn't be fully resolved:

1. **Token streaming mechanism**
   - What we know: CONTEXT.md specifies "separate from event bus"
   - What's unclear: Whether to use a parallel async iterator or completely separate subsystem
   - Recommendation: Implement as separate `TokenStream` class, not through EventBus; keeps event bus focused on discrete lifecycle events

2. **Event delivery ordering guarantees**
   - What we know: asyncio.Queue is FIFO; fnmatch ordering is deterministic
   - What's unclear: Whether events should be ordered globally or per-subscriber
   - Recommendation: Per-subscriber FIFO ordering (each subscription has its own queue); don't guarantee cross-subscriber ordering

3. **Exact buffer sizes for backpressure**
   - What we know: Buffer too small = dropped events; too large = memory pressure
   - What's unclear: Optimal size depends on consumer speed and burst patterns
   - Recommendation: Default to 100 events (covers typical UI render cycles); make configurable per-subscription

4. **Thread safety for OTel bridge**
   - What we know: BatchSpanProcessor may call on_end from worker thread
   - What's unclear: Whether HFS always runs in single-threaded asyncio
   - Recommendation: Always use `loop.call_soon_threadsafe()` in SpanProcessor to be safe

## Sources

### Primary (HIGH confidence)
- [Python asyncio.Queue documentation](https://docs.python.org/3/library/asyncio-queue.html) - Queue API, backpressure behavior
- [Pydantic discriminated unions](https://docs.pydantic.dev/latest/concepts/unions/) - Event type hierarchy pattern
- [OpenTelemetry Python SDK trace docs](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html) - SpanProcessor interface
- [Python fnmatch documentation](https://docs.python.org/3/library/fnmatch.html) - Wildcard pattern matching
- [PEP 525](https://peps.python.org/pep-0525/) - Asynchronous generators specification

### Secondary (MEDIUM confidence)
- [Azure SDK custom SpanProcessor sample](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core-tracing-opentelemetry/samples/sample_custom_span_processor.py) - Practical SpanProcessor implementation
- [bubus GitHub](https://github.com/browser-use/bubus) - Production event bus patterns
- [TinyBus GitHub](https://github.com/rmonvfer/tinybus) - Modern async-first event bus design

### Tertiary (LOW confidence)
- [WebSearch results on asyncio memory leaks](https://github.com/python/cpython/pull/129214) - Awareness of potential issues, not verified for our use case

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib or already-used dependencies, verified with official docs
- Architecture: HIGH - Patterns derived from official Python and Pydantic documentation
- Pitfalls: MEDIUM - Based on known issues and best practices, some extrapolated
- OTel bridge: HIGH - SpanProcessor interface well-documented, Azure sample verified

**Research date:** 2026-01-30
**Valid until:** ~2026-03-30 (60 days - stable domain, asyncio/Pydantic APIs unlikely to change significantly)
