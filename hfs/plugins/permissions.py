"""Plugin permission management for HFS.

This module handles plugin permission tracking and approval. When plugins
are first discovered, they require user approval before activation. Approved
permissions are persisted to ~/.hfs/plugin_permissions.yaml.

Usage:
    from hfs.plugins import PermissionManager

    pm = PermissionManager()
    if not pm.is_approved("my-plugin", ["commands", "hooks"]):
        pm.approve("my-plugin", "1.0.0", ["commands", "hooks"])
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PluginCapability(str, Enum):
    """Plugin capabilities requiring permission.

    These capabilities define what a plugin can do. Users must approve
    requested capabilities before a plugin is activated.

    Attributes:
        COMMANDS: Register slash commands.
        WIDGETS: Add UI widgets to the TUI.
        HOOKS: Lifecycle hooks (on_start, on_message, etc.).
        FILESYSTEM: File system access.
        NETWORK: Network access.
    """

    COMMANDS = "commands"  # Register slash commands
    WIDGETS = "widgets"  # Add UI widgets
    HOOKS = "hooks"  # Lifecycle hooks
    FILESYSTEM = "filesystem"  # File system access
    NETWORK = "network"  # Network access


class PluginPermission(BaseModel):
    """Stored permission for a plugin.

    Attributes:
        plugin_name: Name of the plugin.
        plugin_version: Version when permission was granted.
        capabilities: List of approved capability strings.
        approved: Whether the plugin is currently approved.
        approved_at: ISO timestamp of when approval was granted.
    """

    plugin_name: str
    plugin_version: str
    capabilities: list[str]
    approved: bool
    approved_at: str | None = None


class PermissionManager:
    """Manages plugin permission approvals.

    Permissions stored in: ~/.hfs/plugin_permissions.yaml

    This class handles loading, saving, and querying plugin permissions.
    Permissions are persisted to disk so users don't need to re-approve
    plugins on every startup.

    Attributes:
        _path: Path to the permissions YAML file.
        _permissions: In-memory cache of plugin permissions.
    """

    def __init__(self, permissions_path: Path | None = None) -> None:
        """Initialize the permission manager.

        Args:
            permissions_path: Override path for permissions file.
                Defaults to ~/.hfs/plugin_permissions.yaml.
        """
        self._path = permissions_path or (
            Path.home() / ".hfs" / "plugin_permissions.yaml"
        )
        self._permissions: dict[str, PluginPermission] = {}
        self._load()

    def _load(self) -> None:
        """Load permissions from file."""
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = yaml.safe_load(f) or {}
                for name, perm_data in data.items():
                    self._permissions[name] = PluginPermission(**perm_data)
            except Exception as e:
                logger.error(f"Failed to load permissions: {e}")

    def _save(self) -> None:
        """Save permissions to file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: perm.model_dump() for name, perm in self._permissions.items()}
        with open(self._path, "w") as f:
            yaml.dump(data, f)

    def is_approved(self, plugin_name: str, capabilities: list[str]) -> bool:
        """Check if plugin has approved permissions for all capabilities.

        Args:
            plugin_name: Name of the plugin to check.
            capabilities: List of capabilities to verify.

        Returns:
            True if plugin is approved and has all requested capabilities.
        """
        perm = self._permissions.get(plugin_name)
        if not perm or not perm.approved:
            return False
        return all(cap in perm.capabilities for cap in capabilities)

    def approve(
        self, plugin_name: str, plugin_version: str, capabilities: list[str]
    ) -> None:
        """Approve plugin with capabilities.

        Args:
            plugin_name: Name of the plugin to approve.
            plugin_version: Current version of the plugin.
            capabilities: List of capabilities to approve.
        """
        self._permissions[plugin_name] = PluginPermission(
            plugin_name=plugin_name,
            plugin_version=plugin_version,
            capabilities=capabilities,
            approved=True,
            approved_at=datetime.utcnow().isoformat(),
        )
        self._save()

    def revoke(self, plugin_name: str) -> None:
        """Revoke plugin permissions.

        Args:
            plugin_name: Name of the plugin to revoke.
        """
        if plugin_name in self._permissions:
            del self._permissions[plugin_name]
            self._save()

    def list_approved(self) -> list[PluginPermission]:
        """List all approved plugins.

        Returns:
            List of PluginPermission objects for approved plugins.
        """
        return [p for p in self._permissions.values() if p.approved]
