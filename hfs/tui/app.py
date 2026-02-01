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

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer


class HFSApp(App):
    """Main HFS Textual application.

    This is the entry point for the interactive terminal UI. It provides
    a chat-based interface where users can interact with HFS agents to
    generate frontend code.

    Attributes:
        TITLE: Application title shown in terminal.
        SUB_TITLE: Subtitle shown below the title.
        BINDINGS: Keyboard shortcuts for the application.
    """

    TITLE = "HFS"
    SUB_TITLE = "Hexagonal Frontend System"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    CSS = """
    Screen {
        align: center middle;
    }

    #welcome {
        width: auto;
        height: auto;
        padding: 2 4;
        border: solid green;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app.

        This minimal scaffold yields a welcome message. Future plans will
        add chat history, input area, and status panels.

        Yields:
            Static: Welcome message widget.
            Footer: Keybinding hints footer.
        """
        yield Static(
            "Welcome to HFS\n\n"
            "Hexagonal Frontend System\n"
            "Interactive REPL\n\n"
            "Press Ctrl+C or Ctrl+Q to exit",
            id="welcome"
        )
        yield Footer()

    def action_quit(self) -> None:
        """Handle quit action (Ctrl+C or Ctrl+Q)."""
        self.exit(0)
