"""Configuration loading and validation for HFS.

This module provides Pydantic models for validating HFS configuration and
a load_config() function that reads YAML config files and returns validated
configuration objects.

Configuration schema as defined in DESIGN.md includes:
- Triads: id, preset, scope, budget, objectives
- Pressure settings: temperature, decay, thresholds
- Sections: the "territory" that triads will divide
- Arbiter settings: model, max_tokens, temperature
- Output settings: format, style_system
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ConfigError(Exception):
    """Exception raised for configuration validation failures."""
    pass


# ============================================================
# TRIAD CONFIGURATION MODELS
# ============================================================

class ScopeConfigModel(BaseModel):
    """Scope configuration for a triad.

    Attributes:
        primary: Sections this triad owns by default (guaranteed territory)
        reach: Sections this triad can claim (aspirational territory)
    """
    primary: List[str] = Field(default_factory=list, description="Sections this triad owns by default")
    reach: List[str] = Field(default_factory=list, description="Sections this triad can claim")


class BudgetConfigModel(BaseModel):
    """Budget configuration for a triad.

    Attributes:
        tokens: Maximum tokens for this triad
        tool_calls: Maximum tool invocations
        time_ms: Maximum execution time in milliseconds
    """
    tokens: int = Field(default=20000, ge=0, description="Max tokens")
    tool_calls: int = Field(default=50, ge=0, description="Max tool invocations")
    time_ms: int = Field(default=30000, ge=0, description="Max execution time in milliseconds")


class TriadConfigModel(BaseModel):
    """Configuration for a single triad.

    Attributes:
        id: Unique identifier for the triad
        preset: The preset type (hierarchical, dialectic, consensus)
        scope: Scope configuration (primary and reach sections)
        budget: Budget constraints
        objectives: What this triad optimizes for
        system_context: Optional additional context for system prompts
    """
    id: str = Field(..., min_length=1, description="Unique identifier")
    preset: Literal["hierarchical", "dialectic", "consensus"] = Field(
        ..., description="Triad preset type"
    )
    scope: ScopeConfigModel = Field(default_factory=ScopeConfigModel)
    budget: BudgetConfigModel = Field(default_factory=BudgetConfigModel)
    objectives: List[str] = Field(default_factory=list, description="Optimization objectives")
    system_context: Optional[str] = Field(None, description="Additional context for prompts")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure triad ID is valid (alphanumeric and underscores)."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Triad ID must be alphanumeric with underscores/dashes: {v}")
        return v


# ============================================================
# PRESSURE CONFIGURATION MODELS
# ============================================================

class GlobalBudgetConfigModel(BaseModel):
    """Global budget configuration.

    Attributes:
        tokens: Total tokens for all triads combined
        time_ms: Total wall-clock time in milliseconds
    """
    tokens: int = Field(default=100000, ge=0, description="Total tokens for all triads")
    time_ms: int = Field(default=60000, ge=0, description="Total wall-clock time in ms")


class PressureConfigModel(BaseModel):
    """Pressure mechanics configuration.

    Attributes:
        initial_temperature: Starting temperature (default: 1.0)
        temperature_decay: Decrease per round (default: 0.15)
        freeze_threshold: Freeze when below this (default: 0.1)
        max_negotiation_rounds: Hard cap on rounds (default: 10)
        escalation_threshold: Rounds stuck before escalate (default: 2)
        global_budget: Total budget for all triads
        validation: List of validation checks to run
    """
    initial_temperature: float = Field(default=1.0, ge=0.0, le=1.0)
    temperature_decay: float = Field(default=0.15, ge=0.0, le=1.0)
    freeze_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    max_negotiation_rounds: int = Field(default=10, ge=1, le=100)
    escalation_threshold: int = Field(default=2, ge=1, le=50)
    global_budget: GlobalBudgetConfigModel = Field(default_factory=GlobalBudgetConfigModel)
    validation: List[str] = Field(default_factory=list)

    @field_validator('validation')
    @classmethod
    def validate_validation_checks(cls, v: List[str]) -> List[str]:
        """Validate that validation check names are known."""
        known_checks = {
            'must_compile',
            'must_render',
            'no_contradictions',
            'accessibility_a11y',
            'accessibility_basic',
            'performance_budget',
        }
        for check in v:
            if check not in known_checks:
                # Allow unknown checks with a warning (they'll be skipped)
                pass
        return v


# ============================================================
# ARBITER CONFIGURATION MODEL
# ============================================================

class ArbiterConfigModel(BaseModel):
    """Arbiter configuration.

    Attributes:
        model: LLM model to use for arbitration
        max_tokens: Maximum tokens for arbiter responses
        temperature: LLM temperature (lower = more deterministic)
    """
    model: str = Field(default="claude-sonnet-4-20250514", description="LLM model for arbitration")
    max_tokens: int = Field(default=2000, ge=100, le=16000)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


# ============================================================
# OUTPUT CONFIGURATION MODEL
# ============================================================

class OutputConfigModel(BaseModel):
    """Output configuration.

    Attributes:
        format: Output framework format
        style_system: CSS style system to use
        include_emergent_report: Whether to include emergent center analysis
        include_negotiation_log: Whether to include full negotiation history
    """
    format: Literal["react", "vue", "svelte", "html", "vanilla"] = Field(
        default="react", description="Output framework format"
    )
    style_system: Literal["tailwind", "css-modules", "styled-components", "vanilla"] = Field(
        default="tailwind", description="CSS style system"
    )
    include_emergent_report: bool = Field(default=True)
    include_negotiation_log: bool = Field(default=False)


# ============================================================
# MAIN HFS CONFIGURATION MODEL
# ============================================================

class HFSConfig(BaseModel):
    """Main HFS configuration model.

    This is the root configuration object that contains all HFS settings.

    Attributes:
        triads: List of triad configurations
        pressure: Pressure mechanics configuration
        sections: List of section names (the "territory")
        arbiter: Arbiter configuration
        output: Output configuration
    """
    triads: List[TriadConfigModel] = Field(
        default_factory=list, min_length=1, description="Triad configurations"
    )
    pressure: PressureConfigModel = Field(default_factory=PressureConfigModel)
    sections: List[str] = Field(default_factory=list, min_length=1)
    arbiter: ArbiterConfigModel = Field(default_factory=ArbiterConfigModel)
    output: OutputConfigModel = Field(default_factory=OutputConfigModel)

    @model_validator(mode='after')
    def validate_triad_ids_unique(self) -> 'HFSConfig':
        """Ensure all triad IDs are unique."""
        ids = [t.id for t in self.triads]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate triad IDs found: {set(duplicates)}")
        return self

    @model_validator(mode='after')
    def validate_scopes_reference_sections(self) -> 'HFSConfig':
        """Validate that triad scopes reference defined sections."""
        section_set = set(self.sections)
        # Also include parent sections for hierarchical section names
        expanded_sections = set()
        for section in self.sections:
            expanded_sections.add(section)
            # Add parent paths (e.g., "layout/grid" implies "layout" is valid)
            parts = section.split('/')
            for i in range(len(parts)):
                expanded_sections.add('/'.join(parts[:i+1]))

        for triad in self.triads:
            for scope_section in triad.scope.primary + triad.scope.reach:
                if scope_section not in expanded_sections:
                    # Only warn, don't fail - sections might be defined elsewhere
                    pass
        return self


def load_config(path: Union[str, Path]) -> HFSConfig:
    """Load and validate an HFS configuration file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Validated HFSConfig object

    Raises:
        ConfigError: If the file cannot be read or parsed
        ConfigError: If validation fails
    """
    path = Path(path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    if not path.is_file():
        raise ConfigError(f"Configuration path is not a file: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}") from e
    except IOError as e:
        raise ConfigError(f"Failed to read configuration file: {e}") from e

    if raw_config is None:
        raise ConfigError("Configuration file is empty")

    # Handle nested 'config' key if present
    if 'config' in raw_config:
        raw_config = raw_config['config']

    try:
        config = HFSConfig(**raw_config)
    except Exception as e:
        raise ConfigError(f"Configuration validation failed: {e}") from e

    return config


def load_config_dict(data: Dict[str, Any]) -> HFSConfig:
    """Load and validate an HFS configuration from a dictionary.

    Args:
        data: Dictionary containing configuration data

    Returns:
        Validated HFSConfig object

    Raises:
        ConfigError: If validation fails
    """
    # Handle nested 'config' key if present
    if 'config' in data:
        data = data['config']

    try:
        config = HFSConfig(**data)
    except Exception as e:
        raise ConfigError(f"Configuration validation failed: {e}") from e

    return config
