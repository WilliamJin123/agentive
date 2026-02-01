"""Pulsing dot streaming indicator for HFS TUI.

This module provides the PulsingDot widget, a simple animated indicator
that shows when the assistant is generating a response. It displays a
pulsing "..." animation using opacity transitions.

Usage:
    from hfs.tui.widgets import PulsingDot

    spinner = PulsingDot(id="spinner")
    spinner.is_pulsing = True  # Start animation
    spinner.is_pulsing = False  # Stop animation
"""

from textual.reactive import reactive
from textual.widgets import Static


class PulsingDot(Static):
    """Pulsing dot indicator for streaming state.

    This widget displays an animated "..." that pulses in opacity to
    indicate that the assistant is generating a response. Per CONTEXT.md,
    a pulsing dot is preferred over a blinking block cursor.

    Attributes:
        is_pulsing: Reactive boolean controlling animation state.
        DEFAULT_CSS: Styling for the indicator.
    """

    DEFAULT_CSS = """
    PulsingDot {
        width: auto;
        height: 1;
        color: $primary;
        padding: 0 2;
    }
    """

    is_pulsing: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        """Initialize the PulsingDot widget.

        Args:
            **kwargs: Additional arguments passed to Static.
        """
        super().__init__("", **kwargs)
        self._high_opacity = True

    def on_mount(self) -> None:
        """Called when widget is mounted to the DOM.

        Sets up the pulse interval timer.
        """
        self.set_interval(0.5, self._pulse)

    def _pulse(self) -> None:
        """Animate opacity between low and high values.

        Called by the interval timer to create the pulsing effect.
        Only animates when is_pulsing is True.
        """
        if self.is_pulsing:
            # Toggle between 0.3 and 1.0 opacity
            target_opacity = 0.3 if self._high_opacity else 1.0
            self._high_opacity = not self._high_opacity
            self.styles.animate("opacity", target_opacity, duration=0.4)

    def watch_is_pulsing(self, pulsing: bool) -> None:
        """React to changes in is_pulsing state.

        Updates the display text and resets opacity when animation
        state changes.

        Args:
            pulsing: The new pulsing state.
        """
        if pulsing:
            self.update("...")
            self.styles.opacity = 1.0
            self._high_opacity = True
        else:
            self.update("")
            self.styles.opacity = 1.0
