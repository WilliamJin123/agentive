# Requirements: HFS CLI v1.1 (Textual)

**Defined:** 2026-01-30
**Core Value:** Rich terminal UI with full observability into multi-agent negotiation

## v1.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Abstraction Layer

- [ ] **ABS-01**: Event bus emits typed events for all HFS lifecycle stages
- [ ] **ABS-02**: State manager computes snapshots from events + orchestrator
- [ ] **ABS-03**: Query interface returns agent tree structure as Pydantic models
- [ ] **ABS-04**: Query interface returns negotiation state (claims, contests, decisions)
- [ ] **ABS-05**: Query interface returns token usage per agent, phase, and total
- [ ] **ABS-06**: Query interface returns trace timeline with phase durations
- [ ] **ABS-07**: OpenTelemetry SpanProcessor emits events to event bus
- [ ] **ABS-08**: All query responses are JSON-serializable for future web UI

### Streaming & Display

- [ ] **STRM-01**: User sees LLM responses token-by-token as they stream
- [ ] **STRM-02**: Markdown renders with syntax highlighting, code fences, tables
- [ ] **STRM-03**: Progress indicator shows current operation during agent work
- [ ] **STRM-04**: Errors display gracefully with retry option

### Chat Interface

- [ ] **CHAT-01**: Chat-style REPL with input at bottom, messages scroll up
- [ ] **CHAT-02**: Command history accessible via arrow keys
- [ ] **CHAT-03**: Fuzzy history search via Ctrl+R
- [ ] **CHAT-04**: Session context persists across messages within a run
- [ ] **CHAT-05**: /clear resets conversation state
- [ ] **CHAT-06**: /exit and Ctrl+C quit gracefully
- [ ] **CHAT-07**: /help shows available commands

### Agent Visibility

- [ ] **AGENT-01**: Agent tree widget shows triad structure, roles, status
- [ ] **AGENT-02**: Active agent highlighted in real-time
- [ ] **AGENT-03**: Negotiation panel shows spec sections and claim status
- [ ] **AGENT-04**: Temperature decay and round progress visible
- [ ] **AGENT-05**: Arbiter interventions highlighted
- [ ] **AGENT-06**: Model escalation events shown with reason

### Inspection & Metrics

- [ ] **INSP-01**: /inspect command opens deep inspection mode
- [ ] **INSP-02**: Inspection shows full agent tree with drill-down
- [ ] **INSP-03**: Inspection shows negotiation state detail
- [ ] **INSP-04**: Inspection shows token/cost breakdown by agent and phase
- [ ] **INSP-05**: Trace timeline shows phase durations with visual bars
- [ ] **INSP-06**: Navigation between inspection views (tree, negotiation, tokens, trace)

### Visual Theme

- [ ] **THEME-01**: Yellow/amber primary color palette (#F59E0B base)
- [ ] **THEME-02**: Consistent color coding for triad types (Hierarchical, Dialectic, Consensus)
- [ ] **THEME-03**: Hexagonal motifs in borders/decorations where appropriate
- [ ] **THEME-04**: Status bar shows current phase, token count, active agent

### Configuration

- [ ] **CONF-01**: Config file support (~/.hfs/config.yaml or .hfs/config.yaml)
- [ ] **CONF-02**: Environment variables for API keys (existing Keycycle integration)
- [ ] **CONF-03**: /config command to view/edit settings

### Session Management

- [ ] **SESS-01**: Sessions persist to database (SQLAlchemy integration)
- [ ] **SESS-02**: User can list previous sessions
- [ ] **SESS-03**: User can resume a previous session
- [ ] **SESS-04**: User can name/rename sessions

### Checkpoints

- [ ] **CHKP-01**: Automatic checkpoints at key state changes
- [ ] **CHKP-02**: User can list checkpoints within a session
- [ ] **CHKP-03**: User can rewind to a previous checkpoint
- [ ] **CHKP-04**: Checkpoint includes conversation state and agent state

### Export/Import

- [ ] **EXPT-01**: Export conversation to markdown file
- [ ] **EXPT-02**: Export conversation to JSON
- [ ] **EXPT-03**: Import previous conversation from JSON

### Output Modes

- [ ] **MODE-01**: Compact mode shows minimal output
- [ ] **MODE-02**: Verbose mode shows full agent activity
- [ ] **MODE-03**: Toggle between modes via command or config

### Input Enhancement

- [ ] **INPUT-01**: Vim keybinding mode for input
- [ ] **INPUT-02**: Emacs keybinding mode for input
- [ ] **INPUT-03**: Tab completion for slash commands
- [ ] **INPUT-04**: Tab completion for file paths in arguments

### Plugin System

- [ ] **PLUG-01**: Plugin discovery from ~/.hfs/plugins/
- [ ] **PLUG-02**: Plugins can register new slash commands
- [ ] **PLUG-03**: Plugins can add custom widgets to UI
- [ ] **PLUG-04**: Plugin lifecycle hooks (on_start, on_message, on_complete)

### Entry Point

- [ ] **ENTRY-01**: Global `hfs` command installed via pip
- [ ] **ENTRY-02**: `hfs` launches interactive REPL by default
- [ ] **ENTRY-03**: `hfs --version` shows version
- [ ] **ENTRY-04**: `hfs --help` shows usage

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### File Watching

- **WATCH-01**: Watch mode monitors file changes
- **WATCH-02**: Configurable file patterns to watch
- **WATCH-03**: Reactive agents triggered by file events
- **WATCH-04**: Agent-to-pattern assignment in config

### Web UI

- **WEB-01**: Textual-web serves CLI in browser
- **WEB-02**: Alternative: Next.js frontend consuming query API
- **WEB-03**: WebSocket transport for event streaming

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Built-in code execution (REPL) | HFS is design negotiation, not code running |
| Real-time collaboration | Massive complexity, individual run focus |
| Over-animated UI | Terminal users value speed/clarity |
| AI command suggestions | Agents ARE the AI, don't add meta-layer |
| Complex nested menus | Flat slash commands are better UX |
| Mobile app | CLI-first, Textual-web covers browser |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (To be filled by roadmapper) | | |

**Coverage:**
- v1.1 requirements: 52 total
- Mapped to phases: 0
- Unmapped: 52

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-30 after initial definition*
