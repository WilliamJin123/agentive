"""Unit tests for AgnoTriad subclass ModelSelector integration.

Tests that HierarchicalAgnoTriad, DialecticAgnoTriad, and ConsensusAgnoTriad
properly integrate with ModelSelector via _get_model_for_role().
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, create_autospec

from agno.models.base import Model

from hfs.core.triad import TriadConfig, TriadPreset
from hfs.core.model_tiers import TierConfig, ModelTiersConfig
from hfs.core.model_selector import ModelSelector
from hfs.core.escalation_tracker import EscalationTracker
from hfs.presets.triad_factory import create_agno_triad, AGNO_TRIAD_REGISTRY
from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad
from hfs.agno.teams.dialectic import DialecticAgnoTriad
from hfs.agno.teams.consensus import ConsensusAgnoTriad


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


def create_mock_model(provider: str, model_id: str) -> Mock:
    """Create a mock that passes Agno's Model type check."""
    mock = create_autospec(Model, instance=True)
    mock.id = f"{provider}:{model_id}"
    mock.provider = provider
    mock.model_id = model_id
    return mock


@pytest.fixture
def mock_provider_manager() -> Mock:
    """Mock ProviderManager that returns mock models."""
    manager = Mock()
    manager.available_providers = ["cerebras", "groq"]

    # Track model calls to verify role-specific models
    def get_model(provider, model_id):
        return create_mock_model(provider, model_id)

    manager.get_model = Mock(side_effect=get_model)
    return manager


@pytest.fixture
def mock_model_selector(base_tiers, mock_provider_manager) -> ModelSelector:
    """ModelSelector with mock provider manager."""
    config = ModelTiersConfig(
        tiers=base_tiers,
        role_defaults={
            # Hierarchical roles
            "orchestrator": "reasoning",
            "worker_a": "general",
            "worker_b": "general",
            # Dialectic roles
            "proposer": "general",
            "critic": "general",
            "synthesizer": "reasoning",
            # Consensus roles
            "peer_1": "general",
            "peer_2": "general",
            "peer_3": "general",
        },
    )
    return ModelSelector(config, mock_provider_manager)


@pytest.fixture
def hierarchical_config() -> TriadConfig:
    """Test config for hierarchical triad."""
    return TriadConfig(
        id="test_hierarchical",
        preset=TriadPreset.HIERARCHICAL,
        scope_primary=["layout", "grid"],
        scope_reach=["spacing"],
        budget_tokens=10000,
        budget_tool_calls=50,
        budget_time_ms=30000,
        objectives=["performance", "responsiveness"],
    )


@pytest.fixture
def dialectic_config() -> TriadConfig:
    """Test config for dialectic triad."""
    return TriadConfig(
        id="test_dialectic",
        preset=TriadPreset.DIALECTIC,
        scope_primary=["colors", "typography"],
        scope_reach=["spacing"],
        budget_tokens=10000,
        budget_tool_calls=50,
        budget_time_ms=30000,
        objectives=["aesthetic_quality", "brand_consistency"],
    )


@pytest.fixture
def consensus_config() -> TriadConfig:
    """Test config for consensus triad."""
    return TriadConfig(
        id="test_consensus",
        preset=TriadPreset.CONSENSUS,
        scope_primary=["accessibility", "standards"],
        scope_reach=["compliance"],
        budget_tokens=10000,
        budget_tool_calls=50,
        budget_time_ms=30000,
        objectives=["accessibility", "standards_compliance"],
    )


@pytest.fixture
def mock_spec() -> Mock:
    """Mock Spec for triad initialization."""
    spec = Mock()
    spec.sections = {}
    return spec


class TestHierarchicalAgnoTriadModelSelector:
    """Tests for HierarchicalAgnoTriad ModelSelector integration."""

    def test_init_accepts_model_selector(
        self, hierarchical_config, mock_model_selector, mock_spec
    ):
        """HierarchicalAgnoTriad accepts model_selector parameter."""
        triad = HierarchicalAgnoTriad(
            config=hierarchical_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )
        assert triad.model_selector is mock_model_selector

    def test_init_accepts_escalation_tracker(
        self, hierarchical_config, mock_model_selector, mock_spec
    ):
        """HierarchicalAgnoTriad accepts escalation_tracker parameter."""
        tracker = Mock(spec=EscalationTracker)
        triad = HierarchicalAgnoTriad(
            config=hierarchical_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
            escalation_tracker=tracker,
        )
        assert triad.escalation_tracker is tracker

    def test_creates_agents_with_role_specific_models(
        self, hierarchical_config, mock_model_selector, mock_spec, mock_provider_manager
    ):
        """HierarchicalAgnoTriad creates agents with role-specific models."""
        triad = HierarchicalAgnoTriad(
            config=hierarchical_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )

        # Should have called get_model for orchestrator, worker_a, worker_b, and team
        # (team also uses orchestrator's model, but still calls _get_model_for_role)
        assert mock_provider_manager.get_model.call_count >= 4

        # Verify agents exist
        assert "orchestrator" in triad.agents
        assert "worker_a" in triad.agents
        assert "worker_b" in triad.agents

    def test_orchestrator_gets_reasoning_tier(
        self, hierarchical_config, mock_model_selector, mock_spec, mock_provider_manager
    ):
        """Orchestrator gets model from 'reasoning' tier per role_defaults."""
        triad = HierarchicalAgnoTriad(
            config=hierarchical_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )

        # Check that reasoning tier model was requested
        calls = mock_provider_manager.get_model.call_args_list
        reasoning_calls = [c for c in calls if c[0][1] == "llama-3.3-70b"]
        assert len(reasoning_calls) >= 1, "Orchestrator should use reasoning tier"


class TestDialecticAgnoTriadModelSelector:
    """Tests for DialecticAgnoTriad ModelSelector integration."""

    def test_init_accepts_model_selector(
        self, dialectic_config, mock_model_selector, mock_spec
    ):
        """DialecticAgnoTriad accepts model_selector parameter."""
        triad = DialecticAgnoTriad(
            config=dialectic_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )
        assert triad.model_selector is mock_model_selector

    def test_init_accepts_escalation_tracker(
        self, dialectic_config, mock_model_selector, mock_spec
    ):
        """DialecticAgnoTriad accepts escalation_tracker parameter."""
        tracker = Mock(spec=EscalationTracker)
        triad = DialecticAgnoTriad(
            config=dialectic_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
            escalation_tracker=tracker,
        )
        assert triad.escalation_tracker is tracker

    def test_creates_agents_with_role_specific_models(
        self, dialectic_config, mock_model_selector, mock_spec, mock_provider_manager
    ):
        """DialecticAgnoTriad creates agents with role-specific models."""
        triad = DialecticAgnoTriad(
            config=dialectic_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )

        # Should have called get_model for proposer, critic, synthesizer, and team
        assert mock_provider_manager.get_model.call_count >= 4

        # Verify agents exist
        assert "proposer" in triad.agents
        assert "critic" in triad.agents
        assert "synthesizer" in triad.agents

    def test_synthesizer_gets_reasoning_tier(
        self, dialectic_config, mock_model_selector, mock_spec, mock_provider_manager
    ):
        """Synthesizer gets model from 'reasoning' tier per role_defaults."""
        triad = DialecticAgnoTriad(
            config=dialectic_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )

        # Check that reasoning tier model was requested for synthesizer
        calls = mock_provider_manager.get_model.call_args_list
        reasoning_calls = [c for c in calls if c[0][1] == "llama-3.3-70b"]
        assert len(reasoning_calls) >= 1, "Synthesizer should use reasoning tier"


class TestConsensusAgnoTriadModelSelector:
    """Tests for ConsensusAgnoTriad ModelSelector integration."""

    def test_init_accepts_model_selector(
        self, consensus_config, mock_model_selector, mock_spec
    ):
        """ConsensusAgnoTriad accepts model_selector parameter."""
        triad = ConsensusAgnoTriad(
            config=consensus_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )
        assert triad.model_selector is mock_model_selector

    def test_init_accepts_escalation_tracker(
        self, consensus_config, mock_model_selector, mock_spec
    ):
        """ConsensusAgnoTriad accepts escalation_tracker parameter."""
        tracker = Mock(spec=EscalationTracker)
        triad = ConsensusAgnoTriad(
            config=consensus_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
            escalation_tracker=tracker,
        )
        assert triad.escalation_tracker is tracker

    def test_creates_agents_with_role_specific_models(
        self, consensus_config, mock_model_selector, mock_spec, mock_provider_manager
    ):
        """ConsensusAgnoTriad creates agents with role-specific models."""
        triad = ConsensusAgnoTriad(
            config=consensus_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )

        # Should have called get_model for peer_1, peer_2, peer_3, and team
        assert mock_provider_manager.get_model.call_count >= 4

        # Verify agents exist
        assert "peer_1" in triad.agents
        assert "peer_2" in triad.agents
        assert "peer_3" in triad.agents

    def test_all_peers_get_general_tier(
        self, consensus_config, mock_model_selector, mock_spec, mock_provider_manager
    ):
        """All consensus peers get model from 'general' tier per role_defaults."""
        triad = ConsensusAgnoTriad(
            config=consensus_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )

        # Check that general tier model was requested for all peers
        calls = mock_provider_manager.get_model.call_args_list
        general_calls = [c for c in calls if c[0][1] == "llama-3.1-8b"]
        assert len(general_calls) >= 4, "All peers + team should use general tier"


class TestCreateAgnoTriadFactory:
    """Tests for create_agno_triad factory function."""

    def test_factory_creates_hierarchical_triad(
        self, hierarchical_config, mock_model_selector, mock_spec
    ):
        """create_agno_triad creates HierarchicalAgnoTriad for HIERARCHICAL preset."""
        triad = create_agno_triad(
            config=hierarchical_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )
        assert isinstance(triad, HierarchicalAgnoTriad)

    def test_factory_creates_dialectic_triad(
        self, dialectic_config, mock_model_selector, mock_spec
    ):
        """create_agno_triad creates DialecticAgnoTriad for DIALECTIC preset."""
        triad = create_agno_triad(
            config=dialectic_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )
        assert isinstance(triad, DialecticAgnoTriad)

    def test_factory_creates_consensus_triad(
        self, consensus_config, mock_model_selector, mock_spec
    ):
        """create_agno_triad creates ConsensusAgnoTriad for CONSENSUS preset."""
        triad = create_agno_triad(
            config=consensus_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
        )
        assert isinstance(triad, ConsensusAgnoTriad)

    def test_factory_passes_escalation_tracker(
        self, hierarchical_config, mock_model_selector, mock_spec
    ):
        """create_agno_triad passes escalation_tracker to subclass."""
        tracker = Mock(spec=EscalationTracker)
        triad = create_agno_triad(
            config=hierarchical_config,
            model_selector=mock_model_selector,
            spec=mock_spec,
            escalation_tracker=tracker,
        )
        assert triad.escalation_tracker is tracker

    def test_factory_raises_for_unknown_preset(
        self, mock_model_selector, mock_spec
    ):
        """create_agno_triad raises ValueError for unknown preset."""
        # Create config with invalid preset by mocking
        config = Mock()
        config.preset = "invalid_preset"

        with pytest.raises(ValueError, match="Unknown triad preset"):
            create_agno_triad(
                config=config,
                model_selector=mock_model_selector,
                spec=mock_spec,
            )


class TestAgnoTriadRegistryCompleteness:
    """Tests for AGNO_TRIAD_REGISTRY completeness."""

    def test_registry_has_all_presets(self):
        """AGNO_TRIAD_REGISTRY contains all TriadPreset values."""
        for preset in TriadPreset:
            assert preset in AGNO_TRIAD_REGISTRY, f"Missing preset: {preset}"

    def test_registry_maps_to_correct_classes(self):
        """AGNO_TRIAD_REGISTRY maps to correct AgnoTriad subclasses."""
        assert AGNO_TRIAD_REGISTRY[TriadPreset.HIERARCHICAL] == HierarchicalAgnoTriad
        assert AGNO_TRIAD_REGISTRY[TriadPreset.DIALECTIC] == DialecticAgnoTriad
        assert AGNO_TRIAD_REGISTRY[TriadPreset.CONSENSUS] == ConsensusAgnoTriad
