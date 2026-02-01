"""Chat input widget for HFS TUI.

This module provides the ChatInput widget, a multi-line text area that
submits on Enter and inserts newlines on Shift+Enter. It extends Textual's
TextArea to provide auto-growing behavior for chat-style input.

The widget also supports command history navigation with up/down arrows
and Ctrl+R fuzzy search through message history.

Usage:
    from hfs.tui.widgets import ChatInput

    input_widget = ChatInput(id="chat-input")
    # Listen for ChatInput.Submitted messages
"""

from textual.binding import Binding
from textual.events import Key
from textual.message import Message
from textual.widgets import TextArea
from textual.widgets.text_area import Selection


class ChatInput(TextArea):
    """Multi-line chat input that submits on Enter, newline on Shift+Enter.

    This widget extends TextArea to provide chat-style input behavior where
    Enter submits the message and Shift+Enter inserts a newline. The input
    auto-grows vertically as content is added, up to a maximum height.

    Supports command history navigation:
    - Up/Down arrows navigate through history
    - Ctrl+R opens fuzzy search mode

    Attributes:
        BINDINGS: Key bindings for submit, newline, and history navigation.
        DEFAULT_CSS: Styling for the input widget.

    Messages:
        Submitted: Posted when user presses Enter with non-empty text.
    """

    BINDINGS = [
        Binding("enter", "submit", "Send", show=False),
        Binding("shift+enter", "newline", "New Line", show=False),
        Binding("up", "history_up", "Previous", show=False),
        Binding("down", "history_down", "Next", show=False),
        Binding("ctrl+r", "history_search", "Search History", show=False),
    ]

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
        max-height: 10;
        min-height: 3;
        border: solid $primary;
        padding: 0 1;
    }

    ChatInput:focus {
        border: solid $accent;
    }
    """

    class Submitted(Message):
        """Posted when user submits input via Enter key.

        Attributes:
            input_widget: The ChatInput widget that posted this message.
            text: The submitted text content (stripped of leading/trailing whitespace).
        """

        def __init__(self, input_widget: "ChatInput", text: str) -> None:
            """Initialize the Submitted message.

            Args:
                input_widget: The ChatInput that originated this message.
                text: The text content being submitted.
            """
            super().__init__()
            self.input_widget = input_widget
            self.text = text

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the ChatInput widget.

        Args:
            *args: Positional arguments passed to TextArea.
            **kwargs: Keyword arguments passed to TextArea.
        """
        # Set soft wrap by default for chat input
        kwargs.setdefault("soft_wrap", True)
        super().__init__(*args, **kwargs)

        # History state
        self._history: list[str] = []
        self._history_index: int = -1  # -1 means not navigating
        self._current_input: str = ""  # Store current input when navigating

        # Search mode state
        self._search_mode: bool = False
        self._search_term: str = ""
        self._search_matches: list[int] = []  # Indices into history
        self._search_match_index: int = 0

    def action_submit(self) -> None:
        """Handle Enter key - submit message if non-empty.

        Gets the current text, strips whitespace, and if non-empty,
        posts a Submitted message and clears the input field.
        Also saves the message to history for later retrieval.
        """
        # If in search mode, exit and select the current match
        if self._search_mode:
            self._exit_search_mode(restore=False)
            return

        text = self.text.strip()
        if text:
            # Save to history (avoid consecutive duplicates)
            if not self._history or self._history[-1] != text:
                self._history.append(text)
            # Reset navigation state
            self._history_index = -1
            self._current_input = ""
            self.post_message(self.Submitted(self, text))
            self.clear()

    def action_history_up(self) -> None:
        """Navigate to previous history entry.

        On first press, saves current input and shows last history item.
        Subsequent presses navigate to older entries.
        """
        if not self._history:
            return

        # First up: save current input, go to last history item
        if self._history_index == -1:
            self._current_input = self.text
            self._history_index = len(self._history) - 1
        # Subsequent up: go to older entry if available
        elif self._history_index > 0:
            self._history_index -= 1
        else:
            return  # Already at oldest

        self.text = self._history[self._history_index]
        self._move_cursor_to_end()

    def action_history_down(self) -> None:
        """Navigate to next history entry or back to current input.

        Navigates forward through history, or returns to the input
        that was being typed before history navigation started.
        """
        if self._history_index == -1:
            return  # Not navigating

        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.text = self._history[self._history_index]
        else:
            # Return to current input
            self._history_index = -1
            self.text = self._current_input
        self._move_cursor_to_end()

    def _move_cursor_to_end(self) -> None:
        """Move cursor to end of text."""
        lines = self.text.split("\n")
        last_line_index = len(lines) - 1
        last_line_length = len(lines[-1])
        self.selection = Selection.cursor((last_line_index, last_line_length))

    def action_newline(self) -> None:
        """Handle Shift+Enter - insert a newline at cursor position."""
        self.insert("\n")

    def action_history_search(self) -> None:
        """Start or cycle reverse history search (Ctrl+R).

        First press enters search mode. Subsequent presses cycle through
        matching history entries. Type to filter, Enter to select, Escape to cancel.
        """
        if not self._history:
            return

        if self._search_mode:
            # Already in search - cycle to next match
            if self._search_matches and len(self._search_matches) > 1:
                self._search_match_index = (
                    self._search_match_index + 1
                ) % len(self._search_matches)
                self._show_search_match()
        else:
            # Enter search mode
            self._search_mode = True
            self._current_input = self.text  # Save current input
            self._search_term = ""
            self._update_search_matches()
            self._search_match_index = 0
            self._show_search_prompt()

    def on_key(self, event: Key) -> None:
        """Handle key events during search mode.

        In search mode, intercepts keypresses to build search term,
        navigate matches, or exit search. Regular input is blocked.

        Args:
            event: The key event to process.
        """
        if not self._search_mode:
            return  # Let normal handling proceed

        if event.key == "escape":
            self._exit_search_mode(restore=True)
            event.prevent_default()
        elif event.key == "enter":
            self._exit_search_mode(restore=False)
            event.prevent_default()
        elif event.key == "backspace":
            if self._search_term:
                self._search_term = self._search_term[:-1]
                self._update_search_matches()
                self._show_search_prompt()
            event.prevent_default()
        elif event.character and len(event.character) == 1 and event.character.isprintable():
            self._search_term += event.character
            self._update_search_matches()
            self._show_search_prompt()
            event.prevent_default()

    def _update_search_matches(self) -> None:
        """Find history entries matching search term (case-insensitive)."""
        if not self._search_term:
            # Show all history items (most recent first)
            self._search_matches = list(range(len(self._history) - 1, -1, -1))
        else:
            term = self._search_term.lower()
            # Search from most recent to oldest
            self._search_matches = [
                i for i in range(len(self._history) - 1, -1, -1)
                if term in self._history[i].lower()
            ]
        self._search_match_index = 0

    def _show_search_prompt(self) -> None:
        """Update text to show search prompt and current match."""
        if self._search_matches:
            match = self._history[self._search_matches[self._search_match_index]]
            # Truncate long matches for display
            display_match = match[:50] + "..." if len(match) > 50 else match
            self.text = f"(reverse-i-search)`{self._search_term}': {display_match}"
        else:
            self.text = f"(reverse-i-search)`{self._search_term}': "

    def _show_search_match(self) -> None:
        """Show current search match in the prompt."""
        if self._search_matches:
            match = self._history[self._search_matches[self._search_match_index]]
            display_match = match[:50] + "..." if len(match) > 50 else match
            self.text = f"(reverse-i-search)`{self._search_term}': {display_match}"

    def _exit_search_mode(self, restore: bool) -> None:
        """Exit search mode.

        Args:
            restore: If True, restore previous input. If False, use selected match.
        """
        self._search_mode = False
        if restore:
            self.text = self._current_input
        elif self._search_matches:
            self.text = self._history[self._search_matches[self._search_match_index]]
            self._move_cursor_to_end()
        else:
            self.text = self._current_input
        self._search_term = ""
        self._search_matches = []
