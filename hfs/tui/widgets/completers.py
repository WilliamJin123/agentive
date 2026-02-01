"""Tab completion widgets for HFS TUI.

This module provides completion functionality for slash commands and file paths
in the chat input. Since TextArea (which ChatInput extends) doesn't support
the Suggester interface, we implement a custom dropdown-based completion.

Usage:
    from hfs.tui.widgets import CommandCompleter

    # In a Screen's compose():
    yield CommandCompleter(target="chat-input")
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from textual import on
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Key
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static


class CompletionItem(ListItem):
    """A single completion option in the dropdown."""

    def __init__(
        self,
        text: str,
        *,
        meta: str = "",
        id: str | None = None,
    ) -> None:
        """Initialize a completion item.

        Args:
            text: The completion text to display and insert.
            meta: Optional metadata shown on the left (e.g., icon or type hint).
            id: Optional widget ID.
        """
        super().__init__(id=id)
        self.completion_text = text
        self.meta = meta

    def compose(self):
        """Create the item content."""
        if self.meta:
            yield Static(f"[dim]{self.meta}[/dim] {self.completion_text}")
        else:
            yield Static(self.completion_text)


class CommandCompleter(Widget):
    """Dropdown autocomplete for slash commands and file paths.

    This widget monitors a target ChatInput and shows completion suggestions
    when the user types a slash command. It supports:
    - Command completion (when input starts with /)
    - File path completion (after a command with a space)

    The widget positions itself as an overlay above the input field.

    Attributes:
        COMMANDS: List of available slash commands with their metadata.
        visible: Whether the dropdown is currently visible.
    """

    BINDINGS = [
        Binding("escape", "hide", "Hide completions", show=False),
        Binding("up", "cursor_up", "Previous", show=False),
        Binding("down", "cursor_down", "Next", show=False),
        Binding("tab", "accept", "Accept", show=False),
        Binding("enter", "accept", "Accept", show=False),
    ]

    DEFAULT_CSS = """
    CommandCompleter {
        layer: overlay;
        dock: bottom;
        height: auto;
        max-height: 10;
        width: 100%;
        display: none;
        margin: 0 1 4 1;
    }

    CommandCompleter.visible {
        display: block;
    }

    CommandCompleter ListView {
        height: auto;
        max-height: 8;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }

    CommandCompleter ListView > ListItem {
        padding: 0 1;
    }

    CommandCompleter ListView > ListItem.--highlight {
        background: $accent;
    }
    """

    # Command definitions with metadata
    COMMANDS: list[tuple[str, str]] = [
        ("/help", "?"),
        ("/clear", "X"),
        ("/config", "C"),
        ("/config set output_mode compact", ""),
        ("/config set output_mode verbose", ""),
        ("/config set keybinding_mode vim", ""),
        ("/config set keybinding_mode standard", ""),
        ("/mode compact", "M"),
        ("/mode verbose", "M"),
        ("/inspect", "I"),
        ("/exit", "Q"),
    ]

    visible = reactive(False)

    class CompletionAccepted(Message):
        """Posted when a completion is accepted."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(
        self,
        target: str | Widget,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the command completer.

        Args:
            target: The ID of the ChatInput widget to monitor, or the widget itself.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._target_id = target if isinstance(target, str) else target.id
        self._target: Widget | None = None
        self._current_text = ""
        self._candidates: list[tuple[str, str]] = []

    def compose(self):
        """Create the dropdown list."""
        yield ListView(id="completion-list")

    def on_mount(self) -> None:
        """Find and monitor the target widget."""
        if self._target_id:
            try:
                self._target = self.app.query_one(f"#{self._target_id}")
            except Exception:
                self._target = None

    def watch_visible(self, visible: bool) -> None:
        """Update CSS class when visibility changes."""
        self.set_class(visible, "visible")

    def show_completions(self, text: str) -> None:
        """Update and show completions for the given input text.

        Args:
            text: The current input text.
        """
        self._current_text = text
        candidates = self._get_candidates(text)

        if not candidates:
            self.hide_completions()
            return

        self._candidates = candidates
        self._update_list(candidates)
        self.visible = True

    def hide_completions(self) -> None:
        """Hide the completion dropdown."""
        self.visible = False
        self._candidates = []

    def _get_candidates(self, text: str) -> list[tuple[str, str]]:
        """Get completion candidates for the current text.

        Args:
            text: The current input text.

        Returns:
            List of (completion_text, meta) tuples.
        """
        if not text:
            return []

        # Check if we're completing a file path (after command + space)
        if " " in text:
            parts = text.split(" ", 1)
            command = parts[0]
            arg = parts[1] if len(parts) > 1 else ""

            # Only complete paths if the argument looks path-like or is empty
            if arg.startswith((".", "/", "~")) or text.endswith(" ") or "\\" in arg:
                path_candidates = self._get_path_completions(arg)
                if path_candidates:
                    # Prepend command to each path completion
                    return [(f"{command} {path}", meta) for path, meta in path_candidates]

        # Command completion (when starting with /)
        if text.startswith("/"):
            text_lower = text.lower()
            return [
                (cmd, meta)
                for cmd, meta in self.COMMANDS
                if cmd.lower().startswith(text_lower)
            ]

        return []

    def _get_path_completions(self, partial_path: str) -> list[tuple[str, str]]:
        """Get file/directory completions for a partial path.

        Args:
            partial_path: The partial path to complete.

        Returns:
            List of (path, meta) tuples where meta is 'D' for directory, 'F' for file.
        """
        try:
            if not partial_path or partial_path == ".":
                base = Path.cwd()
                prefix = ""
            else:
                # Handle ~ for home directory
                if partial_path.startswith("~"):
                    partial_path = str(Path.home()) + partial_path[1:]

                path = Path(partial_path)
                if partial_path.endswith(("/", "\\")):
                    base = path
                    prefix = partial_path
                else:
                    base = path.parent if path.parent.exists() else Path.cwd()
                    prefix = str(path.parent) + "/" if str(path.parent) != "." else ""
                    # Filter by partial filename
                    partial_name = path.name.lower()

            if not base.exists():
                return []

            completions = []
            for item in base.iterdir():
                name = item.name

                # Filter by partial name if provided
                if partial_path and not partial_path.endswith(("/", "\\")):
                    partial_name = Path(partial_path).name.lower()
                    if not name.lower().startswith(partial_name):
                        continue

                is_dir = item.is_dir()
                if is_dir:
                    name += "/"
                full_path = prefix + name
                meta = "D" if is_dir else "F"
                completions.append((full_path, meta))

            return sorted(completions, key=lambda x: (not x[0].endswith("/"), x[0].lower()))

        except (OSError, PermissionError):
            return []

    def _update_list(self, candidates: list[tuple[str, str]]) -> None:
        """Update the ListView with new candidates.

        Args:
            candidates: List of (completion_text, meta) tuples.
        """
        list_view = self.query_one("#completion-list", ListView)
        list_view.clear()

        for text, meta in candidates[:10]:  # Limit to 10 items
            list_view.append(CompletionItem(text, meta=meta))

        # Select first item
        if list_view.children:
            list_view.index = 0

    def action_hide(self) -> None:
        """Hide the completion dropdown."""
        self.hide_completions()

    def action_cursor_up(self) -> None:
        """Move cursor up in the list."""
        if not self.visible:
            return
        list_view = self.query_one("#completion-list", ListView)
        if list_view.index is not None and list_view.index > 0:
            list_view.index -= 1

    def action_cursor_down(self) -> None:
        """Move cursor down in the list."""
        if not self.visible:
            return
        list_view = self.query_one("#completion-list", ListView)
        if list_view.index is not None:
            max_index = len(list_view.children) - 1
            if list_view.index < max_index:
                list_view.index += 1

    def action_accept(self) -> None:
        """Accept the currently selected completion."""
        if not self.visible or not self._candidates:
            return

        list_view = self.query_one("#completion-list", ListView)
        if list_view.index is not None and list_view.index < len(self._candidates):
            text, _ = self._candidates[list_view.index]
            self.post_message(self.CompletionAccepted(text))
            self.hide_completions()

    @on(ListView.Selected)
    def on_list_item_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection via click."""
        event.stop()
        self.action_accept()
