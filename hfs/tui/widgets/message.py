"""Chat message widget for HFS TUI.

This module provides the ChatMessage widget, which displays a single chat
message with markdown rendering. It supports both user and assistant messages
with distinct styling, and provides streaming support for assistant responses.

Usage:
    from hfs.tui.widgets import ChatMessage

    # User message
    user_msg = ChatMessage("Hello!", is_user=True)

    # Assistant message with streaming
    assistant_msg = ChatMessage("", is_user=False)
    await assistant_msg.append_content("Hello")
    await assistant_msg.append_content(" world!")
"""

from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Markdown, Static


class ChatMessage(Vertical):
    """A single chat message with markdown rendering.

    This widget displays a chat message with a role label and markdown-rendered
    content. User and assistant messages are styled differently. Assistant
    messages support streaming content updates.

    Attributes:
        content: The message text content.
        is_user: True if this is a user message, False for assistant.
        timestamp: Optional timestamp for the message.
        DEFAULT_CSS: Styling for message display.
    """

    DEFAULT_CSS = """
    ChatMessage {
        height: auto;
        width: 100%;
        padding: 0 1;
        margin: 1 0;
    }

    ChatMessage > .message-role {
        height: auto;
        width: auto;
        text-style: bold;
    }

    ChatMessage > .message-role.user-role {
        color: $secondary;
    }

    ChatMessage > .message-role.assistant-role {
        color: $primary;
    }

    ChatMessage > .message-content {
        height: auto;
        width: 100%;
        padding: 0 0 0 2;
    }

    ChatMessage.user-message {
        background: $surface;
    }

    ChatMessage.assistant-message {
        background: $panel;
    }

    ChatMessage.system-message {
        background: $surface;
        text-style: italic;
    }

    ChatMessage.system-message > .message-role {
        color: $warning;
    }
    """

    def __init__(
        self,
        content: str = "",
        *,
        is_user: bool = False,
        is_system: bool = False,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> None:
        """Initialize the ChatMessage widget.

        Args:
            content: The message text content.
            is_user: True if this is a user message.
            is_system: True if this is a system message (e.g., help output).
            timestamp: Optional timestamp for the message.
            **kwargs: Additional arguments passed to Vertical.
        """
        super().__init__(**kwargs)
        self._content = content
        self._is_user = is_user
        self._is_system = is_system
        self._timestamp = timestamp or datetime.now()
        self._markdown_widget: Optional[Markdown] = None
        self._accumulated_content = content

        # Apply appropriate class
        if is_system:
            self.add_class("system-message")
        elif is_user:
            self.add_class("user-message")
        else:
            self.add_class("assistant-message")

    def compose(self) -> ComposeResult:
        """Create child widgets for the message.

        Yields:
            Static: The role label (You, Assistant, or System).
            Markdown: The message content with markdown rendering.
        """
        # Determine role label and class
        if self._is_system:
            role_text = "System"
            role_class = "system-role"
        elif self._is_user:
            role_text = "You"
            role_class = "user-role"
        else:
            role_text = "Assistant"
            role_class = "assistant-role"

        role_label = Static(role_text, classes=f"message-role {role_class}")
        yield role_label

        self._markdown_widget = Markdown(self._content, classes="message-content")
        yield self._markdown_widget

    @property
    def markdown_widget(self) -> Optional[Markdown]:
        """Get the Markdown widget for streaming updates.

        Returns:
            The Markdown widget if composed, None otherwise.
        """
        return self._markdown_widget

    async def append_content(self, text: str) -> None:
        """Append content to the message for streaming.

        This method accumulates text and updates the markdown widget.
        For efficient streaming, it rebuilds the entire markdown content.

        Args:
            text: The text to append to the message.
        """
        self._accumulated_content += text
        if self._markdown_widget is not None:
            await self._markdown_widget.update(self._accumulated_content)

    async def set_content(self, text: str) -> None:
        """Replace the entire message content.

        Args:
            text: The new content for the message.
        """
        self._accumulated_content = text
        if self._markdown_widget is not None:
            await self._markdown_widget.update(text)

    @property
    def content(self) -> str:
        """Get the current message content.

        Returns:
            The accumulated message text.
        """
        return self._accumulated_content
