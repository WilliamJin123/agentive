"""Schema migration for HFS export files.

This module handles versioned migration of exported JSON files to ensure
forward compatibility as the schema evolves.

Usage:
    from hfs.export.migration import migrate_export, CURRENT_VERSION

    # Migrate old export to current version
    migrated_data = migrate_export(old_data)

Migration strategy:
    - Each schema version has a migration function to the next version
    - Migrations are applied sequentially until current version is reached
    - Future versions raise ValueError (user needs to upgrade HFS)
    - Missing metadata is handled gracefully (legacy format support)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Current schema version - must match EXPORT_SCHEMA_VERSION in json_export.py
CURRENT_VERSION = "1.0.0"


def _compare_versions(v1: str, v2: str) -> int:
    """Compare two semantic version strings.

    Args:
        v1: First version string (e.g., "1.0.0").
        v2: Second version string (e.g., "1.1.0").

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2.
    """
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]

    # Pad shorter version with zeros
    while len(parts1) < len(parts2):
        parts1.append(0)
    while len(parts2) < len(parts1):
        parts2.append(0)

    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        if p1 > p2:
            return 1
    return 0


def migrate_export(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate export data to current schema version.

    Handles version differences automatically by applying sequential
    migrations. Supports graceful handling of:
    - Missing metadata (legacy format)
    - Older versions (apply migrations)
    - Current version (no-op)
    - Future versions (raise error)

    Args:
        data: Raw JSON data from import file.

    Returns:
        Migrated data compatible with current version.

    Raises:
        ValueError: If migration not possible (future version).

    Example:
        >>> data = {"messages": [{"role": "user", "content": "Hi"}]}
        >>> migrated = migrate_export(data)
        >>> migrated["metadata"]["schema_version"]
        '1.0.0'
    """
    # Handle very old versions without metadata
    if "metadata" not in data:
        data = _migrate_legacy_format(data)
        # After legacy migration, we have metadata at CURRENT_VERSION
        return data

    version = data.get("metadata", {}).get("schema_version", "0.0.0")

    # Already current version - no migration needed
    if version == CURRENT_VERSION:
        return data

    # Check if version is newer than we support
    if _compare_versions(version, CURRENT_VERSION) > 0:
        raise ValueError(
            f"Export version {version} is newer than supported {CURRENT_VERSION}. "
            "Please upgrade HFS."
        )

    # Apply sequential migrations
    # Future: Add migration functions as schema evolves
    # if _compare_versions(version, "0.9.0") <= 0:
    #     data = _migrate_0_9_to_1_0(data)
    #     version = "1.0.0"

    # Update version in metadata to current
    data["metadata"]["schema_version"] = CURRENT_VERSION

    return data


def _migrate_legacy_format(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy format (no metadata) to current schema.

    Legacy exports might just have a messages array without
    proper metadata structure.

    Args:
        data: Legacy export data without metadata block.

    Returns:
        Data with proper metadata structure at current version.
    """
    # Extract messages (might be at root or nested)
    messages = data.get("messages", [])

    # Build proper structure with metadata
    return {
        "metadata": {
            "schema_version": CURRENT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "hfs_version": "unknown",
            "session_name": "Imported Session",
        },
        "messages": messages,
        "checkpoints": data.get("checkpoints"),
        "run_snapshot": data.get("run_snapshot"),
    }


# Future migration functions would go here:
# def _migrate_0_9_to_1_0(data: dict[str, Any]) -> dict[str, Any]:
#     """Migrate from 0.9.0 to 1.0.0 schema."""
#     # Example: rename field, add new required field, etc.
#     return data


__all__ = ["migrate_export", "CURRENT_VERSION"]
