"""Plugin discovery for HFS.

This module handles automatic discovery and loading of plugins from
the ~/.hfs/plugins/ directory. Each plugin must have a manifest.yaml
file describing its name, version, and capabilities.

Usage:
    from hfs.plugins import discover_plugins

    plugins = discover_plugins()
    for plugin in plugins:
        print(f"Loaded: {plugin.manifest.name}")
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PluginManifest(BaseModel):
    """Plugin manifest schema.

    Manifest file: ~/.hfs/plugins/<plugin_name>/manifest.yaml

    Example manifest.yaml:
        name: my-plugin
        version: 1.0.0
        description: Adds custom commands
        entry_point: __init__  # Module to import (default)
        capabilities:
          - commands
          - hooks

    Attributes:
        name: Unique plugin identifier (e.g., "my-plugin").
        version: Semantic version string (e.g., "1.0.0").
        description: Optional description of what the plugin does.
        entry_point: Python module filename without .py (default: "__init__").
        capabilities: List of required capabilities (commands, widgets, hooks).
    """

    name: str
    version: str
    description: str | None = None
    entry_point: str = "__init__"  # Module filename without .py
    capabilities: list[str] = []  # commands, widgets, hooks


class DiscoveredPlugin:
    """Container for discovered plugin data.

    Attributes:
        manifest: The parsed plugin manifest.
        module: The loaded Python module.
        path: Path to the plugin directory.
    """

    def __init__(self, manifest: PluginManifest, module: Any, path: Path) -> None:
        """Initialize a discovered plugin.

        Args:
            manifest: The plugin's manifest data.
            module: The loaded plugin module.
            path: Path to the plugin directory.
        """
        self.manifest = manifest
        self.module = module
        self.path = path


def discover_plugins(
    plugins_dir: Path | None = None,
    disabled_plugins: list[str] | None = None,
) -> list[DiscoveredPlugin]:
    """Discover and load plugins from directory.

    Scans the plugins directory for subdirectories containing manifest.yaml files.
    Each valid plugin is loaded and returned in a list. Invalid plugins are logged
    and skipped.

    Args:
        plugins_dir: Override for plugins directory (default: ~/.hfs/plugins).
        disabled_plugins: List of plugin names to skip.

    Returns:
        List of successfully loaded plugins.

    Plugin structure:
        ~/.hfs/plugins/
            my-plugin/
                manifest.yaml
                __init__.py
    """
    if plugins_dir is None:
        plugins_dir = Path.home() / ".hfs" / "plugins"

    if disabled_plugins is None:
        disabled_plugins = []

    if not plugins_dir.exists():
        return []

    plugins = []

    for plugin_path in plugins_dir.iterdir():
        if not plugin_path.is_dir():
            continue

        manifest_path = plugin_path / "manifest.yaml"
        if not manifest_path.exists():
            logger.debug(f"Skipping {plugin_path.name}: no manifest.yaml")
            continue

        try:
            # Load manifest
            with open(manifest_path) as f:
                manifest_data = yaml.safe_load(f)
            manifest = PluginManifest(**manifest_data)

            # Check if disabled
            if manifest.name in disabled_plugins:
                logger.info(f"Plugin {manifest.name} is disabled")
                continue

            # Load plugin module
            entry_path = plugin_path / f"{manifest.entry_point}.py"
            if not entry_path.exists():
                logger.warning(f"Plugin {manifest.name}: entry point not found")
                continue

            spec = importlib.util.spec_from_file_location(
                f"hfs_plugin_{manifest.name.replace('-', '_')}",
                entry_path,
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                plugins.append(DiscoveredPlugin(manifest, module, plugin_path))
                logger.info(f"Loaded plugin: {manifest.name} v{manifest.version}")

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_path.name}: {e}")
            # Continue loading other plugins

    return plugins
