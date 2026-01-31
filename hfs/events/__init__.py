"""
HFS Events module - async event bus for lifecycle events.

Provides typed Pydantic event models and an async event bus for publishing
and subscribing to HFS lifecycle events. Used by UI components (Textual widgets)
and StateManager for real-time updates.

Quick Start:
    >>> from hfs.events import EventBus, AgentStartedEvent
    >>>
    >>> bus = EventBus()
    >>> stream = await bus.subscribe("agent.*")
    >>>
    >>> # Emit event
    >>> await bus.emit(AgentStartedEvent(
    ...     run_id="run-123",
    ...     agent_id="agent-1",
    ...     triad_id="triad-1",
    ...     role="orchestrator"
    ... ))
    >>>
    >>> # Consume event
    >>> async for event in stream:
    ...     print(event.event_type)  # "agent.started"

Event Types:
    - Run: RunStartedEvent, RunEndedEvent
    - Phase: PhaseStartedEvent, PhaseEndedEvent
    - Agent: AgentStartedEvent, AgentEndedEvent
    - Negotiation: NegotiationClaimedEvent, NegotiationContestedEvent, NegotiationResolvedEvent
    - Monitoring: ErrorEvent, UsageEvent

Subscription Patterns:
    - "*" - All events
    - "agent.*" - All agent events
    - "negotiation.*" - All negotiation events
    - "run.ended" - Specific event type
"""

from hfs.events.models import (
    # Base
    HFSEvent,
    # Run lifecycle
    RunStartedEvent,
    RunEndedEvent,
    # Phase lifecycle
    PhaseStartedEvent,
    PhaseEndedEvent,
    # Agent lifecycle
    AgentStartedEvent,
    AgentEndedEvent,
    # Negotiation
    NegotiationClaimedEvent,
    NegotiationContestedEvent,
    NegotiationResolvedEvent,
    # Error and usage
    ErrorEvent,
    UsageEvent,
    # Union type
    AnyHFSEvent,
)
from hfs.events.bus import EventBus
from hfs.events.stream import EventStream, Subscription
from hfs.events.otel_bridge import EventBridgeSpanProcessor


__all__ = [
    # Event bus
    "EventBus",
    "EventStream",
    "Subscription",
    # OTel bridge
    "EventBridgeSpanProcessor",
    # Base
    "HFSEvent",
    # Run lifecycle
    "RunStartedEvent",
    "RunEndedEvent",
    # Phase lifecycle
    "PhaseStartedEvent",
    "PhaseEndedEvent",
    # Agent lifecycle
    "AgentStartedEvent",
    "AgentEndedEvent",
    # Negotiation
    "NegotiationClaimedEvent",
    "NegotiationContestedEvent",
    "NegotiationResolvedEvent",
    # Error and usage
    "ErrorEvent",
    "UsageEvent",
    # Union type
    "AnyHFSEvent",
]
