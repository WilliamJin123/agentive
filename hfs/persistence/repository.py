"""Repository for session persistence CRUD operations.

This module provides the SessionRepository class for creating, reading,
updating, and deleting chat sessions and messages.

Classes:
    SessionRepository: CRUD operations for sessions and messages
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from .models import CheckpointModel, MessageModel, SessionModel

# Placeholder name for new sessions (updated on first message)
PLACEHOLDER_NAME = "New Session"


class SessionRepository:
    """Repository for session and message CRUD operations.

    Uses async context managers for database operations to ensure proper
    session lifecycle management.

    Args:
        session_factory: Async session factory for creating database sessions.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize repository with session factory.

        Args:
            session_factory: Factory for creating async database sessions.
        """
        self._session_factory = session_factory

    async def create(self, name: str | None = None) -> SessionModel:
        """Create a new session.

        Args:
            name: Session name. If None, uses placeholder (updated on first message).

        Returns:
            Created SessionModel instance with ID.
        """
        async with self._session_factory() as session:
            async with session.begin():
                db_session = SessionModel(
                    name=name or PLACEHOLDER_NAME,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(db_session)
                await session.flush()  # Get ID
                # Return a detached copy with ID
                session_id = db_session.id
                session_name = db_session.name
                created_at = db_session.created_at

        # Return new instance (detached from session)
        result = SessionModel(
            name=session_name,
            created_at=created_at,
        )
        result.id = session_id
        return result

    async def get(self, session_id: int) -> SessionModel | None:
        """Get a session by ID with messages loaded.

        Args:
            session_id: ID of the session to retrieve.

        Returns:
            SessionModel with messages loaded, or None if not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(SessionModel)
                .options(selectinload(SessionModel.messages))
                .where(SessionModel.id == session_id)
            )
            db_session = result.scalar_one_or_none()
            if db_session:
                # Ensure messages are loaded before returning
                _ = db_session.messages
            return db_session

    async def list_recent(self, limit: int = 20) -> list[SessionModel]:
        """List recent sessions ordered by creation date.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of SessionModel instances (messages not loaded).
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(SessionModel)
                .options(selectinload(SessionModel.messages))
                .order_by(SessionModel.created_at.desc())
                .limit(limit)
            )
            sessions = result.scalars().all()
            # Force load messages for count
            for s in sessions:
                _ = s.messages
            return list(sessions)

    async def rename(self, session_id: int, new_name: str) -> SessionModel | None:
        """Rename a session.

        Args:
            session_id: ID of the session to rename.
            new_name: New name for the session.

        Returns:
            Updated SessionModel, or None if not found.
        """
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(SessionModel).where(SessionModel.id == session_id)
                )
                db_session = result.scalar_one_or_none()
                if db_session is None:
                    return None

                db_session.name = new_name
                db_session.updated_at = datetime.now(timezone.utc)
                await session.flush()

                # Return copy of updated data
                return db_session

    async def add_message(
        self, session_id: int, role: str, content: str
    ) -> MessageModel | None:
        """Add a message to a session.

        If this is the first user message and the session has a placeholder name,
        generates a name from the message content and timestamp.

        Args:
            session_id: ID of the session to add message to.
            role: Message role (user, assistant, system).
            content: Message content text.

        Returns:
            Created MessageModel instance, or None if session not found.
        """
        async with self._session_factory() as session:
            async with session.begin():
                # Get session
                result = await session.execute(
                    select(SessionModel)
                    .options(selectinload(SessionModel.messages))
                    .where(SessionModel.id == session_id)
                )
                db_session = result.scalar_one_or_none()
                if db_session is None:
                    return None

                # Create message
                now = datetime.now(timezone.utc)
                message = MessageModel(
                    session_id=session_id,
                    role=role,
                    content=content,
                    created_at=now,
                )
                session.add(message)

                # Update session timestamp
                db_session.updated_at = now

                # Auto-generate name on first user message if placeholder
                if role == "user" and db_session.name == PLACEHOLDER_NAME:
                    # First 30 chars of message + timestamp
                    truncated = content[:30].strip()
                    if len(content) > 30:
                        truncated += "..."
                    timestamp = now.strftime("%Y-%m-%d_%H-%M")
                    db_session.name = f"{truncated} - {timestamp}"

                await session.flush()
                return message

    async def delete(self, session_id: int) -> bool:
        """Delete a session and all its messages.

        Args:
            session_id: ID of the session to delete.

        Returns:
            True if session was deleted, False if not found.
        """
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(SessionModel).where(SessionModel.id == session_id)
                )
                db_session = result.scalar_one_or_none()
                if db_session is None:
                    return False

                await session.delete(db_session)
                return True


class CheckpointRepository:
    """Repository for checkpoint CRUD operations.

    Provides methods for creating, listing, and pruning checkpoints
    within a session. Checkpoints capture state at key moments.

    Args:
        session_factory: Async session factory for creating database sessions.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize repository with session factory.

        Args:
            session_factory: Factory for creating async database sessions.
        """
        self._session_factory = session_factory

    async def create(
        self,
        session_id: int,
        message_index: int,
        trigger_event: str,
        state_json: str,
    ) -> CheckpointModel:
        """Create a new checkpoint.

        Args:
            session_id: ID of the session this checkpoint belongs to.
            message_index: Position in conversation (for timeline display).
            trigger_event: Event that triggered the checkpoint.
            state_json: Serialized state snapshot.

        Returns:
            Created CheckpointModel instance with ID.
        """
        async with self._session_factory() as session:
            async with session.begin():
                checkpoint = CheckpointModel(
                    session_id=session_id,
                    message_index=message_index,
                    trigger_event=trigger_event,
                    state_json=state_json,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(checkpoint)
                await session.flush()
                # Return a detached copy
                checkpoint_id = checkpoint.id
                checkpoint_session_id = checkpoint.session_id
                checkpoint_message_index = checkpoint.message_index
                checkpoint_trigger_event = checkpoint.trigger_event
                checkpoint_state_json = checkpoint.state_json
                checkpoint_created_at = checkpoint.created_at

        # Return new instance (detached from session)
        result = CheckpointModel(
            session_id=checkpoint_session_id,
            message_index=checkpoint_message_index,
            trigger_event=checkpoint_trigger_event,
            state_json=checkpoint_state_json,
            created_at=checkpoint_created_at,
        )
        result.id = checkpoint_id
        return result

    async def list_for_session(self, session_id: int) -> list[CheckpointModel]:
        """List all checkpoints for a session ordered by message index.

        Args:
            session_id: ID of the session to get checkpoints for.

        Returns:
            List of CheckpointModel instances ordered by message_index ASC.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointModel)
                .where(CheckpointModel.session_id == session_id)
                .order_by(CheckpointModel.message_index.asc())
            )
            return list(result.scalars().all())

    async def get(self, checkpoint_id: int) -> CheckpointModel | None:
        """Get a checkpoint by ID.

        Args:
            checkpoint_id: ID of the checkpoint to retrieve.

        Returns:
            CheckpointModel instance, or None if not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointModel).where(CheckpointModel.id == checkpoint_id)
            )
            return result.scalar_one_or_none()

    async def prune_oldest(self, session_id: int, keep_count: int) -> int:
        """Delete oldest checkpoints beyond the keep_count limit.

        Args:
            session_id: ID of the session to prune checkpoints for.
            keep_count: Number of most recent checkpoints to keep.

        Returns:
            Number of checkpoints deleted.
        """
        async with self._session_factory() as session:
            async with session.begin():
                # Get all checkpoints for session ordered by created_at DESC
                result = await session.execute(
                    select(CheckpointModel)
                    .where(CheckpointModel.session_id == session_id)
                    .order_by(CheckpointModel.created_at.desc())
                )
                checkpoints = list(result.scalars().all())

                # Delete oldest beyond keep_count
                if len(checkpoints) <= keep_count:
                    return 0

                to_delete = checkpoints[keep_count:]
                for cp in to_delete:
                    await session.delete(cp)

                return len(to_delete)
