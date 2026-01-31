"""
EventStream async generator for consuming events.

Provides an async generator wrapper around a subscription queue, enabling
clean `async for event in stream` consumption patterns with proper
cancellation support.

Example:
    >>> bus = EventBus()
    >>> stream = await bus.subscribe("agent.*")
    >>> async for event in stream:
    ...     handle(event)
    ...     if done:
    ...         break  # or stream.cancel()
"""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hfs.events.models import HFSEvent


@dataclass
class Subscription:
    """Single subscription with bounded queue for backpressure.

    Attributes:
        pattern: Wildcard pattern for event matching (e.g., "agent.*", "*")
        queue: Bounded asyncio Queue for event delivery
        _cancelled: Flag indicating subscription is cancelled
    """
    pattern: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    _cancelled: bool = field(default=False)

    def __init__(self, pattern: str, maxsize: int = 100):
        """Initialize subscription with pattern and queue size.

        Args:
            pattern: Wildcard pattern for event filtering
            maxsize: Maximum queue size for backpressure (default 100)
        """
        self.pattern = pattern
        self.queue: asyncio.Queue["HFSEvent"] = asyncio.Queue(maxsize=maxsize)
        self._cancelled = False

    async def put(self, event: "HFSEvent", timeout: float = 1.0) -> bool:
        """Put event in queue with timeout for backpressure.

        Args:
            event: The event to deliver
            timeout: Max seconds to wait if queue full (default 1.0)

        Returns:
            True if delivered, False if cancelled or timed out (dropped)
        """
        if self._cancelled:
            return False
        try:
            await asyncio.wait_for(self.queue.put(event), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            # Slow consumer - drop event to avoid blocking emitter
            return False

    def cancel(self) -> None:
        """Cancel the subscription."""
        self._cancelled = True


class EventStream:
    """Async generator wrapper for event subscription.

    Implements async iterator protocol for clean `async for` consumption.
    Supports both breaking from loop and explicit cancel() for termination.

    Example:
        >>> stream = await bus.subscribe("negotiation.*")
        >>> async for event in stream:
        ...     if event.event_type == "negotiation.resolved":
        ...         break
    """

    def __init__(self, subscription: Subscription):
        """Initialize stream with subscription.

        Args:
            subscription: The underlying subscription with queue
        """
        self._subscription = subscription

    def __aiter__(self) -> "EventStream":
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> "HFSEvent":
        """Get next event from subscription queue.

        Returns:
            Next HFSEvent from the queue

        Raises:
            StopAsyncIteration: If subscription is cancelled
        """
        if self._subscription._cancelled:
            raise StopAsyncIteration

        try:
            event = await self._subscription.queue.get()
            self._subscription.queue.task_done()
            return event
        except asyncio.CancelledError:
            raise StopAsyncIteration

    def cancel(self) -> None:
        """Explicitly cancel the stream.

        After calling cancel(), the async for loop will terminate
        on next iteration. Also works to break from loop manually.
        """
        self._subscription.cancel()

    @property
    def pattern(self) -> str:
        """Get the subscription pattern."""
        return self._subscription.pattern

    @property
    def is_cancelled(self) -> bool:
        """Check if stream is cancelled."""
        return self._subscription._cancelled


__all__ = [
    "Subscription",
    "EventStream",
]
