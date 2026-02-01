"""
HFS State & Query Layer.

Provides StateManager for computing state from events, QueryInterface for clean
typed queries, and Pydantic snapshot models for UI consumption. Widgets query
this layer for current HFS state and subscribe to changes.

Example:
    >>> from hfs.events import EventBus
    >>> from hfs.state import StateManager, QueryInterface, RunSnapshot
    >>>
    >>> bus = EventBus()
    >>> manager = StateManager(bus)
    >>> query = QueryInterface(manager)
    >>> await manager.start()
    >>>
    >>> # Query current state
    >>> snapshot: RunSnapshot = query.get_snapshot()
    >>> print(f"Version: {query.version}, Agents: {len(snapshot.agent_tree.agent_index)}")
    >>>
    >>> # Subscribe to changes
    >>> unsubscribe = query.subscribe(on_change, ChangeCategory.AGENT_TREE)

Classes:
    StateManager: Maintains state computed from events
    QueryInterface: Clean API for querying state
    ChangeCategory: Categories of state changes
    StateChange: Notification of state change
    StateChanges: Changes since a version (for delta queries)
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
from hfs.state.query import (
    ChangeCategory,
    QueryInterface,
    StateChange,
    StateChanges,
)

__all__ = [
    # StateManager
    "StateManager",
    # QueryInterface
    "QueryInterface",
    "ChangeCategory",
    "StateChange",
    "StateChanges",
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
