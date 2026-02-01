"""Chat screen for HFS TUI.

This module provides the ChatScreen, the main interface where users
interact with HFS. It includes a message list, chat input, and pulsing
dot indicator for streaming responses.

Usage:
    from hfs.tui.screens import ChatScreen

    # In HFSApp.compose() or on_mount()
    self.push_screen(ChatScreen())
"""

import asyncio
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen

from ..widgets import ChatInput, ChatMessage, MessageList, PulsingDot


class ChatScreen(Screen):
    """Main chat interface screen.

    This screen provides the chat experience with a scrollable message list,
    chat input at the bottom, and streaming indicator. It handles slash
    commands (/help, /clear, /exit) and mock streaming responses.

    Attributes:
        SLASH_COMMANDS: Mapping of slash commands to handler method names.
        DEFAULT_CSS: Styling for the chat screen layout.
    """

    SLASH_COMMANDS: ClassVar[dict[str, str]] = {
        "/help": "show_help",
        "/clear": "clear_conversation",
        "/exit": "quit_app",
    }

    DEFAULT_CSS = """
    ChatScreen {
        layout: vertical;
    }

    ChatScreen > #chat-container {
        height: 1fr;
        width: 100%;
    }

    ChatScreen > #input-container {
        height: auto;
        width: 100%;
        padding: 0 1 1 1;
    }

    ChatScreen > #input-container > #spinner {
        height: auto;
        dock: top;
    }

    ChatScreen > #input-container > #input {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the chat screen.

        Yields:
            MessageList: Scrollable container for chat messages.
            Container: Input area with spinner and chat input.
        """
        yield MessageList(id="messages")
        with Container(id="input-container"):
            yield PulsingDot(id="spinner")
            yield ChatInput(id="input")

    async def on_mount(self) -> None:
        """Called when screen is mounted.

        Sets initial focus to the input field.
        """
        self.query_one("#input", ChatInput).focus()

    async def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle chat input submission.

        Args:
            event: The Submitted event containing the input text.
        """
        text = event.text

        # Check for slash commands
        if text.startswith("/"):
            cmd = text.split()[0].lower()
            if cmd in self.SLASH_COMMANDS:
                handler_name = self.SLASH_COMMANDS[cmd]
                handler = getattr(self, handler_name, None)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                    return
            # Unknown command
            message_list = self.query_one("#messages", MessageList)
            await message_list.add_message(
                f"Unknown command: `{cmd}`\n\nType `/help` for available commands.",
                is_system=True,
            )
            return

        # Regular message
        await self.send_message(text)

    async def send_message(self, text: str) -> None:
        """Send a user message and get mock response.

        Args:
            text: The user's message text.
        """
        message_list = self.query_one("#messages", MessageList)
        spinner = self.query_one("#spinner", PulsingDot)

        # Add user message
        await message_list.add_message(text, is_user=True)

        # Start streaming indicator
        spinner.is_pulsing = True

        # Create streaming assistant message
        assistant_msg = await message_list.add_streaming_message()

        # Stream mock response (worker handles async)
        self._stream_mock_response(assistant_msg, spinner)

    @work
    async def _stream_mock_response(
        self,
        message: ChatMessage,
        spinner: PulsingDot,
    ) -> None:
        """Stream a mock response to demonstrate functionality.

        This is a placeholder until real LLM integration. Streams a
        sample markdown response character by character.

        Args:
            message: The ChatMessage widget to stream into.
            spinner: The PulsingDot to stop when done.
        """
        # Mock response with markdown to test rendering
        mock_response = """I'm a mock response demonstrating **markdown rendering**.

Here's some code:

```python
def hello():
    print("Hello from HFS!")
```

And a list:
- Item one
- Item two
- Item three

*Streaming complete!*"""

        try:
            for char in mock_response:
                await message.append_content(char)
                await asyncio.sleep(0.02)  # Simulate streaming delay
        finally:
            spinner.is_pulsing = False

    async def show_help(self) -> None:
        """Show help message with available commands."""
        message_list = self.query_one("#messages", MessageList)
        help_text = """**Available Commands**

| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/clear` | Clear all messages |
| `/exit` | Exit the application |

**Input Tips**
- Press **Enter** to send a message
- Press **Shift+Enter** to insert a new line
"""
        await message_list.add_message(help_text, is_system=True)

    async def clear_conversation(self) -> None:
        """Clear all messages from the chat."""
        message_list = self.query_one("#messages", MessageList)
        await message_list.clear_messages()

    def quit_app(self) -> None:
        """Exit the application."""
        self.app.exit(0)
