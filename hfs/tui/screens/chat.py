"""Chat screen for HFS TUI.

This module provides the ChatScreen, the main interface where users
interact with HFS. It includes a message list, chat input, and pulsing
dot indicator for streaming responses.

Usage:
    from hfs.tui.screens import ChatScreen

    # In HFSApp.compose() or on_mount()
    self.push_screen(ChatScreen())
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen

from textual import on
from textual.events import Key
from textual.widgets import TextArea

from hfs.user_config import ConfigLoader
from ..widgets import ChatInput, ChatMessage, CommandCompleter, HFSStatusBar, MessageList, PulsingDot, VimChatInput
from ..widgets.vim_input import VimMode

if TYPE_CHECKING:
    from hfs.agno.providers import ProviderManager

logger = logging.getLogger(__name__)


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
        "/inspect": "open_inspection",
        "/config": "handle_config",
        "/mode": "handle_mode",
        "/sessions": "handle_sessions",
        "/resume": "handle_resume",
        "/rename": "handle_rename",
    }

    DEFAULT_CSS = """
    ChatScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr auto auto;
        layers: base overlay;
    }

    ChatScreen > #input-container {
        height: auto;
        width: 100%;
        padding: 0 1 1 1;
    }

    ChatScreen > #input-container > #spinner {
        height: auto;
    }

    ChatScreen > #input-container > #input {
        height: auto;
    }
    """

    # TODO: Wire output_mode to widget visibility when agent widgets added to ChatScreen
    # Currently output_mode is stored as preference but has no visual effect on chat view

    def compose(self) -> ComposeResult:
        """Create child widgets for the chat screen.

        Layout (top to bottom):
            - MessageList: Scrollable container for chat messages
            - PulsingDot: Streaming indicator
            - ChatInput or VimChatInput: Message input area (based on config)
            - HFSStatusBar: Model, tokens, agents info

        Yields:
            MessageList: Scrollable container for chat messages.
            Container: Input area with spinner and chat input.
            HFSStatusBar: Status information at bottom.
        """
        yield MessageList(id="messages")
        with Container(id="input-container"):
            yield PulsingDot(id="spinner")
            # Select input widget based on keybinding mode
            config = self.app.get_user_config()
            if config.keybinding_mode == "vim":
                yield VimChatInput(id="input")
            else:
                yield ChatInput(id="input")
        yield CommandCompleter(target="input", id="completer")
        yield HFSStatusBar(id="status-bar")

    async def on_mount(self) -> None:
        """Called when screen is mounted.

        Sets initial focus to the input field and initializes vim mode indicator.
        """
        input_widget = self.query_one("#input")
        input_widget.focus()

        # Initialize vim mode indicator if using vim mode
        if hasattr(input_widget, "mode"):
            status_bar = self.query_one("#status-bar", HFSStatusBar)
            status_bar.vim_mode = input_widget.mode.name

    def on_vim_chat_input_mode_changed(self, event: VimChatInput.ModeChanged) -> None:
        """Handle vim mode changes to update status bar.

        Args:
            event: The ModeChanged event with the new vim mode.
        """
        status_bar = self.query_one("#status-bar", HFSStatusBar)
        status_bar.vim_mode = event.mode.name

    @on(TextArea.Changed, "#input")
    def on_input_changed(self, event: TextArea.Changed) -> None:
        """Handle input text changes for tab completion.

        Shows completion dropdown when user types slash commands.

        Args:
            event: The Changed event with the new text.
        """
        completer = self.query_one("#completer", CommandCompleter)
        text = event.text_area.text

        # Only show completions for text starting with /
        if text.startswith("/"):
            completer.show_completions(text)
        else:
            completer.hide_completions()

    @on(CommandCompleter.CompletionAccepted)
    def on_completion_accepted(self, event: CommandCompleter.CompletionAccepted) -> None:
        """Handle completion selection.

        Updates the input with the selected completion text.

        Args:
            event: The CompletionAccepted event with the completion text.
        """
        input_widget = self.query_one("#input")
        input_widget.text = event.text
        # Move cursor to end
        if hasattr(input_widget, "_move_cursor_to_end"):
            input_widget._move_cursor_to_end()
        input_widget.focus()

    def on_key(self, event: Key) -> None:
        """Handle key events for tab completion navigation.

        Intercepts Tab, Up, Down, Escape keys when completion dropdown is visible
        to allow navigation and selection of completions.

        Args:
            event: The key event to process.
        """
        completer = self.query_one("#completer", CommandCompleter)

        if not completer.visible:
            return  # Let events pass through normally

        # Handle completion navigation keys
        if event.key == "tab":
            completer.action_accept()
            event.prevent_default()
            event.stop()
        elif event.key == "up":
            completer.action_cursor_up()
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            completer.action_cursor_down()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            completer.action_hide()
            event.prevent_default()
            event.stop()

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
                        await handler(text)
                    else:
                        handler(text)
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
        """Send a user message and get LLM response.

        Args:
            text: The user's message text.
        """
        message_list = self.query_one("#messages", MessageList)
        spinner = self.query_one("#spinner", PulsingDot)
        status_bar = self.query_one("#status-bar", HFSStatusBar)

        # Ensure we have a session for persistence
        await self._ensure_session()

        # Add user message
        await message_list.add_message(text, is_user=True)

        # Persist user message
        await self._persist_message("user", text)

        # Update token count (estimate ~4 chars per token for input)
        user_tokens = max(1, len(text) // 4)
        status_bar.add_tokens(user_tokens)

        # Start streaming indicator
        spinner.is_pulsing = True

        # Create streaming assistant message
        assistant_msg = await message_list.add_streaming_message()

        # Stream LLM response (worker handles async)
        self._stream_llm_response(assistant_msg, spinner, status_bar, text)

    @work
    async def _stream_llm_response(
        self,
        message: ChatMessage,
        spinner: PulsingDot,
        status_bar: HFSStatusBar,
        user_text: str,
    ) -> None:
        """Stream a response from the LLM via Agno Agent.

        Gets a model from ProviderManager and streams the response token-by-token.
        Falls back to mock response if no providers are configured.

        Args:
            message: The ChatMessage widget to stream into.
            spinner: The PulsingDot to stop when done.
            status_bar: The HFSStatusBar to update token count.
            user_text: The user's input message.
        """
        response_length = 0

        try:
            # Get provider manager from app
            provider_manager = self.app.get_provider_manager()

            if provider_manager is None or not provider_manager.available_providers:
                # No providers configured - fall back to mock
                await self._stream_mock_response(message, spinner, status_bar)
                return

            # Get a model from any available provider
            from agno.agent import Agent
            from keycycle import NoAvailableKeyError

            try:
                provider_name, model = provider_manager.get_any_model(
                    estimated_tokens=2000
                )
                logger.info(f"Using {provider_name} for LLM request")

                # Update status bar with model info
                status_bar.model = f"{provider_name}"

            except NoAvailableKeyError:
                await message.append_content(
                    "*All API keys exhausted. Please wait for rate limits to reset "
                    "or configure additional keys.*\n\n"
                    "Falling back to mock response...\n\n"
                )
                await self._stream_mock_response(message, spinner, status_bar)
                return

            # Create Agno Agent with the model
            agent = Agent(
                model=model,
                system="You are HFS, a helpful AI assistant for frontend development. "
                "You help users build hexagonal frontend systems with clean architecture.",
            )

            # Stream response from LLM
            async for event in await agent.arun(user_text, stream=True):
                # Check for content events
                event_type = getattr(event, "event", None)

                if event_type in ("run_content", "intermediate_run_content"):
                    content = getattr(event, "content", None)
                    if content:
                        text = str(content)
                        await message.append_content(text)
                        response_length += len(text)

                elif event_type == "run_completed":
                    # Extract metrics if available
                    metrics = getattr(event, "metrics", None)
                    if metrics:
                        # Update token count with actual usage
                        input_tokens = getattr(metrics, "input_tokens", 0) or 0
                        output_tokens = getattr(metrics, "output_tokens", 0) or 0
                        total_tokens = input_tokens + output_tokens
                        if total_tokens > 0:
                            status_bar.add_tokens(total_tokens)
                            logger.info(
                                f"LLM tokens: input={input_tokens}, output={output_tokens}"
                            )
                        break

                elif event_type == "run_error":
                    error_content = getattr(event, "content", "Unknown error")
                    await message.append_content(f"\n\n*Error: {error_content}*")
                    break

        except Exception as e:
            logger.error(f"LLM streaming error: {e}", exc_info=True)
            await message.append_content(
                f"\n\n*Error occurred: {type(e).__name__}: {e}*\n\n"
                "Please try again or check your API configuration."
            )

        finally:
            spinner.is_pulsing = False
            # If we didn't get metrics, estimate tokens from response length
            if response_length > 0:
                estimated_tokens = max(1, response_length // 4)
                status_bar.add_tokens(estimated_tokens)

            # Persist assistant message
            full_response = message.content
            if full_response:
                await self._persist_message("assistant", full_response)

    async def _stream_mock_response(
        self,
        message: ChatMessage,
        spinner: PulsingDot,
        status_bar: HFSStatusBar,
    ) -> None:
        """Stream a mock response when no LLM providers are available.

        This is a fallback for when providers aren't configured. Streams a
        sample markdown response character by character.

        Args:
            message: The ChatMessage widget to stream into.
            spinner: The PulsingDot to stop when done.
            status_bar: The HFSStatusBar to update token count.
        """
        # Mock response with markdown to test rendering
        mock_response = """*LLM providers not configured. Showing mock response.*

I'm a mock response demonstrating **markdown rendering**.

Here's some code:

```python
def hello():
    print("Hello from HFS!")
```

And a list:
- Item one
- Item two
- Item three

**To enable real LLM responses:**
1. Set API keys (e.g., `CEREBRAS_API_KEY_1`, `GROQ_API_KEY_1`)
2. Set key counts (e.g., `NUM_CEREBRAS=1`, `NUM_GROQ=1`)
3. Restart the application

*Streaming complete!*"""

        try:
            for char in mock_response:
                await message.append_content(char)
                await asyncio.sleep(0.02)  # Simulate streaming delay
        finally:
            spinner.is_pulsing = False
            # Update token count for response (mock: estimate ~4 chars per token)
            response_tokens = max(1, len(mock_response) // 4)
            status_bar.add_tokens(response_tokens)
            # Persist mock response
            await self._persist_message("assistant", mock_response)

    async def show_help(self, _text: str = "") -> None:
        """Show help message with available commands."""
        message_list = self.query_one("#messages", MessageList)
        help_text = """**Available Commands**

| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/clear` | Clear all messages |
| `/sessions` | List saved sessions |
| `/resume <id>` | Resume a previous session |
| `/rename <name>` | Rename current session |
| `/config` | View current configuration |
| `/config set key value` | Change a setting |
| `/mode compact` or `/mode verbose` | Switch output mode |
| `/inspect` | Open inspection mode |
| `/exit` | Exit the application |

**Input Tips**
- Press **Enter** to send a message
- Press **Shift+Enter** to insert a new line
- Press **Tab** to complete commands (type `/` first)
- Press **Up/Down** to navigate history
- Press **Ctrl+R** to search history

**Keybindings (Standard/Emacs mode)**
- **Ctrl+A**: Move to beginning of line
- **Ctrl+E**: Move to end of line
- **Ctrl+K**: Delete to end of line
- **Ctrl+U**: Delete to beginning of line
- **Ctrl+W**: Delete word before cursor

**Vim Mode**
Set `keybinding_mode: vim` in config for modal editing.
- NORMAL mode: h/j/k/l navigation, i/a/A/I to insert
- INSERT mode: Type normally, Escape to exit
"""
        await message_list.add_message(help_text, is_system=True)

    def open_inspection(self, _text: str = "") -> None:
        """Open inspection mode to view agent and negotiation state."""
        self.app.push_screen("inspection")

    async def clear_conversation(self, _text: str = "") -> None:
        """Clear all messages from the chat."""
        message_list = self.query_one("#messages", MessageList)
        await message_list.clear_messages()

    def quit_app(self, _text: str = "") -> None:
        """Exit the application."""
        self.app.exit(0)

    async def handle_config(self, text: str) -> None:
        """Handle /config command for viewing and editing settings.

        Subcommands:
            /config - Show current effective configuration
            /config set key value - Update a setting

        Args:
            text: Full command text including /config.
        """
        message_list = self.query_one("#messages", MessageList)
        loader = ConfigLoader()
        parts = text.strip().split()

        # /config (show all)
        if len(parts) == 1:
            effective = loader.get_effective_config()
            table_rows = []
            for key, info in effective.items():
                source = info["source"]
                # Shorten source path for display
                if source.startswith(str(loader.global_path.parent)):
                    source = f"~/.hfs/config.yaml"
                elif source.startswith(str(loader.project_path.parent)):
                    source = ".hfs/config.yaml"
                elif source.startswith("env:"):
                    pass  # Keep as-is
                table_rows.append(f"| `{key}` | `{info['value']}` | {source} |")

            config_text = f"""**HFS Configuration**

| Setting | Value | Source |
|---------|-------|--------|
{chr(10).join(table_rows)}

*Use `/config set key value` to change a setting.*
"""
            await message_list.add_message(config_text, is_system=True)
            return

        # /config set key value
        if len(parts) >= 4 and parts[1].lower() == "set":
            key = parts[2]
            value = parts[3]

            # Check if key is valid
            from hfs.user_config import UserConfig
            valid_keys = UserConfig.get_field_names()
            if key not in valid_keys:
                await message_list.add_message(
                    f"**Error:** Unknown setting `{key}`.\n\n"
                    f"Valid settings: {', '.join(f'`{k}`' for k in valid_keys)}",
                    is_system=True,
                )
                return

            # Check if value is valid
            valid_values = UserConfig.get_valid_values(key)
            if valid_values and value not in valid_values:
                await message_list.add_message(
                    f"**Error:** Invalid value `{value}` for `{key}`.\n\n"
                    f"Must be one of: {', '.join(f'`{v}`' for v in valid_values)}",
                    is_system=True,
                )
                return

            # Save the setting
            try:
                loader.save(key, value)
                # Reload app config to pick up changes
                self.app.reload_user_config()
                await message_list.add_message(
                    f"**Configuration updated**\n\n"
                    f"`{key}` set to `{value}`\n\n"
                    f"*Saved to {loader.global_path}*",
                    is_system=True,
                )
            except Exception as e:
                await message_list.add_message(
                    f"**Error saving configuration:** {e}",
                    is_system=True,
                )
            return

        # Invalid subcommand
        await message_list.add_message(
            "**Usage:**\n"
            "- `/config` - View all settings\n"
            "- `/config set key value` - Change a setting\n\n"
            "**Example:** `/config set output_mode compact`",
            is_system=True,
        )

    async def handle_mode(self, text: str) -> None:
        """Handle /mode shorthand for output mode switching.

        This is a convenience alias for `/config set output_mode <mode>`.

        Args:
            text: Full command text including /mode.
        """
        message_list = self.query_one("#messages", MessageList)
        parts = text.strip().split()

        if len(parts) != 2:
            await message_list.add_message(
                "**Usage:** `/mode compact` or `/mode verbose`",
                is_system=True,
            )
            return

        mode = parts[1].lower()
        if mode not in ("compact", "verbose"):
            await message_list.add_message(
                f"**Error:** Invalid mode `{mode}`.\n\n"
                "Must be `compact` or `verbose`.",
                is_system=True,
            )
            return

        # Delegate to config set
        await self.handle_config(f"/config set output_mode {mode}")

    async def _ensure_session(self) -> None:
        """Ensure a session exists for persistence.

        Creates a new session if none exists. Called before sending messages.
        """
        repo = self.app.get_session_repo()
        if repo is None:
            return  # Persistence not available

        if self.app.get_current_session_id() is None:
            # Create new session
            session = await repo.create()
            self.app.set_current_session_id(session.id)
            logger.info(f"Created new session: {session.id}")

    async def _persist_message(self, role: str, content: str) -> None:
        """Persist a message to the current session.

        Args:
            role: Message role (user, assistant, system).
            content: Message content text.
        """
        repo = self.app.get_session_repo()
        session_id = self.app.get_current_session_id()

        if repo is None or session_id is None:
            return  # Persistence not available

        try:
            await repo.add_message(session_id, role, content)
            logger.debug(f"Persisted {role} message to session {session_id}")
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")

    async def handle_sessions(self, _text: str = "") -> None:
        """Handle /sessions command to list saved sessions.

        Shows a table of recent sessions with ID, name, message count, and date.
        """
        message_list = self.query_one("#messages", MessageList)
        repo = self.app.get_session_repo()

        if repo is None:
            await message_list.add_message(
                "**Error:** Persistence not available.",
                is_system=True,
            )
            return

        sessions = await repo.list_recent(20)

        if not sessions:
            await message_list.add_message(
                "**No saved sessions.**\n\n"
                "Send a message to start a new session.",
                is_system=True,
            )
            return

        current_id = self.app.get_current_session_id()
        table_rows = []
        for s in sessions:
            msg_count = len(s.messages)
            created = s.created_at.strftime("%Y-%m-%d %H:%M")
            current_marker = " (current)" if s.id == current_id else ""
            # Truncate long names
            name = s.name[:40] + "..." if len(s.name) > 40 else s.name
            table_rows.append(f"| {s.id} | {name}{current_marker} | {msg_count} | {created} |")

        sessions_text = f"""**Saved Sessions**

| ID | Name | Messages | Created |
|----|------|----------|---------|
{chr(10).join(table_rows)}

*Use `/resume <id>` to load a session.*
*Use `/rename <name>` to rename current session.*
"""
        await message_list.add_message(sessions_text, is_system=True)

    async def handle_resume(self, text: str) -> None:
        """Handle /resume command to load a previous session.

        Args:
            text: Full command text including /resume.
        """
        message_list = self.query_one("#messages", MessageList)
        repo = self.app.get_session_repo()

        if repo is None:
            await message_list.add_message(
                "**Error:** Persistence not available.",
                is_system=True,
            )
            return

        parts = text.strip().split()
        if len(parts) != 2:
            await message_list.add_message(
                "**Usage:** `/resume <session_id>`\n\n"
                "Use `/sessions` to see available sessions.",
                is_system=True,
            )
            return

        try:
            session_id = int(parts[1])
        except ValueError:
            await message_list.add_message(
                f"**Error:** Invalid session ID `{parts[1]}`. Must be a number.",
                is_system=True,
            )
            return

        session = await repo.get(session_id)
        if session is None:
            await message_list.add_message(
                f"**Error:** Session `{session_id}` not found.",
                is_system=True,
            )
            return

        # Clear current messages
        await message_list.clear_messages()

        # Load session messages
        for msg in session.messages:
            is_user = msg.role == "user"
            is_system = msg.role == "system"
            await message_list.add_message(msg.content, is_user=is_user, is_system=is_system)

        # Set current session
        self.app.set_current_session_id(session_id)

        await message_list.add_message(
            f"**Resumed session:** {session.name}\n\n"
            f"*{len(session.messages)} messages loaded.*",
            is_system=True,
        )

    async def handle_rename(self, text: str) -> None:
        """Handle /rename command to rename a session.

        Supports:
            /rename <new_name> - Rename current session
            /rename <id> <new_name> - Rename specific session

        Args:
            text: Full command text including /rename.
        """
        message_list = self.query_one("#messages", MessageList)
        repo = self.app.get_session_repo()

        if repo is None:
            await message_list.add_message(
                "**Error:** Persistence not available.",
                is_system=True,
            )
            return

        parts = text.strip().split(maxsplit=2)
        if len(parts) < 2:
            await message_list.add_message(
                "**Usage:**\n"
                "- `/rename <new_name>` - Rename current session\n"
                "- `/rename <id> <new_name>` - Rename specific session",
                is_system=True,
            )
            return

        # Check if first arg is a number (session ID)
        try:
            session_id = int(parts[1])
            if len(parts) < 3:
                await message_list.add_message(
                    "**Error:** Missing new name.\n\n"
                    "**Usage:** `/rename <id> <new_name>`",
                    is_system=True,
                )
                return
            new_name = parts[2]
        except ValueError:
            # First arg is the name, use current session
            session_id = self.app.get_current_session_id()
            if session_id is None:
                await message_list.add_message(
                    "**Error:** No current session. Send a message first.",
                    is_system=True,
                )
                return
            new_name = " ".join(parts[1:])

        session = await repo.rename(session_id, new_name)
        if session is None:
            await message_list.add_message(
                f"**Error:** Session `{session_id}` not found.",
                is_system=True,
            )
            return

        await message_list.add_message(
            f"**Session renamed to:** {new_name}",
            is_system=True,
        )
