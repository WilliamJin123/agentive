# Roadmap: HFS CLI v1.1 (Textual)

## Milestones

- [x] **v1 Agno + Keycycle Integration** - Phases 1-7 (shipped 2026-01-30)
- [ ] **v1.1 HFS CLI (Textual)** - Phases 8-13 (in progress)

## Overview

This milestone delivers a rich Textual-based CLI frontend with full observability into multi-agent negotiation. The architecture follows an event sourcing lite pattern: HFS emits typed Pydantic events via an async event bus, a state manager computes snapshots, and a query interface provides inspection data. The Textual UI consumes these layers for real-time agent visualization, streaming responses, and deep inspection capabilities. The foundation phases (8-9) establish the abstraction layer that both CLI and future web UI will consume. Phases 10-11 build the core TUI experience. Phases 12-13 add polish features and the plugin system.

## Phases

<details>
<summary>v1 Agno + Keycycle Integration (Phases 1-7) - SHIPPED 2026-01-30</summary>

See: .planning/MILESTONES.md for v1 summary.

- 7 phases, 20 plans, 108 commits
- Real LLM-powered multi-agent negotiation with Keycycle key rotation
- 4 providers configured (208 total API keys)
- Full OpenTelemetry observability

</details>

### v1.1 HFS CLI (Textual) (In Progress)

**Milestone Goal:** Rich terminal UI with full observability into multi-agent negotiation, preparing for future web UI.

- [x] **Phase 8: Event Foundation** - Event models, async event bus, OTel bridge
- [ ] **Phase 9: State & Query Layer** - State snapshots, query interface, JSON serialization
- [ ] **Phase 10: Textual Core** - Entry point, chat REPL, streaming, visual theme
- [ ] **Phase 11: Agent Visibility & Inspection** - Agent tree widget, negotiation panel, inspection mode
- [ ] **Phase 12: User Experience** - Configuration, output modes, input keybindings
- [ ] **Phase 13: Persistence & Plugins** - Sessions, checkpoints, export, plugin system

## Phase Details

### Phase 8: Event Foundation

**Goal**: HFS emits typed events that UI components can subscribe to in real-time
**Depends on**: Phase 7 (v1 complete)
**Requirements**: ABS-01, ABS-07

**Success Criteria** (what must be TRUE):
1. Event bus accepts subscriptions for specific event types and emits events to all matching handlers
2. Typed Pydantic events exist for all HFS lifecycle stages (run, phase, agent, negotiation, usage)
3. EventStream async generator yields events for real-time consumption
4. OpenTelemetry spans automatically emit corresponding events via custom SpanProcessor

**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md — Event models and async event bus
- [x] 08-02-PLAN.md — OTel SpanProcessor for event emission

---

### Phase 9: State & Query Layer

**Goal**: Clean API returns inspection data as JSON-serializable Pydantic models
**Depends on**: Phase 8
**Requirements**: ABS-02, ABS-03, ABS-04, ABS-05, ABS-06, ABS-08

**Success Criteria** (what must be TRUE):
1. StateManager computes RunSnapshot from events and orchestrator state
2. Query interface returns agent tree structure showing triads and their agents
3. Query interface returns negotiation state (claims, contests, section ownership)
4. Query interface returns token usage breakdown by agent, phase, and total
5. Query interface returns trace timeline with phase durations

**Plans**: TBD

Plans:
- [ ] 09-01: Snapshot models and StateManager
- [ ] 09-02: Query interface implementation

---

### Phase 10: Textual Core

**Goal**: Users can chat with HFS via a rich terminal interface with streaming responses
**Depends on**: Phase 9
**Requirements**: ENTRY-01, ENTRY-02, ENTRY-03, ENTRY-04, CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, STRM-01, STRM-02, STRM-03, STRM-04, THEME-01, THEME-02, THEME-03, THEME-04

**Success Criteria** (what must be TRUE):
1. `hfs` command launches interactive REPL with chat-style interface (input at bottom, messages scroll up)
2. LLM responses stream token-by-token with markdown rendering and syntax highlighting
3. Command history works with arrow keys and Ctrl+R fuzzy search
4. Slash commands work: /help, /clear, /exit, and Ctrl+C quits gracefully
5. Visual theme applies yellow/amber colors with triad-type color coding

**Plans**: TBD

Plans:
- [ ] 10-01: Entry point and Textual app scaffold
- [ ] 10-02: Chat widget with streaming and markdown
- [ ] 10-03: Visual theme and status bar

---

### Phase 11: Agent Visibility & Inspection

**Goal**: Users can observe agent activity and inspect detailed state at any time
**Depends on**: Phase 10
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06, INSP-01, INSP-02, INSP-03, INSP-04, INSP-05, INSP-06

**Success Criteria** (what must be TRUE):
1. Agent tree widget displays triad structure with roles, status, and active agent highlighting
2. Negotiation panel shows spec sections, claim status, temperature decay, and arbiter interventions
3. /inspect command opens deep inspection mode with agent tree drill-down
4. Inspection shows token/cost breakdown by agent and phase with visual trace timeline
5. User can navigate between inspection views (tree, negotiation, tokens, trace)

**Plans**: TBD

Plans:
- [ ] 11-01: Agent tree and negotiation widgets
- [ ] 11-02: Inspection mode with navigation

---

### Phase 12: User Experience

**Goal**: Users can configure HFS and customize their input/output experience
**Depends on**: Phase 11
**Requirements**: CONF-01, CONF-02, CONF-03, MODE-01, MODE-02, MODE-03, INPUT-01, INPUT-02, INPUT-03, INPUT-04

**Success Criteria** (what must be TRUE):
1. Config file loads from ~/.hfs/config.yaml or .hfs/config.yaml with env vars for API keys
2. /config command allows viewing and editing settings
3. Compact and verbose output modes toggle via command or config
4. Vim and Emacs keybinding modes work for input
5. Tab completion works for slash commands and file paths

**Plans**: TBD

Plans:
- [ ] 12-01: Configuration system and /config command
- [ ] 12-02: Output modes and input keybindings

---

### Phase 13: Persistence & Plugins

**Goal**: Users can save, resume, and extend their HFS sessions
**Depends on**: Phase 12
**Requirements**: SESS-01, SESS-02, SESS-03, SESS-04, CHKP-01, CHKP-02, CHKP-03, CHKP-04, EXPT-01, EXPT-02, EXPT-03, PLUG-01, PLUG-02, PLUG-03, PLUG-04

**Success Criteria** (what must be TRUE):
1. Sessions persist to database with list, resume, and rename capabilities
2. Automatic checkpoints capture state at key changes; user can list and rewind to checkpoints
3. Conversations export to markdown and JSON; import from JSON works
4. Plugin discovery loads plugins from ~/.hfs/plugins/
5. Plugins can register slash commands, add widgets, and hook into lifecycle events

**Plans**: TBD

Plans:
- [ ] 13-01: Session management with SQLAlchemy
- [ ] 13-02: Checkpoint system
- [ ] 13-03: Export/import functionality
- [ ] 13-04: Plugin system architecture

---

## Progress

**Execution Order:** Phases execute sequentially: 8 -> 9 -> 10 -> 11 -> 12 -> 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 8. Event Foundation | v1.1 | 2/2 | ✓ Complete | 2026-01-31 |
| 9. State & Query Layer | v1.1 | 0/2 | Not started | - |
| 10. Textual Core | v1.1 | 0/3 | Not started | - |
| 11. Agent Visibility & Inspection | v1.1 | 0/2 | Not started | - |
| 12. User Experience | v1.1 | 0/2 | Not started | - |
| 13. Persistence & Plugins | v1.1 | 0/4 | Not started | - |

**Total:** 2/15 plans complete (13%)

---
*Roadmap created: 2026-01-30*
*Last updated: 2026-01-31*
