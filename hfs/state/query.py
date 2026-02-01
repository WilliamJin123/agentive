"""
QueryInterface for clean state queries.

Wraps StateManager and provides typed query methods returning Pydantic models.
Supports both composite queries (get_snapshot) and focused queries (get_agent_tree).
All responses are JSON-serializable via model_dump(mode='json').

Example:
    >>> from hfs.events import EventBus
    >>> from hfs.state import StateManager
    >>> from hfs.state.query import QueryInterface
    >>>
    >>> bus = EventBus()
    >>> mgr = StateManager(bus)
    >>> query = QueryInterface(mgr)
    >>>
    >>> tree = query.get_agent_tree()
    >>> print(tree.model_dump_json())
"""

from enum import Enum
from typing import Optional, Callable, Awaitable
from datetime import datetime

from pydantic import BaseModel, Field

from hfs.state.manager import StateManager
from hfs.state.models import (
    AgentTree,
    AgentNode,
    TriadInfo,
    NegotiationSnapshot,
    SectionNegotiationState,
    TokenUsageSummary,
    AgentTokenUsage,
    PhaseTokenUsage,
    TraceTimeline,
    PhaseTimeline,
    RunSnapshot,
)


class ChangeCategory(str, Enum):
    """Categories of state changes for subscription filtering.

    Used by widgets to subscribe to specific change types.

    Values:
        AGENT_TREE: Agent/triad state changes
        NEGOTIATION: Negotiation state changes
        USAGE: Token usage changes
        TIMELINE: Phase/run timing changes
        ALL: All change types
    """

    AGENT_TREE = "agent_tree"
    NEGOTIATION = "negotiation"
    USAGE = "usage"
    TIMELINE = "timeline"
    ALL = "all"


class StateChange(BaseModel):
    """Notification of state change.

    Sent to subscribers when state is modified.

    Attributes:
        version: State version after change
        category: Type of change that occurred
        timestamp: When change was processed
    """

    version: int
    category: ChangeCategory
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StateChanges(BaseModel):
    """Changes since a given version for delta queries.

    Enables efficient incremental updates for widgets.

    Attributes:
        from_version: Starting version requested
        to_version: Current state version
        events_processed: Number of events since from_version
        categories_changed: List of categories that changed
    """

    from_version: int
    to_version: int
    events_processed: int
    categories_changed: list[ChangeCategory] = Field(default_factory=list)


class QueryInterface:
    """Clean API for querying HFS state.

    Wraps StateManager and provides typed query methods. All methods return
    Pydantic models that serialize to JSON via model_dump(mode='json').

    Supports:
    - Composite queries: get_snapshot() for full state
    - Focused queries: get_agent_tree(), get_negotiation_state(), etc.
    - Parameterized queries: get_agent(agent_id), get_usage_by_phase(phase_name)
    - Delta queries: get_changes_since(version) for efficient incremental updates
    - Subscriptions: subscribe() for real-time change notifications

    Example:
        >>> query = QueryInterface(state_manager)
        >>> tree = query.get_agent_tree()
        >>> print(tree.model_dump_json())

        >>> # Subscribe to agent changes
        >>> unsubscribe = query.subscribe(on_change, ChangeCategory.AGENT_TREE)
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with StateManager reference.

        Args:
            state_manager: The StateManager to wrap for queries
        """
        self._state = state_manager

    @property
    def version(self) -> int:
        """Current state version for cache invalidation.

        Textual widgets can compare versions to skip re-render if unchanged.

        Returns:
            Current state version number
        """
        return self._state.version

    # =========================================================================
    # Composite Queries
    # =========================================================================

    def get_snapshot(self) -> RunSnapshot:
        """Get complete state snapshot.

        Returns full snapshot containing agent tree, negotiation state,
        token usage, and trace timeline. Use for initial load or full refresh.

        Returns:
            RunSnapshot with all state components
        """
        return self._state.build_snapshot()

    # =========================================================================
    # Agent Tree Queries (ABS-03)
    # =========================================================================

    def get_agent_tree(self) -> AgentTree:
        """Get agent tree structure.

        Returns hierarchical view of triads and their agents. Use agent_index
        computed field for flat lookups by agent_id.

        Returns:
            AgentTree with triads list and agent_index computed field
        """
        return self._state.build_agent_tree()

    def get_agent(self, agent_id: str) -> Optional[AgentNode]:
        """Get single agent by ID.

        Args:
            agent_id: The agent's unique identifier

        Returns:
            AgentNode if found, None otherwise
        """
        tree = self._state.build_agent_tree()
        return tree.agent_index.get(agent_id)

    def get_triad(self, triad_id: str) -> Optional[TriadInfo]:
        """Get single triad by ID.

        Args:
            triad_id: The triad's unique identifier

        Returns:
            TriadInfo if found, None otherwise
        """
        return self._state._triads.get(triad_id)

    # =========================================================================
    # Negotiation Queries (ABS-04)
    # =========================================================================

    def get_negotiation_state(self) -> NegotiationSnapshot:
        """Get negotiation state.

        Returns section-centric view with claims, contests, and owners.

        Returns:
            NegotiationSnapshot with sections, temperature, round
        """
        return self._state.build_negotiation_snapshot()

    def get_section(self, section_name: str) -> Optional[SectionNegotiationState]:
        """Get single section's negotiation state.

        Args:
            section_name: The section name

        Returns:
            SectionNegotiationState if found, None otherwise
        """
        return self._state._sections.get(section_name)

    # =========================================================================
    # Token Usage Queries (ABS-05)
    # =========================================================================

    def get_token_usage(self) -> TokenUsageSummary:
        """Get complete token usage breakdown.

        Returns usage by phase and by agent with computed totals.

        Returns:
            TokenUsageSummary with by_phase, by_agent, total_tokens
        """
        return self._state.build_token_usage()

    def get_usage_by_phase(self, phase_name: str) -> Optional[PhaseTokenUsage]:
        """Get token usage for specific phase.

        Args:
            phase_name: The phase name

        Returns:
            PhaseTokenUsage if found, None otherwise
        """
        return self._state._phase_usage.get(phase_name)

    def get_usage_by_agent(self, agent_id: str) -> Optional[AgentTokenUsage]:
        """Get token usage for specific agent.

        Args:
            agent_id: The agent's unique identifier

        Returns:
            AgentTokenUsage if found, None otherwise
        """
        return self._state._agent_usage.get(agent_id)

    # =========================================================================
    # Trace Timeline Queries (ABS-06)
    # =========================================================================

    def get_trace_timeline(self) -> TraceTimeline:
        """Get trace timeline with phase durations.

        Returns timeline of all phases with start/end times and computed durations.

        Returns:
            TraceTimeline with phases list and total_duration_ms
        """
        return self._state.build_trace_timeline()

    def get_phase_timeline(self, phase_name: str) -> Optional[PhaseTimeline]:
        """Get timeline for specific phase.

        Args:
            phase_name: The phase name

        Returns:
            PhaseTimeline if found, None otherwise
        """
        return self._state._phases.get(phase_name)

    # =========================================================================
    # Delta Queries
    # =========================================================================

    def get_changes_since(self, version: int) -> StateChanges:
        """Get changes since given version for incremental updates.

        Scans event history to determine what categories changed since
        the requested version. If version >= current, returns empty changes.

        Args:
            version: The version to compare from

        Returns:
            StateChanges with events processed and categories changed
        """
        current = self._state.version
        if version >= current:
            return StateChanges(
                from_version=version,
                to_version=current,
                events_processed=0,
                categories_changed=[],
            )

        # Scan event history to find changes
        categories: set[ChangeCategory] = set()
        events_count = 0

        for event in self._state._event_history:
            # Determine category from event type
            if event.event_type.startswith("agent."):
                categories.add(ChangeCategory.AGENT_TREE)
            elif event.event_type.startswith("negotiation."):
                categories.add(ChangeCategory.NEGOTIATION)
            elif event.event_type == "usage.recorded":
                categories.add(ChangeCategory.USAGE)
            elif event.event_type.startswith(("phase.", "run.")):
                categories.add(ChangeCategory.TIMELINE)
            events_count += 1

        return StateChanges(
            from_version=version,
            to_version=current,
            events_processed=events_count,
            categories_changed=list(categories),
        )

    # =========================================================================
    # Subscriptions
    # =========================================================================

    def subscribe(
        self,
        callback: Callable[[StateChange], Awaitable[None]],
        category: ChangeCategory = ChangeCategory.ALL,
    ) -> Callable[[], None]:
        """Subscribe to state changes.

        Convenience wrapper around StateManager.subscribe.

        Args:
            callback: Async function called on state changes
            category: Filter by change category (default: ALL)

        Returns:
            Unsubscribe function - call to stop receiving notifications
        """
        return self._state.subscribe(callback, category)


__all__ = [
    "ChangeCategory",
    "StateChange",
    "StateChanges",
    "QueryInterface",
]
