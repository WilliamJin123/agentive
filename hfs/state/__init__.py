"""
HFS State & Query Layer.

Provides StateManager for computing state from events and Pydantic snapshot
models for UI consumption. Widgets query this layer for current HFS state.

Example:
    >>> from hfs.events import EventBus
    >>> from hfs.state import StateManager, RunSnapshot
    >>>
    >>> bus = EventBus()
    >>> manager = StateManager(bus)
    >>> await manager.start()
    >>>
    >>> # Query current state
    >>> snapshot: RunSnapshot = manager.build_snapshot()
    >>> print(f"Version: {snapshot.version}, Agents: {len(snapshot.agent_tree.agent_index)}")

Classes:
    StateManager: Maintains state computed from events
    RunSnapshot: Complete run state snapshot
    AgentTree: Hierarchical and flat agent views
    NegotiationSnapshot: Current negotiation state
    TokenUsageSummary: Token usage breakdown
    TraceTimeline: Run timing information
"""

from hfs.state.manager import StateManager
from hfs.state.models import (
    AgentNode,
    AgentStatus,
    AgentTokenUsage,
    AgentTree,
    ContestEvent,
    NegotiationSnapshot,
    PhaseTimeline,
    PhaseTokenUsage,
    RunSnapshot,
    SectionNegotiationState,
    TokenUsageSummary,
    TraceTimeline,
    TriadInfo,
)

__all__ = [
    # StateManager
    "StateManager",
    # Models - Agent
    "AgentStatus",
    "AgentNode",
    "TriadInfo",
    "AgentTree",
    # Models - Negotiation
    "ContestEvent",
    "SectionNegotiationState",
    "NegotiationSnapshot",
    # Models - Token Usage
    "AgentTokenUsage",
    "PhaseTokenUsage",
    "TokenUsageSummary",
    # Models - Timeline
    "PhaseTimeline",
    "TraceTimeline",
    # Models - Composite
    "RunSnapshot",
]
