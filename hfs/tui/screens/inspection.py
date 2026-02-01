"""Inspection screen for HFS TUI.

This module provides the InspectionScreen, a split-view interface for
inspecting agent state, negotiation, token usage, and trace timeline.
Users can navigate between views using sidebar buttons or number keys (1-4).

Usage:
    from hfs.tui.screens import InspectionScreen

    # Push screen via /inspect command
    self.app.push_screen("inspection")

    # Navigation:
    # - 1: Agent tree view
    # - 2: Negotiation panel
    # - 3: Token breakdown
    # - 4: Trace timeline
    # - F: Toggle fullscreen (hide/show sidebar)
    # - Escape: Exit inspection mode
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, ContentSwitcher, Static

from hfs.tui.widgets import (
    AgentTreeWidget,
    NegotiationPanel,
    TokenBreakdown,
    TraceTimelineWidget,
)


class InspectionScreen(Screen):
    """Split-view inspection screen for deep state inspection.

    Provides a sidebar with navigation buttons and a main content area
    that switches between four views:
    - Tree: Agent hierarchy with status
    - Negotiation: Section ownership and claims
    - Tokens: Usage breakdown by phase/agent
    - Trace: Gantt-style timeline

    Attributes:
        BINDINGS: Keyboard shortcuts for view switching and navigation.

    Bindings:
        1: Show tree view
        2: Show negotiation view
        3: Show tokens view
        4: Show trace view
        f: Toggle fullscreen (hide sidebar)
        escape: Exit inspection mode
    """

    DEFAULT_CSS = """
    InspectionScreen {
        layout: horizontal;
    }

    InspectionScreen #inspection-sidebar {
        width: 16;
        background: $surface;
        border-right: solid #404040;
        padding: 1;
    }

    InspectionScreen #inspection-content {
        width: 1fr;
        height: 100%;
    }

    InspectionScreen .nav-button {
        width: 100%;
        margin: 0 0 1 0;
        background: $panel;
    }

    InspectionScreen .nav-button:hover {
        background: $surface;
    }

    InspectionScreen .nav-button.-active {
        background: $primary;
        color: $background;
        text-style: bold;
    }

    InspectionScreen #inspection-sidebar.hidden {
        display: none;
    }
    """

    BINDINGS = [
        Binding("1", "show_view('tree')", "Tree", show=True),
        Binding("2", "show_view('negotiation')", "Negotiation", show=True),
        Binding("3", "show_view('tokens')", "Tokens", show=True),
        Binding("4", "show_view('trace')", "Trace", show=True),
        Binding("f", "toggle_fullscreen", "Fullscreen", show=True),
        Binding("escape", "exit_inspection", "Back", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        """Initialize the InspectionScreen.

        Args:
            **kwargs: Additional arguments passed to Screen.
        """
        super().__init__(**kwargs)
        self._current_view = "tree"
        self._fullscreen = False

    def compose(self) -> ComposeResult:
        """Compose the split-view layout.

        Layout:
        - Left: Sidebar with navigation buttons
        - Right: ContentSwitcher with four view widgets

        Yields:
            Sidebar and content area widgets.
        """
        with Horizontal():
            # Sidebar with navigation buttons
            with Vertical(id="inspection-sidebar"):
                yield Button("1. Tree", id="nav-tree", classes="nav-button -active")
                yield Button("2. Negotiation", id="nav-negotiation", classes="nav-button")
                yield Button("3. Tokens", id="nav-tokens", classes="nav-button")
                yield Button("4. Trace", id="nav-trace", classes="nav-button")

            # Content area with view switcher
            with ContentSwitcher(id="inspection-content", initial="tree"):
                yield AgentTreeWidget(id="tree", label="Agents")
                yield NegotiationPanel(id="negotiation")
                yield TokenBreakdown(id="tokens")
                yield TraceTimelineWidget(id="trace")

    def on_mount(self) -> None:
        """Called when screen is mounted.

        Loads initial state data into widgets if query interface is available.
        """
        self._load_state_data()
        # Focus the content area
        content_switcher = self.query_one("#inspection-content", ContentSwitcher)
        current_widget = content_switcher.query_one(f"#{self._current_view}")
        if current_widget:
            current_widget.focus()

    def _load_state_data(self) -> None:
        """Load state data into widgets from query interface.

        If the app has a query_interface property, uses it to load:
        - Agent tree data
        - Negotiation snapshot
        - Token usage summary
        - Trace timeline

        If no query interface is available, widgets show placeholder content.
        """
        # Check if app has query_interface
        query_interface = getattr(self.app, "query_interface", None)
        if query_interface is None:
            # No state available - widgets will show their default content
            return

        # Try to load each data type
        try:
            # Load agent tree
            tree_widget = self.query_one("#tree", AgentTreeWidget)
            agent_tree = query_interface.get_agent_tree()
            if agent_tree:
                tree_widget.populate_from_tree(agent_tree)
        except Exception:
            pass  # Widget shows default content

        try:
            # Load negotiation state
            negotiation_panel = self.query_one("#negotiation", NegotiationPanel)
            negotiation_state = query_interface.get_negotiation_state()
            if negotiation_state:
                negotiation_panel.set_snapshot(negotiation_state)
        except Exception:
            pass

        try:
            # Load token usage
            token_breakdown = self.query_one("#tokens", TokenBreakdown)
            token_usage = query_interface.get_token_usage()
            if token_usage:
                token_breakdown.set_usage(token_usage)
        except Exception:
            pass

        try:
            # Load trace timeline
            timeline_widget = self.query_one("#trace", TraceTimelineWidget)
            timeline = query_interface.get_trace_timeline()
            if timeline:
                timeline_widget.set_timeline(timeline)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle sidebar button presses.

        Extracts the view ID from the button ID and switches to that view.

        Args:
            event: The button pressed event.
        """
        button_id = event.button.id
        if button_id and button_id.startswith("nav-"):
            view_id = button_id[4:]  # Remove "nav-" prefix
            self.action_show_view(view_id)

    def action_show_view(self, view_id: str) -> None:
        """Switch to the specified view.

        Updates the ContentSwitcher, button active states, and focus.

        Args:
            view_id: The view to switch to (tree, negotiation, tokens, trace).
        """
        # Update content switcher
        content_switcher = self.query_one("#inspection-content", ContentSwitcher)
        content_switcher.current = view_id
        self._current_view = view_id

        # Update button active states
        for button in self.query(".nav-button"):
            button.remove_class("-active")

        active_button = self.query_one(f"#nav-{view_id}", Button)
        active_button.add_class("-active")

        # Focus the new view
        try:
            current_widget = content_switcher.query_one(f"#{view_id}")
            if current_widget:
                current_widget.focus()
        except Exception:
            pass

    def action_toggle_fullscreen(self) -> None:
        """Toggle sidebar visibility for fullscreen mode.

        Hides or shows the sidebar to maximize content area space.
        """
        sidebar = self.query_one("#inspection-sidebar", Vertical)
        self._fullscreen = not self._fullscreen

        if self._fullscreen:
            sidebar.add_class("hidden")
        else:
            sidebar.remove_class("hidden")

    def action_exit_inspection(self) -> None:
        """Exit inspection mode and return to chat.

        Pops this screen from the application stack.
        """
        self.app.pop_screen()


__all__ = ["InspectionScreen"]
