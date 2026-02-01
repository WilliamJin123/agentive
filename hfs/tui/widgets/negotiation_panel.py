"""Negotiation panel widgets for HFS TUI.

This module provides widgets for displaying negotiation state in a document-style
format. The NegotiationPanel shows sections with ownership badges, while
NegotiationSection handles individual section display with expandable claims
for contested sections.

Usage:
    from hfs.tui.widgets import NegotiationPanel, NegotiationSection
    from hfs.state.models import NegotiationSnapshot, SectionNegotiationState

    # Create from snapshot
    panel = NegotiationPanel(snapshot)

    # Or set later
    panel = NegotiationPanel()
    panel.set_snapshot(snapshot)
"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Collapsible, Static
from rich.text import Text

from hfs.state.models import NegotiationSnapshot, SectionNegotiationState
from hfs.tui.widgets.temperature_bar import TemperatureBar


class NegotiationSection(Vertical):
    """Single section in the negotiation panel with owner badge and claims.

    Displays a document section with:
    - Header showing section name and owner badge (if claimed)
    - Expandable claims list for contested sections
    - Temperature bar showing section heat

    CSS Classes:
        -contested: Applied when section status is "contested"
        -claimed: Applied when section has an owner
    """

    DEFAULT_CSS = """
    NegotiationSection {
        height: auto;
        margin: 0 1;
        padding: 1;
        border: solid #404040;
    }

    NegotiationSection.-contested {
        border: solid $warning;
    }

    NegotiationSection.-claimed {
        border: solid $success;
    }

    NegotiationSection .section-header {
        text-style: bold;
    }

    NegotiationSection .claim-item {
        padding-left: 2;
    }

    NegotiationSection .section-temp {
        margin-top: 1;
    }
    """

    def __init__(
        self,
        section: SectionNegotiationState,
        temperature: float = 0.5,
        **kwargs,
    ) -> None:
        """Initialize the NegotiationSection widget.

        Args:
            section: The section negotiation state to display.
            temperature: Temperature value for this section (0.0 to 1.0).
            **kwargs: Additional arguments passed to Vertical.
        """
        super().__init__(**kwargs)
        self._section = section
        self._temperature = temperature

    def compose(self) -> ComposeResult:
        """Compose the section display.

        Yields header, claims (if contested), and temperature bar.
        """
        section = self._section

        # Header with section name and owner badge
        header = Text()
        header.append(section.section_name, style="bold")

        if section.owner:
            header.append(" ")
            header.append(f"[{section.owner}]", style="green bold")

        yield Static(header, classes="section-header")

        # If contested, show expandable claims with temperature
        if section.status == "contested":
            self.add_class("-contested")

            # Build claims content
            claims_widgets = []
            for claimant in section.claimants:
                claim_text = Text()
                claim_text.append(f"\u2022 {claimant}", style="yellow")
                claims_widgets.append(Static(claim_text, classes="claim-item"))

            # Show claim count in collapsible title
            claim_count = len(section.claimants)
            with Collapsible(
                title=f"Claims ({claim_count})",
                collapsed=True,
            ):
                for widget in claims_widgets:
                    yield widget

            # Temperature indicator for contested sections
            yield TemperatureBar(temperature=self._temperature, classes="section-temp")

        elif section.status == "claimed":
            self.add_class("-claimed")


class NegotiationPanel(VerticalScroll):
    """Container for negotiation state display.

    Displays negotiation state in a document-style format with:
    - Header showing round number and overall temperature
    - List of NegotiationSection widgets for each section
    - Support for pausing live updates

    Attributes:
        is_paused: Reactive boolean for pause/resume live updates.
    """

    DEFAULT_CSS = """
    NegotiationPanel {
        height: 100%;
        padding: 1;
        scrollbar-gutter: stable;
    }

    NegotiationPanel .panel-header {
        text-style: bold;
        margin-bottom: 1;
    }

    NegotiationPanel .panel-temp-container {
        margin-bottom: 1;
    }

    NegotiationPanel .panel-temp-label {
        margin-bottom: 0;
    }
    """

    is_paused: reactive[bool] = reactive(False)

    def __init__(
        self,
        snapshot: NegotiationSnapshot | None = None,
        **kwargs,
    ) -> None:
        """Initialize the NegotiationPanel widget.

        Args:
            snapshot: Optional initial negotiation snapshot to display.
            **kwargs: Additional arguments passed to VerticalScroll.
        """
        super().__init__(**kwargs)
        self._snapshot = snapshot

    def compose(self) -> ComposeResult:
        """Compose initial panel content.

        If a snapshot was provided, displays it. Otherwise shows placeholder.
        """
        if self._snapshot:
            yield from self._build_snapshot_content(self._snapshot)
        else:
            yield Static("No negotiation data", classes="panel-header")

    def set_snapshot(self, snapshot: NegotiationSnapshot) -> None:
        """Update the panel with a new negotiation snapshot.

        Clears existing content and rebuilds with new snapshot data.
        If the panel is not yet mounted, stores the snapshot for compose().

        Args:
            snapshot: The new negotiation snapshot to display.
        """
        self._snapshot = snapshot
        # Only rebuild if mounted (otherwise compose() will use the snapshot)
        if self.is_attached:
            self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild panel content from current snapshot."""
        # Remove all children
        for child in list(self.children):
            child.remove()

        # Build new content
        if self._snapshot:
            for widget in self._build_snapshot_content(self._snapshot):
                self.mount(widget)
        else:
            self.mount(Static("No negotiation data", classes="panel-header"))

    def _build_snapshot_content(
        self,
        snapshot: NegotiationSnapshot,
    ) -> list:
        """Build widget list from snapshot.

        Args:
            snapshot: The negotiation snapshot to render.

        Returns:
            List of widgets representing the snapshot.
        """
        widgets = []

        # Header with round number
        header_text = Text()
        header_text.append(f"Negotiation Round {snapshot.round}", style="bold")
        if snapshot.contested_count > 0:
            header_text.append(f" ({snapshot.contested_count} contested)", style="yellow")
        widgets.append(Static(header_text, classes="panel-header"))

        # Overall temperature bar with label
        temp_label = Text()
        temp_label.append("Temperature: ", style="dim")
        widgets.append(Static(temp_label, classes="panel-temp-label"))
        widgets.append(
            TemperatureBar(temperature=snapshot.temperature, classes="panel-temp-container")
        )

        # Section list
        for section in snapshot.sections:
            # Calculate per-section temperature based on contest history
            # If contested, use overall temp; if claimed/frozen, use lower temp
            section_temp = snapshot.temperature
            if section.status == "claimed":
                section_temp = max(0.1, snapshot.temperature * 0.3)
            elif section.status == "frozen":
                section_temp = 0.0

            widgets.append(NegotiationSection(section, temperature=section_temp))

        return widgets

    def watch_is_paused(self, paused: bool) -> None:
        """React to pause state changes.

        Args:
            paused: Whether updates are paused.
        """
        # Could update header to show paused state
        pass


__all__ = ["NegotiationPanel", "NegotiationSection"]
