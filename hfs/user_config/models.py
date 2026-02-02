"""User configuration models for HFS.

This module provides Pydantic models for user preferences. These settings
control the TUI experience (output mode, keybinding mode) and are separate
from the HFS run configuration in hfs/core/config.py.

User preferences are stored in:
- Global: ~/.hfs/config.yaml
- Project: .hfs/config.yaml (in project root)
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class UserConfig(BaseModel):
    """User preferences for HFS TUI.

    These settings control the terminal interface experience. They are
    loaded from config files and can be modified via /config commands.

    Attributes:
        output_mode: Display mode - 'verbose' shows full agent activity,
            'compact' hides agent details and shows only final responses.
        keybinding_mode: Input mode - 'standard' uses typical shortcuts,
            'vim' enables modal editing, 'emacs' uses readline-style bindings.
    """

    model_config = ConfigDict(extra="ignore")

    output_mode: Literal["compact", "verbose"] = "verbose"
    keybinding_mode: Literal["standard", "vim", "emacs"] = "standard"
    checkpoint_retention: int = 10

    @classmethod
    def get_valid_values(cls, field_name: str) -> list[str] | None:
        """Get valid values for a field.

        Args:
            field_name: Name of the field to get valid values for.

        Returns:
            List of valid string values, or None if field doesn't exist
            or doesn't have literal constraints.
        """
        if field_name == "output_mode":
            return ["compact", "verbose"]
        elif field_name == "keybinding_mode":
            return ["standard", "vim", "emacs"]
        elif field_name == "checkpoint_retention":
            # Integer field, no fixed list - return None
            return None
        return None

    @classmethod
    def get_field_names(cls) -> list[str]:
        """Get all configurable field names.

        Returns:
            List of field names that can be configured.
        """
        return ["output_mode", "keybinding_mode", "checkpoint_retention"]
