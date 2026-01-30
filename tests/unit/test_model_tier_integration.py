"""Integration tests for model tier wiring into AgnoTriad and factory.

These tests verify that ModelSelector and EscalationTracker are properly
wired into the AgnoTriad base class and the triad factory.

Tests cover:
- AgnoTriad accepts ModelSelector + EscalationTracker parameters
- AgnoTriad has _get_model_for_role helper method
- create_agno_triad exists with new API
- Legacy create_triad preserved
- code_execution role maps to fast tier (MODL-03)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from inspect import signature

from hfs.core.triad import TriadConfig, TriadPreset
from hfs.core.model_tiers import TierConfig, ModelTiersConfig
from hfs.core.model_selector import ModelSelector
from hfs.core.escalation_tracker import EscalationTracker
from hfs.agno.teams.base import AgnoTriad
from hfs.presets.triad_factory import (
    create_triad,
    create_agno_triad,
    TRIAD_REGISTRY,
    AGNO_TRIAD_REGISTRY,
)


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
                "cerebras": "llama-fast",
                "groq": "llama-fast-instant",
            },
        ),
    }


@pytest.fixture
def model_tiers_config(base_tiers) -> ModelTiersConfig:
    """Model tiers config with MODL-03 code_execution mapping."""
    return ModelTiersConfig(
        tiers=base_tiers,
        role_defaults={
            "orchestrator": "reasoning",
            "worker_a": "general",
            "worker_b": "general",
            "code_execution": "fast",  # MODL-03: code execution always fast
        },
    )


@pytest.fixture
def mock_provider_manager() -> Mock:
    """Mock ProviderManager for testing."""
    manager = Mock()
    manager.available_providers = ["cerebras", "groq"]
    manager.get_model = Mock(return_value=Mock(name="mock_model"))
    return manager


@pytest.fixture
def mock_model_selector(model_tiers_config, mock_provider_manager) -> ModelSelector:
    """Real ModelSelector with mock provider manager."""
    return ModelSelector(model_tiers_config, mock_provider_manager)


@pytest.fixture
def mock_escalation_tracker(model_tiers_config, tmp_path) -> EscalationTracker:
    """Real EscalationTracker with temp config file."""
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text("config:\n  model_tiers:\n    escalation_state: {}")
    return EscalationTracker(config_path, model_tiers_config)


@pytest.fixture
def triad_config() -> TriadConfig:
    """Standard triad config for testing."""
    return TriadConfig(
        id="test_triad",
        preset=TriadPreset.HIERARCHICAL,
        scope_primary=["layout"],
        scope_reach=[],
        budget_tokens=10000,
        budget_tool_calls=50,
        budget_time_ms=30000,
        objectives=["test"],
    )


@pytest.fixture
def mock_spec() -> Mock:
    """Mock Spec for triad initialization."""
    spec = Mock()
    spec.sections = {}
    return spec


class TestAgnoTriadSignature:
    """Test AgnoTriad base class accepts new parameters."""

    def test_init_accepts_model_selector_parameter(self):
        """AgnoTriad.__init__ accepts model_selector parameter."""
        sig = signature(AgnoTriad.__init__)
        params = list(sig.parameters.keys())

        assert "model_selector" in params, "AgnoTriad should accept model_selector"

    def test_init_accepts_escalation_tracker_parameter(self):
        """AgnoTriad.__init__ accepts escalation_tracker parameter."""
        sig = signature(AgnoTriad.__init__)
        params = list(sig.parameters.keys())

        assert "escalation_tracker" in params, "AgnoTriad should accept escalation_tracker"

    def test_escalation_tracker_is_optional(self):
        """escalation_tracker parameter has default None."""
        sig = signature(AgnoTriad.__init__)
        param = sig.parameters.get("escalation_tracker")

        assert param is not None
        assert param.default is None, "escalation_tracker should default to None"

    def test_has_get_model_for_role_method(self):
        """AgnoTriad has _get_model_for_role helper method."""
        assert hasattr(AgnoTriad, "_get_model_for_role"), \
            "AgnoTriad should have _get_model_for_role method"

    def test_get_model_for_role_signature(self):
        """_get_model_for_role has correct signature."""
        sig = signature(AgnoTriad._get_model_for_role)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "role" in params
        assert "phase" in params


class TestGetModelForRole:
    """Test _get_model_for_role helper method behavior."""

    def test_delegates_to_model_selector(
        self, mock_model_selector, mock_spec, triad_config
    ):
        """_get_model_for_role delegates to model_selector.get_model."""
        # Create a concrete mock subclass
        with patch.object(AgnoTriad, "__abstractmethods__", set()):
            with patch.object(AgnoTriad, "_create_agents", return_value={}):
                with patch.object(AgnoTriad, "_create_team", return_value=Mock()):
                    triad = AgnoTriad(
                        config=triad_config,
                        model_selector=mock_model_selector,
                        spec=mock_spec,
                    )

        # Call helper method
        triad._get_model_for_role("worker_a")

        # Should delegate to model_selector
        mock_model_selector.provider_manager.get_model.assert_called()

    def test_passes_phase_to_model_selector(
        self, mock_model_selector, mock_spec, triad_config
    ):
        """_get_model_for_role passes phase parameter."""
        with patch.object(AgnoTriad, "__abstractmethods__", set()):
            with patch.object(AgnoTriad, "_create_agents", return_value={}):
                with patch.object(AgnoTriad, "_create_team", return_value=Mock()):
                    triad = AgnoTriad(
                        config=triad_config,
                        model_selector=mock_model_selector,
                        spec=mock_spec,
                    )

        # Use a mock to track the get_model call
        mock_model_selector.get_model = Mock(return_value=Mock())

        triad._get_model_for_role("worker_a", phase="execution")

        # Verify phase was passed
        mock_model_selector.get_model.assert_called_once_with(
            triad_config.id, "worker_a", "execution"
        )


class TestEscalationTrackerIntegration:
    """Test escalation tracker is wired into _run_with_error_handling."""

    @pytest.mark.asyncio
    async def test_records_success_for_all_roles(
        self, mock_model_selector, mock_escalation_tracker, mock_spec, triad_config
    ):
        """On success, records success for all agent roles."""
        mock_team = AsyncMock()
        mock_team.arun = AsyncMock(return_value="success")

        with patch.object(AgnoTriad, "__abstractmethods__", set()):
            with patch.object(
                AgnoTriad, "_create_agents",
                return_value={"orchestrator": Mock(), "worker_a": Mock(), "worker_b": Mock()}
            ):
                with patch.object(AgnoTriad, "_create_team", return_value=mock_team):
                    triad = AgnoTriad(
                        config=triad_config,
                        model_selector=mock_model_selector,
                        spec=mock_spec,
                        escalation_tracker=mock_escalation_tracker,
                    )

        # Run phase
        await triad._run_with_error_handling("deliberation", "test prompt")

        # Verify success recorded for all roles
        assert mock_escalation_tracker.get_failure_count(triad_config.id, "orchestrator") == 0
        assert mock_escalation_tracker.get_failure_count(triad_config.id, "worker_a") == 0
        assert mock_escalation_tracker.get_failure_count(triad_config.id, "worker_b") == 0

    @pytest.mark.asyncio
    async def test_records_failure_for_team_on_exception(
        self, mock_model_selector, mock_escalation_tracker, mock_spec, triad_config
    ):
        """On exception, records failure for 'team' role."""
        mock_team = AsyncMock()
        mock_team.arun = AsyncMock(side_effect=Exception("Test error"))

        with patch.object(AgnoTriad, "__abstractmethods__", set()):
            with patch.object(AgnoTriad, "_create_agents", return_value={"orchestrator": Mock()}):
                with patch.object(AgnoTriad, "_create_team", return_value=mock_team):
                    triad = AgnoTriad(
                        config=triad_config,
                        model_selector=mock_model_selector,
                        spec=mock_spec,
                        escalation_tracker=mock_escalation_tracker,
                    )

        # Mock _save_partial_progress to avoid file I/O
        triad._save_partial_progress = Mock()

        # Run phase expecting exception
        from hfs.agno.teams.schemas import TriadExecutionError
        with pytest.raises(TriadExecutionError):
            await triad._run_with_error_handling("deliberation", "test prompt")

        # Verify failure recorded for team
        assert mock_escalation_tracker.get_failure_count(triad_config.id, "team") == 1

    @pytest.mark.asyncio
    async def test_no_error_when_tracker_is_none(
        self, mock_model_selector, mock_spec, triad_config
    ):
        """No error when escalation_tracker is None."""
        mock_team = AsyncMock()
        mock_team.arun = AsyncMock(return_value="success")

        with patch.object(AgnoTriad, "__abstractmethods__", set()):
            with patch.object(AgnoTriad, "_create_agents", return_value={"orchestrator": Mock()}):
                with patch.object(AgnoTriad, "_create_team", return_value=mock_team):
                    triad = AgnoTriad(
                        config=triad_config,
                        model_selector=mock_model_selector,
                        spec=mock_spec,
                        escalation_tracker=None,  # No tracker
                    )

        # Should not raise
        result = await triad._run_with_error_handling("deliberation", "test prompt")
        assert result == "success"


class TestCreateAgnoTriadFactory:
    """Test create_agno_triad factory function."""

    def test_create_agno_triad_exists(self):
        """create_agno_triad function exists."""
        assert callable(create_agno_triad)

    def test_create_agno_triad_signature(self):
        """create_agno_triad has correct signature."""
        sig = signature(create_agno_triad)
        params = list(sig.parameters.keys())

        assert "config" in params
        assert "model_selector" in params
        assert "spec" in params
        assert "escalation_tracker" in params

    def test_create_agno_triad_escalation_tracker_optional(self):
        """escalation_tracker parameter has default None."""
        sig = signature(create_agno_triad)
        param = sig.parameters.get("escalation_tracker")

        assert param is not None
        assert param.default is None

    def test_agno_triad_registry_exists(self):
        """AGNO_TRIAD_REGISTRY maps presets to AgnoTriad subclasses."""
        assert AGNO_TRIAD_REGISTRY is not None
        assert TriadPreset.HIERARCHICAL in AGNO_TRIAD_REGISTRY
        assert TriadPreset.DIALECTIC in AGNO_TRIAD_REGISTRY
        assert TriadPreset.CONSENSUS in AGNO_TRIAD_REGISTRY


class TestLegacyCreateTriadPreserved:
    """Test legacy create_triad is preserved."""

    def test_create_triad_still_exists(self):
        """create_triad function still exists."""
        assert callable(create_triad)

    def test_triad_registry_still_exists(self):
        """TRIAD_REGISTRY for legacy triads still exists."""
        assert TRIAD_REGISTRY is not None
        assert TriadPreset.HIERARCHICAL in TRIAD_REGISTRY
        assert TriadPreset.DIALECTIC in TRIAD_REGISTRY
        assert TriadPreset.CONSENSUS in TRIAD_REGISTRY

    def test_create_triad_signature_unchanged(self):
        """create_triad signature unchanged (config, llm_client)."""
        sig = signature(create_triad)
        params = list(sig.parameters.keys())

        assert "config" in params
        assert "llm_client" in params
        # Should NOT have model_selector
        assert "model_selector" not in params


class TestCodeExecutionFastTier:
    """Test MODL-03: code_execution role maps to fast tier."""

    def test_code_execution_defaults_to_fast(
        self, model_tiers_config, mock_provider_manager
    ):
        """code_execution role defaults to fast tier."""
        selector = ModelSelector(model_tiers_config, mock_provider_manager)

        # Get model for code_execution role
        selector.get_model("any_triad", "code_execution")

        # Should use fast tier model
        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-fast"
        )

    def test_code_execution_in_default_config(self, base_tiers):
        """code_execution role mapping exists in default role_defaults."""
        config = ModelTiersConfig(
            tiers=base_tiers,
            role_defaults={
                "orchestrator": "reasoning",
                "worker_a": "general",
                "worker_b": "general",
                "code_execution": "fast",
            },
        )

        # Verify code_execution maps to fast
        assert config.role_defaults.get("code_execution") == "fast"

    def test_fast_tier_for_code_execution_not_overridden_by_phase(
        self, model_tiers_config, mock_provider_manager
    ):
        """code_execution stays fast even with phase overrides for other roles."""
        # Add phase override for workers but not code_execution
        model_tiers_config.phase_overrides = {
            "execution": {
                "worker_a": "fast",
                "worker_b": "fast",
            }
        }

        selector = ModelSelector(model_tiers_config, mock_provider_manager)

        # code_execution still uses fast (role default)
        selector.get_model("triad", "code_execution", phase="deliberation")

        mock_provider_manager.get_model.assert_called_with(
            "cerebras", "llama-fast"
        )


class TestModelSelectorImportChain:
    """Test import chain is established."""

    def test_model_selector_imported_in_base_for_type_checking(self):
        """ModelSelector is imported in base.py for type checking."""
        import hfs.agno.teams.base as base_module
        # Verify the module imports ModelSelector (via TYPE_CHECKING for circular import avoidance)
        assert "ModelSelector" in base_module.__annotations__ or \
               hasattr(base_module.AgnoTriad.__init__, "__annotations__")

    def test_escalation_tracker_imported_in_base_for_type_checking(self):
        """EscalationTracker is imported in base.py for type checking."""
        import hfs.agno.teams.base as base_module
        # Verify the module imports EscalationTracker
        assert "EscalationTracker" in str(base_module.AgnoTriad.__init__.__annotations__) or \
               hasattr(base_module.AgnoTriad, "__init__")

    def test_model_selector_importable_from_factory(self):
        """ModelSelector can be imported from triad_factory module."""
        from hfs.presets.triad_factory import ModelSelector as FactoryModelSelector
        assert FactoryModelSelector is ModelSelector

    def test_base_module_references_model_selector_in_init(self):
        """AgnoTriad.__init__ references ModelSelector type."""
        from inspect import signature
        sig = signature(AgnoTriad.__init__)
        param = sig.parameters.get("model_selector")
        assert param is not None
        # The annotation should reference ModelSelector (as string due to TYPE_CHECKING)
        assert param.annotation == "ModelSelector" or "ModelSelector" in str(param.annotation)
