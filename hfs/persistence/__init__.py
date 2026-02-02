"""Session persistence module for HFS.

This module provides SQLAlchemy-based persistence for chat sessions and messages.
Uses async SQLite with WAL mode for concurrent access.

Exports:
    Base: SQLAlchemy declarative base
    SessionModel: Chat session ORM model
    MessageModel: Message ORM model
    create_db_engine: Factory for async SQLite engine
    get_session_factory: Factory for async session maker
    SessionRepository: CRUD operations for sessions
"""

from .engine import create_db_engine, get_session_factory
from .models import Base, MessageModel, SessionModel
from .repository import SessionRepository

__all__ = [
    "Base",
    "SessionModel",
    "MessageModel",
    "create_db_engine",
    "get_session_factory",
    "SessionRepository",
]
