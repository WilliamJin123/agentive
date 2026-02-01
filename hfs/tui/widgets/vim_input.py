"""Vim-style modal input widget for HFS TUI.

This module provides the VimChatInput widget, which extends ChatInput with
vim-style modal editing. It supports NORMAL and INSERT modes with standard
vim keybindings for navigation and editing.

Usage:
    from hfs.tui.widgets import VimChatInput
    from hfs.tui.widgets.vim_input import VimMode

    vim_input = VimChatInput(id="input")
    # Starts in NORMAL mode - user must press i to type
"""

from enum import Enum, auto

from textual.events import Key
from textual.message import Message

from .chat_input import ChatInput


class VimMode(Enum):
    """Vim editing modes.

    NORMAL: Navigation and commands. Keys are interpreted as vim commands.
    INSERT: Text entry mode. Keys are typed as text (except Escape).
    """

    NORMAL = auto()
    INSERT = auto()


class VimChatInput(ChatInput):
    """ChatInput with vim-style modal editing.

    This widget provides modal editing where the user starts in NORMAL mode
    and must press i/a/A/I to enter INSERT mode. In NORMAL mode, h/j/k/l
    navigate and other vim commands work. Escape returns to NORMAL mode.

    Attributes:
        mode: Current vim mode (NORMAL or INSERT).

    Messages:
        ModeChanged: Posted when the vim mode changes.

    Example:
        vim_input = VimChatInput(id="input")
        # Listen for ModeChanged to update status bar
    """

    class ModeChanged(Message):
        """Posted when vim mode changes.

        Attributes:
            mode: The new vim mode.
        """

        def __init__(self, mode: VimMode) -> None:
            """Initialize the ModeChanged message.

            Args:
                mode: The new vim mode.
            """
            super().__init__()
            self.mode = mode

    def __init__(self, **kwargs) -> None:
        """Initialize the VimChatInput widget.

        Starts in NORMAL mode per vim convention.

        Args:
            **kwargs: Arguments passed to ChatInput.
        """
        super().__init__(**kwargs)
        self._mode = VimMode.NORMAL

    @property
    def mode(self) -> VimMode:
        """Get the current vim mode."""
        return self._mode

    def _set_mode(self, mode: VimMode) -> None:
        """Set the vim mode and post ModeChanged if changed.

        Args:
            mode: The new vim mode.
        """
        if mode != self._mode:
            self._mode = mode
            self.post_message(self.ModeChanged(mode))

    def on_key(self, event: Key) -> None:
        """Handle key events based on current vim mode.

        In NORMAL mode, intercepts all keys and handles vim commands.
        In INSERT mode, passes most keys through except Escape.

        Args:
            event: The key event to process.
        """
        if self._mode == VimMode.NORMAL:
            self._handle_normal_mode(event)
        else:
            self._handle_insert_mode(event)

    def _handle_normal_mode(self, event: Key) -> None:
        """Handle keys in NORMAL mode.

        Intercepts all keys and handles vim navigation/commands.

        Args:
            event: The key event to process.
        """
        event.prevent_default()
        key = event.key

        # Mode switches
        if key == "i":
            self._set_mode(VimMode.INSERT)
        elif key == "a":
            # Insert after cursor
            self.action_cursor_right()
            self._set_mode(VimMode.INSERT)
        elif key == "A":
            # Insert at line end
            self.action_cursor_line_end()
            self._set_mode(VimMode.INSERT)
        elif key == "I":
            # Insert at line start
            self.action_cursor_line_start()
            self._set_mode(VimMode.INSERT)
        elif key == "o":
            # Open line below
            self.action_cursor_line_end()
            self.insert("\n")
            self._set_mode(VimMode.INSERT)

        # Movement
        elif key == "h":
            self.action_cursor_left()
        elif key == "l":
            self.action_cursor_right()
        elif key == "j":
            self.action_cursor_down()
        elif key == "k":
            self.action_cursor_up()
        elif key == "0":
            self.action_cursor_line_start()
        elif key == "dollar":  # $
            self.action_cursor_line_end()
        elif key == "w":
            self.action_cursor_word_right()
        elif key == "b":
            self.action_cursor_word_left()

        # Editing
        elif key == "x":
            self.action_delete_right()
        elif key == "D":
            self.action_delete_to_end_of_line()

        # Note: dd (delete line) requires state tracking for double-key
        # commands, omitted for simplicity in this implementation.

    def _handle_insert_mode(self, event: Key) -> None:
        """Handle keys in INSERT mode.

        Escape returns to NORMAL mode with cursor moved left (vim behavior).
        All other keys are passed through to ChatInput's default handling.

        Args:
            event: The key event to process.
        """
        if event.key == "escape":
            event.prevent_default()
            self._set_mode(VimMode.NORMAL)
            # Move cursor left (vim behavior) - but not if at line start
            # TextArea's action_cursor_left handles boundary
            self.action_cursor_left()
        else:
            # Pass through to ChatInput's on_key for normal handling
            super().on_key(event)
