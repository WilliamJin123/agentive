"""JSON import for HFS conversations.

This module provides JSON import functionality with automatic schema
migration support for forward compatibility.

Usage:
    from hfs.export import import_from_json

    json_content = Path("export.json").read_text()
    result = import_from_json(json_content)

    print(f"Session: {result.session_name}")
    print(f"Messages: {len(result.messages)}")
    if result.migrated:
        print(f"Migrated from v{result.original_version}")
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from .migration import CURRENT_VERSION, migrate_export


class ImportResult(BaseModel):
    """Result of a JSON import operation.

    Contains the imported session data and migration information.

    Attributes:
        session_name: Name of the imported session.
        messages: List of message dicts with role, content, created_at.
        migrated: True if migration was applied during import.
        original_version: Schema version of the import file before migration.
    """

    session_name: str
    messages: list[dict[str, Any]]
    migrated: bool
    original_version: str


def import_from_json(json_content: str) -> ImportResult:
    """Import conversation from JSON file.

    Handles schema migration automatically. Supports:
    - Current version JSON (no migration)
    - Older version JSON (migrated silently)
    - Legacy format without metadata (converted to current)

    Args:
        json_content: Raw JSON string from file.

    Returns:
        ImportResult with session_name, messages, migration info.

    Raises:
        ValueError: If JSON invalid or migration fails (future version).
        json.JSONDecodeError: If not valid JSON.

    Example:
        >>> json_content = '{"metadata": {...}, "messages": [...]}'
        >>> result = import_from_json(json_content)
        >>> result.session_name
        'My Session'
        >>> result.migrated
        False
    """
    # Parse JSON
    data = json.loads(json_content)

    # Get original version before migration
    original_version = data.get("metadata", {}).get("schema_version", "0.0.0")

    # Migrate to current version
    migrated_data = migrate_export(data)

    # Check if migration was applied
    was_migrated = original_version != CURRENT_VERSION

    return ImportResult(
        session_name=migrated_data["metadata"]["session_name"],
        messages=migrated_data.get("messages", []),
        migrated=was_migrated,
        original_version=original_version,
    )


__all__ = ["import_from_json", "ImportResult"]
