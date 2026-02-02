"""Event-driven checkpoint service for HFS.

This module provides the CheckpointService class that subscribes to EventBus
and creates checkpoints at key state changes. Checkpoints enable users to
list conversation history and rewind to previous states.

Checkpoint triggers:
    - run.ended: After each agent run completes
    - negotiation.resolved: When negotiation reaches resolution
    - phase.ended: At phase transitions
    - manual: User-initiated checkpoints

Usage:
    checkpoint_service = CheckpointService(event_bus, checkpoint_repo)
    await checkpoint_service.start()
    checkpoint_service.set_session(session_id, message_count)
    # Service auto-creates checkpoints on events
    await checkpoint_service.stop()
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hfs.events.bus import EventBus
    from hfs.events.models import HFSEvent
    from hfs.events.stream import EventStream
    from hfs.state.manager import StateManager

from .models import CheckpointModel
from .repository import CheckpointRepository

logger = logging.getLogger(__name__)


class CheckpointService:
    """Event-driven automatic checkpointing.

    Subscribes to EventBus and creates checkpoints at key state changes:
    - run.ended: After each agent run completes
    - negotiation.resolved: When negotiation reaches resolution
    - phase.ended: At phase transitions

    Attributes:
        CHECKPOINT_EVENTS: Set of event types that trigger checkpoints.
    """

    CHECKPOINT_EVENTS = {
        "run.ended",
        "negotiation.resolved",
        "phase.ended",
    }

    def __init__(
        self,
        event_bus: EventBus | None,
        checkpoint_repo: CheckpointRepository,
        state_manager: StateManager | None = None,
        retention_limit: int = 10,
    ) -> None:
        """Initialize the checkpoint service.

        Args:
            event_bus: EventBus for subscribing to events (None for no auto-checkpoints).
            checkpoint_repo: Repository for persisting checkpoints.
            state_manager: StateManager for getting state snapshots (optional).
            retention_limit: Maximum number of checkpoints to retain per session.
        """
        self._event_bus = event_bus
        self._checkpoint_repo = checkpoint_repo
        self._state_manager = state_manager
        self._retention_limit = retention_limit
        self._current_session_id: int | None = None
        self._current_message_index: int = 0
        self._stream: EventStream | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start listening for checkpoint events.

        Subscribes to the EventBus and starts processing events in a background task.
        Does nothing if no EventBus was provided.
        """
        if self._event_bus is None:
            logger.debug("CheckpointService: no event bus, skipping auto-checkpoints")
            return

        self._stream = await self._event_bus.subscribe("*")
        self._task = asyncio.create_task(self._process_events())
        logger.info("CheckpointService started listening for events")

    async def stop(self) -> None:
        """Stop listening and cleanup.

        Cancels the event processing task and unsubscribes from the EventBus.
        """
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._stream and self._event_bus:
            await self._event_bus.unsubscribe(self._stream)
            self._stream = None

        logger.info("CheckpointService stopped")

    def set_session(self, session_id: int, message_count: int) -> None:
        """Set current session for checkpoints.

        Args:
            session_id: ID of the session to create checkpoints for.
            message_count: Current number of messages in the session.
        """
        self._current_session_id = session_id
        self._current_message_index = message_count
        logger.debug(f"CheckpointService: session={session_id}, messages={message_count}")

    def increment_message_index(self) -> None:
        """Increment message index after each message.

        Should be called after adding each message to keep checkpoint
        positions accurate.
        """
        self._current_message_index += 1

    async def _process_events(self) -> None:
        """Process events and create checkpoints.

        Runs as a background task, iterating over events from the EventBus
        and creating checkpoints when checkpoint events occur.
        """
        if self._stream is None:
            return

        try:
            async for event in self._stream:
                if event.event_type in self.CHECKPOINT_EVENTS:
                    await self._create_checkpoint(event)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"CheckpointService event processing error: {e}")

    async def _create_checkpoint(self, event: HFSEvent) -> None:
        """Create checkpoint from event.

        Args:
            event: The event that triggered the checkpoint.
        """
        if self._current_session_id is None:
            logger.debug("CheckpointService: no session, skipping checkpoint")
            return

        # Get current state snapshot
        state_json = "{}"
        if self._state_manager:
            try:
                snapshot = self._state_manager.get_snapshot()
                if snapshot:
                    state_json = snapshot.model_dump_json()
            except Exception as e:
                logger.warning(f"Failed to get state snapshot: {e}")

        # Create checkpoint
        try:
            await self._checkpoint_repo.create(
                session_id=self._current_session_id,
                message_index=self._current_message_index,
                trigger_event=event.event_type,
                state_json=state_json,
            )
            logger.info(
                f"Created checkpoint: session={self._current_session_id}, "
                f"msg={self._current_message_index}, event={event.event_type}"
            )

            # Prune old checkpoints
            deleted = await self._checkpoint_repo.prune_oldest(
                self._current_session_id,
                self._retention_limit,
            )
            if deleted > 0:
                logger.debug(f"Pruned {deleted} old checkpoints")

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")

    async def create_manual_checkpoint(self, trigger: str = "manual") -> CheckpointModel | None:
        """Create a manual checkpoint.

        Args:
            trigger: Trigger label for the checkpoint (default "manual").

        Returns:
            Created CheckpointModel instance, or None if no session active.
        """
        if self._current_session_id is None:
            logger.warning("Cannot create manual checkpoint: no session")
            return None

        state_json = "{}"
        if self._state_manager:
            try:
                snapshot = self._state_manager.get_snapshot()
                if snapshot:
                    state_json = snapshot.model_dump_json()
            except Exception as e:
                logger.warning(f"Failed to get state snapshot: {e}")

        try:
            checkpoint = await self._checkpoint_repo.create(
                session_id=self._current_session_id,
                message_index=self._current_message_index,
                trigger_event=trigger,
                state_json=state_json,
            )
            logger.info(
                f"Created manual checkpoint: session={self._current_session_id}, "
                f"msg={self._current_message_index}"
            )

            # Prune old checkpoints
            await self._checkpoint_repo.prune_oldest(
                self._current_session_id,
                self._retention_limit,
            )

            return checkpoint
        except Exception as e:
            logger.error(f"Failed to create manual checkpoint: {e}")
            return None

    @property
    def current_session_id(self) -> int | None:
        """Get the current session ID."""
        return self._current_session_id

    @property
    def current_message_index(self) -> int:
        """Get the current message index."""
        return self._current_message_index


__all__ = [
    "CheckpointService",
]
