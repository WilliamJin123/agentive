"""
Pydantic event models for HFS lifecycle events.

Defines typed event models for all HFS lifecycle stages including run, phase,
agent, and negotiation events. Uses Pydantic discriminated unions for efficient
validation and type-safe event handling.

Event Naming Convention:
    - run.started, run.ended: Top-level pipeline lifecycle
    - phase.started, phase.ended: Phase execution lifecycle
    - agent.started, agent.ended: Individual agent execution
    - negotiation.claimed, negotiation.contested, negotiation.resolved: Negotiation events
    - error.occurred: Error events with context
    - usage.recorded: Token usage tracking

Payloads are minimal (IDs only) per CONTEXT.md - consumers query StateManager for details.
"""

from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class HFSEvent(BaseModel):
    """Base event model with common fields.

    All HFS events inherit from this base class and include:
    - timestamp: When the event occurred (UTC)
    - run_id: The HFS run this event belongs to
    - event_type: Discriminator field for union type resolution
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: str
    event_type: str


# =============================================================================
# Run Lifecycle Events
# =============================================================================

class RunStartedEvent(HFSEvent):
    """Emitted when an HFS run begins."""
    event_type: Literal["run.started"] = "run.started"


class RunEndedEvent(HFSEvent):
    """Emitted when an HFS run completes."""
    event_type: Literal["run.ended"] = "run.ended"
    duration_ms: float


# =============================================================================
# Phase Lifecycle Events
# =============================================================================

class PhaseStartedEvent(HFSEvent):
    """Emitted when a phase (deliberation, negotiation, execution) begins."""
    event_type: Literal["phase.started"] = "phase.started"
    phase_id: str
    phase_name: str


class PhaseEndedEvent(HFSEvent):
    """Emitted when a phase completes."""
    event_type: Literal["phase.ended"] = "phase.ended"
    phase_id: str
    phase_name: str
    duration_ms: float


# =============================================================================
# Agent Lifecycle Events
# =============================================================================

class AgentStartedEvent(HFSEvent):
    """Emitted when an agent within a triad begins execution."""
    event_type: Literal["agent.started"] = "agent.started"
    agent_id: str
    triad_id: str
    role: str


class AgentEndedEvent(HFSEvent):
    """Emitted when an agent completes execution."""
    event_type: Literal["agent.ended"] = "agent.ended"
    agent_id: str
    triad_id: str
    role: str
    duration_ms: float


# =============================================================================
# Negotiation Events
# =============================================================================

class NegotiationClaimedEvent(HFSEvent):
    """Emitted when a triad claims a section during negotiation."""
    event_type: Literal["negotiation.claimed"] = "negotiation.claimed"
    triad_id: str
    section_name: str


class NegotiationContestedEvent(HFSEvent):
    """Emitted when multiple triads claim the same section."""
    event_type: Literal["negotiation.contested"] = "negotiation.contested"
    section_name: str
    claimants: list[str]


class NegotiationResolvedEvent(HFSEvent):
    """Emitted when a contested section is resolved."""
    event_type: Literal["negotiation.resolved"] = "negotiation.resolved"
    section_name: str
    winner: str
    resolution_type: Literal["concede", "arbiter"]


# =============================================================================
# Error and Usage Events
# =============================================================================

class ErrorEvent(HFSEvent):
    """Emitted when an error occurs during HFS execution."""
    event_type: Literal["error.occurred"] = "error.occurred"
    error_type: str
    message: str
    triad_id: Optional[str] = None
    agent_id: Optional[str] = None


class UsageEvent(HFSEvent):
    """Emitted to track token usage for a triad."""
    event_type: Literal["usage.recorded"] = "usage.recorded"
    triad_id: str
    prompt_tokens: int
    completion_tokens: int
    model: str


# =============================================================================
# Discriminated Union
# =============================================================================

AnyHFSEvent = Annotated[
    Union[
        RunStartedEvent,
        RunEndedEvent,
        PhaseStartedEvent,
        PhaseEndedEvent,
        AgentStartedEvent,
        AgentEndedEvent,
        NegotiationClaimedEvent,
        NegotiationContestedEvent,
        NegotiationResolvedEvent,
        ErrorEvent,
        UsageEvent,
    ],
    Field(discriminator="event_type")
]
"""Union type for any HFS event, using event_type as discriminator for efficient validation."""


__all__ = [
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
