# Phase 13: Persistence & Plugins - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can save, resume, and extend their HFS sessions. This phase delivers:
1. Session persistence with list/resume/rename
2. Automatic checkpoints with rewind capability
3. Export to markdown/JSON and import from JSON
4. Plugin system for commands, widgets, and lifecycle hooks

</domain>

<decisions>
## Implementation Decisions

### Session Storage
- Auto-generated name from first message + timestamp (e.g., "Fix login bug - 2026-02-01_14-30")
- Sessions can be renamed later
- Auto-save after each message exchange (every user message + response persisted immediately)
- /sessions lists most recent first with name + timestamp + message count

### Checkpoint Behavior
- Automatic checkpoints trigger both after each agent run completes AND at key state changes (negotiation resolution, phase transitions, arbiter decisions)
- Checkpoint retention configurable in config (default 10)
- Rewind creates a branch from checkpoint, preserving original history
- /checkpoints displays visual ASCII timeline showing checkpoint positions in conversation

### Export Formats
- Markdown export includes full trace: messages + agents + token usage + timing
- JSON export pretty-printed by default (indented, human-readable)
- Schema mismatches handled via automatic migration (upgrade old schemas silently)
- Exports saved to ~/.hfs/exports/ by default

### Plugin Architecture
- Discovery: scan ~/.hfs/plugins/ directory, config can disable specific plugins
- Capabilities: full access (commands, widgets, lifecycle hooks like on_message, on_run_start)
- Security: permission prompts when plugin first loads (user approves capabilities)
- Structure: package directory format (my_plugin/ with __init__.py and manifest)

### Claude's Discretion
- Storage backend choice (SQLite vs JSON files)
- Exact checkpoint data structure
- Migration strategy implementation details
- Plugin manifest schema

</decisions>

<specifics>
## Specific Ideas

- Visual ASCII timeline for checkpoints (not just a list)
- Branch-based rewind preserves history (like git branches)
- Full trace export for comprehensive debugging/sharing
- Permission prompts for plugin security (like mobile app permissions)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-persistence-plugins*
*Context gathered: 2026-02-01*
