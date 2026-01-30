"""Unit tests for hfs.core.escalation_tracker module."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from hfs.core.escalation_tracker import EscalationTracker
from hfs.core.model_tiers import ModelTiersConfig, TierConfig


def make_valid_tiers() -> dict:
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


def make_config(
    role_defaults: dict = None,
    escalation_state: dict = None
) -> ModelTiersConfig:
    """Create a ModelTiersConfig for testing."""
    return ModelTiersConfig(
        tiers=make_valid_tiers(),
        role_defaults=role_defaults or {
            "orchestrator": "reasoning",
            "worker_a": "general",
            "worker_b": "general",
        },
        escalation_state=escalation_state or {},
    )


def write_yaml_config(path: Path, config: ModelTiersConfig) -> None:
    """Write a config to a YAML file in the expected format."""
    yaml = YAML()
    yaml.preserve_quotes = True
    data = {
        "config": {
            "model_tiers": {
                "tiers": {
                    name: {"description": t.description, "providers": t.providers}
                    for name, t in config.tiers.items()
                },
                "role_defaults": config.role_defaults,
                "escalation_state": config.escalation_state,
            }
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def read_yaml_escalation_state(path: Path) -> dict:
    """Read the escalation_state from a YAML config file."""
    yaml = YAML()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f)
    return data.get("config", {}).get("model_tiers", {}).get("escalation_state", {})


class TestFailureCounting:
    """Tests for failure count tracking."""

    def test_record_failure_increments_count(self, tmp_path):
        """record_failure increments the failure count."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        assert tracker.get_failure_count("triad_1", "worker_a") == 0
        tracker.record_failure("triad_1", "worker_a")
        assert tracker.get_failure_count("triad_1", "worker_a") == 1
        tracker.record_failure("triad_1", "worker_a")
        assert tracker.get_failure_count("triad_1", "worker_a") == 2

    def test_failure_count_persists_across_calls(self, tmp_path):
        """Failure count persists across multiple calls."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        for _ in range(2):
            tracker.record_failure("triad_1", "worker_a")

        assert tracker.get_failure_count("triad_1", "worker_a") == 2

    def test_different_triad_role_keys_tracked_separately(self, tmp_path):
        """Different triad:role keys are tracked independently."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        tracker.record_failure("triad_1", "worker_a")
        tracker.record_failure("triad_1", "worker_a")
        tracker.record_failure("triad_2", "worker_a")
        tracker.record_failure("triad_1", "orchestrator")

        assert tracker.get_failure_count("triad_1", "worker_a") == 2
        assert tracker.get_failure_count("triad_2", "worker_a") == 1
        assert tracker.get_failure_count("triad_1", "orchestrator") == 1


class TestEscalationTrigger:
    """Tests for escalation threshold triggering."""

    def test_no_escalation_before_threshold(self, tmp_path):
        """No escalation when below threshold (2 failures)."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # 2 failures - no escalation
        result1 = tracker.record_failure("triad_1", "worker_a")
        result2 = tracker.record_failure("triad_1", "worker_a")

        assert result1 is None
        assert result2 is None
        assert "triad_1:worker_a" not in config.escalation_state

    def test_escalation_at_threshold(self, tmp_path):
        """Escalation triggers at exactly 3 consecutive failures."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # 3 failures - should escalate
        tracker.record_failure("triad_1", "worker_a")
        tracker.record_failure("triad_1", "worker_a")
        new_tier = tracker.record_failure("triad_1", "worker_a")

        assert new_tier == "reasoning"  # general -> reasoning
        assert config.escalation_state["triad_1:worker_a"] == "reasoning"

    def test_failure_count_resets_after_escalation(self, tmp_path):
        """Failure count resets to 0 after escalation."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # Trigger escalation
        for _ in range(3):
            tracker.record_failure("triad_1", "worker_a")

        # Count should be reset
        assert tracker.get_failure_count("triad_1", "worker_a") == 0


class TestSuccessHandling:
    """Tests for success recording behavior."""

    def test_record_success_resets_failure_count(self, tmp_path):
        """record_success resets failure count to 0."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        tracker.record_failure("triad_1", "worker_a")
        tracker.record_failure("triad_1", "worker_a")
        assert tracker.get_failure_count("triad_1", "worker_a") == 2

        tracker.record_success("triad_1", "worker_a")
        assert tracker.get_failure_count("triad_1", "worker_a") == 0

    def test_success_on_zero_count_is_noop(self, tmp_path):
        """Success on key with 0 failures is a no-op."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # Should not raise, just be a no-op
        tracker.record_success("triad_1", "worker_a")
        assert tracker.get_failure_count("triad_1", "worker_a") == 0


class TestTierProgression:
    """Tests for tier escalation path."""

    def test_fast_escalates_to_general(self, tmp_path):
        """Fast tier escalates to general tier."""
        config = make_config(role_defaults={"worker_a": "fast"})
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        for _ in range(3):
            result = tracker.record_failure("triad_1", "worker_a")

        assert result == "general"
        assert config.escalation_state["triad_1:worker_a"] == "general"

    def test_general_escalates_to_reasoning(self, tmp_path):
        """General tier escalates to reasoning tier."""
        config = make_config(role_defaults={"worker_a": "general"})
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        for _ in range(3):
            result = tracker.record_failure("triad_1", "worker_a")

        assert result == "reasoning"
        assert config.escalation_state["triad_1:worker_a"] == "reasoning"

    def test_reasoning_tier_cannot_escalate(self, tmp_path, caplog):
        """Reasoning tier (highest) cannot escalate further."""
        config = make_config(role_defaults={"orchestrator": "reasoning"})
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                result = tracker.record_failure("triad_1", "orchestrator")

        assert result is None
        assert "triad_1:orchestrator" not in config.escalation_state
        assert "already at highest tier" in caplog.text

    def test_escalation_respects_existing_escalation_state(self, tmp_path):
        """Escalation uses existing escalation_state, not just role_defaults."""
        # Start worker_a at general default, but already escalated to reasoning
        config = make_config(
            role_defaults={"worker_a": "general"},
            escalation_state={"triad_1:worker_a": "reasoning"}
        )
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # Already at reasoning, should not escalate
        for _ in range(3):
            result = tracker.record_failure("triad_1", "worker_a")

        assert result is None


class TestConfigPersistence:
    """Tests for YAML config file persistence."""

    def test_escalation_persists_to_yaml_file(self, tmp_path):
        """Escalation state is written to the YAML file."""
        config = make_config()
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # Trigger escalation
        for _ in range(3):
            tracker.record_failure("triad_1", "worker_a")

        # Read file directly to verify persistence
        persisted_state = read_yaml_escalation_state(config_path)
        assert persisted_state["triad_1:worker_a"] == "reasoning"

    def test_yaml_preserves_other_config_content(self, tmp_path):
        """Round-trip editing preserves other config content."""
        config = make_config()
        config_path = tmp_path / "config.yaml"

        # Write initial config with extra content
        yaml = YAML()
        yaml.preserve_quotes = True
        data = {
            "config": {
                "model_tiers": {
                    "tiers": {
                        name: {"description": t.description, "providers": t.providers}
                        for name, t in config.tiers.items()
                    },
                    "role_defaults": config.role_defaults,
                    "escalation_state": {},
                },
                "other_section": {
                    "key1": "value1",
                    "key2": 42,
                }
            }
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        tracker = EscalationTracker(config_path, config)

        # Trigger escalation
        for _ in range(3):
            tracker.record_failure("triad_1", "worker_a")

        # Read file and verify other content preserved
        with open(config_path, "r", encoding="utf-8") as f:
            final_data = yaml.load(f)

        assert final_data["config"]["other_section"]["key1"] == "value1"
        assert final_data["config"]["other_section"]["key2"] == 42
        assert final_data["config"]["model_tiers"]["escalation_state"]["triad_1:worker_a"] == "reasoning"

    def test_yaml_creates_missing_nested_paths(self, tmp_path):
        """Persistence creates missing nested paths in YAML."""
        config = make_config()
        config_path = tmp_path / "config.yaml"

        # Write minimal config without escalation_state
        yaml = YAML()
        yaml.preserve_quotes = True
        data = {"config": {}}  # Missing model_tiers entirely
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        tracker = EscalationTracker(config_path, config)

        # Trigger escalation
        for _ in range(3):
            tracker.record_failure("triad_1", "worker_a")

        # Should have created the path
        persisted_state = read_yaml_escalation_state(config_path)
        assert persisted_state["triad_1:worker_a"] == "reasoning"

    def test_multiple_escalations_accumulate_in_yaml(self, tmp_path):
        """Multiple escalations for different keys accumulate in YAML."""
        config = make_config(role_defaults={
            "worker_a": "fast",
            "worker_b": "fast",
        })
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # Escalate worker_a
        for _ in range(3):
            tracker.record_failure("triad_1", "worker_a")

        # Escalate worker_b
        for _ in range(3):
            tracker.record_failure("triad_1", "worker_b")

        # Both should be in file
        persisted_state = read_yaml_escalation_state(config_path)
        assert persisted_state["triad_1:worker_a"] == "general"
        assert persisted_state["triad_1:worker_b"] == "general"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_role_not_in_defaults_uses_general(self, tmp_path):
        """Role not in role_defaults defaults to general tier."""
        config = make_config(role_defaults={})  # No defaults
        config_path = tmp_path / "config.yaml"
        write_yaml_config(config_path, config)

        tracker = EscalationTracker(config_path, config)

        # Unknown role should start at general, escalate to reasoning
        for _ in range(3):
            result = tracker.record_failure("triad_1", "unknown_role")

        assert result == "reasoning"
