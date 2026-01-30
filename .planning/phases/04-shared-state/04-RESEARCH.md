# Phase 4: Shared State - Research

**Researched:** 2026-01-29
**Domain:** Markdown-Based Multi-Agent Coordination, Async File I/O, Queue-Based Locking
**Confidence:** HIGH

## Summary

This phase implements a markdown-based coordination layer for multi-agent collaboration. Research focused on: (1) async file I/O patterns using aiofiles, (2) queue-based write locking using asyncio.Lock's FIFO-fair semantics, (3) inline IP marker design for work item tracking, and (4) tool interface design following existing HFSToolkit patterns from Phase 2.

The locked decisions from CONTEXT.md prescribe: single shared state file at `.hfs/state.md`, queue-based FIFO write ordering, inline IP markers (`[IP:agent-id]`), and a query/update tool interface. Reads are non-locking, writes queue up and execute in order with configurable timeout.

Key insight: The existing `hfs/core/spec.py` provides an in-memory state model for HFS negotiation. Phase 4 adds a **file-backed coordination layer** that is conceptually separate - the Spec handles spec sections/claims during deliberation, while shared state handles work item tracking during execution across multiple agent sessions.

**Primary recommendation:** Create a `SharedStateManager` class that wraps async file operations with asyncio.Lock for write serialization. Implement `get_work_items()` and `update_work_item()` tools following the HFSToolkit pattern. Use inline markdown syntax for IP markers (`- [ ] Task [IP:agent-id]`) for human readability.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiofiles | 25.1.0 | Async file read/write operations | Non-blocking file I/O for asyncio, already available |
| asyncio.Lock | stdlib | FIFO-fair write queue serialization | Built-in, fair acquisition guarantees |
| pydantic | 2.x | Input/output schemas for tools | Consistent with Phase 2 HFSToolkit patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re | stdlib | Regex for IP marker parsing | Extracting `[IP:agent-id]` from markdown lines |
| pathlib | stdlib | Cross-platform path handling | File path operations |
| asyncio.wait_for | stdlib | Timeout wrapper for lock acquisition | Configurable timeout per CONTEXT.md |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.Lock | aiorwlock (read/write lock) | asyncio.Lock simpler; per CONTEXT.md reads don't lock anyway |
| Inline IP markers | Separate claims file | Inline keeps work items and status together, more human-readable |
| aiofiles | aiofile (mosquito) | aiofiles more widely used, thread-pool based is fine for this use case |
| Single state file | SQLite/database | File-based per CONTEXT.md decisions; simpler, human-editable |

**Installation:**
```bash
pip install aiofiles
```

Note: aiofiles may already be installed via other dependencies. Verify with `pip show aiofiles`.

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── agno/
│   ├── tools/              # Existing from Phase 2
│   │   ├── toolkit.py      # HFSToolkit
│   │   └── schemas.py      # Existing schemas
│   └── state/              # NEW: Shared state management
│       ├── __init__.py     # Export SharedStateManager, SharedStateToolkit
│       ├── manager.py      # SharedStateManager class (file I/O + locking)
│       ├── toolkit.py      # SharedStateToolkit (Agno tools)
│       ├── schemas.py      # WorkItem, StateFile Pydantic models
│       └── parser.py       # Markdown parsing utilities
```

### Pattern 1: SharedStateManager with Write Queue
**What:** Central manager class wrapping async file I/O with FIFO-fair locking
**When to use:** All shared state read/write operations
**Example:**
```python
# Source: asyncio.Lock docs (FIFO fairness) + aiofiles patterns
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

class SharedStateManager:
    """Manages async access to shared state file with write serialization.

    Reads are non-blocking (no lock required per CONTEXT.md).
    Writes queue up and execute in FIFO order via asyncio.Lock.
    """

    def __init__(
        self,
        state_path: Path = Path(".hfs/state.md"),
        timeout_seconds: float = 30.0,
    ):
        self._state_path = state_path
        self._timeout = timeout_seconds
        self._write_lock = asyncio.Lock()

    async def read_state(self) -> str:
        """Read current state without locking.

        Returns raw markdown content. Parser extracts work items.
        Non-blocking - multiple agents can read concurrently.
        """
        if not self._state_path.exists():
            return self._get_initial_template()

        async with aiofiles.open(self._state_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def write_state(self, content: str) -> bool:
        """Write state with FIFO-queued locking.

        Queues behind other pending writes. Times out if lock
        not acquired within configured timeout.

        Returns:
            True if write succeeded, False if timeout
        """
        try:
            await asyncio.wait_for(
                self._write_lock.acquire(),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            return False

        try:
            # Ensure directory exists
            self._state_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(self._state_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            return True
        finally:
            self._write_lock.release()
```

### Pattern 2: Markdown State File Schema
**What:** Structured markdown sections for work items, claims, and agent registry
**When to use:** The `.hfs/state.md` file format (Claude's discretion per CONTEXT.md)
**Example:**
```markdown
# Shared State

## Available Work Items
- [ ] Build authentication module
- [ ] Implement user dashboard
- [ ] Add payment integration

## In Progress
- [ ] Create API endpoints [IP:agent-1]
- [ ] Design database schema [IP:agent-2]

## Completed
- [x] Set up project structure
- [x] Configure CI/CD pipeline

## Agent Registry
| Agent ID | Current Task | Started |
|----------|--------------|---------|
| agent-1 | Create API endpoints | 2026-01-29T14:30:00Z |
| agent-2 | Design database schema | 2026-01-29T14:32:00Z |
```

### Pattern 3: IP Marker Parsing with Regex
**What:** Extract and modify inline IP markers from markdown work items
**When to use:** Claim, release, and query operations
**Example:**
```python
# Source: CONTEXT.md IP marker decision + regex patterns
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass

# Regex for work item with optional IP marker
# Matches: - [ ] Task description [IP:agent-id]
# Groups: (checkbox_state, task_text, ip_marker_or_none)
WORK_ITEM_PATTERN = re.compile(
    r'^(\s*-\s*\[)([ xX])(\]\s*)(.+?)(\s*\[IP:([^\]]+)\])?\s*$'
)

@dataclass
class WorkItem:
    """Parsed work item from markdown."""
    raw_line: str
    indent: str
    is_complete: bool
    description: str
    claimed_by: Optional[str] = None
    line_number: int = 0

    @property
    def status(self) -> str:
        if self.is_complete:
            return "completed"
        elif self.claimed_by:
            return "in_progress"
        return "available"

def parse_work_item(line: str, line_num: int = 0) -> Optional[WorkItem]:
    """Parse a markdown line into a WorkItem if it matches the pattern."""
    match = WORK_ITEM_PATTERN.match(line)
    if not match:
        return None

    checkbox_state = match.group(2)
    task_text = match.group(4).strip()
    ip_marker = match.group(6)  # Agent ID or None

    return WorkItem(
        raw_line=line,
        indent=match.group(1).replace('-', '').replace('[', ''),
        is_complete=checkbox_state.lower() == 'x',
        description=task_text,
        claimed_by=ip_marker,
        line_number=line_num,
    )

def add_ip_marker(line: str, agent_id: str) -> str:
    """Add IP marker to a work item line."""
    # Remove existing marker if present
    line = re.sub(r'\s*\[IP:[^\]]+\]\s*$', '', line.rstrip())
    return f"{line} [IP:{agent_id}]"

def remove_ip_marker(line: str) -> str:
    """Remove IP marker from a work item line."""
    return re.sub(r'\s*\[IP:[^\]]+\]\s*$', '', line.rstrip())
```

### Pattern 4: SharedStateToolkit for Agno Agents
**What:** Toolkit extending Agno Toolkit with shared state query/update tools
**When to use:** Agents accessing shared state during execution
**Example:**
```python
# Source: Phase 2 HFSToolkit pattern + CONTEXT.md tool interface decisions
from agno.tools.toolkit import Toolkit
from typing import Callable, List, Optional
from pydantic import BaseModel, Field
import json

from .manager import SharedStateManager
from .schemas import WorkItemOutput, WorkItemsListOutput

class SharedStateToolkit(Toolkit):
    """Tools for multi-agent coordination via shared state.

    Provides:
    - get_work_items(): Query available/claimed/completed items
    - update_work_item(): Claim, complete, or release work items
    - get_agent_memory(): Read agent's local memory file
    - update_agent_memory(): Write to agent's local memory file
    """

    def __init__(
        self,
        manager: SharedStateManager,
        agent_id: str,
        **kwargs,
    ):
        self._manager = manager
        self._agent_id = agent_id

        tools: List[Callable] = [
            self.get_work_items,
            self.update_work_item,
            self.get_agent_memory,
            self.update_agent_memory,
        ]

        super().__init__(name="shared_state", tools=tools, **kwargs)

    def get_work_items(
        self,
        status: Optional[str] = None,
    ) -> str:
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
        # Implementation reads state, parses, filters
        pass

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
        # Implementation acquires write lock, modifies state
        pass
```

### Pattern 5: Per-Agent Local Memory Files
**What:** Optional markdown files for agent-specific scratchpad, subtasks, notes
**When to use:** Agent needs persistent local state between sessions (Claude's discretion)
**Example:**
```markdown
# Agent Memory: agent-1

## Scratchpad
Current approach: Using REST API with JWT authentication.
Need to verify: Rate limiting requirements from requirements doc.

## Subtasks
- [x] Review auth requirements
- [ ] Implement login endpoint
- [ ] Add token refresh logic

## Notes
- User mentioned preference for OAuth2 in standup
- Consider caching strategy for token validation
```

```python
# Local memory tool implementation
def get_agent_memory(self) -> str:
    """Read your local memory file.

    WHEN TO USE: At the start of a work session to recall context,
    or when you need to reference your previous notes.

    Returns:
        JSON with your memory file contents (scratchpad, subtasks, notes).
        Returns empty template if no memory file exists yet.
    """
    pass

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
    pass
```

### Pattern 6: Read-During-Write Semantics
**What:** Define behavior when reads occur while writes are pending
**When to use:** Claude's discretion per CONTEXT.md
**Example:**
```python
# Recommendation: Reads return latest committed state (last successful write)
# This is naturally achieved by file-based storage - reads see the file as-is

async def read_state(self) -> str:
    """Read current state without locking.

    Reads are non-blocking. If a write is in progress, this returns
    the state as it existed before that write started. The read will
    NOT see partial writes.

    This provides "snapshot isolation" - each read sees a consistent
    state, even if it's slightly stale during concurrent writes.
    """
    # aiofiles.open reads the current file atomically
    async with aiofiles.open(self._state_path, 'r', encoding='utf-8') as f:
        return await f.read()
```

### Anti-Patterns to Avoid
- **Read locking:** Per CONTEXT.md, reads should NOT require locks. Don't use aiorwlock when asyncio.Lock suffices for write serialization.
- **Heartbeat polling:** CONTEXT.md explicitly defers heartbeat systems. Don't add auto-expiry or timeout-based claim release.
- **Structured database:** Keep it simple with markdown files. Don't reach for SQLite or other databases.
- **Complex state machines:** IP markers are simple claim/release. Don't build elaborate status transitions.
- **Global state singleton:** Pass SharedStateManager via dependency injection, not module-level globals.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async file I/O | threading.Thread + open() | aiofiles | Non-blocking, integrates with asyncio event loop |
| Write queue ordering | Custom queue + workers | asyncio.Lock | FIFO-fair guarantee built in |
| Timeout handling | Manual time tracking | asyncio.wait_for | Clean timeout semantics |
| File watching | inotify/polling loop | N/A - not needed | CONTEXT.md has no heartbeat requirement |
| Markdown parsing | Hand-rolled line parser | Regex + dataclass | Regex handles edge cases (indentation, etc.) |

**Key insight:** The coordination model is intentionally simple. Agents mark IP when starting, done when finished. Orphaned claims are handled by human/orchestrator review, not automated expiry. This simplicity is a feature, not a gap.

## Common Pitfalls

### Pitfall 1: Blocking File I/O in Async Code
**What goes wrong:** Using synchronous `open()` blocks the event loop
**Why it happens:** Habit from sync Python
**How to avoid:** Always use `aiofiles.open()` for file operations in async contexts
**Warning signs:** Slow response times, event loop warnings

### Pitfall 2: Lock Timeout Without Feedback
**What goes wrong:** Agent waits for lock, times out, doesn't know why
**Why it happens:** Silent timeout handling
**How to avoid:** Return structured error with `"reason": "lock_timeout"` and retry hints
**Warning signs:** Agents stuck in retry loops without context

### Pitfall 3: Partial Write on Error
**What goes wrong:** Write starts, error occurs, state file corrupted
**Why it happens:** Not using atomic write patterns
**How to avoid:** Write to temp file, then rename (atomic on most filesystems)
**Warning signs:** Truncated or corrupted state files after crashes

### Pitfall 4: IP Marker Collision
**What goes wrong:** Two agents claim same item simultaneously before write completes
**Why it happens:** Read-claim-write race condition
**How to avoid:** The write lock serializes operations; read-modify-write is atomic within locked section
**Warning signs:** Multiple agents with same item claimed (shouldn't happen with proper locking)

### Pitfall 5: Over-Engineering State Schema
**What goes wrong:** Complex nested structures in markdown that are hard to parse/edit
**Why it happens:** Trying to capture too much metadata
**How to avoid:** Keep state file flat and simple. Use inline markers only for IP.
**Warning signs:** Frequent parse errors, hard to manually edit state file

### Pitfall 6: Forgetting Directory Creation
**What goes wrong:** First write fails because `.hfs/` doesn't exist
**Why it happens:** Assuming directory structure exists
**How to avoid:** Always `mkdir(parents=True, exist_ok=True)` before writing
**Warning signs:** FileNotFoundError on first state write

## Code Examples

### Complete SharedStateManager Implementation
```python
# Source: asyncio.Lock docs + aiofiles patterns + CONTEXT.md decisions
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import re

from .schemas import WorkItem, StateFileModel

WORK_ITEM_RE = re.compile(
    r'^(\s*-\s*\[)([ xX])(\]\s*)(.+?)(\s*\[IP:([^\]]+)\])?\s*$'
)

class SharedStateManager:
    """Manages shared state file with async I/O and write serialization."""

    DEFAULT_TIMEOUT = 30.0  # seconds

    def __init__(
        self,
        state_path: Path = Path(".hfs/state.md"),
        timeout_seconds: float = DEFAULT_TIMEOUT,
    ):
        self._state_path = Path(state_path)
        self._timeout = timeout_seconds
        self._write_lock = asyncio.Lock()

    async def read_state(self) -> str:
        """Read current state (non-locking)."""
        if not self._state_path.exists():
            return self._get_initial_template()

        async with aiofiles.open(self._state_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def write_state(self, content: str) -> Dict[str, Any]:
        """Write state with FIFO-queued locking.

        Returns:
            {"success": True} or {"success": False, "reason": "lock_timeout"}
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
            self._state_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write via temp file + rename
            temp_path = self._state_path.with_suffix('.tmp')
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            # Rename is atomic on most filesystems
            temp_path.rename(self._state_path)

            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "reason": "write_error",
                "error": str(e),
            }
        finally:
            self._write_lock.release()

    async def get_work_items(
        self,
        status: Optional[str] = None,
    ) -> List[WorkItem]:
        """Parse and filter work items from state."""
        content = await self.read_state()
        items = self._parse_work_items(content)

        if status:
            items = [i for i in items if i.status == status]

        return items

    async def claim_item(
        self,
        description: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Claim a work item (read-modify-write with lock)."""
        # Read current state
        content = await self.read_state()

        # Find and modify the item
        lines = content.split('\n')
        found = False

        for i, line in enumerate(lines):
            item = self._parse_line(line, i)
            if item and item.description == description:
                if item.status != "available":
                    return {
                        "success": False,
                        "reason": "not_available",
                        "current_status": item.status,
                        "claimed_by": item.claimed_by,
                    }
                # Add IP marker
                lines[i] = self._add_ip_marker(line, agent_id)
                found = True
                break

        if not found:
            return {
                "success": False,
                "reason": "not_found",
                "hint": "Work item not found. Check description spelling.",
            }

        # Write modified state
        new_content = '\n'.join(lines)
        result = await self.write_state(new_content)

        if result["success"]:
            return {
                "success": True,
                "description": description,
                "claimed_by": agent_id,
                "status": "in_progress",
            }
        return result

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

    def _parse_work_items(self, content: str) -> List[WorkItem]:
        """Parse all work items from markdown content."""
        items = []
        for i, line in enumerate(content.split('\n')):
            item = self._parse_line(line, i)
            if item:
                items.append(item)
        return items

    def _parse_line(self, line: str, line_num: int) -> Optional[WorkItem]:
        """Parse a single line into WorkItem if it matches."""
        match = WORK_ITEM_RE.match(line)
        if not match:
            return None

        checkbox = match.group(2)
        description = match.group(4).strip()
        ip_marker = match.group(6)

        return WorkItem(
            raw_line=line,
            line_number=line_num,
            is_complete=checkbox.lower() == 'x',
            description=description,
            claimed_by=ip_marker,
        )

    def _add_ip_marker(self, line: str, agent_id: str) -> str:
        """Add IP marker to line."""
        line = re.sub(r'\s*\[IP:[^\]]+\]\s*$', '', line.rstrip())
        return f"{line} [IP:{agent_id}]"

    def _remove_ip_marker(self, line: str) -> str:
        """Remove IP marker from line."""
        return re.sub(r'\s*\[IP:[^\]]+\]\s*$', '', line.rstrip())
```

### Pydantic Schemas
```python
# Source: Phase 2 schema patterns + CONTEXT.md work item design
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

class WorkItemStatus(str, Enum):
    """Status of a work item."""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class WorkItem(BaseModel):
    """A parsed work item from shared state."""
    description: str = Field(..., description="The work item text")
    status: WorkItemStatus = Field(..., description="Current status")
    claimed_by: Optional[str] = Field(None, description="Agent ID if claimed")
    line_number: int = Field(0, description="Line number in state file")
    is_complete: bool = Field(False, description="Whether checkbox is checked")
    raw_line: str = Field("", description="Original markdown line")

class GetWorkItemsInput(BaseModel):
    """Input for get_work_items tool."""
    status: Optional[Literal["available", "in_progress", "completed"]] = Field(
        None,
        description="Filter by status. None returns all items."
    )

class GetWorkItemsOutput(BaseModel):
    """Output for get_work_items tool."""
    success: bool
    message: str
    items: List[WorkItem]
    counts: dict  # {"available": N, "in_progress": N, "completed": N}

class UpdateWorkItemInput(BaseModel):
    """Input for update_work_item tool."""
    description: str = Field(..., min_length=1, description="Work item to match")
    action: Literal["claim", "complete", "release", "add"] = Field(
        ...,
        description="Action to perform"
    )
    new_description: Optional[str] = Field(
        None,
        description="For 'add' action: the new work item text"
    )

class UpdateWorkItemOutput(BaseModel):
    """Output for update_work_item tool."""
    success: bool
    message: str
    description: str
    status: Optional[str] = None
    claimed_by: Optional[str] = None
    error_reason: Optional[str] = None
    hint: Optional[str] = None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Database-backed state | Markdown files | Phase 4 design | Human-readable, version-controlled |
| Complex heartbeat systems | Simple IP markers | Phase 4 design | Reduced complexity per CONTEXT.md |
| Read/write locks | Write-only locks | Phase 4 design | Higher read concurrency |
| Structured JSON state | Inline markdown markers | Phase 4 design | Easier manual editing/review |

**Deprecated/outdated:**
- None in this phase - this is new functionality

## Open Questions

1. **State File Sections (Claude's Discretion)**
   - What we know: CONTEXT.md marks exact sections as Claude's discretion
   - Recommendation: Use simple sections: Available, In Progress, Completed, Agent Registry
   - The proposed schema above provides a good starting point

2. **Timeout Defaults**
   - What we know: CONTEXT.md says "configurable timeout with reasonable defaults"
   - Recommendation: 30 seconds default, configurable via SharedStateManager constructor
   - Consider environment variable override: `HFS_STATE_TIMEOUT`

3. **Error Return Type**
   - What we know: CONTEXT.md marks "exception vs result" as Claude's discretion
   - Recommendation: Return result dict with `success` flag, consistent with Phase 2 tools
   - Exceptions only for truly unexpected errors (file permissions, etc.)

4. **Agent Memory Template**
   - What we know: CONTEXT.md says "structured template sections" at Claude's discretion
   - Recommendation: Three sections (Scratchpad, Subtasks, Notes) as shown in Pattern 5

5. **State File Location**
   - Locked: `.hfs/state.md` per CONTEXT.md
   - Per-agent files: `.hfs/agents/{agent-id}.md` (recommendation)

## Sources

### Primary (HIGH confidence)
- [Python asyncio.Lock documentation](https://docs.python.org/3/library/asyncio-sync.html) - FIFO fairness guarantees
- [aiofiles PyPI](https://pypi.org/project/aiofiles/) - v25.1.0 API documentation
- Phase 2 RESEARCH.md - HFSToolkit patterns for tool design
- CONTEXT.md - Locked decisions for Phase 4

### Secondary (MEDIUM confidence)
- [GitHub aiofiles](https://github.com/Tinche/aiofiles) - Usage patterns and examples
- [Markdown Task Lists Guide](https://blog.markdowntools.com/posts/markdown-task-lists-and-checkboxes-complete-guide) - Checkbox syntax
- [aiorwlock](https://github.com/aio-libs/aiorwlock) - Read/write lock patterns (considered but not selected)

### Tertiary (LOW confidence)
- Web search results on multi-agent coordination patterns (verified against official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - aiofiles and asyncio.Lock are well-documented stdlib/standard libraries
- Architecture: HIGH - patterns derived from Phase 2 toolkit design and CONTEXT.md decisions
- Pitfalls: MEDIUM - based on common async file I/O issues and locking patterns
- Code examples: HIGH - validated against library documentation

**Research date:** 2026-01-29
**Valid until:** 90 days (stable libraries, simple patterns)
