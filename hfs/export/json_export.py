"""JSON export for HFS conversations.

This module provides versioned JSON export functionality for chat sessions.
The schema version enables forward-compatible imports through migration.

Usage:
    from hfs.export import export_to_json, EXPORT_SCHEMA_VERSION

    content = export_to_json(
        session_name="My Session",
        messages=[{"role": "user", "content": "Hello", "created_at": "2026-02-01T10:00:00"}],
        checkpoints=[{"trigger": "run.ended", "message_index": 2}],
    )
    Path("export.json").write_text(content)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from hfs.state.models import RunSnapshot


# Schema version for export format
# Increment on breaking changes, add migrations in migration.py
EXPORT_SCHEMA_VERSION = "1.0.0"


def _get_hfs_version() -> str:
    """Get the current HFS version string.

    Returns:
        Version string from package or "unknown" if not available.
    """
    try:
        from hfs import __version__

        return __version__
    except (ImportError, AttributeError):
        return "unknown"


class ExportMetadata(BaseModel):
    """Metadata block for exported sessions.

    Contains versioning information for migration support and
    general export metadata.

    Attributes:
        schema_version: Export format version for migration compatibility.
        exported_at: ISO timestamp when export was created.
        hfs_version: HFS application version that created the export.
        session_name: Name of the exported session.
    """

    schema_version: str = EXPORT_SCHEMA_VERSION
    exported_at: datetime
    hfs_version: str
    session_name: str


class SessionExport(BaseModel):
    """Complete session export structure.

    Top-level model containing all exported session data.

    Attributes:
        metadata: Export metadata including version info.
        messages: List of message dicts with role, content, created_at.
        checkpoints: Optional list of checkpoint dicts.
        run_snapshot: Optional serialized RunSnapshot state.
    """

    metadata: ExportMetadata
    messages: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]] | None = None
    run_snapshot: dict[str, Any] | None = None


def export_to_json(
    session_name: str,
    messages: list[dict[str, Any]],
    run_snapshot: RunSnapshot | None = None,
    checkpoints: list[dict[str, Any]] | None = None,
) -> str:
    """Export session to JSON with schema version.

    Creates a versioned JSON document that can be imported later,
    with migration support for schema changes.

    Args:
        session_name: Name of the session being exported.
        messages: List of message dicts with role, content, created_at.
        run_snapshot: Optional RunSnapshot for full state.
        checkpoints: Optional list of checkpoint dicts.

    Returns:
        Pretty-printed JSON string (indent=2) ready to write to file.

    Example output:
        {
          "metadata": {
            "schema_version": "1.0.0",
            "exported_at": "2026-02-01T10:30:00",
            "hfs_version": "1.0.0",
            "session_name": "My Session"
          },
          "messages": [
            {"role": "user", "content": "Hello", "created_at": "..."}
          ],
          "checkpoints": null,
          "run_snapshot": null
        }
    """
    # Build metadata
    metadata = ExportMetadata(
        schema_version=EXPORT_SCHEMA_VERSION,
        exported_at=datetime.now(),
        hfs_version=_get_hfs_version(),
        session_name=session_name,
    )

    # Serialize run_snapshot if provided
    snapshot_dict = None
    if run_snapshot:
        snapshot_dict = run_snapshot.model_dump(mode="json")

    # Build export structure
    export = SessionExport(
        metadata=metadata,
        messages=messages,
        checkpoints=checkpoints,
        run_snapshot=snapshot_dict,
    )

    # Serialize to pretty JSON
    return export.model_dump_json(indent=2)


__all__ = ["export_to_json", "EXPORT_SCHEMA_VERSION", "ExportMetadata", "SessionExport"]
