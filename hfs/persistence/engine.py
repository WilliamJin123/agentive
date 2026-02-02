"""Async SQLite engine for session persistence.

This module provides factory functions for creating async SQLAlchemy engines
and session factories. Uses SQLite with WAL mode for better concurrency.

Functions:
    create_db_engine: Create async engine with proper configuration
    get_session_factory: Create async session factory from engine
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

if TYPE_CHECKING:
    pass


async def create_db_engine(db_path: Path | None = None) -> AsyncEngine:
    """Create async SQLite engine with proper configuration.

    Creates the database file and parent directories if they don't exist.
    Enables WAL mode for better concurrency and creates all tables.

    Args:
        db_path: Path to SQLite database file. Defaults to ~/.hfs/sessions.db

    Returns:
        Configured AsyncEngine instance.
    """
    if db_path is None:
        db_path = Path.home() / ".hfs" / "sessions.db"

    # Create parent directories if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create async engine
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )

    # Enable WAL mode for better concurrency
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory from engine.

    Uses expire_on_commit=False to avoid async lazy loading issues.
    Each database operation should create a new session from this factory.

    Args:
        engine: AsyncEngine instance to create sessions from.

    Returns:
        Configured async_sessionmaker for creating AsyncSession instances.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
