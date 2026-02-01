"""Chat input widget for HFS TUI.

This module provides the ChatInput widget, a multi-line text area that
submits on Enter and inserts newlines on Shift+Enter. It extends Textual's
TextArea to provide auto-growing behavior for chat-style input.

Usage:
    from hfs.tui.widgets import ChatInput

    input_widget = ChatInput(id="chat-input")
    # Listen for ChatInput.Submitted messages
"""

from textual.binding import Binding
from textual.message import Message
from textual.widgets import TextArea


class ChatInput(TextArea):
    """Multi-line chat input that submits on Enter, newline on Shift+Enter.

    This widget extends TextArea to provide chat-style input behavior where
    Enter submits the message and Shift+Enter inserts a newline. The input
    auto-grows vertically as content is added, up to a maximum height.

    Attributes:
        BINDINGS: Key bindings for submit (Enter) and newline (Shift+Enter).
        DEFAULT_CSS: Styling for the input widget.

    Messages:
        Submitted: Posted when user presses Enter with non-empty text.
    """

    BINDINGS = [
        Binding("enter", "submit", "Send", show=False),
        Binding("shift+enter", "newline", "New Line", show=False),
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

    def action_submit(self) -> None:
        """Handle Enter key - submit message if non-empty.

        Gets the current text, strips whitespace, and if non-empty,
        posts a Submitted message and clears the input field.
        """
        text = self.text.strip()
        if text:
            self.post_message(self.Submitted(self, text))
            self.clear()

    def action_newline(self) -> None:
        """Handle Shift+Enter - insert a newline at cursor position."""
        self.insert("\n")
