"""Temperature bar widget for HFS TUI.

This module provides the TemperatureBar widget, which displays a temperature
value as a color-coded progress bar. Temperature ranges from 0.0 (cool) to
1.0 (hot), with colors transitioning from blue to amber to red.

Usage:
    from hfs.tui.widgets import TemperatureBar

    bar = TemperatureBar()
    bar.temperature = 0.7  # Hot - displays red
    bar.temperature = 0.4  # Warm - displays amber
    bar.temperature = 0.2  # Cool - displays blue
"""

from textual.reactive import reactive
from textual.widgets import Static
from rich.text import Text


class TemperatureBar(Static):
    """Visual temperature indicator with color gradient.

    Displays temperature as a colored progress bar where:
    - temp > 0.66: Hot (red #EF4444)
    - temp > 0.33: Warm (amber #F59E0B)
    - temp <= 0.33: Cool (blue #3B82F6)

    The bar uses filled blocks and empty blocks with a percentage label.

    Attributes:
        temperature: Reactive float from 0.0 to 1.0 controlling the display.
    """

    DEFAULT_CSS = """
    TemperatureBar {
        height: 1;
        width: 100%;
    }
    """

    # Color thresholds and values
    COLOR_HOT = "#EF4444"  # Red
    COLOR_WARM = "#F59E0B"  # Amber
    COLOR_COOL = "#3B82F6"  # Blue

    temperature: reactive[float] = reactive(0.5)

    def __init__(self, temperature: float = 0.5, **kwargs) -> None:
        """Initialize the TemperatureBar widget.

        Args:
            temperature: Initial temperature value (0.0 to 1.0).
            **kwargs: Additional arguments passed to Static.
        """
        super().__init__("", **kwargs)
        self.temperature = temperature

    def watch_temperature(self, value: float) -> None:
        """React to temperature changes by refreshing the display.

        Args:
            value: The new temperature value.
        """
        self.refresh()

    def render(self) -> Text:
        """Render the temperature bar with color gradient.

        Returns:
            Rich Text object representing the colored bar with percentage.
        """
        # Clamp temperature to valid range
        temp = max(0.0, min(1.0, self.temperature))

        # Determine color based on temperature
        if temp > 0.66:
            color = self.COLOR_HOT
        elif temp > 0.33:
            color = self.COLOR_WARM
        else:
            color = self.COLOR_COOL

        # Calculate bar dimensions
        # Reserve space for percentage label " XX%"
        label_width = 5
        available_width = max(1, self.size.width - label_width)
        filled = int(temp * available_width)
        empty = available_width - filled

        # Build the bar
        text = Text()
        text.append("\u2588" * filled, style=color)  # Filled blocks
        text.append("\u2591" * empty, style="dim")  # Empty blocks
        text.append(f" {temp:.0%}", style="bold")

        return text


__all__ = ["TemperatureBar"]
