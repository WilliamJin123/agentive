# Phase 11: Agent Visibility & Inspection - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can observe agent activity and inspect detailed state at any time. This includes an agent tree widget showing triad structure, a negotiation panel showing claims and contests, and an inspection mode with drill-down capabilities. Token breakdowns and trace timelines complete the observability picture.

</domain>

<decisions>
## Implementation Decisions

### Agent Tree Presentation
- Deep hierarchy: orchestrator > triad > agent with expandable levels
- Full dashboard per agent: activity state, running token count, last action time, current focus/task
- Active agent highlighting: triad-color styling (blue/purple/green) PLUS pulsing animation when streaming
- Tree updates live as agents become active

### Negotiation Visualization
- Visual document style: shows spec structure as abridged section list with ownership
- Format: section names with ownership badges, document hierarchy feel (not a flat table)
- Contested sections expand to show: agent names, percentage claim strength, AND temperature indicator
- Temperature shown as color gradient: hot colors (red/orange) cooling to blue as negotiation settles
- Live updates by default with pause capability to freeze and examine a moment
- Arbiter interventions: inline annotation on affected section AND separate intervention history log

### Inspection Navigation
- Split view: chat on one side, inspection on the other (not overlay or full replace)
- Fullscreen toggle: either panel can expand to full screen
- Sidebar menu for view switching: Tree | Negotiation | Tokens | Trace
- Progressive drill-down: start with agent summary card, expand sections to reveal deeper history

### Token/Trace Display
- Token breakdown: both agent view AND phase view with toggle between them
- Show tokens only (no dollar cost amounts)
- Trace timeline: Gantt-style with parallel agent tracks showing concurrent activity
- Phase summary row at top of Gantt showing phase duration bars (waterfall style)
- Full interactivity: click to inspect a moment, drag to scrub through time and watch state evolve

### Claude's Discretion
- Auto-expand behavior for agent tree (whether to auto-reveal active agents)
- Keyboard navigation scheme for inspection mode (vim-style, arrows, or hybrid)
- Exact layout proportions for split view
- Sidebar menu styling and icons

</decisions>

<specifics>
## Specific Ideas

- Negotiation panel should feel like viewing a document with ownership annotations, not a data table
- Contest display combines all three signals: who's fighting (names), who's winning (percentages), how hot (temperature)
- Timeline scrubbing lets you "replay" the negotiation to understand how it evolved
- The split view + fullscreen toggle gives flexibility: quick glance vs deep dive

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-agent-visibility*
*Context gathered: 2026-01-31*
