"""HFS Plugin System.

This package provides plugin discovery, permission management, and lifecycle hooks
for extending HFS functionality. Plugins are discovered from ~/.hfs/plugins/ and
require user approval before activation.

Plugin Structure:
    ~/.hfs/plugins/
        my-plugin/
            manifest.yaml  # Required: name, version, capabilities
            __init__.py    # Entry point module

Example manifest.yaml:
    name: my-plugin
    version: 1.0.0
    description: Adds custom commands
    capabilities:
      - commands
      - hooks

Example __init__.py:
    COMMANDS = {
        "greet": lambda text: print(f"Hello! {text}")
    }

    def on_message(message: str, is_user: bool) -> str | None:
        if is_user:
            print(f"User said: {message}")
        return None  # Return modified message or None

Usage:
    from hfs.plugins import PluginManager

    manager = PluginManager()
    manager.load_plugins()

    # Check for pending approvals
    pending = manager.get_pending_approvals()
    for plugin in pending:
        print(f"Approve {plugin.manifest.name}? [y/n]")
        manager.approve_plugin(plugin.manifest.name)

    # Call hooks
    await manager.call_hook("on_message", message="Hello", is_user=True)

    # Execute plugin commands
    if manager.has_command("/greet"):
        await manager.call_command("/greet", "/greet World")
"""

from .discovery import DiscoveredPlugin, PluginManifest, discover_plugins
from .hooks import HOOK_NAMES, HFSHookSpec
from .manager import PluginManager
from .permissions import PermissionManager, PluginCapability, PluginPermission

__all__ = [
    # Discovery
    "PluginManifest",
    "DiscoveredPlugin",
    "discover_plugins",
    # Permissions
    "PermissionManager",
    "PluginCapability",
    "PluginPermission",
    # Hooks
    "HFSHookSpec",
    "HOOK_NAMES",
    # Manager
    "PluginManager",
]
