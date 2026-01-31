"""
EventBus for async event distribution with wildcard subscriptions.

Provides publish-subscribe pattern for HFS lifecycle events. Supports
wildcard pattern matching (e.g., "agent.*"), bounded queues with backpressure,
and one-shot subscriptions via once().

Example:
    >>> bus = EventBus()
    >>> stream = await bus.subscribe("agent.*")
    >>> await bus.emit(AgentStartedEvent(run_id="r1", agent_id="a1", ...))
    >>> event = await stream.__anext__()  # or async for event in stream

Thread Safety:
    All subscription management is protected by asyncio.Lock.
    Event emission iterates over a snapshot of subscriptions.
"""

import asyncio
import fnmatch
from typing import Optional

from hfs.events.models import HFSEvent
from hfs.events.stream import EventStream, Subscription


class EventBus:
    """Async event bus with wildcard pattern subscriptions.

    Supports:
    - Pattern-based subscriptions: "agent.*", "negotiation.*", "*"
    - Bounded queues with configurable maxsize for backpressure
    - One-shot subscriptions via once() with optional timeout
    - Clean unsubscribe via unsubscribe() or stream.cancel()

    Example:
        >>> bus = EventBus()
        >>>
        >>> # Persistent subscription
        >>> stream = await bus.subscribe("agent.*", maxsize=50)
        >>> async for event in stream:
        ...     handle(event)
        >>>
        >>> # One-shot subscription
        >>> event = await bus.once("run.ended", timeout=30.0)
    """

    def __init__(self) -> None:
        """Initialize empty event bus."""
        self._subscriptions: list[Subscription] = []
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        pattern: str = "*",
        maxsize: int = 100,
    ) -> EventStream:
        """Subscribe to events matching pattern.

        Args:
            pattern: Unix-style wildcard pattern (e.g., "agent.*", "*")
            maxsize: Queue size for backpressure (default 100)

        Returns:
            EventStream async generator for consuming events

        Example:
            >>> stream = await bus.subscribe("negotiation.*")
            >>> async for event in stream:
            ...     if event.event_type == "negotiation.resolved":
            ...         break
        """
        subscription = Subscription(pattern, maxsize)
        async with self._lock:
            self._subscriptions.append(subscription)
        return EventStream(subscription)

    async def unsubscribe(self, stream: EventStream) -> None:
        """Remove a subscription.

        Cancels the stream and removes it from active subscriptions.

        Args:
            stream: The EventStream to unsubscribe
        """
        stream.cancel()
        async with self._lock:
            if stream._subscription in self._subscriptions:
                self._subscriptions.remove(stream._subscription)

    async def emit(self, event: HFSEvent) -> int:
        """Emit event to all matching subscribers.

        Events are delivered to subscribers whose pattern matches the
        event's event_type field using fnmatch glob matching.

        Args:
            event: The HFSEvent to emit

        Returns:
            Number of subscribers that received the event

        Example:
            >>> count = await bus.emit(AgentStartedEvent(...))
            >>> print(f"Delivered to {count} subscribers")
        """
        # Take snapshot under lock to avoid iteration mutation
        async with self._lock:
            subscriptions = list(self._subscriptions)

        delivered = 0
        for subscription in subscriptions:
            if self._matches(event.event_type, subscription.pattern):
                if await subscription.put(event):
                    delivered += 1

        return delivered

    async def once(
        self,
        pattern: str,
        timeout: Optional[float] = None,
    ) -> Optional[HFSEvent]:
        """Wait for a single event matching pattern.

        Creates a temporary subscription, waits for one matching event,
        then automatically unsubscribes.

        Args:
            pattern: Wildcard pattern to match
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            The matching event, or None if timeout elapsed

        Example:
            >>> # Wait up to 30s for run to complete
            >>> event = await bus.once("run.ended", timeout=30.0)
            >>> if event:
            ...     print(f"Run completed in {event.duration_ms}ms")
        """
        stream = await self.subscribe(pattern, maxsize=1)
        try:
            if timeout is not None:
                return await asyncio.wait_for(stream.__anext__(), timeout)
            return await stream.__anext__()
        except (asyncio.TimeoutError, StopAsyncIteration):
            return None
        finally:
            await self.unsubscribe(stream)

    def _matches(self, event_type: str, pattern: str) -> bool:
        """Check if event_type matches subscription pattern.

        Uses fnmatch for Unix shell-style wildcards:
        - "*" matches everything
        - "agent.*" matches "agent.started", "agent.ended"
        - "negotiation.*" matches all negotiation events

        Args:
            event_type: The event's event_type field
            pattern: The subscription pattern

        Returns:
            True if event_type matches pattern
        """
        if pattern == "*":
            return True
        return fnmatch.fnmatch(event_type, pattern)

    @property
    def subscriber_count(self) -> int:
        """Get current number of active subscriptions."""
        return len(self._subscriptions)


__all__ = [
    "EventBus",
    "Subscription",
]
