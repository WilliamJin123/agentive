"""Tests for HFSOrchestrator ModelSelector integration.

These tests verify that the orchestrator correctly integrates with
ModelSelector and EscalationTracker for role-based model selection.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from hfs.core.orchestrator import HFSOrchestrator
from hfs.core.model_selector import ModelSelector
from hfs.core.escalation_tracker import EscalationTracker
from hfs.core.model_tiers import ModelTiersConfig, TierConfig


@pytest.fixture
def minimal_config_dict():
    """Minimal valid HFS config dict for testing."""
    return {
        "config": {
            "triads": [
                {
                    "id": "test_triad",
                    "preset": "hierarchical",
                    "scope": {"primary": ["layout"], "reach": ["spacing"]},
                    "budget": {"tokens": 1000, "tool_calls": 10, "time_ms": 5000},
                    "objectives": ["test"],
                }
            ],
            "sections": ["layout", "spacing"],
            "pressure": {
                "initial_temperature": 0.5,
                "temperature_decay": 0.1,
                "freeze_threshold": 0.9,
            },
            "arbiter": {"model": "test", "max_tokens": 100, "temperature": 0.5},
            "output": {"format": "react"},
        }
    }


@pytest.fixture
def model_tiers_config():
    """ModelTiersConfig for testing."""
    return ModelTiersConfig(
        tiers={
            "reasoning": TierConfig(
                description="high",
                providers={"cerebras": "llama-3.3-70b"},
            ),
            "general": TierConfig(
                description="mid",
                providers={"cerebras": "llama-3.1-8b-instant"},
            ),
            "fast": TierConfig(
                description="low",
                providers={"cerebras": "llama-3.1-8b-instant"},
            ),
        },
        role_defaults={
            "orchestrator": "reasoning",
            "worker_a": "general",
            "worker_b": "general",
        },
        phase_overrides={},
        escalation_state={},
    )


@pytest.fixture
def mock_provider_manager():
    """Mock ProviderManager for testing."""
    manager = Mock()
    manager.available_providers = ["cerebras"]
    manager.get_model.return_value = Mock()
    return manager


@pytest.fixture
def mock_model_selector(model_tiers_config, mock_provider_manager):
    """Mock ModelSelector for testing."""
    selector = ModelSelector(model_tiers_config, mock_provider_manager)
    return selector


class TestOrchestratorModelSelectorInit:
    """Tests for orchestrator initialization with ModelSelector."""

    def test_accepts_model_selector_parameter(
        self, minimal_config_dict, mock_model_selector
    ):
        """Orchestrator should accept model_selector parameter."""
        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
        )
        assert orch.model_selector is mock_model_selector

    def test_accepts_escalation_tracker_parameter(
        self, minimal_config_dict, mock_model_selector, model_tiers_config, tmp_path
    ):
        """Orchestrator should accept escalation_tracker parameter."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("config: {}")
        tracker = EscalationTracker(config_path, model_tiers_config)

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
            escalation_tracker=tracker,
        )
        assert orch.escalation_tracker is tracker

    def test_backward_compat_without_model_selector(self, minimal_config_dict):
        """Orchestrator should work without model_selector for backward compat."""
        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
        )
        assert orch.model_selector is None

    def test_model_selector_none_by_default(self, minimal_config_dict):
        """model_selector should be None when not provided."""
        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
        )
        assert orch.model_selector is None
        assert orch.escalation_tracker is None

    def test_stores_config_path_for_escalation_tracker(self, tmp_path):
        """Config path should be stored for EscalationTracker creation."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
config:
  triads:
    - id: test_triad
      preset: hierarchical
      scope:
        primary: [layout]
        reach: [spacing]
      budget:
        tokens: 1000
        tool_calls: 10
        time_ms: 5000
      objectives: [test]
  sections: [layout, spacing]
  pressure:
    initial_temperature: 0.5
    temperature_decay: 0.1
    freeze_threshold: 0.9
  arbiter:
    model: test
    max_tokens: 100
    temperature: 0.5
  output:
    format: react
""")

        orch = HFSOrchestrator(
            config_path=str(config_path),
            llm_client=Mock(),
        )
        assert orch._config_path == config_path


class TestOrchestratorSpawnTriads:
    """Tests for _spawn_triads with ModelSelector."""

    @patch("hfs.core.orchestrator.create_agno_triad")
    def test_calls_create_agno_triad_when_model_selector_provided(
        self, mock_create_agno, minimal_config_dict, mock_model_selector
    ):
        """_spawn_triads should call create_agno_triad when model_selector exists."""
        mock_triad = Mock()
        mock_create_agno.return_value = mock_triad

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
        )
        orch._spawn_triads()

        mock_create_agno.assert_called_once()
        # Verify model_selector was passed
        call_args = mock_create_agno.call_args[0]
        assert call_args[1] is mock_model_selector  # Second positional arg

    @patch("hfs.core.orchestrator.create_triad")
    def test_calls_create_triad_when_no_model_selector(
        self, mock_create_triad, minimal_config_dict
    ):
        """_spawn_triads should call create_triad when no model_selector."""
        mock_triad = Mock()
        mock_create_triad.return_value = mock_triad

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
        )
        orch._spawn_triads()

        mock_create_triad.assert_called_once()

    @patch("hfs.core.orchestrator.create_agno_triad")
    def test_passes_spec_to_create_agno_triad(
        self, mock_create_agno, minimal_config_dict, mock_model_selector
    ):
        """create_agno_triad should receive the shared spec instance."""
        mock_create_agno.return_value = Mock()

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
        )
        orch._spawn_triads()

        # Verify spec was passed (third positional arg)
        call_args = mock_create_agno.call_args[0]
        assert call_args[2] is orch.spec

    @patch("hfs.core.orchestrator.create_agno_triad")
    def test_passes_escalation_tracker_to_create_agno_triad(
        self, mock_create_agno, minimal_config_dict, mock_model_selector,
        model_tiers_config, tmp_path
    ):
        """create_agno_triad should receive escalation_tracker if provided."""
        mock_create_agno.return_value = Mock()
        config_path = tmp_path / "config.yaml"
        config_path.write_text("config: {}")
        tracker = EscalationTracker(config_path, model_tiers_config)

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
            escalation_tracker=tracker,
        )
        orch._spawn_triads()

        # Verify escalation_tracker was passed as keyword arg
        call_kwargs = mock_create_agno.call_args[1]
        assert call_kwargs.get("escalation_tracker") is tracker

    @patch("hfs.core.orchestrator.create_agno_triad")
    def test_passes_none_escalation_tracker_when_not_provided(
        self, mock_create_agno, minimal_config_dict, mock_model_selector
    ):
        """create_agno_triad should receive None escalation_tracker when not provided."""
        mock_create_agno.return_value = Mock()

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
        )
        orch._spawn_triads()

        # Verify escalation_tracker is None
        call_kwargs = mock_create_agno.call_args[1]
        assert call_kwargs.get("escalation_tracker") is None


class TestOrchestratorBackwardCompatibility:
    """Tests ensuring backward compatibility is maintained."""

    def test_llm_client_still_stored(self, minimal_config_dict):
        """self.llm should still be stored for backward compat."""
        mock_llm = Mock()
        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=mock_llm,
        )
        assert orch.llm is mock_llm

    @patch("hfs.core.orchestrator.create_agno_triad")
    def test_triads_dict_populated_with_model_selector(
        self, mock_create_agno, minimal_config_dict, mock_model_selector
    ):
        """self.triads dict should be populated after _spawn_triads with model_selector."""
        mock_triad = Mock()
        mock_create_agno.return_value = mock_triad

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
            model_selector=mock_model_selector,
        )
        orch._spawn_triads()

        assert "test_triad" in orch.triads
        assert orch.triads["test_triad"] is mock_triad

    @patch("hfs.core.orchestrator.create_triad")
    def test_triads_dict_populated_without_model_selector(
        self, mock_create_triad, minimal_config_dict
    ):
        """self.triads dict should be populated after _spawn_triads without model_selector."""
        mock_triad = Mock()
        mock_create_triad.return_value = mock_triad

        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
        )
        orch._spawn_triads()

        assert "test_triad" in orch.triads
        assert orch.triads["test_triad"] is mock_triad


class TestOrchestratorCreateDefaultModelSelector:
    """Tests for _create_default_model_selector helper."""

    def test_creates_model_selector_from_model_tiers(self, tmp_path):
        """_create_default_model_selector should create ModelSelector from config."""
        config_dict = {
            "config": {
                "triads": [
                    {
                        "id": "test_triad",
                        "preset": "hierarchical",
                        "scope": {"primary": ["layout"], "reach": []},
                        "budget": {"tokens": 1000, "tool_calls": 10, "time_ms": 5000},
                        "objectives": ["test"],
                    }
                ],
                "sections": ["layout"],
                "pressure": {
                    "initial_temperature": 0.5,
                    "temperature_decay": 0.1,
                    "freeze_threshold": 0.9,
                },
                "arbiter": {"model": "test", "max_tokens": 100, "temperature": 0.5},
                "output": {"format": "react"},
                "model_tiers": {
                    "tiers": {
                        "reasoning": {
                            "description": "High capability",
                            "providers": {"cerebras": "llama-3.3-70b"},
                        },
                        "general": {
                            "description": "General purpose",
                            "providers": {"cerebras": "llama-3.1-8b-instant"},
                        },
                        "fast": {
                            "description": "Fast responses",
                            "providers": {"cerebras": "llama-3.1-8b-instant"},
                        },
                    },
                    "role_defaults": {
                        "orchestrator": "reasoning",
                        "worker_a": "general",
                    },
                },
            }
        }

        orch = HFSOrchestrator(
            config_dict=config_dict,
            llm_client=Mock(),
        )

        # Call helper directly
        with patch("hfs.core.orchestrator.ProviderManager") as mock_pm:
            mock_pm_instance = Mock()
            mock_pm_instance.available_providers = ["cerebras"]
            mock_pm.return_value = mock_pm_instance

            selector = orch._create_default_model_selector()

        assert isinstance(selector, ModelSelector)
        assert "reasoning" in selector.config.tiers
        assert "general" in selector.config.tiers
        assert "fast" in selector.config.tiers

    def test_raises_error_when_model_tiers_missing(self, minimal_config_dict):
        """_create_default_model_selector should raise when model_tiers missing."""
        orch = HFSOrchestrator(
            config_dict=minimal_config_dict,
            llm_client=Mock(),
        )

        with pytest.raises(ValueError, match="model_tiers section missing"):
            orch._create_default_model_selector()


class TestOrchestratorLazyInitialization:
    """Tests for lazy initialization of ModelSelector and EscalationTracker in run()."""

    def test_raw_config_stored_for_model_tiers_access(self):
        """_raw_config should be stored for model_tiers access."""
        config_dict = {
            "config": {
                "triads": [
                    {
                        "id": "test_triad",
                        "preset": "hierarchical",
                        "scope": {"primary": ["layout"], "reach": []},
                        "budget": {"tokens": 1000, "tool_calls": 10, "time_ms": 5000},
                        "objectives": ["test"],
                    }
                ],
                "sections": ["layout"],
                "pressure": {
                    "initial_temperature": 0.5,
                    "temperature_decay": 0.1,
                    "freeze_threshold": 0.9,
                },
                "arbiter": {"model": "test", "max_tokens": 100, "temperature": 0.5},
                "output": {"format": "react"},
                "model_tiers": {"tiers": {}, "role_defaults": {}},
            }
        }

        orch = HFSOrchestrator(
            config_dict=config_dict,
            llm_client=Mock(),
        )

        assert "model_tiers" in orch._raw_config
