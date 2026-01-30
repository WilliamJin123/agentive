# Phase 4: Shared State - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Markdown-based coordination layer enabling multi-agent collaboration with async locking. Agents read/write shared state files to know what work is claimed vs available. This phase delivers the state schema, locking mechanism, IP markers, and tools for querying/updating state.

</domain>

<decisions>
## Implementation Decisions

### State file structure
- Single shared state file at `.hfs/state.md` for coordination
- Optional per-agent local memory files with structured templates
- Shared state separates runtime coordination from planning docs
- Per-agent files follow defined sections (scratchpad, subtasks, notes)

### Locking behavior
- Queue-based ordering: writes queue up and execute in FIFO order
- Configurable timeout for acquiring write access (with reasonable defaults)
- Timeout behavior and read-during-write semantics at Claude's discretion

### IP marker design
- Inline tags embedded in work items: `- [ ] Build auth [IP:agent-1]`
- No heartbeat/polling system — agents mark IP when starting, done when finished
- Orphaned claims handled via manual review (human or orchestrator checks)
- No auto-expiry — simple claim/release lifecycle

### Query interface
- Single query tool with filters: `get_work_items(status='available')` etc.
- Single combined update tool with good docstring for all write operations (claim, complete, release)
- Agents can add new work items to shared state (enables dynamic task discovery)
- Dedicated local memory tools: `update_agent_memory()`, `get_agent_memory()`

### Claude's Discretion
- Exact sections for shared state file (Claims, Available, Completed, Agent Registry, etc.)
- Timeout defaults and error behavior (exception vs result)
- Read behavior during pending writes
- Structured template sections for per-agent local memory

</decisions>

<specifics>
## Specific Ideas

- Keep it simple — no complex heartbeat/polling infrastructure
- IP markers should be human-readable inline in the markdown
- State lives in `.hfs/` to separate runtime from planning artifacts

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-shared-state*
*Context gathered: 2026-01-29*
