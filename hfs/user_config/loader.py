"""Configuration loader for HFS user preferences.

This module provides ConfigLoader which handles layered configuration loading
with precedence: env > project > global > defaults.

Config files are YAML format:
- Global: ~/.hfs/config.yaml
- Project: .hfs/config.yaml

Environment variable mapping:
- HFS_OUTPUT_MODE -> output_mode
- HFS_KEYBINDING_MODE -> keybinding_mode
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML

from .models import UserConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and saves user configuration with layered precedence.

    Config precedence (highest to lowest):
    1. Environment variables (HFS_OUTPUT_MODE, HFS_KEYBINDING_MODE)
    2. Project config (.hfs/config.yaml in current directory)
    3. Global config (~/.hfs/config.yaml in home directory)
    4. Defaults (defined in UserConfig model)
    """

    # Environment variable to config key mapping
    ENV_MAP: dict[str, str] = {
        "HFS_OUTPUT_MODE": "output_mode",
        "HFS_KEYBINDING_MODE": "keybinding_mode",
    }

    def __init__(
        self,
        global_path: Path | None = None,
        project_path: Path | None = None,
    ) -> None:
        """Initialize the config loader.

        Args:
            global_path: Override for global config path (default: ~/.hfs/config.yaml)
            project_path: Override for project config path (default: .hfs/config.yaml)
        """
        self._global_path = global_path or (Path.home() / ".hfs" / "config.yaml")
        self._project_path = project_path or (Path.cwd() / ".hfs" / "config.yaml")
        self._sources: dict[str, str] = {}  # Track source of each setting

    @property
    def global_path(self) -> Path:
        """Path to global config file."""
        return self._global_path

    @property
    def project_path(self) -> Path:
        """Path to project config file."""
        return self._project_path

    def load(self) -> UserConfig:
        """Load configuration with layered precedence.

        Loads from global -> project -> env, with later sources overriding
        earlier ones. Validates the merged config with Pydantic.

        Returns:
            Validated UserConfig with all settings applied.
        """
        config_dict: dict[str, Any] = {}
        self._sources = {}

        # Set defaults first
        for field in UserConfig.get_field_names():
            self._sources[field] = "default"

        # 1. Load global config (~/.hfs/config.yaml)
        if self._global_path.exists():
            global_data = self._load_yaml(self._global_path)
            if global_data:
                for key, value in global_data.items():
                    if key in UserConfig.get_field_names():
                        config_dict[key] = value
                        self._sources[key] = str(self._global_path)

        # 2. Load project config (.hfs/config.yaml)
        if self._project_path.exists():
            project_data = self._load_yaml(self._project_path)
            if project_data:
                for key, value in project_data.items():
                    if key in UserConfig.get_field_names():
                        config_dict[key] = value
                        self._sources[key] = str(self._project_path)

        # 3. Apply environment variable overrides
        for env_key, config_key in self.ENV_MAP.items():
            if env_key in os.environ:
                config_dict[config_key] = os.environ[env_key]
                self._sources[config_key] = f"env:{env_key}"

        # 4. Validate with Pydantic (uses defaults for missing)
        try:
            return UserConfig(**config_dict)
        except Exception as e:
            logger.warning(f"Config validation error, using defaults: {e}")
            return UserConfig()

    def _load_yaml(self, path: Path) -> dict[str, Any] | None:
        """Load YAML file safely.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed dict or None if loading failed.
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else None
        except yaml.YAMLError as e:
            logger.warning(f"Invalid YAML in {path}: {e}")
            return None
        except OSError as e:
            logger.warning(f"Failed to read {path}: {e}")
            return None

    def save(self, key: str, value: Any) -> None:
        """Save a single setting to global config file.

        Updates only the specified key in ~/.hfs/config.yaml, preserving
        any existing content and comments.

        Args:
            key: Configuration key to update.
            value: New value for the key.

        Raises:
            ValueError: If key is not a valid config key.
        """
        if key not in UserConfig.get_field_names():
            raise ValueError(f"Unknown config key: {key}")

        # Validate value before saving
        valid_values = UserConfig.get_valid_values(key)
        if valid_values and value not in valid_values:
            raise ValueError(
                f"Invalid value '{value}' for '{key}'. "
                f"Must be one of: {', '.join(valid_values)}"
            )

        # Use ruamel.yaml to preserve comments
        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True

        # Load existing or start fresh
        if self._global_path.exists():
            with open(self._global_path, encoding="utf-8") as f:
                data = yaml_handler.load(f) or {}
        else:
            data = {}
            # Create parent directories
            self._global_path.parent.mkdir(parents=True, exist_ok=True)

        # Update the value
        data[key] = value

        # Write back
        with open(self._global_path, "w", encoding="utf-8") as f:
            yaml_handler.dump(data, f)

        logger.info(f"Saved {key}={value} to {self._global_path}")

    def get_effective_config(self) -> dict[str, dict[str, Any]]:
        """Get current effective config with source information.

        Returns:
            Dict mapping field names to dicts with 'value' and 'source' keys.
        """
        # Ensure load() has been called to populate sources
        config = self.load()

        result: dict[str, dict[str, Any]] = {}
        for field in UserConfig.get_field_names():
            result[field] = {
                "value": getattr(config, field),
                "source": self._sources.get(field, "default"),
            }

        return result


def load_user_config() -> UserConfig:
    """Convenience function to load user config with defaults.

    Returns:
        Validated UserConfig with all settings applied.
    """
    return ConfigLoader().load()
