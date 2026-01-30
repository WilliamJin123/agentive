"""SharedStateToolkit - Agno toolkit for multi-agent coordination.

This module provides the SharedStateToolkit class which extends Agno's Toolkit
to provide shared state tools for agents during multi-agent coordination.

Tools enable agents to:
- Query work items with status filters
- Claim, complete, or release work items
- Read and write their local memory files
"""

import asyncio
import json
from typing import Callable, List, Optional

from agno.tools.toolkit import Toolkit
from pydantic import ValidationError

from .manager import SharedStateManager
from .schemas import (
    WorkItemStatus,
    GetWorkItemsInput,
    GetWorkItemsOutput,
    UpdateWorkItemInput,
    UpdateWorkItemOutput,
    UpdateAgentMemoryInput,
    UpdateAgentMemoryOutput,
    AgentMemorySection,
)

# Import error formatters from hfs.agno.tools
from hfs.agno.tools.errors import format_validation_error, format_runtime_error


def _run_async(coro):
    """Run async coroutine from sync context.

    Handles both cases:
    - When running in an existing event loop (e.g., in async context)
    - When no event loop exists (e.g., direct tool calls)
    """
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - can't use run_until_complete
        # Create a new thread to run the coroutine
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - create new one
        return asyncio.run(coro)


class SharedStateToolkit(Toolkit):
    """Tools for multi-agent coordination via shared state.

    Provides:
    - get_work_items(): Query available/claimed/completed items
    - update_work_item(): Claim, complete, release, or add work items
    - get_agent_memory(): Read agent's local memory file
    - update_agent_memory(): Write to agent's local memory file

    All tools validate inputs with Pydantic and return JSON strings.
    ValidationError returns retry_allowed=True with hints.
    RuntimeError returns retry_allowed=False.
    """

    def __init__(
        self,
        manager: SharedStateManager,
        agent_id: str,
        **kwargs,
    ):
        """Initialize SharedStateToolkit with shared state manager.

        Args:
            manager: SharedStateManager instance for state operations
            agent_id: Identifier for the agent using this toolkit
            **kwargs: Additional args passed to Toolkit base
        """
        self._manager = manager
        self._agent_id = agent_id

        tools: List[Callable] = [
            self.get_work_items,
            self.update_work_item,
            self.get_agent_memory,
            self.update_agent_memory,
        ]

        super().__init__(name="shared_state", tools=tools, **kwargs)

    def get_work_items(self, status: Optional[str] = None) -> str:
        """Query work items from shared state.

        WHEN TO USE: Before starting work to see what's available,
        or to check what you've claimed.

        FILTERS:
        - status="available": Items not claimed by any agent
        - status="in_progress": Items currently claimed (by you or others)
        - status="completed": Finished items
        - status=None: Return all items

        EXAMPLE:
        >>> get_work_items(status="available")

        Args:
            status: Filter by status. One of: "available", "in_progress", "completed", or None for all.

        Returns:
            JSON with list of work items matching filter, grouped by status.
        """
        # Validate input
        try:
            input_model = GetWorkItemsInput(status=status)
        except ValidationError as e:
            return format_validation_error(e)

        try:
            # Get work items from manager
            items = _run_async(self._manager.get_work_items(input_model.status))

            # Count by status
            counts = {
                "available": 0,
                "in_progress": 0,
                "completed": 0,
            }
            for item in items:
                counts[item.status.value] += 1

            output = GetWorkItemsOutput(
                success=True,
                message=f"Found {len(items)} work item(s)" + (f" with status '{status}'" if status else ""),
                items=items,
                counts=counts,
            )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, "get_work_items")

    def update_work_item(
        self,
        description: str,
        action: str,
        new_description: Optional[str] = None,
    ) -> str:
        """Update a work item's status.

        WHEN TO USE: To claim work before starting, mark complete when done,
        or release if you can't finish.

        ACTIONS:
        - "claim": Mark item as in-progress with your agent ID
        - "complete": Mark item as done (checkbox checked)
        - "release": Remove your claim (if you can't finish)
        - "add": Add a new work item to the available list

        IMPORTANT CONSTRAINTS:
        - Can only claim items with status="available"
        - Can only complete items you have claimed
        - Can only release items you have claimed
        - Description must match an existing item (for claim/complete/release)

        EXAMPLE:
        >>> update_work_item(description="Build auth module", action="claim")
        >>> update_work_item(description="Build auth module", action="complete")

        Args:
            description: The work item description to match (or new description for "add")
            action: One of "claim", "complete", "release", "add"
            new_description: For "add" action only - the new work item text

        Returns:
            JSON with success status and updated item details.
        """
        # Validate input
        try:
            input_model = UpdateWorkItemInput(
                description=description,
                action=action,
                new_description=new_description,
            )
        except ValidationError as e:
            return format_validation_error(e)

        try:
            # Route to appropriate manager method based on action
            if input_model.action == "claim":
                result = _run_async(
                    self._manager.claim_item(input_model.description, self._agent_id)
                )
            elif input_model.action == "complete":
                result = _run_async(
                    self._manager.complete_item(input_model.description, self._agent_id)
                )
            elif input_model.action == "release":
                result = _run_async(
                    self._manager.release_item(input_model.description, self._agent_id)
                )
            elif input_model.action == "add":
                result = _run_async(
                    self._manager.add_item(input_model.new_description)
                )
            else:
                # Should not reach here due to Pydantic validation
                return format_runtime_error(
                    ValueError(f"Unknown action: {input_model.action}"),
                    "update_work_item"
                )

            # Convert manager result to output schema
            if result.get("success"):
                output = UpdateWorkItemOutput(
                    success=True,
                    message=result.get("message", "Operation completed"),
                    description=result.get("description", input_model.description),
                    status=result.get("status"),
                    claimed_by=result.get("claimed_by"),
                )
            else:
                output = UpdateWorkItemOutput(
                    success=False,
                    message=result.get("hint", "Operation failed"),
                    description=result.get("description", input_model.description),
                    error_reason=result.get("reason"),
                    hint=result.get("hint"),
                )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, f"update_work_item({action})")

    def get_agent_memory(self) -> str:
        """Read your local memory file.

        WHEN TO USE: At the start of a work session to recall context,
        or when you need to reference your previous notes.

        Returns:
            JSON with your memory file contents (scratchpad, subtasks, notes).
            Returns empty template if no memory file exists yet.
        """
        try:
            content = _run_async(self._manager.read_agent_memory(self._agent_id))

            return json.dumps({
                "success": True,
                "message": f"Memory for agent {self._agent_id}",
                "agent_id": self._agent_id,
                "content": content,
            })

        except Exception as e:
            return format_runtime_error(e, "get_agent_memory")

    def update_agent_memory(
        self,
        section: str,
        content: str,
        append: bool = False,
    ) -> str:
        """Update your local memory file.

        WHEN TO USE: To save context for later, track subtasks,
        or record notes and learnings.

        SECTIONS:
        - "scratchpad": Working notes and current approach
        - "subtasks": Your personal task breakdown
        - "notes": Observations and learnings

        EXAMPLE:
        >>> update_agent_memory(section="scratchpad", content="Implementing OAuth2 flow...")
        >>> update_agent_memory(section="subtasks", content="- [ ] Add token refresh", append=True)

        Args:
            section: Which section to update ("scratchpad", "subtasks", "notes")
            content: The content to write
            append: If True, append to existing content; if False, replace

        Returns:
            JSON with success status and updated section preview.
        """
        # Validate input
        try:
            input_model = UpdateAgentMemoryInput(
                section=AgentMemorySection(section),
                content=content,
                append=append,
            )
        except ValidationError as e:
            return format_validation_error(e)
        except ValueError as e:
            # Handle invalid enum value
            return json.dumps({
                "success": False,
                "error": "validation_error",
                "message": f"Invalid section: {section}. Must be one of: scratchpad, subtasks, notes",
                "hints": [f"section: '{section}' is not a valid AgentMemorySection"],
                "retry_allowed": True,
            })

        try:
            result = _run_async(
                self._manager.write_agent_memory(
                    self._agent_id,
                    input_model.section.value,
                    input_model.content,
                    input_model.append,
                )
            )

            if result.get("success"):
                output = UpdateAgentMemoryOutput(
                    success=True,
                    message=result.get("message", "Memory updated"),
                    section=input_model.section.value,
                    preview=result.get("preview", ""),
                )
            else:
                output = UpdateAgentMemoryOutput(
                    success=False,
                    message=result.get("hint", "Operation failed"),
                    section=input_model.section.value,
                    preview="",
                )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, f"update_agent_memory({section})")
