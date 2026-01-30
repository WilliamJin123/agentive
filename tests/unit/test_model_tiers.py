"""Unit tests for hfs.core.model_tiers module."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from hfs.core.model_tiers import ModelTiersConfig, TierConfig, TierName


class TestTierConfig:
    """Tests for TierConfig validation."""

    def test_valid_tier_with_description_and_providers(self):
        """Valid tier with description and providers dict."""
        tier = TierConfig(
            description="High capability for orchestration",
            providers={
                "cerebras": "qwen-3-235b",
                "groq": "llama-70b",
            }
        )
        assert tier.description == "High capability for orchestration"
        assert tier.providers["cerebras"] == "qwen-3-235b"
        assert tier.providers["groq"] == "llama-70b"

    def test_invalid_tier_missing_description(self):
        """Tier without description raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TierConfig(providers={"cerebras": "test-model"})
        assert "description" in str(exc_info.value)

    def test_invalid_tier_missing_providers(self):
        """Tier without providers raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TierConfig(description="Test tier")
        assert "providers" in str(exc_info.value)

    def test_tier_with_empty_providers(self):
        """Tier with empty providers dict is allowed."""
        tier = TierConfig(description="Empty tier", providers={})
        assert tier.providers == {}


class TestModelTiersConfig:
    """Tests for ModelTiersConfig validation."""

    def _make_valid_tiers(self) -> dict:
        """Create valid tiers dict for testing."""
        return {
            "reasoning": TierConfig(
                description="High capability",
                providers={"cerebras": "high-model"}
            ),
            "general": TierConfig(
                description="Balanced capability",
                providers={"cerebras": "general-model"}
            ),
            "fast": TierConfig(
                description="Speed optimized",
                providers={"cerebras": "fast-model"}
            ),
        }

    def test_valid_config_with_all_three_tiers(self):
        """Valid config with all 3 required tiers."""
        config = ModelTiersConfig(tiers=self._make_valid_tiers())
        assert set(config.tiers.keys()) == {"reasoning", "general", "fast"}

    def test_missing_reasoning_tier_raises_error(self):
        """Config without reasoning tier raises validation error."""
        tiers = self._make_valid_tiers()
        del tiers["reasoning"]
        with pytest.raises(ValidationError) as exc_info:
            ModelTiersConfig(tiers=tiers)
        assert "reasoning" in str(exc_info.value)

    def test_missing_general_tier_raises_error(self):
        """Config without general tier raises validation error."""
        tiers = self._make_valid_tiers()
        del tiers["general"]
        with pytest.raises(ValidationError) as exc_info:
            ModelTiersConfig(tiers=tiers)
        assert "general" in str(exc_info.value)

    def test_missing_fast_tier_raises_error(self):
        """Config without fast tier raises validation error."""
        tiers = self._make_valid_tiers()
        del tiers["fast"]
        with pytest.raises(ValidationError) as exc_info:
            ModelTiersConfig(tiers=tiers)
        assert "fast" in str(exc_info.value)

    def test_empty_role_defaults_allowed(self):
        """Empty role_defaults is allowed (defaults to empty dict)."""
        config = ModelTiersConfig(tiers=self._make_valid_tiers())
        assert config.role_defaults == {}

    def test_role_defaults_work_correctly(self):
        """role_defaults mapping is validated and accessible."""
        config = ModelTiersConfig(
            tiers=self._make_valid_tiers(),
            role_defaults={
                "orchestrator": "reasoning",
                "worker_a": "general",
                "code_execution": "fast",
            }
        )
        assert config.role_defaults["orchestrator"] == "reasoning"
        assert config.role_defaults["worker_a"] == "general"
        assert config.role_defaults["code_execution"] == "fast"

    def test_invalid_role_default_tier_raises_error(self):
        """Invalid tier name in role_defaults raises validation error."""
        with pytest.raises(ValidationError):
            ModelTiersConfig(
                tiers=self._make_valid_tiers(),
                role_defaults={"orchestrator": "invalid_tier"}  # type: ignore
            )

    def test_phase_overrides_work_correctly(self):
        """phase_overrides mapping is validated and accessible."""
        config = ModelTiersConfig(
            tiers=self._make_valid_tiers(),
            phase_overrides={
                "execution": {
                    "worker_a": "fast",
                    "worker_b": "fast",
                }
            }
        )
        assert config.phase_overrides["execution"]["worker_a"] == "fast"
        assert config.phase_overrides["execution"]["worker_b"] == "fast"

    def test_escalation_state_stores_triad_role_keys(self):
        """escalation_state can store 'triad_id:role' keys."""
        config = ModelTiersConfig(
            tiers=self._make_valid_tiers(),
            escalation_state={
                "triad_1:worker_a": "general",
                "triad_2:orchestrator": "reasoning",
            }
        )
        assert config.escalation_state["triad_1:worker_a"] == "general"
        assert config.escalation_state["triad_2:orchestrator"] == "reasoning"

    def test_escalation_state_defaults_to_empty(self):
        """escalation_state defaults to empty dict."""
        config = ModelTiersConfig(tiers=self._make_valid_tiers())
        assert config.escalation_state == {}


class TestLoadFromYAML:
    """Tests for loading ModelTiersConfig from YAML."""

    def test_load_model_tiers_from_default_yaml(self):
        """Load model_tiers section from default.yaml and validate."""
        default_yaml_path = Path(__file__).parent.parent.parent / "hfs" / "config" / "default.yaml"

        with open(default_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        model_tiers_data = data["config"]["model_tiers"]

        # Convert nested dicts to TierConfig objects
        tiers = {
            name: TierConfig(**tier_data)
            for name, tier_data in model_tiers_data["tiers"].items()
        }

        config = ModelTiersConfig(
            tiers=tiers,
            role_defaults=model_tiers_data.get("role_defaults", {}),
            phase_overrides=model_tiers_data.get("phase_overrides", {}),
            escalation_state=model_tiers_data.get("escalation_state", {}),
        )

        # Verify structure
        assert set(config.tiers.keys()) == {"reasoning", "general", "fast"}

        # Verify all tiers have all 4 providers
        for tier_name, tier_config in config.tiers.items():
            assert "cerebras" in tier_config.providers, f"{tier_name} missing cerebras"
            assert "groq" in tier_config.providers, f"{tier_name} missing groq"
            assert "gemini" in tier_config.providers, f"{tier_name} missing gemini"
            assert "openrouter" in tier_config.providers, f"{tier_name} missing openrouter"

        # Verify role defaults include key roles
        assert config.role_defaults.get("orchestrator") == "reasoning"
        assert config.role_defaults.get("code_execution") == "fast"

        # Verify phase overrides
        assert "execution" in config.phase_overrides
        assert config.phase_overrides["execution"].get("worker_a") == "fast"

        # Verify escalation state is empty initially
        assert config.escalation_state == {}
