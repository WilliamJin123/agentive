"""Unit tests for shared state module.

Tests cover:
- Parser utilities (parse_work_item, add_ip_marker, remove_ip_marker, mark_complete)
- Pydantic schemas (WorkItem status computation, input validators)
- SharedStateManager (async read/write, work item operations, agent memory)
- SharedStateToolkit (tool count, JSON output, tool operations)
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from hfs.agno.state import (
    SharedStateManager,
    SharedStateToolkit,
    WorkItem,
    WorkItemStatus,
)
from hfs.agno.state.schemas import (
    GetWorkItemsInput,
    UpdateWorkItemInput,
    UpdateAgentMemoryInput,
    AgentMemorySection,
)
from hfs.agno.state.parser import (
    parse_work_item,
    add_ip_marker,
    remove_ip_marker,
    mark_complete,
    WORK_ITEM_PATTERN,
    get_section_range,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_state_dir(tmp_path):
    """Provide a temporary directory for state files."""
    state_dir = tmp_path / ".hfs"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def manager(temp_state_dir):
    """Provide a SharedStateManager with temp state path."""
    state_path = temp_state_dir / "state.md"
    mgr = SharedStateManager(state_path=state_path)
    # Also set AGENTS_DIR to temp location
    mgr.AGENTS_DIR = temp_state_dir / "agents"
    return mgr


@pytest.fixture
def toolkit(manager):
    """Provide a SharedStateToolkit with the test manager."""
    return SharedStateToolkit(manager, agent_id="test-agent")


@pytest.fixture
def sample_state_content():
    """Provide sample state file content for tests."""
    return """# Shared State

## Available Work Items
- [ ] Build auth module
- [ ] Setup database

## In Progress
- [ ] Implement API [IP:agent-1]

## Completed
- [x] Project setup

## Agent Registry
| Agent ID | Current Task | Started |
|----------|--------------|---------|
"""


# ============================================================================
# Parser Tests
# ============================================================================

class TestParser:
    """Tests for parser utilities."""

    def test_parse_work_item_available(self):
        """Parse available work item (unchecked, no IP marker)."""
        line = "- [ ] Build auth module"
        item = parse_work_item(line, 0)

        assert item is not None
        assert item.description == "Build auth module"
        assert item.claimed_by is None
        assert item.is_complete is False
        assert item.status == WorkItemStatus.AVAILABLE

    def test_parse_work_item_with_ip_marker(self):
        """Parse work item with IP marker (in progress)."""
        line = "- [ ] Implement API [IP:agent-1]"
        item = parse_work_item(line, 5)

        assert item is not None
        assert item.description == "Implement API"
        assert item.claimed_by == "agent-1"
        assert item.is_complete is False
        assert item.status == WorkItemStatus.IN_PROGRESS
        assert item.line_number == 5

    def test_parse_work_item_completed(self):
        """Parse completed work item (checked checkbox)."""
        line = "- [x] Project setup"
        item = parse_work_item(line, 10)

        assert item is not None
        assert item.description == "Project setup"
        assert item.is_complete is True
        assert item.status == WorkItemStatus.COMPLETED

    def test_parse_work_item_completed_uppercase(self):
        """Parse completed work item with uppercase X."""
        line = "- [X] Done task"
        item = parse_work_item(line)

        assert item is not None
        assert item.is_complete is True

    def test_parse_work_item_invalid(self):
        """Return None for non-matching lines."""
        assert parse_work_item("Not a work item") is None
        assert parse_work_item("## Section header") is None
        assert parse_work_item("") is None
        assert parse_work_item("   ") is None
        assert parse_work_item("- Regular list item") is None

    def test_add_ip_marker(self):
        """Add IP marker to work item line."""
        line = "- [ ] Build auth"
        result = add_ip_marker(line, "agent-1")

        assert result == "- [ ] Build auth [IP:agent-1]"

    def test_add_ip_marker_replaces_existing(self):
        """Replace existing IP marker with new one."""
        line = "- [ ] Build auth [IP:old-agent]"
        result = add_ip_marker(line, "new-agent")

        assert result == "- [ ] Build auth [IP:new-agent]"
        assert "[IP:old-agent]" not in result

    def test_remove_ip_marker(self):
        """Remove IP marker from line."""
        line = "- [ ] Build auth [IP:agent-1]"
        result = remove_ip_marker(line)

        assert result == "- [ ] Build auth"
        assert "[IP:" not in result

    def test_remove_ip_marker_no_marker(self):
        """Return unchanged line when no IP marker present."""
        line = "- [ ] Build auth"
        result = remove_ip_marker(line)

        assert result == "- [ ] Build auth"

    def test_mark_complete(self):
        """Mark work item as complete (check checkbox, remove IP)."""
        line = "- [ ] Build auth [IP:agent-1]"
        result = mark_complete(line)

        assert result == "- [x] Build auth"
        assert "[IP:" not in result
        assert "[ ]" not in result

    def test_mark_complete_already_done(self):
        """Already completed item stays completed."""
        line = "- [x] Already done"
        result = mark_complete(line)

        assert result == "- [x] Already done"


# ============================================================================
# Schema Tests
# ============================================================================

class TestSchemas:
    """Tests for Pydantic schemas."""

    def test_work_item_status_available(self):
        """WorkItem with no claim and not complete is available."""
        item = WorkItem(
            description="Test task",
            claimed_by=None,
            is_complete=False,
            raw_line="- [ ] Test task",
        )
        assert item.status == WorkItemStatus.AVAILABLE

    def test_work_item_status_in_progress(self):
        """WorkItem with claim but not complete is in_progress."""
        item = WorkItem(
            description="Test task",
            claimed_by="agent-1",
            is_complete=False,
            raw_line="- [ ] Test task [IP:agent-1]",
        )
        assert item.status == WorkItemStatus.IN_PROGRESS

    def test_work_item_status_completed(self):
        """WorkItem with is_complete=True is completed (regardless of claim)."""
        item = WorkItem(
            description="Test task",
            claimed_by="agent-1",  # Has claim but is complete
            is_complete=True,
            raw_line="- [x] Test task",
        )
        assert item.status == WorkItemStatus.COMPLETED

    def test_update_work_item_input_requires_description_for_add(self):
        """UpdateWorkItemInput requires new_description when action is 'add'."""
        with pytest.raises(ValueError, match="new_description required"):
            UpdateWorkItemInput(
                description="placeholder",
                action="add",
                new_description=None,  # Missing
            )

    def test_update_work_item_input_add_valid(self):
        """UpdateWorkItemInput accepts add with new_description."""
        input_model = UpdateWorkItemInput(
            description="placeholder",
            action="add",
            new_description="New task item",
        )
        assert input_model.new_description == "New task item"

    def test_get_work_items_input_valid_status(self):
        """GetWorkItemsInput accepts valid status values."""
        for status in ["available", "in_progress", "completed", None]:
            input_model = GetWorkItemsInput(status=status)
            assert input_model.status == status

    def test_update_agent_memory_input_valid(self):
        """UpdateAgentMemoryInput accepts valid section values."""
        input_model = UpdateAgentMemoryInput(
            section=AgentMemorySection.SCRATCHPAD,
            content="Test content",
            append=True,
        )
        assert input_model.section == AgentMemorySection.SCRATCHPAD
        assert input_model.append is True


# ============================================================================
# Manager Tests
# ============================================================================

class TestManager:
    """Tests for SharedStateManager."""

    @pytest.mark.asyncio
    async def test_manager_read_state_creates_template(self, manager):
        """First read returns initial template."""
        content = await manager.read_state()

        assert "# Shared State" in content
        assert "## Available Work Items" in content
        assert "## In Progress" in content
        assert "## Completed" in content
        assert "## Agent Registry" in content

    @pytest.mark.asyncio
    async def test_manager_write_state_success(self, manager):
        """Write and read back state content."""
        test_content = "# Test State\n\nSome content"
        result = await manager.write_state(test_content)

        assert result["success"] is True

        read_content = await manager.read_state()
        assert read_content == test_content

    @pytest.mark.asyncio
    async def test_manager_write_state_creates_directory(self, tmp_path):
        """Write creates parent directory if missing."""
        state_path = tmp_path / "new_dir" / ".hfs" / "state.md"
        mgr = SharedStateManager(state_path=state_path)

        result = await mgr.write_state("# Test")

        assert result["success"] is True
        assert state_path.exists()

    @pytest.mark.asyncio
    async def test_manager_get_work_items_all(self, manager, sample_state_content):
        """Get all work items without filter."""
        await manager.write_state(sample_state_content)

        items = await manager.get_work_items()

        assert len(items) == 4
        descriptions = [i.description for i in items]
        assert "Build auth module" in descriptions
        assert "Setup database" in descriptions
        assert "Implement API" in descriptions
        assert "Project setup" in descriptions

    @pytest.mark.asyncio
    async def test_manager_get_work_items_filtered(self, manager, sample_state_content):
        """Get work items filtered by status."""
        await manager.write_state(sample_state_content)

        available = await manager.get_work_items("available")
        assert len(available) == 2

        in_progress = await manager.get_work_items("in_progress")
        assert len(in_progress) == 1
        assert in_progress[0].claimed_by == "agent-1"

        completed = await manager.get_work_items("completed")
        assert len(completed) == 1
        assert completed[0].is_complete is True

    @pytest.mark.asyncio
    async def test_manager_claim_item_success(self, manager, sample_state_content):
        """Claim an available item."""
        await manager.write_state(sample_state_content)

        result = await manager.claim_item("Build auth module", "test-agent")

        assert result["success"] is True
        assert result["claimed_by"] == "test-agent"
        assert result["status"] == "in_progress"

        # Verify state was updated
        items = await manager.get_work_items("in_progress")
        descriptions = [i.description for i in items]
        assert "Build auth module" in descriptions

    @pytest.mark.asyncio
    async def test_manager_claim_item_already_claimed(self, manager, sample_state_content):
        """Cannot claim item already in progress."""
        await manager.write_state(sample_state_content)

        result = await manager.claim_item("Implement API", "test-agent")

        assert result["success"] is False
        assert result["reason"] == "not_available"
        assert "agent-1" in result.get("claimed_by", "")

    @pytest.mark.asyncio
    async def test_manager_claim_item_not_found(self, manager, sample_state_content):
        """Cannot claim non-existent item."""
        await manager.write_state(sample_state_content)

        result = await manager.claim_item("Nonexistent task", "test-agent")

        assert result["success"] is False
        assert result["reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_manager_complete_item_success(self, manager, sample_state_content):
        """Complete an item you own."""
        await manager.write_state(sample_state_content)

        result = await manager.complete_item("Implement API", "agent-1")

        assert result["success"] is True
        assert result["status"] == "completed"

        # Verify state was updated
        items = await manager.get_work_items("completed")
        descriptions = [i.description for i in items]
        assert "Implement API" in descriptions

    @pytest.mark.asyncio
    async def test_manager_complete_item_not_owner(self, manager, sample_state_content):
        """Cannot complete item you don't own."""
        await manager.write_state(sample_state_content)

        result = await manager.complete_item("Implement API", "wrong-agent")

        assert result["success"] is False
        assert result["reason"] == "not_owner"

    @pytest.mark.asyncio
    async def test_manager_release_item_success(self, manager, sample_state_content):
        """Release an item you own."""
        await manager.write_state(sample_state_content)

        result = await manager.release_item("Implement API", "agent-1")

        assert result["success"] is True
        assert result["status"] == "available"

        # Verify state was updated
        items = await manager.get_work_items("available")
        descriptions = [i.description for i in items]
        assert "Implement API" in descriptions

    @pytest.mark.asyncio
    async def test_manager_add_item(self, manager, sample_state_content):
        """Add a new work item."""
        await manager.write_state(sample_state_content)

        result = await manager.add_item("New task item")

        assert result["success"] is True
        assert result["status"] == "available"

        # Verify state was updated
        items = await manager.get_work_items("available")
        descriptions = [i.description for i in items]
        assert "New task item" in descriptions

    @pytest.mark.asyncio
    async def test_manager_read_agent_memory_empty(self, manager):
        """Read returns template when memory file doesn't exist."""
        content = await manager.read_agent_memory("new-agent")

        assert "# Agent Memory: new-agent" in content
        assert "## Scratchpad" in content
        assert "## Subtasks" in content
        assert "## Notes" in content

    @pytest.mark.asyncio
    async def test_manager_write_agent_memory(self, manager):
        """Write to agent memory section."""
        result = await manager.write_agent_memory(
            "test-agent",
            "scratchpad",
            "Test content here",
            append=False,
        )

        assert result["success"] is True
        assert "scratchpad" in result["section"].lower()

        # Verify content was written
        content = await manager.read_agent_memory("test-agent")
        assert "Test content here" in content

    @pytest.mark.asyncio
    async def test_manager_write_agent_memory_append(self, manager):
        """Append to existing agent memory section."""
        # Write initial content
        await manager.write_agent_memory(
            "test-agent",
            "notes",
            "Line 1",
            append=False,
        )

        # Append more content
        result = await manager.write_agent_memory(
            "test-agent",
            "notes",
            "Line 2",
            append=True,
        )

        assert result["success"] is True

        # Verify both lines present
        content = await manager.read_agent_memory("test-agent")
        assert "Line 1" in content
        assert "Line 2" in content


# ============================================================================
# Toolkit Tests
# ============================================================================

class TestToolkit:
    """Tests for SharedStateToolkit."""

    def test_toolkit_has_four_tools(self, toolkit):
        """Toolkit has exactly 4 tools with expected names."""
        assert len(toolkit.tools) == 4

        tool_names = [f.__name__ for f in toolkit.tools]
        assert "get_work_items" in tool_names
        assert "update_work_item" in tool_names
        assert "get_agent_memory" in tool_names
        assert "update_agent_memory" in tool_names

    def test_toolkit_get_work_items_returns_json(self, toolkit, manager, sample_state_content):
        """get_work_items returns valid JSON."""
        # Setup state
        asyncio.run(manager.write_state(sample_state_content))

        result = toolkit.get_work_items()

        # Should be valid JSON
        data = json.loads(result)
        assert "success" in data
        assert "items" in data
        assert data["success"] is True

    def test_toolkit_get_work_items_filtered(self, toolkit, manager, sample_state_content):
        """get_work_items respects status filter."""
        asyncio.run(manager.write_state(sample_state_content))

        result = toolkit.get_work_items(status="available")

        data = json.loads(result)
        assert data["success"] is True
        assert len(data["items"]) == 2

    def test_toolkit_update_work_item_claim(self, toolkit, manager, sample_state_content):
        """update_work_item claim action works."""
        asyncio.run(manager.write_state(sample_state_content))

        result = toolkit.update_work_item(
            description="Build auth module",
            action="claim",
        )

        data = json.loads(result)
        assert data["success"] is True
        assert data["status"] == "in_progress"

    def test_toolkit_update_work_item_complete(self, toolkit, manager, sample_state_content):
        """update_work_item complete action requires ownership."""
        asyncio.run(manager.write_state(sample_state_content))

        # Try to complete item owned by agent-1 (not test-agent)
        result = toolkit.update_work_item(
            description="Implement API",
            action="complete",
        )

        data = json.loads(result)
        assert data["success"] is False
        assert data["error_reason"] == "not_owner"

    def test_toolkit_update_work_item_add(self, toolkit, manager, sample_state_content):
        """update_work_item add action creates new item."""
        asyncio.run(manager.write_state(sample_state_content))

        result = toolkit.update_work_item(
            description="placeholder",
            action="add",
            new_description="Brand new task",
        )

        data = json.loads(result)
        assert data["success"] is True
        assert data["status"] == "available"

    def test_toolkit_get_agent_memory_empty(self, toolkit, manager):
        """get_agent_memory returns template for new agent."""
        result = toolkit.get_agent_memory()

        data = json.loads(result)
        assert data["success"] is True
        assert "## Scratchpad" in data["content"]
        assert "test-agent" in data["agent_id"]

    def test_toolkit_update_agent_memory(self, toolkit, manager):
        """update_agent_memory writes to section."""
        result = toolkit.update_agent_memory(
            section="scratchpad",
            content="Working on auth implementation",
            append=False,
        )

        data = json.loads(result)
        assert data["success"] is True
        assert data["section"] == "scratchpad"

        # Verify via get
        get_result = toolkit.get_agent_memory()
        get_data = json.loads(get_result)
        assert "Working on auth implementation" in get_data["content"]

    def test_toolkit_update_agent_memory_invalid_section(self, toolkit):
        """update_agent_memory rejects invalid section."""
        result = toolkit.update_agent_memory(
            section="invalid_section",
            content="Test",
            append=False,
        )

        data = json.loads(result)
        assert data["success"] is False
        assert "retry_allowed" in data

    def test_toolkit_validation_error_returns_hints(self, toolkit):
        """Validation errors return retry_allowed and hints."""
        result = toolkit.update_work_item(
            description="placeholder",
            action="add",
            # Missing new_description
        )

        data = json.loads(result)
        assert data["success"] is False
        assert data.get("retry_allowed") is True
        assert "hints" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_work_item_lifecycle(self, toolkit, manager, sample_state_content):
        """Test complete claim -> complete lifecycle."""
        asyncio.run(manager.write_state(sample_state_content))

        # 1. Check available items
        available = toolkit.get_work_items(status="available")
        available_data = json.loads(available)
        assert len(available_data["items"]) == 2

        # 2. Claim an item
        claim_result = toolkit.update_work_item(
            description="Build auth module",
            action="claim",
        )
        claim_data = json.loads(claim_result)
        assert claim_data["success"] is True

        # 3. Verify item is now in progress
        in_progress = toolkit.get_work_items(status="in_progress")
        in_progress_data = json.loads(in_progress)
        descriptions = [i["description"] for i in in_progress_data["items"]]
        assert "Build auth module" in descriptions

        # 4. Complete the item
        complete_result = toolkit.update_work_item(
            description="Build auth module",
            action="complete",
        )
        complete_data = json.loads(complete_result)
        assert complete_data["success"] is True

        # 5. Verify item is now completed
        completed = toolkit.get_work_items(status="completed")
        completed_data = json.loads(completed)
        descriptions = [i["description"] for i in completed_data["items"]]
        assert "Build auth module" in descriptions

    def test_agent_memory_workflow(self, toolkit):
        """Test agent memory read/write/append workflow."""
        # 1. Initial read returns template
        initial = toolkit.get_agent_memory()
        initial_data = json.loads(initial)
        assert "## Scratchpad" in initial_data["content"]

        # 2. Write to scratchpad
        write_result = toolkit.update_agent_memory(
            section="scratchpad",
            content="Starting auth implementation",
            append=False,
        )
        write_data = json.loads(write_result)
        assert write_data["success"] is True

        # 3. Append to scratchpad
        append_result = toolkit.update_agent_memory(
            section="scratchpad",
            content="OAuth2 flow selected",
            append=True,
        )
        append_data = json.loads(append_result)
        assert append_data["success"] is True

        # 4. Verify both entries present
        final = toolkit.get_agent_memory()
        final_data = json.loads(final)
        assert "Starting auth implementation" in final_data["content"]
        assert "OAuth2 flow selected" in final_data["content"]
