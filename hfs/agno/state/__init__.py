"""Shared state management for multi-agent coordination.

This module provides:
- SharedStateManager: Async file I/O with FIFO-queued write locking
- Pydantic schemas for work items and tool inputs/outputs
- Markdown parser utilities for IP markers

State files live in .hfs/ to separate runtime from planning artifacts.
"""

# Schemas
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

# Parser utilities
from .parser import (
    parse_work_item,
    add_ip_marker,
    remove_ip_marker,
    mark_complete,
    get_section_range,
    extract_section,
    WORK_ITEM_PATTERN,
)

# Manager
from .manager import SharedStateManager

# Toolkit
from .toolkit import SharedStateToolkit

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
    # Parser
    "parse_work_item",
    "add_ip_marker",
    "remove_ip_marker",
    "mark_complete",
    "get_section_range",
    "extract_section",
    "WORK_ITEM_PATTERN",
    # Manager
    "SharedStateManager",
    # Toolkit
    "SharedStateToolkit",
]
