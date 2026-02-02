"""Session persistence module for HFS.

This module provides SQLAlchemy-based persistence for chat sessions and messages.
Uses async SQLite with WAL mode for concurrent access.

Exports:
    Base: SQLAlchemy declarative base
    SessionModel: Chat session ORM model
    MessageModel: Message ORM model
    CheckpointModel: Checkpoint ORM model for state snapshots
    create_db_engine: Factory for async SQLite engine
    get_session_factory: Factory for async session maker
    SessionRepository: CRUD operations for sessions
    CheckpointRepository: CRUD operations for checkpoints
"""

from .engine import create_db_engine, get_session_factory
from .models import Base, CheckpointModel, MessageModel, SessionModel
from .repository import CheckpointRepository, SessionRepository

__all__ = [
    "Base",
    "SessionModel",
    "MessageModel",
    "CheckpointModel",
    "create_db_engine",
    "get_session_factory",
    "SessionRepository",
    "CheckpointRepository",
]
