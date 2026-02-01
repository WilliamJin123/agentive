"""
StateManager for computing HFS state from events.

Subscribes to EventBus for all events and maintains indexed state for efficient
queries. Supports version tracking for cache invalidation and bounded event
history for delta queries.

Example:
    >>> bus = EventBus()
    >>> manager = StateManager(bus)
    >>> await manager.start()
    >>>
    >>> # Events processed automatically
    >>> await bus.emit(RunStartedEvent(run_id="r1"))
    >>>
    >>> # Query current state
    >>> snapshot = manager.build_snapshot()
    >>> print(f"Run: {snapshot.run_id}, Version: {snapshot.version}")
    >>>
    >>> await manager.stop()
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Callable, Awaitable

from hfs.events.bus import EventBus

if TYPE_CHECKING:
    from hfs.state.query import ChangeCategory, StateChange
from hfs.events.models import (
    AgentEndedEvent,
    AgentStartedEvent,
    HFSEvent,
    NegotiationClaimedEvent,
    NegotiationContestedEvent,
    NegotiationResolvedEvent,
    PhaseEndedEvent,
    PhaseStartedEvent,
    RunEndedEvent,
    RunStartedEvent,
    UsageEvent,
)
from hfs.events.stream import EventStream
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


class StateManager:
    """Maintains HFS state computed from events.

    Subscribes to EventBus for all events and maintains indexed state
    for efficient queries. Supports version tracking for cache invalidation.

    Attributes:
        version: Current state version, increments on each event

    Example:
        >>> bus = EventBus()
        >>> manager = StateManager(bus)
        >>> await manager.start()
        >>>
        >>> snapshot = manager.build_snapshot()
        >>> print(f"Version: {manager.version}")
        >>>
        >>> await manager.stop()
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialize with event bus reference.

        Args:
            event_bus: The EventBus to subscribe to for events
        """
        self._event_bus = event_bus
        self._version: int = 0
        self._run_id: Optional[str] = None

        # Indexed state for efficient lookups
        self._agents: dict[str, AgentNode] = {}
        self._triads: dict[str, TriadInfo] = {}
        self._phases: dict[str, PhaseTimeline] = {}
        self._sections: dict[str, SectionNegotiationState] = {}
        self._agent_usage: dict[str, AgentTokenUsage] = {}
        self._phase_usage: dict[str, PhaseTokenUsage] = {}

        # Timeline tracking
        self._run_started_at: Optional[datetime] = None
        self._run_ended_at: Optional[datetime] = None
        self._negotiation_round: int = 0
        self._temperature: float = 1.0

        # Event history for delta queries (bounded)
        self._event_history: list[HFSEvent] = []
        self._max_history: int = 1000

        # Stream handle for subscription
        self._stream: Optional[EventStream] = None
        self._processing_task: Optional[asyncio.Task] = None

        # Subscribers for state changes
        self._subscribers: list[tuple[ChangeCategory, Callable[[StateChange], Awaitable[None]]]] = []

    @property
    def version(self) -> int:
        """Current state version for cache invalidation."""
        return self._version

    async def start(self) -> None:
        """Subscribe to all events and start processing.

        Creates a wildcard subscription to receive all HFS events
        and starts a background task to process them.
        """
        self._stream = await self._event_bus.subscribe("*")
        self._processing_task = asyncio.create_task(self._process_events())

    async def stop(self) -> None:
        """Stop event processing and cleanup.

        Unsubscribes from the event bus and cancels the processing task.
        """
        if self._stream:
            await self._event_bus.unsubscribe(self._stream)
            self._stream = None
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

    def subscribe(
        self,
        callback: Callable[[StateChange], Awaitable[None]],
        category: ChangeCategory = None,  # type: ignore[assignment]
    ) -> Callable[[], None]:
        """Subscribe to state changes.

        Args:
            callback: Async function called on state changes
            category: Filter by change category (default: ALL)

        Returns:
            Unsubscribe function
        """
        # Import here to avoid circular import
        from hfs.state.query import ChangeCategory as CC

        if category is None:
            category = CC.ALL

        entry = (category, callback)
        self._subscribers.append(entry)

        def unsubscribe() -> None:
            if entry in self._subscribers:
                self._subscribers.remove(entry)

        return unsubscribe

    async def _notify_subscribers(self, category: ChangeCategory) -> None:
        """Notify subscribers of state change.

        Creates a StateChange notification and sends to all matching subscribers.
        Uses asyncio.create_task to avoid blocking event processing.

        Args:
            category: The category of change that occurred
        """
        from hfs.state.query import ChangeCategory as CC, StateChange

        change = StateChange(version=self._version, category=category)
        for sub_category, callback in list(self._subscribers):
            if sub_category == CC.ALL or sub_category == category:
                try:
                    asyncio.create_task(callback(change))
                except Exception:
                    pass  # Don't let one subscriber break others

    def _get_category_for_event(self, event: HFSEvent) -> Optional[ChangeCategory]:
        """Determine change category for an event.

        Args:
            event: The event to categorize

        Returns:
            The ChangeCategory for this event type, or None if unknown
        """
        from hfs.state.query import ChangeCategory as CC

        if event.event_type.startswith("agent."):
            return CC.AGENT_TREE
        elif event.event_type.startswith("negotiation."):
            return CC.NEGOTIATION
        elif event.event_type == "usage.recorded":
            return CC.USAGE
        elif event.event_type.startswith(("phase.", "run.")):
            return CC.TIMELINE
        return None

    async def _process_events(self) -> None:
        """Process events from stream, updating state.

        Continuously reads events from the subscription stream and applies
        them to internal state. Each event increments the version number
        and notifies subscribers of the change category.
        """
        if self._stream is None:
            return

        async for event in self._stream:
            self._apply_event(event)
            self._version += 1
            self._event_history.append(event)
            # Bound history size
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            # Notify subscribers
            category = self._get_category_for_event(event)
            if category is not None:
                await self._notify_subscribers(category)

    def _apply_event(self, event: HFSEvent) -> None:
        """Update internal state based on event type.

        Dispatches to appropriate handler based on event_type field.

        Args:
            event: The HFSEvent to process
        """
        handlers = {
            "run.started": self._handle_run_started,
            "run.ended": self._handle_run_ended,
            "phase.started": self._handle_phase_started,
            "phase.ended": self._handle_phase_ended,
            "agent.started": self._handle_agent_started,
            "agent.ended": self._handle_agent_ended,
            "negotiation.claimed": self._handle_negotiation_claimed,
            "negotiation.contested": self._handle_negotiation_contested,
            "negotiation.resolved": self._handle_negotiation_resolved,
            "usage.recorded": self._handle_usage_recorded,
        }
        handler = handlers.get(event.event_type)
        if handler:
            handler(event)

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _handle_run_started(self, event: HFSEvent) -> None:
        """Handle run.started event."""
        if isinstance(event, RunStartedEvent):
            self._run_id = event.run_id
            self._run_started_at = event.timestamp

    def _handle_run_ended(self, event: HFSEvent) -> None:
        """Handle run.ended event."""
        if isinstance(event, RunEndedEvent):
            self._run_ended_at = event.timestamp

    def _handle_phase_started(self, event: HFSEvent) -> None:
        """Handle phase.started event."""
        if isinstance(event, PhaseStartedEvent):
            self._phases[event.phase_id] = PhaseTimeline(
                phase_name=event.phase_name,
                started_at=event.timestamp,
            )

    def _handle_phase_ended(self, event: HFSEvent) -> None:
        """Handle phase.ended event."""
        if isinstance(event, PhaseEndedEvent):
            if event.phase_id in self._phases:
                phase = self._phases[event.phase_id]
                # Create new model with ended_at set (immutable pattern)
                self._phases[event.phase_id] = PhaseTimeline(
                    phase_name=phase.phase_name,
                    started_at=phase.started_at,
                    ended_at=event.timestamp,
                )

    def _handle_agent_started(self, event: HFSEvent) -> None:
        """Handle agent.started event."""
        if isinstance(event, AgentStartedEvent):
            # Ensure triad exists
            if event.triad_id not in self._triads:
                self._triads[event.triad_id] = TriadInfo(
                    triad_id=event.triad_id,
                    preset="unknown",  # Will be updated if triad info available
                )

            # Create or update agent
            agent = AgentNode(
                agent_id=event.agent_id,
                triad_id=event.triad_id,
                role=event.role,
                status=AgentStatus.WORKING,
                started_at=event.timestamp,
            )
            self._agents[event.agent_id] = agent

            # Add to triad's agent list
            triad = self._triads[event.triad_id]
            # Remove existing agent with same ID if present
            triad.agents = [a for a in triad.agents if a.agent_id != event.agent_id]
            triad.agents.append(agent)

    def _handle_agent_ended(self, event: HFSEvent) -> None:
        """Handle agent.ended event."""
        if isinstance(event, AgentEndedEvent):
            if event.agent_id in self._agents:
                old_agent = self._agents[event.agent_id]
                # Create new agent with updated status and ended_at
                agent = AgentNode(
                    agent_id=old_agent.agent_id,
                    triad_id=old_agent.triad_id,
                    role=old_agent.role,
                    status=AgentStatus.COMPLETE,
                    current_action=old_agent.current_action,
                    progress=old_agent.progress,
                    started_at=old_agent.started_at,
                    ended_at=event.timestamp,
                    blocking_reason=old_agent.blocking_reason,
                )
                self._agents[event.agent_id] = agent

                # Update in triad's agent list
                if old_agent.triad_id in self._triads:
                    triad = self._triads[old_agent.triad_id]
                    triad.agents = [
                        agent if a.agent_id == event.agent_id else a
                        for a in triad.agents
                    ]

    def _handle_negotiation_claimed(self, event: HFSEvent) -> None:
        """Handle negotiation.claimed event."""
        if isinstance(event, NegotiationClaimedEvent):
            section_name = event.section_name
            if section_name not in self._sections:
                # First claim - create section
                self._sections[section_name] = SectionNegotiationState(
                    section_name=section_name,
                    status="claimed",
                    owner=event.triad_id,
                    claimants=[event.triad_id],
                )
            else:
                # Add claimant to existing section
                section = self._sections[section_name]
                if event.triad_id not in section.claimants:
                    section.claimants.append(event.triad_id)
                    # If multiple claimants, status becomes contested
                    if len(section.claimants) > 1:
                        section.status = "contested"

    def _handle_negotiation_contested(self, event: HFSEvent) -> None:
        """Handle negotiation.contested event."""
        if isinstance(event, NegotiationContestedEvent):
            section_name = event.section_name
            self._negotiation_round += 1

            if section_name not in self._sections:
                self._sections[section_name] = SectionNegotiationState(
                    section_name=section_name,
                    status="contested",
                    claimants=event.claimants,
                )
            else:
                section = self._sections[section_name]
                section.status = "contested"
                section.claimants = event.claimants

            # Add to contest history
            section = self._sections[section_name]
            section.contest_history.append(
                ContestEvent(
                    round=self._negotiation_round,
                    claimants=event.claimants,
                )
            )

    def _handle_negotiation_resolved(self, event: HFSEvent) -> None:
        """Handle negotiation.resolved event."""
        if isinstance(event, NegotiationResolvedEvent):
            section_name = event.section_name
            if section_name in self._sections:
                section = self._sections[section_name]
                section.status = "claimed"
                section.owner = event.winner
                # Update latest contest with resolution
                if section.contest_history:
                    latest = section.contest_history[-1]
                    # Create new ContestEvent with resolution (immutable)
                    section.contest_history[-1] = ContestEvent(
                        round=latest.round,
                        claimants=latest.claimants,
                        resolution=event.resolution_type,
                        winner=event.winner,
                    )

    def _handle_usage_recorded(self, event: HFSEvent) -> None:
        """Handle usage.recorded event."""
        if isinstance(event, UsageEvent):
            triad_id = event.triad_id

            # Update agent usage (using triad_id as agent identifier)
            if triad_id not in self._agent_usage:
                self._agent_usage[triad_id] = AgentTokenUsage(agent_id=triad_id)

            usage = self._agent_usage[triad_id]
            # Create new usage with accumulated values
            self._agent_usage[triad_id] = AgentTokenUsage(
                agent_id=triad_id,
                prompt_tokens=usage.prompt_tokens + event.prompt_tokens,
                completion_tokens=usage.completion_tokens + event.completion_tokens,
            )

    # =========================================================================
    # Snapshot Builders
    # =========================================================================

    def build_agent_tree(self) -> AgentTree:
        """Build current AgentTree from indexed state.

        Returns:
            AgentTree with all triads and agents
        """
        return AgentTree(triads=list(self._triads.values()))

    def build_negotiation_snapshot(self) -> NegotiationSnapshot:
        """Build current NegotiationSnapshot.

        Returns:
            NegotiationSnapshot with all section states
        """
        return NegotiationSnapshot(
            temperature=self._temperature,
            round=self._negotiation_round,
            sections=list(self._sections.values()),
        )

    def build_token_usage(self) -> TokenUsageSummary:
        """Build TokenUsageSummary from tracked usage.

        Returns:
            TokenUsageSummary with by_phase and by_agent breakdowns
        """
        return TokenUsageSummary(
            by_phase=list(self._phase_usage.values()),
            by_agent=list(self._agent_usage.values()),
        )

    def build_trace_timeline(self) -> TraceTimeline:
        """Build TraceTimeline from tracked phases.

        Returns:
            TraceTimeline with all phase timings
        """
        return TraceTimeline(
            run_id=self._run_id or "",
            started_at=self._run_started_at or datetime.utcnow(),
            ended_at=self._run_ended_at,
            phases=list(self._phases.values()),
        )

    def build_snapshot(self) -> RunSnapshot:
        """Build complete RunSnapshot.

        Composes all sub-snapshots into a single queryable snapshot.

        Returns:
            RunSnapshot with full state
        """
        return RunSnapshot(
            version=self._version,
            run_id=self._run_id or "",
            agent_tree=self.build_agent_tree(),
            negotiation=self.build_negotiation_snapshot(),
            usage=self.build_token_usage(),
            timeline=self.build_trace_timeline(),
        )


__all__ = [
    "StateManager",
]
