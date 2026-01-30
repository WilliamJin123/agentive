"""Unit tests for ModelSelector tier resolution and provider fallback."""

import pytest
from unittest.mock import Mock, MagicMock

from keycycle import NoAvailableKeyError

from hfs.core.model_tiers import TierConfig, ModelTiersConfig
from hfs.core.model_selector import ModelSelector


@pytest.fixture
def base_tiers() -> dict:
    """Base tier configuration for tests."""
    return {
        "reasoning": TierConfig(
            description="Highest capability",
            providers={
                "cerebras": "llama-3.3-70b",
                "groq": "llama-3.3-70b-versatile",
            },
        ),
        "general": TierConfig(
            description="Balanced capability",
            providers={
                "cerebras": "llama-3.1-8b",
                "groq": "llama-3.1-8b-instant",
            },
        ),
        "fast": TierConfig(
            description="Speed optimized",
            providers={
                "cerebras": "llama-3.1-8b",
                "groq": "llama-3.1-8b-instant",
            },
        ),
    }


@pytest.fixture
def mock_provider_manager() -> Mock:
    """Mock ProviderManager for testing."""
    manager = Mock()
    manager.available_providers = ["cerebras", "groq"]
    manager.get_model = Mock(return_value=Mock(name="mock_model"))
    return manager


class TestTierResolutionPriority:
    """Test tier resolution priority: escalation > phase > role default."""

    def test_role_default_when_no_overrides(
        self, base_tiers, mock_provider_manager
    ):
        """Role default is used when no escalation or phase override exists."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general", "orchestrator": "reasoning"},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # Should use role default
        selector.get_model("triad-1", "worker")
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )

    def test_phase_override_takes_precedence_over_role_default(
        self, base_tiers, mock_provider_manager
    ):
        """Phase override takes precedence over role default."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
            phase_overrides={"execution": {"worker": "fast"}},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # Without phase: uses role default (general)
        selector.get_model("triad-1", "worker")
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )

        # With phase: uses phase override (fast)
        mock_provider_manager.get_model.reset_mock()
        selector.get_model("triad-1", "worker", phase="execution")
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )

    def test_escalation_state_takes_highest_precedence(
        self, base_tiers, mock_provider_manager
    ):
        """Escalation state takes precedence over phase override and role default."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
            phase_overrides={"execution": {"worker": "fast"}},
            escalation_state={"triad-1:worker": "reasoning"},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # Even with phase override, escalation wins
        selector.get_model("triad-1", "worker", phase="execution")
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.3-70b"
        )

    def test_escalation_only_affects_specific_triad_role(
        self, base_tiers, mock_provider_manager
    ):
        """Escalation for one triad:role doesn't affect others."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
            escalation_state={"triad-1:worker": "reasoning"},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # triad-1:worker is escalated
        selector.get_model("triad-1", "worker")
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.3-70b"
        )

        # triad-2:worker uses default
        mock_provider_manager.get_model.reset_mock()
        selector.get_model("triad-2", "worker")
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )


class TestProviderFallback:
    """Test provider fallback chain."""

    def test_uses_first_available_provider(
        self, base_tiers, mock_provider_manager
    ):
        """Uses first available provider for tier."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
        )
        selector = ModelSelector(config, mock_provider_manager)

        selector.get_model("triad-1", "worker")

        # First available provider (cerebras) should be tried
        mock_provider_manager.get_model.assert_called_once()
        call_args = mock_provider_manager.get_model.call_args
        assert call_args[0][0] == "cerebras"

    def test_falls_back_to_next_provider_when_first_unavailable(
        self, base_tiers, mock_provider_manager
    ):
        """Falls back to next provider when first has no keys available."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # First call fails, second succeeds
        mock_provider_manager.get_model.side_effect = [
            NoAvailableKeyError(
                provider="cerebras",
                model_id="llama-3.1-8b",
                wait=True,
                timeout=10.0,
                total_keys=5,
                cooling_down=5,
            ),
            Mock(name="groq_model"),
        ]

        model = selector.get_model("triad-1", "worker")

        assert mock_provider_manager.get_model.call_count == 2
        # Second call should be to groq
        second_call = mock_provider_manager.get_model.call_args_list[1]
        assert second_call[0][0] == "groq"
        assert model is not None

    def test_raises_error_when_all_providers_exhausted(
        self, base_tiers, mock_provider_manager
    ):
        """Raises NoAvailableKeyError when all providers exhausted."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # Both providers fail
        mock_provider_manager.get_model.side_effect = [
            NoAvailableKeyError(
                provider="cerebras",
                model_id="llama-3.1-8b",
                wait=True,
                timeout=10.0,
                total_keys=5,
                cooling_down=5,
            ),
            NoAvailableKeyError(
                provider="groq",
                model_id="llama-3.1-8b-instant",
                wait=True,
                timeout=10.0,
                total_keys=3,
                cooling_down=3,
            ),
        ]

        with pytest.raises(NoAvailableKeyError) as exc_info:
            selector.get_model("triad-1", "worker")

        assert exc_info.value.provider == "all"

    def test_skips_providers_not_in_tier_config(self, mock_provider_manager):
        """Skips providers that don't have models for the tier."""
        # Tier only has cerebras
        tiers = {
            "reasoning": TierConfig(
                description="Highest",
                providers={"cerebras": "llama-3.3-70b"},
            ),
            "general": TierConfig(
                description="Balanced",
                providers={"cerebras": "llama-3.1-8b"},
            ),
            "fast": TierConfig(
                description="Fast",
                providers={"cerebras": "llama-3.1-8b"},
            ),
        }
        config = ModelTiersConfig(
            tiers=tiers,
            role_defaults={"worker": "general"},
        )

        # Provider manager has both, but tier only has cerebras
        mock_provider_manager.available_providers = ["cerebras", "groq"]
        selector = ModelSelector(config, mock_provider_manager)

        selector.get_model("triad-1", "worker")

        # Only cerebras should be called
        assert mock_provider_manager.get_model.call_count == 1
        assert mock_provider_manager.get_model.call_args[0][0] == "cerebras"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_role_falls_back_to_general_tier(
        self, base_tiers, mock_provider_manager
    ):
        """Unknown role falls back to 'general' tier."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "reasoning"},  # No "unknown" role
        )
        selector = ModelSelector(config, mock_provider_manager)

        # "unknown_role" not in role_defaults, should use "general"
        selector.get_model("triad-1", "unknown_role")

        # Should call with general tier model
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )

    def test_unknown_tier_raises_key_error(
        self, base_tiers, mock_provider_manager
    ):
        """Unknown tier in role_defaults raises KeyError."""
        # Manually construct config with invalid tier reference
        config = ModelTiersConfig(tiers=base_tiers)
        # Bypass Pydantic validation by directly modifying
        config.role_defaults = {"worker": "nonexistent"}

        selector = ModelSelector(config, mock_provider_manager)

        with pytest.raises(KeyError):
            selector.get_model("triad-1", "worker")

    def test_empty_escalation_state_doesnt_affect_resolution(
        self, base_tiers, mock_provider_manager
    ):
        """Empty escalation_state doesn't interfere with tier resolution."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
            escalation_state={},  # Explicitly empty
        )
        selector = ModelSelector(config, mock_provider_manager)

        selector.get_model("triad-1", "worker")

        # Should use role default
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )

    def test_phase_override_only_affects_matching_phase(
        self, base_tiers, mock_provider_manager
    ):
        """Phase override only applies when phase matches."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general"},
            phase_overrides={"execution": {"worker": "fast"}},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # Different phase name - should use role default
        selector.get_model("triad-1", "worker", phase="deliberation")

        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.1-8b"
        )

    def test_phase_override_role_must_match(
        self, base_tiers, mock_provider_manager
    ):
        """Phase override only applies when role matches within phase."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={"worker": "general", "orchestrator": "reasoning"},
            phase_overrides={"execution": {"worker": "fast"}},
        )
        selector = ModelSelector(config, mock_provider_manager)

        # Phase exists but no override for orchestrator role
        selector.get_model("triad-1", "orchestrator", phase="execution")

        # Should use role default for orchestrator
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-3.3-70b"
        )
