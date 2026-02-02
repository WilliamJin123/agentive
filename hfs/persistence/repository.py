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

from .models import MessageModel, SessionModel

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
