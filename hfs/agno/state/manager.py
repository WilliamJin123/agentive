"""SharedStateManager - Async file I/O with write serialization.

This module provides the SharedStateManager class for multi-agent
coordination via markdown state files. Reads are non-blocking,
writes queue up and execute in FIFO order via asyncio.Lock.
"""

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from .schemas import WorkItem, WorkItemStatus
from .parser import (
    parse_work_item,
    add_ip_marker,
    remove_ip_marker,
    mark_complete,
    extract_section,
    get_section_range,
)


class SharedStateManager:
    """Manages shared state file with async I/O and write serialization.

    Reads are non-blocking (per CONTEXT.md).
    Writes queue up and execute in FIFO order via asyncio.Lock.

    State file structure:
    - # Shared State
    - ## Available Work Items
    - ## In Progress
    - ## Completed
    - ## Agent Registry
    """

    DEFAULT_TIMEOUT = 30.0  # seconds
    DEFAULT_STATE_PATH = Path(".hfs/state.md")
    AGENTS_DIR = Path(".hfs/agents")

    def __init__(
        self,
        state_path: Optional[Path] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT,
    ):
        """Initialize SharedStateManager.

        Args:
            state_path: Path to state file. Defaults to .hfs/state.md
            timeout_seconds: Timeout for acquiring write lock. Defaults to 30s.
        """
        self._state_path = Path(state_path) if state_path else self.DEFAULT_STATE_PATH
        self._timeout = timeout_seconds
        self._write_lock = asyncio.Lock()

    # ========================================================================
    # Core Read/Write Operations
    # ========================================================================

    async def read_state(self) -> str:
        """Read current state without locking.

        Non-blocking - multiple agents can read concurrently.
        Returns initial template if file doesn't exist.

        Returns:
            Raw markdown content of state file
        """
        if not self._state_path.exists():
            return self._get_initial_template()

        async with aiofiles.open(self._state_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def write_state(self, content: str) -> Dict[str, Any]:
        """Write state with FIFO-queued locking.

        Queues behind other pending writes. Times out if lock
        not acquired within configured timeout.

        Args:
            content: New state file content

        Returns:
            {"success": True} on success
            {"success": False, "reason": "lock_timeout", "hint": "..."} on timeout
            {"success": False, "reason": "write_error", "error": "..."} on error
        """
        try:
            await asyncio.wait_for(
                self._write_lock.acquire(),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "reason": "lock_timeout",
                "hint": f"Could not acquire write lock within {self._timeout}s. Other writes may be queued.",
            }

        try:
            # Ensure directory exists
            self._state_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write via temp file + rename
            temp_path = self._state_path.with_suffix('.tmp')
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            # Rename is atomic on most filesystems
            temp_path.replace(self._state_path)

            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "reason": "write_error",
                "error": str(e),
            }
        finally:
            self._write_lock.release()

    # ========================================================================
    # Work Item Operations
    # ========================================================================

    async def get_work_items(self, status: Optional[str] = None) -> List[WorkItem]:
        """Parse and filter work items from state.

        Args:
            status: Filter by status ('available', 'in_progress', 'completed')
                   or None for all items

        Returns:
            List of WorkItem objects matching the filter
        """
        content = await self.read_state()
        items = self._parse_work_items(content)

        if status:
            items = [i for i in items if i.status.value == status]

        return items

    async def claim_item(
        self,
        description: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Claim a work item (read-modify-write with lock).

        Args:
            description: Work item description to match
            agent_id: Agent ID to mark as claimer

        Returns:
            Success dict with item info, or error dict with reason
        """
        content = await self.read_state()
        lines = content.split('\n')
        found = False
        modified_line = None
        item_line_num = -1

        for i, line in enumerate(lines):
            item = parse_work_item(line, i)
            if item and item.description == description:
                if item.status != WorkItemStatus.AVAILABLE:
                    return {
                        "success": False,
                        "reason": "not_available",
                        "description": description,
                        "current_status": item.status.value,
                        "claimed_by": item.claimed_by,
                        "hint": f"Item is {item.status.value}, not available for claiming.",
                    }
                # Add IP marker
                lines[i] = add_ip_marker(line, agent_id)
                modified_line = lines[i]
                item_line_num = i
                found = True
                break

        if not found:
            return {
                "success": False,
                "reason": "not_found",
                "description": description,
                "hint": "Work item not found. Check description spelling.",
            }

        # Write modified state
        new_content = '\n'.join(lines)
        result = await self.write_state(new_content)

        if result["success"]:
            return {
                "success": True,
                "message": f"Claimed: {description}",
                "description": description,
                "claimed_by": agent_id,
                "status": "in_progress",
            }
        return result

    async def complete_item(
        self,
        description: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Mark a work item as complete.

        Verifies the caller owns the item (has claim) before completing.

        Args:
            description: Work item description to match
            agent_id: Agent ID that should own the item

        Returns:
            Success dict with item info, or error dict with reason
        """
        content = await self.read_state()
        lines = content.split('\n')
        found = False

        for i, line in enumerate(lines):
            item = parse_work_item(line, i)
            if item and item.description == description:
                if item.claimed_by != agent_id:
                    return {
                        "success": False,
                        "reason": "not_owner",
                        "description": description,
                        "claimed_by": item.claimed_by,
                        "hint": f"You ({agent_id}) don't own this item. Claimed by: {item.claimed_by or 'nobody'}",
                    }
                if item.is_complete:
                    return {
                        "success": False,
                        "reason": "already_complete",
                        "description": description,
                        "hint": "Item is already marked complete.",
                    }
                # Mark complete (removes IP marker)
                lines[i] = mark_complete(line)
                found = True
                break

        if not found:
            return {
                "success": False,
                "reason": "not_found",
                "description": description,
                "hint": "Work item not found. Check description spelling.",
            }

        # Write modified state
        new_content = '\n'.join(lines)
        result = await self.write_state(new_content)

        if result["success"]:
            return {
                "success": True,
                "message": f"Completed: {description}",
                "description": description,
                "status": "completed",
            }
        return result

    async def release_item(
        self,
        description: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Release a claimed work item.

        Removes IP marker from item the caller has claimed.

        Args:
            description: Work item description to match
            agent_id: Agent ID that should own the item

        Returns:
            Success dict with item info, or error dict with reason
        """
        content = await self.read_state()
        lines = content.split('\n')
        found = False

        for i, line in enumerate(lines):
            item = parse_work_item(line, i)
            if item and item.description == description:
                if item.claimed_by != agent_id:
                    return {
                        "success": False,
                        "reason": "not_owner",
                        "description": description,
                        "claimed_by": item.claimed_by,
                        "hint": f"You ({agent_id}) don't own this item. Claimed by: {item.claimed_by or 'nobody'}",
                    }
                # Remove IP marker
                lines[i] = remove_ip_marker(line)
                found = True
                break

        if not found:
            return {
                "success": False,
                "reason": "not_found",
                "description": description,
                "hint": "Work item not found. Check description spelling.",
            }

        # Write modified state
        new_content = '\n'.join(lines)
        result = await self.write_state(new_content)

        if result["success"]:
            return {
                "success": True,
                "message": f"Released: {description}",
                "description": description,
                "status": "available",
            }
        return result

    async def add_item(self, description: str) -> Dict[str, Any]:
        """Add a new work item to the Available section.

        Args:
            description: Work item description

        Returns:
            Success dict with item info, or error dict with reason
        """
        content = await self.read_state()
        lines = content.split('\n')

        # Find "## Available Work Items" section
        available_start, available_end = get_section_range(content, "Available Work Items")

        if available_start == -1:
            return {
                "success": False,
                "reason": "section_not_found",
                "hint": "Could not find '## Available Work Items' section in state file.",
            }

        # Create new work item line
        new_item_line = f"- [ ] {description}"

        # Insert after the section header (and any existing items)
        # Find the first empty line after the header or the next section
        insert_pos = available_start + 1
        for i in range(available_start + 1, min(available_end, len(lines))):
            if lines[i].strip().startswith('- ['):
                insert_pos = i + 1
            elif lines[i].strip() == '':
                insert_pos = i
                break

        lines.insert(insert_pos, new_item_line)

        # Write modified state
        new_content = '\n'.join(lines)
        result = await self.write_state(new_content)

        if result["success"]:
            return {
                "success": True,
                "message": f"Added: {description}",
                "description": description,
                "status": "available",
            }
        return result

    # ========================================================================
    # Per-Agent Memory Operations
    # ========================================================================

    async def read_agent_memory(self, agent_id: str) -> str:
        """Read agent's local memory file.

        Args:
            agent_id: Agent identifier

        Returns:
            Memory file content or template if doesn't exist
        """
        memory_path = self.AGENTS_DIR / f"{agent_id}.md"

        if not memory_path.exists():
            return self._get_agent_memory_template(agent_id)

        async with aiofiles.open(memory_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def write_agent_memory(
        self,
        agent_id: str,
        section: str,
        content: str,
        append: bool = False,
    ) -> Dict[str, Any]:
        """Update specific section of agent memory file.

        Args:
            agent_id: Agent identifier
            section: Section to update ('scratchpad', 'subtasks', 'notes')
            content: Content to write
            append: If True, append to existing; if False, replace

        Returns:
            Success dict with preview, or error dict with reason
        """
        memory_path = self.AGENTS_DIR / f"{agent_id}.md"

        # Read existing content or use template
        if memory_path.exists():
            async with aiofiles.open(memory_path, 'r', encoding='utf-8') as f:
                current_content = await f.read()
        else:
            current_content = self._get_agent_memory_template(agent_id)

        # Find and update section
        section_title = section.capitalize()
        start, end = get_section_range(current_content, section_title)

        if start == -1:
            return {
                "success": False,
                "reason": "section_not_found",
                "hint": f"Could not find '## {section_title}' section in memory file.",
            }

        lines = current_content.split('\n')

        # Extract section content (excluding header)
        section_content_start = start + 1
        existing_content = '\n'.join(lines[section_content_start:end]).strip()

        # Build new section content
        if append and existing_content:
            new_section_content = f"{existing_content}\n{content}"
        else:
            new_section_content = content

        # Rebuild file with updated section
        new_lines = lines[:section_content_start] + [new_section_content, ''] + lines[end:]

        new_content = '\n'.join(new_lines)

        # Write to file
        try:
            self.AGENTS_DIR.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(memory_path, 'w', encoding='utf-8') as f:
                await f.write(new_content)

            preview = new_section_content[:200]
            if len(new_section_content) > 200:
                preview += "..."

            return {
                "success": True,
                "message": f"Updated {section_title} section",
                "section": section,
                "preview": preview,
            }
        except Exception as e:
            return {
                "success": False,
                "reason": "write_error",
                "error": str(e),
            }

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _get_initial_template(self) -> str:
        """Return initial state file template."""
        return """# Shared State

## Available Work Items

## In Progress

## Completed

## Agent Registry
| Agent ID | Current Task | Started |
|----------|--------------|---------|
"""

    def _get_agent_memory_template(self, agent_id: str) -> str:
        """Return initial per-agent memory template."""
        return f"""# Agent Memory: {agent_id}

## Scratchpad

## Subtasks

## Notes
"""

    def _parse_work_items(self, content: str) -> List[WorkItem]:
        """Parse all work items from markdown content.

        Args:
            content: Full markdown content

        Returns:
            List of WorkItem objects
        """
        items = []
        for i, line in enumerate(content.split('\n')):
            item = parse_work_item(line, i)
            if item:
                items.append(item)
        return items
