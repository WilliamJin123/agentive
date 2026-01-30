"""Shared state management for multi-agent coordination.

This module provides:
- SharedStateManager: Async file I/O with FIFO-queued write locking
- Pydantic schemas for work items and tool inputs/outputs
- Markdown parser utilities for IP markers

State files live in .hfs/ to separate runtime from planning artifacts.
"""

# Schemas (always available)
from .schemas import (
    WorkItem,
    WorkItemStatus,
    GetWorkItemsInput,
    GetWorkItemsOutput,
    UpdateWorkItemInput,
    UpdateWorkItemOutput,
    AgentMemorySection,
    UpdateAgentMemoryInput,
    UpdateAgentMemoryOutput,
)

__all__ = [
    # Schemas
    "WorkItem",
    "WorkItemStatus",
    "GetWorkItemsInput",
    "GetWorkItemsOutput",
    "UpdateWorkItemInput",
    "UpdateWorkItemOutput",
    "AgentMemorySection",
    "UpdateAgentMemoryInput",
    "UpdateAgentMemoryOutput",
]

# Parser utilities (added in Task 2)
# Deferred imports to avoid circular dependencies during incremental development
