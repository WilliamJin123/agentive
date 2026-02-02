"""Plugin manager for HFS.

This module provides the PluginManager class which handles the complete
plugin lifecycle: discovery, permission checking, activation, command
registration, and hook execution.

Usage:
    from hfs.plugins import PluginManager

    manager = PluginManager()
    loaded_count = manager.load_plugins()
    print(f"Loaded {loaded_count} plugins")

    # Handle pending approvals
    for plugin in manager.get_pending_approvals():
        manager.approve_plugin(plugin.manifest.name)

    # Call hooks
    results = await manager.call_hook("on_message", message="Hello", is_user=True)

    # Execute commands
    if manager.has_command("/mycmd"):
        await manager.call_command("/mycmd", "/mycmd argument")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .discovery import DiscoveredPlugin, discover_plugins
from .hooks import HOOK_NAMES
from .permissions import PermissionManager

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle and hook execution.

    Responsibilities:
    - Load plugins from discovery
    - Check permissions (prompt if needed)
    - Register commands from plugins
    - Call hooks at appropriate times

    Attributes:
        _permission_manager: Handles permission persistence.
        _disabled_plugins: List of plugin names to skip.
        _plugins: List of activated plugins.
        _commands: Mapping of command names to handlers.
        _pending_approval: Plugins waiting for user approval.
    """

    def __init__(
        self,
        permission_manager: PermissionManager | None = None,
        disabled_plugins: list[str] | None = None,
    ) -> None:
        """Initialize the plugin manager.

        Args:
            permission_manager: Override for permission handling.
            disabled_plugins: List of plugin names to skip.
        """
        self._permission_manager = permission_manager or PermissionManager()
        self._disabled_plugins = disabled_plugins or []
        self._plugins: list[DiscoveredPlugin] = []
        self._commands: dict[str, Callable[..., Any]] = {}  # /cmd -> handler
        self._pending_approval: list[DiscoveredPlugin] = []

    def load_plugins(self) -> int:
        """Discover and load all plugins.

        Plugins that are already approved will be activated immediately.
        Plugins that need approval will be added to the pending list.

        Returns:
            Number of plugins loaded (activated).
        """
        discovered = discover_plugins(disabled_plugins=self._disabled_plugins)

        for plugin in discovered:
            # Check permissions
            if not self._permission_manager.is_approved(
                plugin.manifest.name,
                plugin.manifest.capabilities,
            ):
                self._pending_approval.append(plugin)
                logger.info(f"Plugin {plugin.manifest.name} pending approval")
                continue

            self._activate_plugin(plugin)

        return len(self._plugins)

    def _activate_plugin(self, plugin: DiscoveredPlugin) -> None:
        """Activate a plugin after approval.

        Registers any commands the plugin provides.

        Args:
            plugin: The plugin to activate.
        """
        self._plugins.append(plugin)

        # Register commands if plugin has them
        if "commands" in plugin.manifest.capabilities:
            commands = getattr(plugin.module, "COMMANDS", {})
            for cmd_name, handler in commands.items():
                full_cmd = f"/{cmd_name}" if not cmd_name.startswith("/") else cmd_name
                self._commands[full_cmd] = handler
                logger.info(
                    f"Registered command {full_cmd} from {plugin.manifest.name}"
                )

    def get_pending_approvals(self) -> list[DiscoveredPlugin]:
        """Get plugins waiting for permission approval.

        Returns:
            List of plugins awaiting user approval.
        """
        return self._pending_approval

    def approve_plugin(self, plugin_name: str) -> bool:
        """Approve a pending plugin.

        Saves the approval to disk and activates the plugin.

        Args:
            plugin_name: Name of the plugin to approve.

        Returns:
            True if plugin was found and approved.
        """
        for plugin in self._pending_approval[:]:
            if plugin.manifest.name == plugin_name:
                self._permission_manager.approve(
                    plugin.manifest.name,
                    plugin.manifest.version,
                    plugin.manifest.capabilities,
                )
                self._activate_plugin(plugin)
                self._pending_approval.remove(plugin)
                return True
        return False

    def deny_plugin(self, plugin_name: str) -> bool:
        """Deny a pending plugin.

        Removes the plugin from the pending list without activation.

        Args:
            plugin_name: Name of the plugin to deny.

        Returns:
            True if plugin was found in pending list.
        """
        for plugin in self._pending_approval[:]:
            if plugin.manifest.name == plugin_name:
                self._pending_approval.remove(plugin)
                return True
        return False

    def get_commands(self) -> dict[str, Callable[..., Any]]:
        """Get all registered plugin commands.

        Returns:
            Mapping of command names to handler functions.
        """
        return self._commands

    def has_command(self, command: str) -> bool:
        """Check if a command is registered by a plugin.

        Args:
            command: Command name including slash (e.g., "/mycmd").

        Returns:
            True if the command exists.
        """
        return command in self._commands

    async def call_command(self, command: str, text: str) -> Any:
        """Call a plugin command.

        Handles both sync and async command handlers.

        Args:
            command: The command name (e.g., "/mycmd").
            text: Full command text.

        Returns:
            Command handler result.
        """
        handler = self._commands.get(command)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(text)
            return handler(text)
        return None

    async def call_hook(self, hook_name: str, **kwargs: Any) -> list[Any]:
        """Call a hook on all plugins that implement it.

        Handles both sync and async hook implementations. Errors in one
        plugin don't affect other plugins.

        Args:
            hook_name: Name of hook (on_start, on_message, etc.).
            **kwargs: Arguments to pass to hook.

        Returns:
            List of non-None results from plugins.
        """
        if hook_name not in HOOK_NAMES:
            logger.warning(f"Unknown hook: {hook_name}")
            return []

        results = []
        for plugin in self._plugins:
            if "hooks" not in plugin.manifest.capabilities:
                continue

            hook = getattr(plugin.module, hook_name, None)
            if hook is None:
                continue

            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(**kwargs)
                else:
                    result = hook(**kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_name} failed in {plugin.manifest.name}: {e}")

        return results

    def get_loaded_plugins(self) -> list[DiscoveredPlugin]:
        """Get list of loaded plugins.

        Returns:
            List of activated plugins.
        """
        return self._plugins
