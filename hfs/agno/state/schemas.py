"""Pydantic models for shared state operations.

These schemas define the contracts for shared state tools used by Agno agents.
Input models validate agent-provided data with detailed error messages.
Output models ensure consistent, typed responses.
"""

from pydantic import BaseModel, Field, model_validator, computed_field
from typing import Optional, List, Dict, Literal
from enum import Enum


class WorkItemStatus(str, Enum):
    """Status of a work item in shared state."""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AgentMemorySection(str, Enum):
    """Valid sections for per-agent memory files."""
    SCRATCHPAD = "scratchpad"
    SUBTASKS = "subtasks"
    NOTES = "notes"


# ============================================================================
# Work Item Model
# ============================================================================

class WorkItem(BaseModel):
    """A parsed work item from shared state.

    Attributes:
        description: The work item text (task description)
        claimed_by: Agent ID if claimed (from IP marker), None if available
        line_number: Position in the state file for modification
        is_complete: Whether the checkbox is checked [x]
        raw_line: Original markdown line for reference
    """
    description: str = Field(..., description="The work item text")
    claimed_by: Optional[str] = Field(None, description="Agent ID if claimed")
    line_number: int = Field(0, description="Line number in state file")
    is_complete: bool = Field(False, description="Whether checkbox is checked")
    raw_line: str = Field("", description="Original markdown line")

    @computed_field
    @property
    def status(self) -> WorkItemStatus:
        """Compute status from is_complete and claimed_by.

        Returns:
            - COMPLETED if checkbox is checked
            - IN_PROGRESS if claimed by an agent
            - AVAILABLE otherwise
        """
        if self.is_complete:
            return WorkItemStatus.COMPLETED
        elif self.claimed_by:
            return WorkItemStatus.IN_PROGRESS
        return WorkItemStatus.AVAILABLE


# ============================================================================
# Input Models
# ============================================================================

class GetWorkItemsInput(BaseModel):
    """Input for get_work_items tool.

    Attributes:
        status: Filter by status. None returns all items.
    """
    status: Optional[Literal["available", "in_progress", "completed"]] = Field(
        None,
        description="Filter by status: 'available', 'in_progress', 'completed', or None for all"
    )


class UpdateWorkItemInput(BaseModel):
    """Input for update_work_item tool.

    Attributes:
        description: Work item to match (or new description for "add")
        action: Action to perform on the work item
        new_description: For "add" action only - the new work item text
    """
    description: str = Field(
        ...,
        min_length=1,
        description="Work item description to match"
    )
    action: Literal["claim", "complete", "release", "add"] = Field(
        ...,
        description="Action: 'claim' to take, 'complete' to finish, 'release' to unclaim, 'add' to create new"
    )
    new_description: Optional[str] = Field(
        None,
        description="For 'add' action only: the new work item text"
    )

    @model_validator(mode='after')
    def require_description_for_add(self) -> 'UpdateWorkItemInput':
        """Ensure new_description is provided when action is 'add'."""
        if self.action == "add" and not self.new_description:
            raise ValueError("new_description required when action is 'add'")
        return self


class UpdateAgentMemoryInput(BaseModel):
    """Input for update_agent_memory tool.

    Attributes:
        section: Which section to update
        content: Content to write
        append: If True, append to existing; if False, replace
    """
    section: AgentMemorySection = Field(
        ...,
        description="Section to update: 'scratchpad', 'subtasks', or 'notes'"
    )
    content: str = Field(
        ...,
        description="Content to write to the section"
    )
    append: bool = Field(
        False,
        description="If True, append to existing content; if False, replace"
    )


# ============================================================================
# Output Models
# ============================================================================

class GetWorkItemsOutput(BaseModel):
    """Output for get_work_items tool.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable status message
        items: List of work items matching the filter
        counts: Count of items by status
    """
    success: bool
    message: str
    items: List[WorkItem]
    counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by status: {'available': N, 'in_progress': N, 'completed': N}"
    )


class UpdateWorkItemOutput(BaseModel):
    """Output for update_work_item tool.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable status message
        description: The work item description
        status: Current status after update
        claimed_by: Agent ID if claimed
        error_reason: Error type if failed (not_found, not_available, not_owner, lock_timeout)
        hint: Actionable hint for fixing errors
    """
    success: bool
    message: str
    description: str
    status: Optional[str] = None
    claimed_by: Optional[str] = None
    error_reason: Optional[str] = None
    hint: Optional[str] = None


class UpdateAgentMemoryOutput(BaseModel):
    """Output for update_agent_memory tool.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable status message
        section: Section that was updated
        preview: First 200 chars of updated section
    """
    success: bool
    message: str
    section: str
    preview: str = Field(
        "",
        description="First 200 characters of the updated section"
    )
