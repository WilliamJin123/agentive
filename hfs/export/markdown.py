"""Markdown export for HFS conversations.

This module provides functionality to export chat sessions to readable
markdown format with full trace information including agents, tokens,
and timing.

Usage:
    from hfs.export import export_to_markdown

    content = export_to_markdown(
        session_name="My Session",
        messages=[{"role": "user", "content": "Hello", "created_at": "2026-02-01T10:00:00"}],
        run_snapshot=snapshot,  # optional
    )
    Path("export.md").write_text(content)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hfs.state.models import RunSnapshot


def export_to_markdown(
    session_name: str,
    messages: list[dict[str, Any]],
    run_snapshot: RunSnapshot | None = None,
) -> str:
    """Export conversation to markdown with full trace.

    Creates a human-readable markdown document containing the conversation
    history and optional agent activity trace.

    Args:
        session_name: Name of the session being exported.
        messages: List of message dicts with role, content, created_at.
        run_snapshot: Optional RunSnapshot for agent/token/timing info.

    Returns:
        Formatted markdown string ready to be written to a file.

    Example output:
        # HFS Session: My Session

        **Exported:** 2026-02-01 10:30:00
        **Messages:** 5

        ## Conversation

        ### User
        Hello, how are you?

        ### Assistant
        I'm doing well, thank you!
    """
    lines: list[str] = []

    # Header
    lines.append(f"# HFS Session: {session_name}")
    lines.append("")

    # Metadata
    export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"**Exported:** {export_time}")
    lines.append(f"**Messages:** {len(messages)}")

    # Run snapshot info (tokens, timing)
    if run_snapshot:
        total_tokens = run_snapshot.usage.total_tokens
        if total_tokens > 0:
            lines.append(f"**Tokens:** {total_tokens}")

        duration_ms = run_snapshot.timeline.total_duration_ms
        if duration_ms is not None:
            lines.append(f"**Duration:** {duration_ms:.0f}ms")

    lines.append("")

    # Agent Activity section (if snapshot has agent info)
    if run_snapshot and run_snapshot.agent_tree.triads:
        lines.append("## Agent Activity")
        lines.append("")

        for triad in run_snapshot.agent_tree.triads:
            lines.append(f"### Triad: {triad.triad_id} ({triad.preset})")
            for agent in triad.agents:
                status = agent.status.value
                lines.append(f"- {agent.role}: {status}")
            lines.append("")

    # Conversation section
    lines.append("## Conversation")
    lines.append("")

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Format role as header
        role_display = role.capitalize()
        if role == "user":
            lines.append("### User")
        elif role == "assistant":
            lines.append("### Assistant")
        elif role == "system":
            lines.append("### System")
        else:
            lines.append(f"### {role_display}")

        lines.append(content)
        lines.append("")

    return "\n".join(lines)


__all__ = ["export_to_markdown"]
