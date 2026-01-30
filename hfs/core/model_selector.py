"""Model selector for role-based tier resolution with provider fallback.

This module provides the ModelSelector class which resolves agent roles to
appropriate model tiers, considering phase overrides and escalation state,
then retrieves models from the provider manager with fallback support.

Tier resolution priority (highest to lowest):
1. Escalation state (triad_id:role specific escalations)
2. Phase overrides (phase-specific role tier mappings)
3. Role defaults (standard role-to-tier mappings)
"""

import logging
from typing import Any, Optional

from keycycle import NoAvailableKeyError

from hfs.agno.providers import ProviderManager
from hfs.core.model_tiers import ModelTiersConfig

logger = logging.getLogger(__name__)


class ModelSelector:
    """Resolves role + triad to appropriate model via tier system.

    The ModelSelector is responsible for:
    1. Resolving which tier a role should use based on escalation state,
       phase overrides, and role defaults
    2. Getting a model from that tier by trying each available provider
       in order until one succeeds

    Attributes:
        config: Model tiers configuration with tier definitions and mappings
        provider_manager: Manager for LLM provider wrappers

    Example:
        >>> config = ModelTiersConfig(...)
        >>> provider_manager = ProviderManager()
        >>> selector = ModelSelector(config, provider_manager)
        >>> model = selector.get_model("triad-123", "worker")
    """

    def __init__(
        self,
        config: ModelTiersConfig,
        provider_manager: ProviderManager,
    ) -> None:
        """Initialize the ModelSelector.

        Args:
            config: Model tiers configuration containing tier definitions,
                role defaults, phase overrides, and escalation state
            provider_manager: Provider manager with initialized LLM wrappers
        """
        self.config = config
        self.provider_manager = provider_manager

    def get_model(
        self,
        triad_id: str,
        role: str,
        phase: Optional[str] = None,
    ) -> Any:
        """Get model for role, considering phase overrides and escalation.

        Resolves the appropriate tier for the given role using the priority:
        escalation > phase override > role default. Then retrieves a model
        from that tier by trying each available provider.

        Args:
            triad_id: Unique identifier for the triad instance
            role: Agent role name (e.g., "worker", "orchestrator", "proposer")
            phase: Optional phase name for phase-specific overrides

        Returns:
            An Agno model instance from the resolved tier

        Raises:
            NoAvailableKeyError: If no provider can supply a model for the tier
            KeyError: If the resolved tier is not defined in config
        """
        tier = self._resolve_tier(triad_id, role, phase)
        logger.debug(
            f"Resolved tier for {triad_id}:{role} (phase={phase}): {tier}"
        )
        return self._get_model_for_tier(tier)

    def _resolve_tier(
        self,
        triad_id: str,
        role: str,
        phase: Optional[str] = None,
    ) -> str:
        """Resolve tier with priority: escalation > phase override > role default.

        Args:
            triad_id: Unique identifier for the triad instance
            role: Agent role name
            phase: Optional phase name

        Returns:
            Resolved tier name (reasoning, general, or fast)
        """
        # 1. Check escalation state first (highest priority)
        escalation_key = f"{triad_id}:{role}"
        if escalation_key in self.config.escalation_state:
            escalated_tier = self.config.escalation_state[escalation_key]
            logger.debug(
                f"Using escalated tier for {escalation_key}: {escalated_tier}"
            )
            return escalated_tier

        # 2. Check phase override
        if phase and phase in self.config.phase_overrides:
            if role in self.config.phase_overrides[phase]:
                override_tier = self.config.phase_overrides[phase][role]
                logger.debug(
                    f"Using phase override for {phase}:{role}: {override_tier}"
                )
                return override_tier

        # 3. Use role default (fallback to "general" if role not found)
        default_tier = self.config.role_defaults.get(role, "general")
        logger.debug(f"Using role default for {role}: {default_tier}")
        return default_tier

    def _get_model_for_tier(self, tier: str) -> Any:
        """Get model from tier, trying each provider in order.

        Iterates through available providers that support the requested tier,
        attempting to get a model from each until one succeeds.

        Args:
            tier: Tier name (reasoning, general, or fast)

        Returns:
            An Agno model instance

        Raises:
            NoAvailableKeyError: If all providers failed to supply a model
            KeyError: If tier is not defined in config
        """
        tier_config = self.config.tiers[tier]
        errors: list[tuple[str, Exception]] = []

        for provider in self.provider_manager.available_providers:
            if provider in tier_config.providers:
                model_id = tier_config.providers[provider]
                try:
                    model = self.provider_manager.get_model(provider, model_id)
                    logger.debug(
                        f"Got model from {provider} for tier {tier}: {model_id}"
                    )
                    return model
                except NoAvailableKeyError as e:
                    logger.debug(
                        f"Provider {provider} unavailable for tier {tier}: {e}"
                    )
                    errors.append((provider, e))
                    continue

        # All providers failed
        error_summary = "; ".join(f"{p}: {e}" for p, e in errors)
        logger.warning(
            f"All providers exhausted for tier {tier}: {error_summary}"
        )
        raise NoAvailableKeyError(
            provider="all",
            model_id=tier,
            wait=True,
            timeout=10.0,
            total_keys=0,
            cooling_down=0,
        )
