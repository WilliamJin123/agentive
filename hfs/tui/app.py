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

from hfs.user_config import ConfigLoader, UserConfig
from .screens import ChatScreen, InspectionScreen
from .theme import HFS_THEME

if TYPE_CHECKING:
    from hfs.agno.providers import ProviderManager
    from hfs.persistence import SessionRepository
    from hfs.state.query import QueryInterface
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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
        """Initialize HFSApp with lazy provider manager and user config."""
        super().__init__()
        self._provider_manager: ProviderManager | None = None
        self._query_interface: QueryInterface | None = None
        self._user_config: UserConfig = ConfigLoader().load()
        # Persistence components (initialized async in on_mount)
        self._db_engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._session_repo: SessionRepository | None = None
        self._current_session_id: int | None = None
        logger.info(f"User config loaded: output_mode={self._user_config.output_mode}")

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

    def get_user_config(self) -> UserConfig:
        """Get the current user configuration.

        Returns:
            UserConfig instance with current settings.
        """
        return self._user_config

    def reload_user_config(self) -> None:
        """Reload user configuration from disk.

        Call this after /config set commands to pick up changes.
        """
        self._user_config = ConfigLoader().load()
        logger.info(f"User config reloaded: output_mode={self._user_config.output_mode}")

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

    async def initialize_persistence(self) -> None:
        """Initialize persistence components (engine, session factory, repository).

        Creates the SQLite database at ~/.hfs/sessions.db if it doesn't exist.
        Should be called once during app startup.
        """
        try:
            from hfs.persistence import (
                SessionRepository,
                create_db_engine,
                get_session_factory,
            )

            self._db_engine = await create_db_engine()
            self._session_factory = get_session_factory(self._db_engine)
            self._session_repo = SessionRepository(self._session_factory)
            logger.info("Persistence initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize persistence: {e}")
            # Persistence is optional - app can run without it

    def get_session_repo(self) -> SessionRepository | None:
        """Get the session repository for CRUD operations.

        Returns:
            SessionRepository instance or None if persistence not initialized.
        """
        return self._session_repo

    def get_current_session_id(self) -> int | None:
        """Get the current chat session ID.

        Returns:
            Current session ID or None if no session active.
        """
        return self._current_session_id

    def set_current_session_id(self, session_id: int) -> None:
        """Set the current chat session ID.

        Args:
            session_id: ID of the session to set as current.
        """
        self._current_session_id = session_id
        logger.info(f"Current session set to: {session_id}")

    async def on_mount(self) -> None:
        """Called when app is mounted.

        Registers the HFS theme, initializes persistence, and pushes the chat screen.
        """
        self.register_theme(HFS_THEME)
        self.theme = "hfs"
        # Initialize persistence (async)
        await self.initialize_persistence()
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
