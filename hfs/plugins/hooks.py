"""Hook specifications for HFS plugins.

This module defines the protocol for plugin lifecycle hooks. Plugins
implement these methods to receive events from HFS during operation.
All hooks are optional - plugins only implement what they need.

Example plugin:
    class MyPlugin:
        def on_start(self, session_id: str) -> None:
            print(f"Session started: {session_id}")

        def on_message(self, message: str, is_user: bool) -> str | None:
            # Return modified message or None to pass through
            return None

Usage:
    from hfs.plugins import HFSHookSpec, HOOK_NAMES

    # Validate hook name
    if hook_name in HOOK_NAMES:
        result = hook(**kwargs)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from hfs.state.models import RunSnapshot


class HFSHookSpec(Protocol):
    """Hook specifications that plugins can implement.

    Plugins implement these methods to receive lifecycle events.
    All hooks are optional - implement only what you need.

    Example plugin:
        class MyPlugin:
            def on_start(self, session_id: str) -> None:
                print(f"Session started: {session_id}")

            def on_message(self, message: str, is_user: bool) -> str | None:
                # Return modified message or None to pass through
                return None
    """

    def on_start(self, session_id: str) -> None:
        """Called when HFS session starts.

        Args:
            session_id: The session ID string.
        """
        ...

    def on_message(self, message: str, is_user: bool) -> str | None:
        """Called for each message.

        Can modify the message by returning a new string,
        or return None to pass through unchanged.

        Args:
            message: The message content.
            is_user: True if user message, False if assistant.

        Returns:
            Modified message or None.
        """
        ...

    def on_run_complete(self, run_snapshot: RunSnapshot) -> None:
        """Called when an agent run completes.

        Args:
            run_snapshot: The complete run state snapshot.
        """
        ...

    def on_exit(self) -> None:
        """Called when HFS is exiting."""
        ...


# List of all hook names for validation
HOOK_NAMES = ["on_start", "on_message", "on_run_complete", "on_exit"]
