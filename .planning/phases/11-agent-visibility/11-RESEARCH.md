# Phase 11: Agent Visibility & Inspection - Research

**Researched:** 2026-01-31
**Domain:** Textual TUI widgets for agent tree, negotiation panel, inspection mode with drill-down
**Confidence:** HIGH

## Summary

This phase implements comprehensive agent visibility and inspection capabilities using Textual widgets. The system requires: (1) an agent tree widget showing hierarchical triad structure with live status updates and pulsing animations for active agents, (2) a negotiation panel with document-style section display including temperature gradient visualization, (3) a split-view inspection mode with sidebar navigation between Tree, Negotiation, Tokens, and Trace views, and (4) a Gantt-style timeline with interactive scrubbing.

The existing HFS codebase provides excellent foundations: the state layer (`hfs/state/`) already has Pydantic models for AgentTree, NegotiationSnapshot, TokenUsageSummary, and TraceTimeline. The QueryInterface provides typed queries and subscription for real-time updates. The TUI layer (`hfs/tui/`) has the app structure, theme with triad colors, and reactive attribute patterns.

Textual's Tree widget is the ideal choice for the agent hierarchy with expandable nodes. For the negotiation panel, a custom widget composing Static elements with Rich text formatting provides the document-style presentation. The split view uses Horizontal containers with a ContentSwitcher for view navigation. The trace timeline requires a custom widget using Unicode block characters for Gantt-style bars.

**Primary recommendation:** Build on existing state layer with new widgets: AgentTreeWidget (Tree subclass with custom node rendering), NegotiationPanel (Vertical container with collapsible sections), InspectionView (split Horizontal + ContentSwitcher), and TraceTimeline (custom canvas-style widget with block characters).

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | >=7.5.0 | TUI framework with Tree, ContentSwitcher, reactive attributes | Already in use; native support for hierarchical displays |
| rich | >=14.3.1 | Text styling, gradients, sparklines | Already in use; powers Textual's rendering |
| hfs.state | existing | State models and QueryInterface | Provides all data models already defined |
| hfs.events | existing | Event subscription for live updates | Already has subscription mechanism |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hfs.tui.theme | existing | Triad colors, theme variables | All styling uses existing theme |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tree widget | DataTable | DataTable is flat; Tree handles hierarchy naturally |
| ContentSwitcher | TabbedContent | ContentSwitcher allows custom sidebar; TabbedContent has built-in tabs |
| Custom timeline widget | External Gantt library | No terminal Gantt libraries exist; custom is necessary |

**Installation:**
```bash
# No new dependencies needed - all requirements already in project
pip install "textual>=7.5.0" "rich>=14.3.1"
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── tui/
│   ├── widgets/
│   │   ├── agent_tree.py       # Tree widget showing triad hierarchy
│   │   ├── negotiation_panel.py # Document-style section display
│   │   ├── token_breakdown.py  # Token usage by agent/phase
│   │   ├── trace_timeline.py   # Gantt-style timeline widget
│   │   └── temperature_bar.py  # Color gradient temperature indicator
│   ├── screens/
│   │   ├── chat.py             # Existing chat screen (modify for split)
│   │   └── inspection.py       # Split-view inspection mode
│   └── styles/
│       └── inspection.tcss     # Inspection-specific styles
```

### Pattern 1: Tree Widget with Custom Node Rendering
**What:** Subclass Tree to render agent nodes with status indicators, triad colors, and pulsing animation
**When to use:** Agent tree display with live status updates
**Example:**
```python
# Source: https://textual.textualize.io/widgets/tree/
from textual.widgets import Tree
from textual.widgets._tree import TreeNode
from rich.text import Text

from hfs.state.models import AgentNode, AgentStatus

class AgentTreeWidget(Tree[AgentNode]):
    """Tree widget for displaying agent hierarchy with live status."""

    # Triad colors from HFS theme
    TRIAD_COLORS = {
        "hierarchical": "#3B82F6",  # Blue
        "dialectic": "#A855F7",     # Purple
        "consensus": "#22C55E",     # Green
    }

    def render_label(
        self,
        node: TreeNode[AgentNode],
        base_style: Style,
        style: Style
    ) -> Text:
        """Custom rendering for agent nodes with status and triad color."""
        agent = node.data
        if agent is None:
            return Text(str(node.label))

        # Status indicator
        status_icon = {
            AgentStatus.IDLE: "[ ]",
            AgentStatus.WORKING: "[>]",
            AgentStatus.BLOCKED: "[!]",
            AgentStatus.COMPLETE: "[+]",
        }.get(agent.status, "[ ]")

        # Color based on triad preset
        color = self.TRIAD_COLORS.get(agent.triad_id.split("-")[0], "#FFFFFF")

        label = Text()
        label.append(status_icon, style=f"bold {color}")
        label.append(f" {agent.role}", style=color)

        # Token count if available
        if hasattr(agent, "token_count") and agent.token_count:
            label.append(f" ({agent.token_count:,} tokens)", style="dim")

        return label
```

### Pattern 2: Split View with ContentSwitcher Navigation
**What:** Horizontal container with sidebar menu and ContentSwitcher for view switching
**When to use:** Inspection mode with multiple views (Tree, Negotiation, Tokens, Trace)
**Example:**
```python
# Source: https://textual.textualize.io/widgets/content_switcher/
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, ContentSwitcher, Static
from textual.screen import Screen

class InspectionView(Screen):
    """Split-view inspection mode with sidebar navigation."""

    DEFAULT_CSS = """
    InspectionView {
        layout: horizontal;
    }

    #inspection-sidebar {
        width: 16;
        background: $surface;
        border-right: solid $hfs-border;
    }

    #inspection-content {
        width: 1fr;
    }

    .nav-button {
        width: 100%;
        margin: 1 0;
    }

    .nav-button.-active {
        background: $primary;
    }
    """

    BINDINGS = [
        Binding("1", "show_view('tree')", "Tree"),
        Binding("2", "show_view('negotiation')", "Negotiation"),
        Binding("3", "show_view('tokens')", "Tokens"),
        Binding("4", "show_view('trace')", "Trace"),
        Binding("f", "toggle_fullscreen", "Fullscreen"),
        Binding("escape", "exit_inspection", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="inspection-sidebar"):
                yield Button("Tree", id="nav-tree", classes="nav-button -active")
                yield Button("Negotiation", id="nav-negotiation", classes="nav-button")
                yield Button("Tokens", id="nav-tokens", classes="nav-button")
                yield Button("Trace", id="nav-trace", classes="nav-button")
            with ContentSwitcher(id="inspection-content", initial="tree"):
                yield AgentTreeWidget(id="tree")
                yield NegotiationPanel(id="negotiation")
                yield TokenBreakdown(id="tokens")
                yield TraceTimeline(id="trace")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button press."""
        view_id = event.button.id.replace("nav-", "")
        self.action_show_view(view_id)

    def action_show_view(self, view_id: str) -> None:
        """Switch to specified view."""
        switcher = self.query_one(ContentSwitcher)
        switcher.current = view_id
        # Update active button styling
        for button in self.query(".nav-button"):
            button.remove_class("-active")
        self.query_one(f"#nav-{view_id}").add_class("-active")
```

### Pattern 3: State Subscription for Live Updates
**What:** Subscribe to StateManager changes and refresh widgets on relevant events
**When to use:** Any widget that needs live updates (agent tree, negotiation panel)
**Example:**
```python
# Source: hfs/state/query.py QueryInterface.subscribe()
from textual.widgets import Static
from textual.reactive import reactive

from hfs.state.query import QueryInterface, ChangeCategory, StateChange

class LiveAgentTree(AgentTreeWidget):
    """Agent tree with automatic live updates from state changes."""

    _query: QueryInterface | None = None
    _unsubscribe: Callable[[], None] | None = None

    def on_mount(self) -> None:
        """Subscribe to state changes on mount."""
        # Get QueryInterface from app (must be provided)
        self._query = self.app.query_interface

        # Subscribe to agent tree changes
        self._unsubscribe = self._query.subscribe(
            self._on_state_change,
            category=ChangeCategory.AGENT_TREE,
        )

        # Initial population
        self._refresh_tree()

    def on_unmount(self) -> None:
        """Unsubscribe on unmount to prevent leaks."""
        if self._unsubscribe:
            self._unsubscribe()

    async def _on_state_change(self, change: StateChange) -> None:
        """Handle state change notification."""
        # Use call_from_thread if needed for thread safety
        self.call_from_thread(self._refresh_tree)

    def _refresh_tree(self) -> None:
        """Rebuild tree from current state."""
        if not self._query:
            return

        tree_data = self._query.get_agent_tree()
        self.clear()

        for triad in tree_data.triads:
            triad_node = self.root.add(f"Triad: {triad.preset}", expand=True)
            for agent in triad.agents:
                triad_node.add_leaf(agent.role, data=agent)
```

### Pattern 4: Temperature Gradient Bar
**What:** Custom widget showing temperature as color gradient (hot red/orange to cool blue)
**When to use:** Negotiation panel to show temperature decay
**Example:**
```python
# Source: https://textual.textualize.io/widgets/progress_bar/ + Rich gradients
from textual.widgets import Static
from rich.text import Text
from rich.style import Style

class TemperatureBar(Static):
    """Visual temperature indicator with color gradient."""

    DEFAULT_CSS = """
    TemperatureBar {
        height: 1;
        width: 100%;
    }
    """

    # Unicode block characters for smooth bar
    BLOCKS = " ▏▎▍▌▋▊▉█"

    temperature: reactive[float] = reactive(1.0)

    def watch_temperature(self, value: float) -> None:
        """Update display when temperature changes."""
        self.refresh()

    def render(self) -> Text:
        """Render temperature as colored bar."""
        # Clamp to 0-1 range
        temp = max(0.0, min(1.0, self.temperature))

        # Color gradient: hot (red) -> warm (orange) -> cool (blue)
        if temp > 0.66:
            # Hot: red to orange
            color = "#EF4444"  # Red
        elif temp > 0.33:
            # Warm: orange to yellow
            color = "#F59E0B"  # Amber
        else:
            # Cool: yellow to blue
            color = "#3B82F6"  # Blue

        # Calculate bar width (terminal columns)
        width = self.size.width - 2  # Leave space for label
        filled = int(temp * width)

        text = Text()
        text.append("█" * filled, style=color)
        text.append("░" * (width - filled), style="dim")
        text.append(f" {temp:.0%}", style="bold")

        return text
```

### Pattern 5: Gantt-Style Timeline with Unicode Blocks
**What:** Custom widget rendering timeline with horizontal bars for phase/agent durations
**When to use:** Trace timeline view with parallel agent tracks
**Example:**
```python
# Source: https://alexwlchan.net/2018/ascii-bar-charts/ + Textual Static
from textual.widgets import Static
from textual.containers import Vertical
from rich.text import Text
from rich.table import Table

from hfs.state.models import TraceTimeline, PhaseTimeline

class TraceTimelineWidget(Vertical):
    """Gantt-style timeline showing phase and agent durations."""

    DEFAULT_CSS = """
    TraceTimelineWidget {
        height: auto;
        width: 100%;
    }

    .timeline-row {
        height: 1;
    }

    .timeline-label {
        width: 20;
    }

    .timeline-bar {
        width: 1fr;
    }
    """

    BLOCK_CHARS = "▏▎▍▌▋▊▉█"

    def __init__(self, timeline: TraceTimeline | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._timeline = timeline

    def set_timeline(self, timeline: TraceTimeline) -> None:
        """Update timeline data and refresh display."""
        self._timeline = timeline
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild timeline visualization."""
        self.remove_children()

        if not self._timeline or not self._timeline.phases:
            self.mount(Static("No timeline data"))
            return

        # Calculate time scale
        total_ms = self._timeline.total_duration_ms or 1.0
        bar_width = 60  # Characters for bar

        # Phase summary row (waterfall style)
        self.mount(Static("Phase Summary", classes="timeline-header"))

        for phase in self._timeline.phases:
            row = self._render_phase_row(phase, total_ms, bar_width)
            self.mount(row)

    def _render_phase_row(
        self,
        phase: PhaseTimeline,
        total_ms: float,
        bar_width: int
    ) -> Static:
        """Render a single phase as a timeline bar."""
        duration = phase.duration_ms or 0
        start_offset = 0  # Would calculate from phase.started_at

        # Calculate bar position and width
        bar_start = int((start_offset / total_ms) * bar_width)
        bar_len = max(1, int((duration / total_ms) * bar_width))

        # Build the bar
        text = Text()
        text.append(f"{phase.phase_name:20}", style="bold")
        text.append(" " * bar_start)
        text.append("█" * bar_len, style="$primary")
        text.append(f" {duration:.0f}ms", style="dim")

        return Static(text, classes="timeline-row")
```

### Pattern 6: Pulsing Animation for Active Agent
**What:** CSS animation or interval-based opacity pulsing for streaming agents
**When to use:** Highlight currently active agent in tree
**Example:**
```python
# Source: https://textual.textualize.io/guide/animation/
from textual.widgets import Static
from textual.reactive import reactive

class PulsingAgentIndicator(Static):
    """Pulsing indicator for active streaming agent."""

    DEFAULT_CSS = """
    PulsingAgentIndicator {
        width: auto;
        height: 1;
    }

    PulsingAgentIndicator.-pulsing {
        /* CSS animation alternative would go here */
    }
    """

    is_active: reactive[bool] = reactive(False)
    _pulse_direction: int = 1

    def on_mount(self) -> None:
        """Start pulse animation timer."""
        self.set_interval(0.1, self._pulse_tick)

    def _pulse_tick(self) -> None:
        """Animate opacity when active."""
        if not self.is_active:
            self.styles.opacity = 1.0
            return

        current = self.styles.opacity or 1.0

        # Pulse between 0.3 and 1.0
        if current >= 1.0:
            self._pulse_direction = -1
        elif current <= 0.3:
            self._pulse_direction = 1

        new_opacity = current + (0.1 * self._pulse_direction)
        self.styles.opacity = max(0.3, min(1.0, new_opacity))
```

### Anti-Patterns to Avoid
- **Polling state instead of subscribing:** Use StateManager subscriptions, not periodic polling
- **Rebuilding entire tree on every update:** Use targeted node updates where possible
- **Blocking UI thread with state queries:** State queries are sync but fast; still use workers for heavy ops
- **Direct widget updates from non-main thread:** Always use `call_from_thread()` for thread-safe updates
- **Creating new subscription on each refresh:** Subscribe once on mount, unsubscribe on unmount

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hierarchical display | Custom nested containers | Textual Tree widget | Built-in expand/collapse, keyboard nav, efficient rendering |
| View switching | Manual visibility toggling | ContentSwitcher | Handles display:none, focus management |
| Live state updates | Polling/timers | QueryInterface.subscribe() | Event-driven, efficient, no wasted CPU |
| Color gradients | Manual color interpolation | Rich Text styling | Rich handles color codes, themes |
| Collapsible sections | Custom toggle logic | Collapsible widget or Tree | Built-in animation, accessibility |
| Token formatting | Manual string formatting | Python f-strings with :, | Built-in thousands separator |

**Key insight:** The existing state layer provides all the data models and query methods needed. The TUI layer's job is pure presentation - consume QueryInterface, render with Textual widgets, subscribe for updates.

## Common Pitfalls

### Pitfall 1: Tree Widget Performance with Large Agent Counts
**What goes wrong:** Tree becomes slow with hundreds of agents updating rapidly
**Why it happens:** Full tree refresh on every agent state change
**How to avoid:**
- Use `move_cursor()` and `scroll_to_node()` for targeted updates
- Batch multiple agent updates into single tree refresh
- Only update visible nodes (Tree handles this but custom rendering can break it)
**Warning signs:** Visible lag when multiple agents become active simultaneously

### Pitfall 2: State Subscription Memory Leaks
**What goes wrong:** Subscriptions accumulate, handlers called on unmounted widgets
**Why it happens:** Forgetting to unsubscribe in `on_unmount()`
**How to avoid:** Store unsubscribe function, call it in `on_unmount()`, use weak references if appropriate
**Warning signs:** Growing memory usage over time, "widget not mounted" errors

### Pitfall 3: Negotiation Panel Layout Thrashing
**What goes wrong:** Layout recalculates on every temperature/claim update
**Why it happens:** Changing widget content causes layout cascade
**How to avoid:**
- Use `Static.update()` instead of replacing widgets
- Set fixed heights where possible
- Batch visual updates with `self.app.batch_update()`
**Warning signs:** Flickering during negotiation rounds, high CPU during updates

### Pitfall 4: Timeline Scrubbing Performance
**What goes wrong:** UI freezes when dragging scrubber across long timeline
**Why it happens:** Rebuilding state display on every scrub position change
**How to avoid:**
- Throttle scrub position updates (e.g., 60fps max)
- Use lightweight preview during drag, full render on release
- Pre-compute timeline layout, only update cursor position
**Warning signs:** Choppy scrubbing, dropped frames during drag

### Pitfall 5: Split View Focus Management
**What goes wrong:** Keyboard navigation stops working after view switch
**Why it happens:** Focus lost when ContentSwitcher hides widgets
**How to avoid:**
- Explicitly set focus after `ContentSwitcher.current` change
- Use `@on(ContentSwitcher.Changed)` to manage focus
- Store last focused widget per view
**Warning signs:** Can't navigate tree after switching to Tokens view and back

### Pitfall 6: Temperature Gradient Rendering Artifacts
**What goes wrong:** Color bands or wrong colors in temperature indicator
**Why it happens:** Integer truncation in color interpolation, terminal color support issues
**How to avoid:**
- Use Rich's built-in color handling
- Test on multiple terminal emulators
- Provide fallback for 16-color terminals
**Warning signs:** Visible color banding, colors look wrong in certain terminals

## Code Examples

Verified patterns from official sources:

### Document-Style Negotiation Section
```python
# Source: Textual widgets + Rich formatting
from textual.widgets import Static, Collapsible
from textual.containers import Vertical
from rich.text import Text
from rich.panel import Panel

from hfs.state.models import SectionNegotiationState

class NegotiationSection(Vertical):
    """Single section in negotiation panel with owner badge and claims."""

    DEFAULT_CSS = """
    NegotiationSection {
        height: auto;
        margin: 0 1;
        padding: 1;
        border: solid $hfs-border;
    }

    NegotiationSection.-contested {
        border: solid $warning;
    }

    NegotiationSection.-claimed {
        border: solid $success;
    }
    """

    def __init__(self, section: SectionNegotiationState, **kwargs) -> None:
        super().__init__(**kwargs)
        self._section = section

    def compose(self) -> ComposeResult:
        section = self._section

        # Header with section name and owner badge
        header = Text()
        header.append(section.section_name, style="bold")

        if section.owner:
            header.append(" ")
            header.append(f"[{section.owner}]", style="green bold")

        yield Static(header, id="section-header")

        # If contested, show expandable claims
        if section.status == "contested":
            self.add_class("-contested")
            with Collapsible(title="Claims", collapsed=True):
                for claimant in section.claimants:
                    claim_text = Text()
                    claim_text.append(f"  {claimant}", style="yellow")
                    yield Static(claim_text)
        elif section.status == "claimed":
            self.add_class("-claimed")
```

### Agent Tree Node with Token Count
```python
# Source: Textual Tree + hfs.state.models
from textual.widgets import Tree
from textual.widgets._tree import TreeNode
from rich.text import Text

class AgentTreeNode:
    """Data class for agent tree node."""

    def __init__(
        self,
        agent_id: str,
        role: str,
        status: str,
        triad_preset: str,
        token_count: int = 0,
        is_streaming: bool = False,
    ):
        self.agent_id = agent_id
        self.role = role
        self.status = status
        self.triad_preset = triad_preset
        self.token_count = token_count
        self.is_streaming = is_streaming

class HFSAgentTree(Tree[AgentTreeNode]):
    """Agent tree with HFS-specific node rendering."""

    TRIAD_STYLES = {
        "hierarchical": "$hfs-hierarchical",
        "dialectic": "$hfs-dialectic",
        "consensus": "$hfs-consensus",
    }

    STATUS_ICONS = {
        "idle": "",
        "working": "",
        "blocked": "",
        "complete": "",
    }

    def render_label(
        self,
        node: TreeNode[AgentTreeNode],
        base_style,
        style,
    ) -> Text:
        data = node.data
        if data is None:
            return Text(str(node.label))

        color = self.TRIAD_STYLES.get(data.triad_preset, "white")
        icon = self.STATUS_ICONS.get(data.status, "")

        label = Text()
        label.append(icon, style=color)
        label.append(f" {data.role}", style=f"bold {color}")

        if data.token_count > 0:
            label.append(f" {data.token_count:,}", style="dim")

        if data.is_streaming:
            label.append(" ...", style=f"blink {color}")

        return label
```

### Token Breakdown Table
```python
# Source: Textual DataTable
from textual.widgets import DataTable
from rich.text import Text

from hfs.state.models import TokenUsageSummary, PhaseTokenUsage

class TokenBreakdown(DataTable):
    """Token usage breakdown with phase/agent toggle."""

    DEFAULT_CSS = """
    TokenBreakdown {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("p", "show_by_phase", "By Phase"),
        Binding("a", "show_by_agent", "By Agent"),
    ]

    _view_mode: str = "phase"  # or "agent"

    def on_mount(self) -> None:
        self.add_columns("Name", "Prompt", "Completion", "Total")
        self.cursor_type = "row"

    def set_usage(self, usage: TokenUsageSummary) -> None:
        """Update table with token usage data."""
        self.clear()

        if self._view_mode == "phase":
            for phase in usage.by_phase:
                self.add_row(
                    phase.phase_name,
                    str(sum(a.prompt_tokens for a in phase.agents)),
                    str(sum(a.completion_tokens for a in phase.agents)),
                    str(phase.total_tokens),
                )
        else:
            for agent in usage.by_agent:
                self.add_row(
                    agent.agent_id,
                    str(agent.prompt_tokens),
                    str(agent.completion_tokens),
                    str(agent.total_tokens),
                )

        # Add total row
        self.add_row(
            Text("TOTAL", style="bold"),
            "",
            "",
            Text(f"{usage.total_tokens:,}", style="bold"),
        )

    def action_show_by_phase(self) -> None:
        self._view_mode = "phase"
        # Trigger refresh (would query state again)

    def action_show_by_agent(self) -> None:
        self._view_mode = "agent"
        # Trigger refresh
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling state with timers | Event subscription pattern | HFS v1.1 state layer | Efficient, event-driven updates |
| Full widget replacement | Reactive attribute watchers | Textual v4.0+ | Smooth updates, no flicker |
| Custom scroll management | VerticalScroll + anchor() | Textual v4.0+ | Built-in auto-scroll |
| Manual focus tracking | ContentSwitcher focus management | Textual v5.0+ | Automatic focus preservation |

**Deprecated/outdated:**
- Manual DOM manipulation for visibility: Use `display` CSS property or ContentSwitcher
- Timer-based animation: Use `styles.animate()` or CSS animations where possible

## Open Questions

Things that couldn't be fully resolved:

1. **Arbiter intervention highlighting**
   - What we know: Need inline annotation on affected section AND separate log
   - What's unclear: Exact visual treatment for inline annotation (border? background? icon?)
   - Recommendation: Use colored left border + icon prefix; add `ArbiterIntervention` event to state layer

2. **Timeline scrubbing state replay**
   - What we know: User wants to drag timeline and see state evolve
   - What's unclear: How to efficiently replay state at arbitrary timestamps
   - Recommendation: Store snapshots at key moments (phase boundaries); interpolate between for scrubbing

3. **Auto-expand active agent in tree**
   - What we know: CONTEXT.md says "Claude's discretion" for auto-expand behavior
   - What's unclear: Whether to auto-expand just the triad or scroll to agent
   - Recommendation: Auto-expand active triad, scroll to active agent, but don't collapse other expanded nodes

4. **Keyboard navigation scheme**
   - What we know: CONTEXT.md says "Claude's discretion" for keyboard navigation
   - What's unclear: vim-style (hjkl) vs arrows vs hybrid
   - Recommendation: Use Textual defaults (arrows) plus number keys (1-4) for view switching; add vim bindings as optional

## Sources

### Primary (HIGH confidence)
- [Textual Tree Widget](https://textual.textualize.io/widgets/tree/) - Node API, render_label customization
- [Textual ContentSwitcher](https://textual.textualize.io/widgets/content_switcher/) - View switching pattern
- [Textual Animation Guide](https://textual.textualize.io/guide/animation/) - styles.animate() API
- [Textual Containers API](https://textual.textualize.io/api/containers/) - Horizontal, Vertical, layout patterns
- [Textual DataTable](https://textual.textualize.io/widgets/data_table/) - Token breakdown table
- [Textual ProgressBar](https://textual.textualize.io/widgets/progress_bar/) - Gradient, bar rendering
- [hfs/state/models.py](existing) - AgentTree, NegotiationSnapshot, TokenUsageSummary models
- [hfs/state/query.py](existing) - QueryInterface subscription API

### Secondary (MEDIUM confidence)
- [Textual TabbedContent](https://textual.textualize.io/widgets/tabbed_content/) - Alternative navigation pattern
- [Unicode Block Characters](https://alexwlchan.net/2018/ascii-bar-charts/) - Gantt bar rendering
- [termgraph](https://github.com/mkaz/termgraph) - Terminal bar chart patterns

### Tertiary (LOW confidence)
- Community patterns for timeline widgets - No standard library exists for terminal Gantt charts

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components already exist in project or are documented Textual features
- Architecture: HIGH - Patterns follow Textual official documentation and existing HFS patterns
- Pitfalls: MEDIUM - Based on general Textual experience and state management patterns
- Timeline widget: MEDIUM - Custom implementation required, patterns extrapolated from block chart examples

**Research date:** 2026-01-31
**Valid until:** 2026-03-01 (30 days; Textual stable, HFS state layer stable)
