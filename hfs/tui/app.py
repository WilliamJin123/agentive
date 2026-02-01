"""HFS Textual Application.

This module provides the main HFSApp class, which is the entry point for
the interactive terminal UI. When users run `hfs` without arguments,
this app is launched to provide a chat-based interface to HFS.

Architecture:
    HFSApp extends textual.app.App and serves as the container for all
    TUI widgets. It manages the application lifecycle, keybindings, and
    screen composition.

Usage:
    from hfs.tui import HFSApp
    app = HFSApp()
    app.run()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from .screens import ChatScreen, InspectionScreen
from .theme import HFS_THEME

if TYPE_CHECKING:
    from hfs.agno.providers import ProviderManager
    from hfs.state.query import QueryInterface

logger = logging.getLogger(__name__)


class HFSApp(App):
    """Main HFS Textual application.

    This is the entry point for the interactive terminal UI. It provides
    a chat-based interface where users can interact with HFS agents to
    generate frontend code.

    Attributes:
        TITLE: Application title shown in terminal.
        SUB_TITLE: Subtitle shown below the title.
        BINDINGS: Keyboard shortcuts for the application.
        SCREENS: Mapping of screen names to screen classes.
    """

    TITLE = "HFS"
    SUB_TITLE = "Hexagonal Frontend System"

    # Path to the theme CSS file
    CSS_PATH = Path(__file__).parent / "styles" / "theme.tcss"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    SCREENS = {
        "chat": ChatScreen,
        "inspection": InspectionScreen,
    }

    def __init__(self) -> None:
        """Initialize HFSApp with lazy provider manager."""
        super().__init__()
        self._provider_manager: ProviderManager | None = None
        self._query_interface: QueryInterface | None = None

    @property
    def query_interface(self) -> QueryInterface | None:
        """Get QueryInterface for state queries, if available.

        Returns:
            QueryInterface instance or None if not set.
        """
        return self._query_interface

    def set_query_interface(self, qi: QueryInterface) -> None:
        """Set QueryInterface for inspection mode.

        The QueryInterface provides access to state data for the inspection
        screen. This is typically set when HFS runs with actual state management.

        Args:
            qi: The QueryInterface instance to use for state queries.
        """
        self._query_interface = qi

    def get_provider_manager(self) -> ProviderManager | None:
        """Get or lazily initialize the ProviderManager.

        Returns the cached ProviderManager instance, creating it on first access.
        Returns None if initialization fails (e.g., no API keys configured).

        Returns:
            ProviderManager instance or None if initialization failed.
        """
        if self._provider_manager is None:
            try:
                # Lazy import to avoid slow startup
                from hfs.agno.providers import ProviderManager

                self._provider_manager = ProviderManager()
                logger.info("ProviderManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ProviderManager: {e}")
                return None
        return self._provider_manager

    def on_mount(self) -> None:
        """Called when app is mounted.

        Registers the HFS theme and pushes the chat screen.
        """
        self.register_theme(HFS_THEME)
        self.theme = "hfs"
        self.push_screen("chat")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app.

        The main content comes from ChatScreen. We yield Footer
        for keybinding hints at the bottom.

        Yields:
            Footer: Keybinding hints footer.
        """
        yield Footer()

    def action_quit(self) -> None:
        """Handle quit action (Ctrl+C or Ctrl+Q)."""
        self.exit(0)
