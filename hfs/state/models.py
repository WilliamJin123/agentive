"""
Pydantic snapshot models for HFS state queries.

Defines composable Pydantic models for representing HFS state snapshots.
All models serialize to JSON via model_dump(mode='json') for UI consumption.

Models:
    - AgentStatus: Agent execution status enum
    - AgentNode: Single agent state
    - TriadInfo: Triad with its agents
    - AgentTree: Both hierarchical and flat agent views
    - ContestEvent: Single negotiation contest record
    - SectionNegotiationState: Negotiation state for a section
    - NegotiationSnapshot: Full negotiation state
    - AgentTokenUsage: Token usage for single agent
    - PhaseTokenUsage: Token usage for a phase
    - TokenUsageSummary: Complete token breakdown
    - PhaseTimeline: Single phase timing
    - TraceTimeline: Full trace timeline
    - RunSnapshot: Complete run state snapshot
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


# =============================================================================
# Agent Models
# =============================================================================


class AgentStatus(str, Enum):
    """Agent execution status.

    Values:
        IDLE: Agent not yet started
        WORKING: Agent actively executing
        BLOCKED: Agent waiting on dependency
        COMPLETE: Agent finished execution
    """

    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class AgentNode(BaseModel):
    """Single agent in the tree.

    Represents the state of an individual agent within a triad,
    including execution status, timing, and optional blocking info.
    """

    agent_id: str
    triad_id: str
    role: str
    status: AgentStatus = AgentStatus.IDLE
    current_action: Optional[str] = None
    progress: Optional[float] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    blocking_reason: Optional[str] = None

    @computed_field
    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds if agent has started and ended."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None


class TriadInfo(BaseModel):
    """Triad with its agents.

    Groups agents by triad, including the triad's preset configuration.
    """

    triad_id: str
    preset: str  # hierarchical, dialectic, consensus
    agents: list[AgentNode] = Field(default_factory=list)


class AgentTree(BaseModel):
    """Both hierarchical and flat views of agents.

    Provides triads list for tree display and computed agent_index
    for O(1) lookups by agent_id.
    """

    triads: list[TriadInfo] = Field(default_factory=list)

    @computed_field
    @property
    def agent_index(self) -> dict[str, AgentNode]:
        """Flat lookup by agent_id for O(1) access."""
        return {
            agent.agent_id: agent
            for triad in self.triads
            for agent in triad.agents
        }


# =============================================================================
# Negotiation Models
# =============================================================================


class ContestEvent(BaseModel):
    """Single contest event in negotiation history.

    Records a contest round where multiple agents claimed the same section.
    """

    round: int
    claimants: list[str]
    resolution: Optional[str] = None  # concede, arbiter
    winner: Optional[str] = None


class SectionNegotiationState(BaseModel):
    """Negotiation state for a single section.

    Tracks ownership, claims, and contest history for a document section.
    """

    section_name: str
    status: str  # unclaimed, contested, claimed, frozen
    owner: Optional[str] = None
    claimants: list[str] = Field(default_factory=list)
    contest_history: list[ContestEvent] = Field(default_factory=list)


class NegotiationSnapshot(BaseModel):
    """Full negotiation state.

    Captures the current negotiation round, temperature, and all section states.
    """

    temperature: float = 1.0
    round: int = 0
    sections: list[SectionNegotiationState] = Field(default_factory=list)

    @computed_field
    @property
    def contested_count(self) -> int:
        """Number of sections currently contested."""
        return sum(1 for s in self.sections if s.status == "contested")


# =============================================================================
# Token Usage Models
# =============================================================================


class AgentTokenUsage(BaseModel):
    """Token usage for a single agent.

    Tracks prompt and completion tokens consumed by an agent.
    """

    agent_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @computed_field
    @property
    def total_tokens(self) -> int:
        """Total tokens consumed (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens


class PhaseTokenUsage(BaseModel):
    """Token usage for a phase.

    Aggregates token usage across all agents in a phase.
    """

    phase_name: str
    agents: list[AgentTokenUsage] = Field(default_factory=list)

    @computed_field
    @property
    def total_tokens(self) -> int:
        """Total tokens consumed in this phase."""
        return sum(a.total_tokens for a in self.agents)


class TokenUsageSummary(BaseModel):
    """Complete token breakdown.

    Provides token usage by phase and by agent for detailed analysis.
    """

    by_phase: list[PhaseTokenUsage] = Field(default_factory=list)
    by_agent: list[AgentTokenUsage] = Field(default_factory=list)

    @computed_field
    @property
    def total_tokens(self) -> int:
        """Total tokens consumed across all phases."""
        return sum(p.total_tokens for p in self.by_phase)


# =============================================================================
# Timeline Models
# =============================================================================


class PhaseTimeline(BaseModel):
    """Single phase in timeline.

    Tracks start/end times for a phase execution.
    """

    phase_name: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    @computed_field
    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds if phase has ended."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Whether phase has completed."""
        return self.ended_at is not None


class TraceTimeline(BaseModel):
    """Full trace timeline.

    Captures the entire run timeline with all phase executions.
    """

    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    phases: list[PhaseTimeline] = Field(default_factory=list)

    @computed_field
    @property
    def total_duration_ms(self) -> Optional[float]:
        """Total duration in milliseconds if run has ended."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None


# =============================================================================
# Composite Snapshot Model
# =============================================================================


class RunSnapshot(BaseModel):
    """Complete run state snapshot.

    Composes all state components into a single queryable snapshot.
    Version number enables cache invalidation for UI widgets.
    """

    version: int
    run_id: str
    agent_tree: AgentTree
    negotiation: NegotiationSnapshot
    usage: TokenUsageSummary
    timeline: TraceTimeline


__all__ = [
    # Agent models
    "AgentStatus",
    "AgentNode",
    "TriadInfo",
    "AgentTree",
    # Negotiation models
    "ContestEvent",
    "SectionNegotiationState",
    "NegotiationSnapshot",
    # Token usage models
    "AgentTokenUsage",
    "PhaseTokenUsage",
    "TokenUsageSummary",
    # Timeline models
    "PhaseTimeline",
    "TraceTimeline",
    # Composite
    "RunSnapshot",
]
