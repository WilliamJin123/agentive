"""Model tier configuration for role-based model selection.

This module provides Pydantic models for configuring model tiers with
provider-specific model IDs, role-to-tier mappings, phase overrides,
and escalation state tracking for adaptive model selection.

Configuration schema:
- tiers: Maps tier names (reasoning, general, fast) to TierConfig
- role_defaults: Maps role names to default tier
- phase_overrides: Maps phase names to role override mappings
- escalation_state: System-managed mapping of "triad_id:role" to escalated tier
"""

from typing import Dict, Literal

from pydantic import BaseModel, Field, model_validator


# Type alias for valid tier names
TierName = Literal["reasoning", "general", "fast"]


class TierConfig(BaseModel):
    """Configuration for a single model tier.

    Attributes:
        description: Human-readable explanation of tier purpose
        providers: Mapping of provider name to provider-specific model ID
    """
    description: str = Field(
        ...,
        description="Human-readable tier purpose"
    )
    providers: Dict[str, str] = Field(
        ...,
        description="Provider name to model ID mapping"
    )


class ModelTiersConfig(BaseModel):
    """Model tier configuration section.

    This configuration controls role-based model selection with support for:
    - Provider-specific model IDs per tier
    - Role-to-tier default mappings
    - Phase-specific tier overrides
    - Escalation state for failure-adaptive tier upgrades

    Attributes:
        tiers: Mapping of tier name to tier configuration
        role_defaults: Mapping of role name to default tier
        phase_overrides: Mapping of phase name to role override mappings
        escalation_state: System-managed mapping of "triad_id:role" to escalated tier
    """
    tiers: Dict[TierName, TierConfig] = Field(
        ...,
        description="Tier name to tier configuration mapping"
    )
    role_defaults: Dict[str, TierName] = Field(
        default_factory=dict,
        description="Role name to default tier mapping"
    )
    phase_overrides: Dict[str, Dict[str, TierName]] = Field(
        default_factory=dict,
        description="Phase name to role override mappings"
    )
    escalation_state: Dict[str, TierName] = Field(
        default_factory=dict,
        description="triad_id:role to escalated tier (system-managed)"
    )

    @model_validator(mode='after')
    def validate_all_tiers_defined(self) -> 'ModelTiersConfig':
        """Ensure all three required tiers (reasoning, general, fast) are defined."""
        required_tiers: set[TierName] = {"reasoning", "general", "fast"}
        defined_tiers = set(self.tiers.keys())

        missing = required_tiers - defined_tiers
        if missing:
            raise ValueError(f"Missing required tiers: {missing}")

        return self
