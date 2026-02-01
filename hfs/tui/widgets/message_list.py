"""Message list container for HFS TUI.

This module provides the MessageList widget, a scrollable container for
chat messages with smart auto-scroll behavior. Messages scroll up as new
ones arrive, but scrolling is paused if the user has scrolled up to read
previous messages.

Usage:
    from hfs.tui.widgets import MessageList

    message_list = MessageList(id="messages")
    await message_list.add_message("Hello!", is_user=True)
    assistant_msg = await message_list.add_streaming_message()
    await assistant_msg.append_content("Hi there!")
"""

from textual.containers import VerticalScroll

from .message import ChatMessage


class MessageList(VerticalScroll):
    """Scrollable container for chat messages with smart scroll behavior.

    This widget provides a scrolling container for chat messages that
    auto-scrolls to the bottom when new messages arrive, but respects
    user scroll position if they've scrolled up to read history.

    Attributes:
        DEFAULT_CSS: Styling for the message list.
    """

    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        width: 100%;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the MessageList widget.

        Args:
            **kwargs: Additional arguments passed to VerticalScroll.
        """
        super().__init__(**kwargs)
        self._auto_scroll = True

    def on_mount(self) -> None:
        """Called when widget is mounted to the DOM.

        Sets up auto-scroll behavior using anchor().
        """
        # Use anchor() for auto-scroll to bottom
        self.anchor()

    async def add_message(
        self,
        content: str,
        *,
        is_user: bool = False,
        is_system: bool = False,
    ) -> ChatMessage:
        """Add a new message to the list.

        Args:
            content: The message text content.
            is_user: True if this is a user message.
            is_system: True if this is a system message.

        Returns:
            The created ChatMessage widget.
        """
        message = ChatMessage(content, is_user=is_user, is_system=is_system)
        await self.mount(message)
        self._scroll_to_bottom_if_appropriate()
        return message

    async def add_streaming_message(self) -> ChatMessage:
        """Add an empty assistant message for streaming content.

        Creates an assistant message with no content, ready to receive
        streaming updates via append_content().

        Returns:
            The created ChatMessage widget for streaming.
        """
        message = ChatMessage("", is_user=False)
        await self.mount(message)
        self._scroll_to_bottom_if_appropriate()
        return message

    def _scroll_to_bottom_if_appropriate(self) -> None:
        """Scroll to bottom if user hasn't scrolled up manually.

        Checks if the scrollbar is being grabbed (indicating user is
        manually scrolling) and only auto-scrolls if not.
        """
        if not self.is_vertical_scrollbar_grabbed:
            self.scroll_end(animate=False)

    async def clear_messages(self) -> None:
        """Remove all messages from the list."""
        await self.remove_children()
