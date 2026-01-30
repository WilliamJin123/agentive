"""Markdown parsing utilities for work items and IP markers.

This module provides pure functions for parsing and modifying markdown
work items with inline IP markers (e.g., `- [ ] Task [IP:agent-1]`).

All functions are side-effect free and handle edge cases gracefully.
"""

import re
from typing import Optional, Tuple

from .schemas import WorkItem

# Regex for work item with optional IP marker
# Matches: `- [ ] Task description [IP:agent-id]`
# Groups:
#   1: Prefix including checkbox opener (`- [` with optional leading whitespace)
#   2: Checkbox state (space, x, or X)
#   3: Checkbox closer and space (`] `)
#   4: Task description text
#   5: Full IP marker with brackets (optional, e.g., ` [IP:agent-1]`)
#   6: Agent ID from IP marker (optional, e.g., `agent-1`)
WORK_ITEM_PATTERN = re.compile(
    r'^(\s*-\s*\[)([ xX])(\]\s*)(.+?)(\s*\[IP:([^\]]+)\])?\s*$'
)

# Pattern for extracting IP marker from any line
IP_MARKER_PATTERN = re.compile(r'\s*\[IP:[^\]]+\]\s*$')


def parse_work_item(line: str, line_num: int = 0) -> Optional[WorkItem]:
    """Parse a markdown line into a WorkItem if it matches the pattern.

    Args:
        line: A single line of markdown text
        line_num: Line number in the source file (0-indexed)

    Returns:
        WorkItem if line matches work item pattern, None otherwise

    Examples:
        >>> parse_work_item("- [ ] Build auth module")
        WorkItem(description='Build auth module', status='available', ...)

        >>> parse_work_item("- [x] Setup CI/CD [IP:agent-1]")
        WorkItem(description='Setup CI/CD', status='completed', ...)

        >>> parse_work_item("Not a work item")
        None
    """
    if not line or not line.strip():
        return None

    match = WORK_ITEM_PATTERN.match(line)
    if not match:
        return None

    checkbox_state = match.group(2)
    description = match.group(4).strip()
    agent_id = match.group(6)  # May be None

    return WorkItem(
        description=description,
        claimed_by=agent_id,
        line_number=line_num,
        is_complete=checkbox_state.lower() == 'x',
        raw_line=line,
    )


def add_ip_marker(line: str, agent_id: str) -> str:
    """Add IP marker to a work item line.

    Removes any existing IP marker first to avoid duplicates,
    then appends the new marker.

    Args:
        line: Original work item line
        agent_id: Agent ID to add as IP marker

    Returns:
        Line with IP marker appended

    Examples:
        >>> add_ip_marker("- [ ] Build auth", "agent-1")
        '- [ ] Build auth [IP:agent-1]'

        >>> add_ip_marker("- [ ] Build auth [IP:old-agent]", "new-agent")
        '- [ ] Build auth [IP:new-agent]'
    """
    if not line:
        return f"[IP:{agent_id}]"

    # Remove existing IP marker if present
    cleaned = remove_ip_marker(line)
    return f"{cleaned} [IP:{agent_id}]"


def remove_ip_marker(line: str) -> str:
    """Remove IP marker from a work item line.

    Args:
        line: Work item line that may contain IP marker

    Returns:
        Line with IP marker removed, trailing whitespace trimmed

    Examples:
        >>> remove_ip_marker("- [ ] Build auth [IP:agent-1]")
        '- [ ] Build auth'

        >>> remove_ip_marker("- [ ] Build auth")
        '- [ ] Build auth'
    """
    if not line:
        return ""

    return IP_MARKER_PATTERN.sub('', line).rstrip()


def mark_complete(line: str) -> str:
    """Mark a work item as complete by checking its checkbox.

    Changes `- [ ]` to `- [x]` and removes any IP marker
    (completed items don't need claims).

    Args:
        line: Work item line to mark complete

    Returns:
        Line with checkbox checked and IP marker removed

    Examples:
        >>> mark_complete("- [ ] Build auth [IP:agent-1]")
        '- [x] Build auth'

        >>> mark_complete("- [x] Already done")
        '- [x] Already done'
    """
    if not line:
        return ""

    # Remove IP marker first
    cleaned = remove_ip_marker(line)

    # Change [ ] to [x]
    # Handle various checkbox formats: [ ], [X], [x]
    result = re.sub(r'(\s*-\s*\[)[ ](\])', r'\1x\2', cleaned)

    return result


def get_section_range(content: str, section_name: str) -> Tuple[int, int]:
    """Find start and end line numbers for a markdown section.

    Sections are identified by `## Section Name` headers.
    The range includes the header line and all content until
    the next section header or end of file.

    Args:
        content: Full markdown content
        section_name: Name of the section to find (case-insensitive)

    Returns:
        Tuple of (start_line, end_line) both 0-indexed.
        Returns (-1, -1) if section not found.

    Examples:
        >>> content = "# Title\\n## Section A\\nContent\\n## Section B\\n"
        >>> get_section_range(content, "Section A")
        (1, 3)  # Lines 1-2 (header + content), line 3 is next section
    """
    if not content or not section_name:
        return (-1, -1)

    lines = content.split('\n')
    section_pattern = re.compile(rf'^##\s+{re.escape(section_name)}\s*$', re.IGNORECASE)
    next_section_pattern = re.compile(r'^##\s+', re.IGNORECASE)

    start_line = -1
    end_line = len(lines)

    for i, line in enumerate(lines):
        if start_line == -1:
            # Looking for start
            if section_pattern.match(line):
                start_line = i
        else:
            # Looking for end (next section)
            if next_section_pattern.match(line):
                end_line = i
                break

    if start_line == -1:
        return (-1, -1)

    return (start_line, end_line)


def extract_section(content: str, section_name: str) -> str:
    """Get content of a named markdown section.

    Extracts all text between the section header and the next
    section header (or end of file).

    Args:
        content: Full markdown content
        section_name: Name of the section to extract

    Returns:
        Section content including header, or empty string if not found

    Examples:
        >>> content = "## Section A\\nLine 1\\nLine 2\\n## Section B\\n"
        >>> extract_section(content, "Section A")
        '## Section A\\nLine 1\\nLine 2'
    """
    if not content or not section_name:
        return ""

    start, end = get_section_range(content, section_name)
    if start == -1:
        return ""

    lines = content.split('\n')
    section_lines = lines[start:end]

    # Remove trailing empty lines
    while section_lines and not section_lines[-1].strip():
        section_lines.pop()

    return '\n'.join(section_lines)
