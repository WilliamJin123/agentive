"""Export/import module for HFS conversations.

This module provides functionality to export conversations to markdown
(for sharing/documentation) and JSON (for backup/transfer), and to import
from JSON files with schema migration support.

Exports:
    export_to_markdown: Export conversation to readable markdown.
    export_to_json: Export conversation to versioned JSON.
    import_from_json: Import conversation from JSON file.
    migrate_export: Migrate export data to current schema version.
    EXPORT_SCHEMA_VERSION: Current export schema version.
    ImportResult: Result of JSON import operation.
    ExportMetadata: Metadata model for exports.
    SessionExport: Complete export model.

Usage:
    from hfs.export import export_to_markdown, export_to_json, import_from_json

    # Export to markdown
    md_content = export_to_markdown("My Session", messages)

    # Export to JSON
    json_content = export_to_json("My Session", messages, checkpoints=checkpoints)

    # Import from JSON
    result = import_from_json(json_content)
    print(f"Imported {len(result.messages)} messages")
"""

from .json_export import (
    EXPORT_SCHEMA_VERSION,
    ExportMetadata,
    SessionExport,
    export_to_json,
)
from .json_import import ImportResult, import_from_json
from .markdown import export_to_markdown
from .migration import migrate_export

__all__ = [
    # Markdown export
    "export_to_markdown",
    # JSON export
    "export_to_json",
    "EXPORT_SCHEMA_VERSION",
    "ExportMetadata",
    "SessionExport",
    # JSON import
    "import_from_json",
    "ImportResult",
    # Migration
    "migrate_export",
]
