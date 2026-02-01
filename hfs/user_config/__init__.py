"""User configuration module for HFS.

This module provides user preference management for the HFS TUI, including:
- UserConfig: Pydantic model for user preferences
- ConfigLoader: Layered config loading with precedence
- load_user_config: Convenience function for quick config access

Config files are YAML format:
- Global: ~/.hfs/config.yaml
- Project: .hfs/config.yaml

Environment variable overrides:
- HFS_OUTPUT_MODE -> output_mode
- HFS_KEYBINDING_MODE -> keybinding_mode

Usage:
    from hfs.user_config import ConfigLoader, UserConfig, load_user_config

    # Quick load with defaults
    config = load_user_config()

    # Full control with ConfigLoader
    loader = ConfigLoader()
    config = loader.load()
    loader.save("output_mode", "compact")
"""

from .loader import ConfigLoader, load_user_config
from .models import UserConfig

__all__ = ["ConfigLoader", "UserConfig", "load_user_config"]
