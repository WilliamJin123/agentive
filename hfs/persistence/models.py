"""SQLAlchemy ORM models for session persistence.

This module defines the database schema for storing chat sessions and messages.
Uses SQLAlchemy 2.x style with Mapped[], mapped_column(), and relationship().

Models:
    Base: DeclarativeBase with AsyncAttrs for async context support
    SessionModel: Chat session with name and timestamps
    MessageModel: Individual message within a session
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models.

    Inherits from AsyncAttrs for async context support and DeclarativeBase
    for SQLAlchemy 2.x declarative mapping.
    """

    pass


class SessionModel(Base):
    """Chat session model.

    Stores metadata about a conversation session, including auto-generated
    name from the first message.

    Attributes:
        id: Primary key.
        name: Session name (auto-generated from first message).
        created_at: When the session was created.
        updated_at: When the session was last updated.
        messages: Relationship to messages in this session.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime]
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="session",
        lazy="selectin",  # Eager load to avoid async issues
        cascade="all, delete-orphan",
    )


class MessageModel(Base):
    """Message model.

    Stores individual messages within a session, including role (user,
    assistant, system) and content.

    Attributes:
        id: Primary key.
        session_id: Foreign key to parent session.
        role: Message role (user, assistant, system).
        content: Message content text.
        created_at: When the message was created.
        session: Relationship back to parent session.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(50))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime]

    session: Mapped["SessionModel"] = relationship(back_populates="messages")
