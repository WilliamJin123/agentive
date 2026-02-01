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

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from .screens import ChatScreen
from .theme import HFS_THEME


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
    }

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
