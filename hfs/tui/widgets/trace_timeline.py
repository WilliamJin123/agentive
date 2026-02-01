"""Trace timeline widget for HFS TUI.

This module provides the TraceTimelineWidget, a Gantt-style visualization
of phase execution timing. Each phase is shown as a horizontal bar with
duration proportional to execution time.

Usage:
    from hfs.tui.widgets import TraceTimelineWidget
    from hfs.state.models import TraceTimeline

    timeline_widget = TraceTimelineWidget()
    timeline_widget.set_timeline(trace_timeline)
"""

from textual.containers import Vertical
from textual.widgets import Static
from rich.text import Text

from hfs.state.models import TraceTimeline, PhaseTimeline


class TraceTimelineWidget(Vertical):
    """Gantt-style timeline showing phase execution durations.

    Displays a vertical list of phases with horizontal bars representing
    their relative durations. Phase names are left-aligned, bars extend
    to the right proportionally, and duration labels appear at bar ends.

    The visualization uses block characters for the bar rendering and
    supports both complete and in-progress timelines.
    """

    DEFAULT_CSS = """
    TraceTimelineWidget {
        height: auto;
        width: 100%;
        padding: 1;
    }

    TraceTimelineWidget .timeline-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    TraceTimelineWidget .timeline-row {
        height: 1;
    }

    TraceTimelineWidget .timeline-empty {
        color: $hfs-muted;
    }
    """

    # Block character for bar rendering
    BLOCK_CHAR = "\u2588"  # Full block

    def __init__(self, timeline: TraceTimeline | None = None, **kwargs) -> None:
        """Initialize the TraceTimelineWidget.

        Args:
            timeline: Optional TraceTimeline to display initially.
            **kwargs: Additional arguments passed to Vertical.
        """
        super().__init__(**kwargs)
        self._timeline = timeline

    def compose(self):
        """Compose initial widget content.

        Yields header and phase rows if timeline data is available.
        """
        yield Static("Phase Summary", classes="timeline-header")

        if self._timeline and self._timeline.phases:
            yield from self._build_phase_rows(self._timeline)
        else:
            yield Static("No trace data available", classes="timeline-empty")

    def set_timeline(self, timeline: TraceTimeline) -> None:
        """Update the widget with new timeline data.

        Clears existing content and rebuilds with the new timeline.

        Args:
            timeline: The TraceTimeline to display.
        """
        self._timeline = timeline
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild the widget content from current timeline."""
        # Remove all children except header
        for child in list(self.children):
            child.remove()

        # Add header
        self.mount(Static("Phase Summary", classes="timeline-header"))

        # Add phase rows
        if self._timeline and self._timeline.phases:
            for widget in self._build_phase_rows(self._timeline):
                self.mount(widget)
        else:
            self.mount(Static("No trace data available", classes="timeline-empty"))

    def _build_phase_rows(self, timeline: TraceTimeline) -> list[Static]:
        """Build phase row widgets from timeline.

        Args:
            timeline: The TraceTimeline containing phases.

        Returns:
            List of Static widgets for each phase row.
        """
        widgets = []

        # Calculate total duration for proportional bars
        total_ms = timeline.total_duration_ms
        if total_ms is None or total_ms == 0:
            # Sum up individual phase durations
            total_ms = sum(
                p.duration_ms for p in timeline.phases if p.duration_ms is not None
            )
            if total_ms == 0:
                total_ms = 1.0  # Avoid division by zero

        # Bar width for rendering
        bar_width = 40  # Characters available for bar

        for phase in timeline.phases:
            row = self._render_phase_row(phase, total_ms, bar_width)
            widgets.append(row)

        return widgets

    def _render_phase_row(
        self,
        phase: PhaseTimeline,
        total_ms: float,
        bar_width: int,
    ) -> Static:
        """Render a single phase as a row with Gantt bar.

        Creates a row with:
        - Phase name (left-aligned, fixed width)
        - Proportional bar (using block characters)
        - Duration label (right side)

        Args:
            phase: The phase to render.
            total_ms: Total timeline duration for proportion calculation.
            bar_width: Maximum bar width in characters.

        Returns:
            Static widget containing the rendered row.
        """
        # Phase name (truncate or pad to fixed width)
        name_width = 16
        name = phase.phase_name[:name_width].ljust(name_width)

        # Calculate bar length
        duration_ms = phase.duration_ms
        if duration_ms is None:
            # Phase still in progress
            duration_ms = 0
            bar_len = 0
            is_running = True
        else:
            bar_len = int((duration_ms / total_ms) * bar_width)
            bar_len = max(1, bar_len)  # Minimum 1 character
            is_running = False

        # Build Rich Text
        row = Text()
        row.append(name, style="bold")
        row.append(" ")

        # Bar
        bar = self.BLOCK_CHAR * bar_len
        row.append(bar, style="bold #F59E0B")  # Primary amber color

        # Padding between bar and duration
        padding = " " * (bar_width - bar_len + 1)
        row.append(padding)

        # Duration label
        if is_running:
            row.append("running...", style="dim italic")
        else:
            if duration_ms >= 1000:
                row.append(f"{duration_ms / 1000:.1f}s", style="dim")
            else:
                row.append(f"{duration_ms:.0f}ms", style="dim")

        return Static(row, classes="timeline-row")


__all__ = ["TraceTimelineWidget"]
