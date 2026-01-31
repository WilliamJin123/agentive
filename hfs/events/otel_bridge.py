"""
OpenTelemetry SpanProcessor bridge to HFS event bus.

Provides EventBridgeSpanProcessor that intercepts OTel span lifecycle callbacks
and emits corresponding HFS events. This enables automatic event emission from
existing traced code without explicit event calls.

Span Filtering:
    Only spans with configured prefixes emit events (default: hfs.*, agent.*, negotiation.*).
    This prevents noise from third-party library instrumentation.

Thread Safety:
    SpanProcessor callbacks (on_start, on_end) are synchronous and may be called
    from worker threads (e.g., BatchSpanProcessor). All async event emission uses
    loop.call_soon_threadsafe() to safely interact with the asyncio event loop.

Example:
    >>> from hfs.events import EventBus
    >>> from hfs.events.otel_bridge import EventBridgeSpanProcessor
    >>> from opentelemetry.sdk.trace import TracerProvider
    >>>
    >>> bus = EventBus()
    >>> processor = EventBridgeSpanProcessor(bus, run_id="run-123")
    >>> provider = TracerProvider()
    >>> provider.add_span_processor(processor)
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Optional

from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.trace import Span, StatusCode

from hfs.events.models import (
    HFSEvent,
    RunStartedEvent,
    RunEndedEvent,
    PhaseStartedEvent,
    PhaseEndedEvent,
    AgentStartedEvent,
    AgentEndedEvent,
    ErrorEvent,
)

if TYPE_CHECKING:
    from hfs.events.bus import EventBus


class EventBridgeSpanProcessor(SpanProcessor):
    """SpanProcessor that bridges OpenTelemetry spans to HFS event bus.

    Intercepts span start and end callbacks and emits corresponding HFS events.
    Only spans with names matching configured prefixes emit events, filtering
    out noise from third-party instrumentation.

    Attributes:
        DEFAULT_PREFIXES: Default span name prefixes that emit events
        ALLOWED_ATTRIBUTES: Span attributes to extract into events

    Example:
        >>> bus = EventBus()
        >>> processor = EventBridgeSpanProcessor(bus, run_id="run-123")
        >>> # Add to TracerProvider to bridge all matching spans
        >>> provider.add_span_processor(processor)
    """

    DEFAULT_PREFIXES: list[str] = ["hfs.", "agent.", "negotiation."]
    ALLOWED_ATTRIBUTES: list[str] = ["agent_id", "phase_id", "triad_id", "role", "status"]

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        prefixes: Optional[list[str]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Initialize the span processor bridge.

        Args:
            event_bus: HFS EventBus to emit events to
            run_id: Run ID to include in all emitted events
            prefixes: Span name prefixes to emit events for (default: DEFAULT_PREFIXES)
            loop: Event loop for async emission (default: get running loop at init)

        Note:
            CRITICAL: Get event loop at init time, not at emit time. This avoids
            "no running event loop" errors when callbacks come from worker threads.
        """
        self.event_bus = event_bus
        self.run_id = run_id
        self.prefixes = prefixes if prefixes is not None else list(self.DEFAULT_PREFIXES)

        # Get event loop at init time - CRITICAL per RESEARCH.md pitfall #4
        # This allows thread-safe emission from sync callbacks
        try:
            self._loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - get default (will create one if needed)
            self._loop = loop or asyncio.new_event_loop()

        # Track span start times for duration calculation
        self._span_starts: dict[int, float] = {}

    def on_start(self, span: Span, parent_context=None) -> None:
        """Handle span start - emit start event.

        Called synchronously when a span starts. MUST NOT block or await.
        Uses loop.call_soon_threadsafe() for async event emission.

        Args:
            span: The starting span
            parent_context: Parent context (unused)
        """
        name = span.name
        if not self._should_emit(name):
            return

        # Store start time for duration calculation on end
        span_id = span.get_span_context().span_id
        self._span_starts[span_id] = time.time()

        # Extract allowed attributes from span
        attrs = self._extract_attributes(span)

        # Convert span name to event type
        event_type = self._span_to_event_type(name, is_end=False)

        # Create and emit event - NON-BLOCKING
        event = self._create_event(event_type, attrs)
        if event:
            self._emit_async(event)

    def on_end(self, span: ReadableSpan) -> None:
        """Handle span end - emit end event and error event if applicable.

        Called synchronously when a span ends. MUST NOT block or await.
        Emits an end event with duration_ms, plus an error event if the
        span has error status.

        Args:
            span: The ending span (ReadableSpan with finalized data)
        """
        name = span.name
        if not self._should_emit(name):
            return

        # Calculate duration from stored start time
        span_id = span.get_span_context().span_id
        start_time = self._span_starts.pop(span_id, None)
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0.0

        # Extract attributes
        attrs = self._extract_attributes(span)
        attrs["duration_ms"] = duration_ms

        # Convert span name to event type
        event_type = self._span_to_event_type(name, is_end=True)

        # Create and emit end event
        event = self._create_event(event_type, attrs)
        if event:
            self._emit_async(event)

        # Emit error event if span has error status (per CONTEXT.md)
        if span.status and span.status.status_code == StatusCode.ERROR:
            error_event = self._create_error_event(span, attrs)
            self._emit_async(error_event)

    def _should_emit(self, span_name: str) -> bool:
        """Check if span name matches any configured prefix.

        Args:
            span_name: The span's name

        Returns:
            True if span should emit events
        """
        return any(span_name.startswith(p) for p in self.prefixes)

    def _span_to_event_type(self, span_name: str, is_end: bool) -> str:
        """Convert span name to event type.

        Extracts the category from span name and appends started/ended.
        Examples:
            - "hfs.phase.deliberation" -> "phase.started" / "phase.ended"
            - "hfs.agent.orchestrator" -> "agent.started" / "agent.ended"
            - "hfs.run" -> "run.started" / "run.ended"

        Args:
            span_name: The span's name (e.g., "hfs.phase.deliberation")
            is_end: True for end events, False for start events

        Returns:
            Event type string (e.g., "phase.started")
        """
        parts = span_name.split(".")
        suffix = "ended" if is_end else "started"

        # Handle different span name patterns
        if len(parts) >= 2:
            # hfs.run -> run, hfs.phase.X -> phase, agent.invoke -> agent
            category = parts[1] if parts[0] in ("hfs", "agent", "negotiation") else parts[0]
            return f"{category}.{suffix}"

        # Fallback for unexpected patterns
        return f"unknown.{suffix}"

    def _extract_attributes(self, span) -> dict:
        """Extract allowed attributes from span.

        Only extracts attributes in ALLOWED_ATTRIBUTES list, removing
        the hfs. prefix from attribute keys.

        Args:
            span: Span to extract attributes from

        Returns:
            Dict of allowed attributes with clean keys
        """
        result = {}

        # Handle both Span (on_start) and ReadableSpan (on_end)
        attributes = None
        if hasattr(span, "attributes") and span.attributes:
            attributes = span.attributes
        elif hasattr(span, "_attributes") and span._attributes:
            attributes = span._attributes

        if attributes:
            for key in self.ALLOWED_ATTRIBUTES:
                # Check both prefixed and unprefixed versions
                full_key = f"hfs.{key}"
                if full_key in attributes:
                    result[key] = attributes[full_key]
                elif key in attributes:
                    result[key] = attributes[key]

        return result

    def _create_event(self, event_type: str, attrs: dict) -> Optional[HFSEvent]:
        """Create appropriate event based on type.

        Factory method that creates the correct Pydantic event model
        based on event_type string.

        Args:
            event_type: Event type string (e.g., "phase.started")
            attrs: Attributes extracted from span

        Returns:
            HFSEvent subclass instance, or None if event type not recognized
        """
        duration_ms = attrs.pop("duration_ms", None)

        # Run events
        if event_type == "run.started":
            return RunStartedEvent(run_id=self.run_id)
        elif event_type == "run.ended":
            return RunEndedEvent(run_id=self.run_id, duration_ms=duration_ms or 0.0)

        # Phase events
        elif event_type == "phase.started":
            return PhaseStartedEvent(
                run_id=self.run_id,
                phase_id=attrs.get("phase_id", "unknown"),
                phase_name=attrs.get("status", "unknown"),  # status often holds phase name
            )
        elif event_type == "phase.ended":
            return PhaseEndedEvent(
                run_id=self.run_id,
                phase_id=attrs.get("phase_id", "unknown"),
                phase_name=attrs.get("status", "unknown"),
                duration_ms=duration_ms or 0.0,
            )

        # Agent events
        elif event_type == "agent.started":
            return AgentStartedEvent(
                run_id=self.run_id,
                agent_id=attrs.get("agent_id", "unknown"),
                triad_id=attrs.get("triad_id", "unknown"),
                role=attrs.get("role", "unknown"),
            )
        elif event_type == "agent.ended":
            return AgentEndedEvent(
                run_id=self.run_id,
                agent_id=attrs.get("agent_id", "unknown"),
                triad_id=attrs.get("triad_id", "unknown"),
                role=attrs.get("role", "unknown"),
                duration_ms=duration_ms or 0.0,
            )

        # Generic HFSEvent for unrecognized types (negotiation.*, etc.)
        # This allows extensibility without breaking on new span types
        return HFSEvent(run_id=self.run_id, event_type=event_type)

    def _create_error_event(self, span: ReadableSpan, attrs: dict) -> ErrorEvent:
        """Create error event from span with error status.

        Args:
            span: Span with error status
            attrs: Extracted span attributes

        Returns:
            ErrorEvent with error details
        """
        return ErrorEvent(
            run_id=self.run_id,
            error_type="span_error",
            message=span.status.description if span.status else "Unknown error",
            triad_id=attrs.get("triad_id"),
            agent_id=attrs.get("agent_id"),
        )

    def _emit_async(self, event: HFSEvent) -> None:
        """Emit event without blocking using thread-safe async dispatch.

        Uses loop.call_soon_threadsafe() to safely schedule async event
        emission from synchronous callbacks that may run on worker threads.

        Args:
            event: Event to emit
        """
        def schedule_emit():
            asyncio.create_task(self.event_bus.emit(event))

        try:
            self._loop.call_soon_threadsafe(schedule_emit)
        except RuntimeError:
            # Loop is closed or not running - silently drop event
            # This can happen during shutdown
            pass

    def shutdown(self) -> None:
        """Shutdown the processor, clearing any state.

        Called when the TracerProvider is shutting down.
        """
        self._span_starts.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush pending events.

        This processor emits events immediately, so nothing to flush.

        Args:
            timeout_millis: Timeout in milliseconds (unused)

        Returns:
            True (always succeeds)
        """
        return True


__all__ = [
    "EventBridgeSpanProcessor",
]
