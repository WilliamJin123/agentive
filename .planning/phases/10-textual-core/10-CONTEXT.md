# Phase 10: Textual Core - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Rich terminal chat interface where users interact with HFS through a streaming REPL. Users can chat with HFS via a Textual-based terminal UI with streaming responses, markdown rendering, and command history. Agent visibility and inspection are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Chat layout
- Minimal style following Claude Code / OpenCode / Gemini CLI conventions
- User vs assistant messages clearly distinguished without heavy chrome
- Timestamps visible on hover/focus only — clean default view
- Messages show in full by default with collapse option for long content
- Vertical spacing at Claude's discretion

### Streaming presentation
- Pulsing dot indicator while streaming (not blinking block)
- Hybrid markdown rendering: inline formatting (bold, italic, code) renders live; code blocks and tables render on complete
- Smart scroll: auto-follows at bottom, stays put if user scrolled up
- Syntax highlighting applies live as code streams in

### Input experience
- Single-line input that auto-grows with content
- Auto-wrapping to prevent overflow
- Large pastes abbreviated (Claude Code style) with configurable line threshold
- Enter submits, Shift+Enter for newlines
- Minimal prompt — no character, just clear visual boundary for input area
- Character/token counter always visible

### Status & chrome
- No header — maximize chat space
- Informative status bar: model name, session token count, active agents
- Cost estimate and response time as configurable additions
- Themed loading spinner: hexagonal/hive-inspired, yellow, with "Thinking..." text
- Spinner appears inline in chat where response will stream

### Claude's Discretion
- Exact vertical spacing between messages
- Specific animation timing for pulsing dot and hex spinner
- Character vs token counter implementation
- Abbreviated paste truncation behavior details

</decisions>

<specifics>
## Specific Ideas

- Follow Claude Code / OpenCode / Gemini CLI aesthetic — minimal but clean
- Hex/hive-themed loading spinner that's unique to HFS (yellow, hexagonal)
- Large paste handling like Claude Code — abbreviate with configurable threshold for logs and big content

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-textual-core*
*Context gathered: 2026-01-31*
