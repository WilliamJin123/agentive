"""Status bar widget for HFS TUI.

This module provides the HFSStatusBar widget, which displays session information
at the bottom of the screen including model name, token count, and active agents.
It uses reactive attributes to automatically update the display when values change.

Usage:
    from hfs.tui.widgets import HFSStatusBar

    status_bar = HFSStatusBar()
    status_bar.model_name = "claude-opus-4"
    status_bar.token_count = 1500
    status_bar.active_agents = ["planner", "coder"]
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static


class HFSStatusBar(Horizontal):
    """Status bar showing model, token count, and active agents.

    This widget provides at-a-glance session information in a compact
    horizontal layout. It uses reactive attributes so the display
    automatically updates when values change.

    Attributes:
        model_name: The name of the active LLM model.
        token_count: Current session token usage count.
        active_agents: List of currently active agent names.
    """

    DEFAULT_CSS = """
    HFSStatusBar {
        height: 1;
        dock: bottom;
        background: $surface;
        padding: 0 1;
        border-top: solid $hfs-border;
    }

    HFSStatusBar > .status-section {
        height: 1;
        width: auto;
        padding: 0 2;
    }

    HFSStatusBar > .status-model {
        color: $primary;
        text-style: bold;
    }

    HFSStatusBar > .status-tokens {
        color: $hfs-muted;
    }

    HFSStatusBar > .status-agents {
        color: $accent;
    }

    HFSStatusBar > .status-spacer {
        width: 1fr;
    }
    """

    # Reactive attributes - display updates automatically when changed
    model_name: reactive[str] = reactive("claude-3-sonnet")
    token_count: reactive[int] = reactive(0)
    active_agents: reactive[list[str]] = reactive(list)

    def __init__(
        self,
        model_name: str = "claude-3-sonnet",
        token_count: int = 0,
        active_agents: list[str] | None = None,
        **kwargs,
    ) -> None:
        """Initialize the status bar.

        Args:
            model_name: Initial model name to display.
            token_count: Initial token count.
            active_agents: Initial list of active agent names.
            **kwargs: Additional arguments passed to Horizontal.
        """
        super().__init__(**kwargs)
        self._initial_model = model_name
        self._initial_tokens = token_count
        self._initial_agents = active_agents or []

    def compose(self) -> ComposeResult:
        """Create child widgets for the status bar.

        Layout: [model] [spacer] [tokens] [agents]

        Yields:
            Static widgets for each status section.
        """
        yield Static(
            self._initial_model,
            id="status-model",
            classes="status-section status-model",
        )
        yield Static("", classes="status-spacer")
        yield Static(
            self._format_tokens(self._initial_tokens),
            id="status-tokens",
            classes="status-section status-tokens",
        )
        yield Static(
            self._format_agents(self._initial_agents),
            id="status-agents",
            classes="status-section status-agents",
        )

    def on_mount(self) -> None:
        """Initialize reactive values after mounting."""
        self.model_name = self._initial_model
        self.token_count = self._initial_tokens
        self.active_agents = self._initial_agents

    def watch_model_name(self, value: str) -> None:
        """Update model display when model_name changes.

        Args:
            value: The new model name.
        """
        try:
            widget = self.query_one("#status-model", Static)
            widget.update(value)
        except Exception:
            pass  # Widget not yet mounted

    def watch_token_count(self, value: int) -> None:
        """Update token display when token_count changes.

        Args:
            value: The new token count.
        """
        try:
            widget = self.query_one("#status-tokens", Static)
            widget.update(self._format_tokens(value))
        except Exception:
            pass  # Widget not yet mounted

    def watch_active_agents(self, value: list[str]) -> None:
        """Update agents display when active_agents changes.

        Args:
            value: The new list of active agent names.
        """
        try:
            widget = self.query_one("#status-agents", Static)
            widget.update(self._format_agents(value))
        except Exception:
            pass  # Widget not yet mounted

    @staticmethod
    def _format_tokens(count: int) -> str:
        """Format token count for display.

        Args:
            count: The token count to format.

        Returns:
            Formatted string like "1,234 tokens" or "1.2k tokens".
        """
        if count >= 1000:
            return f"{count:,} tokens"
        return f"{count} tokens"

    @staticmethod
    def _format_agents(agents: list[str]) -> str:
        """Format active agents list for display.

        Args:
            agents: List of active agent names.

        Returns:
            Formatted string like "2 agents" or agent names if few.
        """
        if not agents:
            return "0 agents"
        if len(agents) <= 2:
            return ", ".join(agents)
        return f"{len(agents)} agents"

    def add_tokens(self, count: int) -> None:
        """Add to the token count.

        Args:
            count: Number of tokens to add.
        """
        self.token_count += count

    def set_agent(self, name: str, active: bool = True) -> None:
        """Add or remove an agent from the active list.

        Args:
            name: Agent name.
            active: True to add, False to remove.
        """
        current = list(self.active_agents)
        if active and name not in current:
            current.append(name)
            self.active_agents = current
        elif not active and name in current:
            current.remove(name)
            self.active_agents = current
