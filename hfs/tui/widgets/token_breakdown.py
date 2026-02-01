"""Token breakdown widget for HFS TUI.

This module provides the TokenBreakdown widget, a DataTable that displays
token usage with a toggle between agent-level and phase-level views.

Usage:
    from hfs.tui.widgets import TokenBreakdown
    from hfs.state.models import TokenUsageSummary

    breakdown = TokenBreakdown()
    breakdown.set_usage(usage_summary)

    # Toggle views with P (phase) or A (agent) keys
"""

from textual.binding import Binding
from textual.widgets import DataTable

from hfs.state.models import TokenUsageSummary


class TokenBreakdown(DataTable):
    """Token usage breakdown table with phase/agent toggle.

    Displays token usage in a table with columns for Name, Prompt, Completion,
    and Total tokens. Supports switching between phase-level and agent-level
    views using keyboard bindings (P and A keys).

    Attributes:
        view_mode: Current view mode ("phase" or "agent").

    Bindings:
        p: Switch to phase view
        a: Switch to agent view
    """

    DEFAULT_CSS = """
    TokenBreakdown {
        height: 100%;
    }

    TokenBreakdown > .datatable--header {
        text-style: bold;
        background: $surface;
    }

    TokenBreakdown > .datatable--cursor {
        background: $panel;
    }
    """

    BINDINGS = [
        Binding("p", "show_by_phase", "By Phase", show=True),
        Binding("a", "show_by_agent", "By Agent", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        """Initialize the TokenBreakdown widget.

        Args:
            **kwargs: Additional arguments passed to DataTable.
        """
        super().__init__(**kwargs)
        self._view_mode = "phase"
        self._usage: TokenUsageSummary | None = None
        self.cursor_type = "row"

    @property
    def view_mode(self) -> str:
        """Current view mode: 'phase' or 'agent'."""
        return self._view_mode

    def on_mount(self) -> None:
        """Set up the table columns on mount."""
        self.add_columns("Name", "Prompt", "Completion", "Total")

    def set_usage(self, usage: TokenUsageSummary) -> None:
        """Update the table with token usage data.

        Clears the existing data and populates the table based on
        the current view mode (phase or agent).

        Args:
            usage: TokenUsageSummary containing usage data to display.
        """
        self._usage = usage
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Rebuild the table with current data and view mode."""
        if self._usage is None:
            return

        # Clear existing rows
        self.clear()

        if self._view_mode == "phase" and self._usage.by_phase:
            # Display by phase
            for phase in self._usage.by_phase:
                prompt = sum(a.prompt_tokens for a in phase.agents)
                completion = sum(a.completion_tokens for a in phase.agents)
                self.add_row(
                    phase.phase_name,
                    f"{prompt:,}",
                    f"{completion:,}",
                    f"{phase.total_tokens:,}",
                )
        elif self._usage.by_agent:
            # Display by agent
            for agent in self._usage.by_agent:
                self.add_row(
                    agent.agent_id,
                    f"{agent.prompt_tokens:,}",
                    f"{agent.completion_tokens:,}",
                    f"{agent.total_tokens:,}",
                )

        # Add total row with bold styling indicator
        total = self._usage.total_tokens
        prompt_total = sum(a.prompt_tokens for a in self._usage.by_agent)
        completion_total = sum(a.completion_tokens for a in self._usage.by_agent)
        self.add_row(
            "TOTAL",
            f"{prompt_total:,}",
            f"{completion_total:,}",
            f"{total:,}",
        )

    def action_show_by_phase(self) -> None:
        """Switch to phase view (triggered by P key)."""
        if self._view_mode != "phase":
            self._view_mode = "phase"
            self._refresh_table()

    def action_show_by_agent(self) -> None:
        """Switch to agent view (triggered by A key)."""
        if self._view_mode != "agent":
            self._view_mode = "agent"
            self._refresh_table()


__all__ = ["TokenBreakdown"]
