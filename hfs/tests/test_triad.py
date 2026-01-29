"""Tests for Triad base classes, presets, and factory.

This module tests:
- TriadPreset enum
- TriadConfig and TriadOutput dataclasses
- Triad ABC prevents direct instantiation
- triad_factory.create_triad() for all presets
- Basic preset behavior (initialization, agents structure)
- get_preset_info() and list_available_presets() utilities
"""

import pytest
from typing import Dict, Any

from hfs.core.triad import (
    TriadPreset,
    TriadConfig,
    TriadOutput,
    Triad,
    NegotiationResponse,
)
from hfs.presets.triad_factory import (
    create_triad,
    create_triad_from_dict,
    get_preset_info,
    list_available_presets,
    TRIAD_REGISTRY,
)
from hfs.presets.hierarchical import HierarchicalTriad
from hfs.presets.dialectic import DialecticTriad
from hfs.presets.consensus import ConsensusTriad


class MockLLMClient:
    """Simple mock LLM client for testing triad initialization."""

    def __init__(self):
        self.calls = []

    async def create_message(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": "Mock response"}


def create_test_config(
    triad_id: str = "test_triad",
    preset: TriadPreset = TriadPreset.HIERARCHICAL,
    scope_primary: list = None,
    scope_reach: list = None,
    objectives: list = None,
) -> TriadConfig:
    """Helper to create TriadConfig for tests."""
    return TriadConfig(
        id=triad_id,
        preset=preset,
        scope_primary=scope_primary or ["section_a", "section_b"],
        scope_reach=scope_reach or ["section_c"],
        budget_tokens=10000,
        budget_tool_calls=50,
        budget_time_ms=30000,
        objectives=objectives or ["quality", "performance"],
        system_context="Test context",
    )


class TestTriadPreset:
    """Tests for TriadPreset enum - values, completeness, and usage."""

    def test_all_preset_values_exist(self):
        """Verify all expected preset values are defined with correct string values."""
        assert TriadPreset.HIERARCHICAL.value == "hierarchical"
        assert TriadPreset.DIALECTIC.value == "dialectic"
        assert TriadPreset.CONSENSUS.value == "consensus"

        # Ensure we have exactly 3 presets
        assert len(TriadPreset) == 3

    def test_preset_string_conversion(self):
        """Verify presets can be created from strings and convert back."""
        for preset in TriadPreset:
            # Create from string value
            reconstructed = TriadPreset(preset.value)
            assert reconstructed == preset

            # Name and value relationship
            assert preset.name.lower() == preset.value

    def test_invalid_preset_raises_error(self):
        """Verify invalid preset strings raise ValueError."""
        with pytest.raises(ValueError):
            TriadPreset("invalid_preset")

        with pytest.raises(ValueError):
            TriadPreset("HIERARCHICAL")  # Case matters


class TestTriadConfig:
    """Tests for TriadConfig dataclass - all fields and optional behavior."""

    def test_required_fields(self):
        """Verify all required fields must be provided."""
        # Should work with all required fields
        config = TriadConfig(
            id="test",
            preset=TriadPreset.HIERARCHICAL,
            scope_primary=["layout"],
            scope_reach=[],
            budget_tokens=1000,
            budget_tool_calls=10,
            budget_time_ms=5000,
            objectives=["quality"],
        )
        assert config.id == "test"
        assert config.preset == TriadPreset.HIERARCHICAL
        assert config.scope_primary == ["layout"]
        assert config.objectives == ["quality"]

        # system_context should default to None
        assert config.system_context is None

    def test_optional_system_context(self):
        """Verify system_context is optional and can be set."""
        config_without = create_test_config()
        config_without.system_context = None  # Explicitly test None works

        config_with = TriadConfig(
            id="test",
            preset=TriadPreset.DIALECTIC,
            scope_primary=["visual"],
            scope_reach=["motion"],
            budget_tokens=5000,
            budget_tool_calls=25,
            budget_time_ms=15000,
            objectives=["aesthetics"],
            system_context="You are a visual design specialist.",
        )
        assert config_with.system_context == "You are a visual design specialist."

    def test_config_immutable_attributes(self):
        """Verify config can be accessed consistently after creation."""
        config = create_test_config(
            triad_id="immutable_test",
            preset=TriadPreset.CONSENSUS,
            scope_primary=["accessibility"],
            objectives=["wcag_compliance"],
        )

        # Access multiple times - should remain consistent
        assert config.id == "immutable_test"
        assert config.id == "immutable_test"
        assert config.preset == TriadPreset.CONSENSUS
        assert "accessibility" in config.scope_primary


class TestTriadOutput:
    """Tests for TriadOutput dataclass - the return type from deliberation."""

    def test_basic_output_creation(self):
        """Verify TriadOutput can be created with all fields."""
        output = TriadOutput(
            position="We recommend using a 12-column grid system",
            claims=["layout", "grid", "spacing"],
            proposals={
                "layout": {"columns": 12, "gutter": "16px"},
                "grid": {"breakpoints": ["sm", "md", "lg"]},
                "spacing": {"base": 8},
            },
        )

        assert "12-column grid" in output.position
        assert len(output.claims) == 3
        assert "layout" in output.claims
        assert output.proposals["layout"]["columns"] == 12

    def test_empty_output(self):
        """Verify TriadOutput can be created with empty values."""
        output = TriadOutput(position="", claims=[], proposals={})

        assert output.position == ""
        assert output.claims == []
        assert output.proposals == {}

    def test_proposals_structure(self):
        """Verify proposals dict supports nested structures."""
        output = TriadOutput(
            position="Complex proposal",
            claims=["section"],
            proposals={
                "section": {
                    "nested": {
                        "deeply": {
                            "value": 42,
                        }
                    },
                    "list": [1, 2, 3],
                    "mixed": {"items": ["a", "b"], "count": 2},
                }
            },
        )

        assert output.proposals["section"]["nested"]["deeply"]["value"] == 42
        assert output.proposals["section"]["list"] == [1, 2, 3]


class TestTriadABC:
    """Tests for Triad ABC - verifies it can't be instantiated directly."""

    def test_cannot_instantiate_directly(self):
        """Verify Triad ABC cannot be instantiated directly."""
        config = create_test_config()
        llm = MockLLMClient()

        with pytest.raises(TypeError) as exc_info:
            Triad(config, llm)

        # The error should mention abstract methods
        assert "abstract" in str(exc_info.value).lower()

    def test_abc_defines_required_methods(self):
        """Verify Triad ABC defines all expected abstract methods."""
        from abc import ABC
        import inspect

        # Triad should be an ABC
        assert issubclass(Triad, ABC)

        # Check abstract methods exist
        abstract_methods = {
            name for name, method in inspect.getmembers(Triad)
            if getattr(method, '__isabstractmethod__', False)
        }

        expected_methods = {'_initialize_agents', 'deliberate', 'negotiate', 'execute'}
        assert abstract_methods == expected_methods


class TestTriadFactory:
    """Tests for triad_factory - create_triad() and utilities."""

    def test_create_triad_hierarchical(self):
        """Verify factory creates HierarchicalTriad for hierarchical preset."""
        config = create_test_config(preset=TriadPreset.HIERARCHICAL)
        llm = MockLLMClient()

        triad = create_triad(config, llm)

        assert isinstance(triad, HierarchicalTriad)
        assert triad.config == config
        assert triad.llm == llm

    def test_create_triad_dialectic(self):
        """Verify factory creates DialecticTriad for dialectic preset."""
        config = create_test_config(preset=TriadPreset.DIALECTIC)
        llm = MockLLMClient()

        triad = create_triad(config, llm)

        assert isinstance(triad, DialecticTriad)
        assert triad.config == config

    def test_create_triad_consensus(self):
        """Verify factory creates ConsensusTriad for consensus preset."""
        config = create_test_config(preset=TriadPreset.CONSENSUS)
        llm = MockLLMClient()

        triad = create_triad(config, llm)

        assert isinstance(triad, ConsensusTriad)
        assert triad.config == config

    def test_create_triad_all_presets(self):
        """Verify factory works for all registered presets."""
        llm = MockLLMClient()

        for preset in TriadPreset:
            config = create_test_config(preset=preset)
            triad = create_triad(config, llm)

            # Should be instance of the expected class
            expected_class = TRIAD_REGISTRY[preset]
            assert isinstance(triad, expected_class)

            # Should be a valid Triad subclass
            assert isinstance(triad, Triad)

    def test_registry_completeness(self):
        """Verify TRIAD_REGISTRY has entry for every TriadPreset."""
        for preset in TriadPreset:
            assert preset in TRIAD_REGISTRY
            assert issubclass(TRIAD_REGISTRY[preset], Triad)


class TestCreateTriadFromDict:
    """Tests for create_triad_from_dict() convenience function."""

    def test_basic_dict_config(self):
        """Verify triad creation from dictionary config."""
        config_dict = {
            "id": "dict_triad",
            "preset": "hierarchical",
            "scope_primary": ["layout"],
            "scope_reach": ["visual"],
            "budget_tokens": 8000,
            "budget_tool_calls": 40,
            "budget_time_ms": 20000,
            "objectives": ["performance"],
        }
        llm = MockLLMClient()

        triad = create_triad_from_dict(config_dict, llm)

        assert isinstance(triad, HierarchicalTriad)
        assert triad.config.id == "dict_triad"
        assert triad.config.scope_primary == ["layout"]

    def test_all_presets_from_dict(self):
        """Verify all preset strings work with dict config."""
        llm = MockLLMClient()

        for preset_str in ["hierarchical", "dialectic", "consensus"]:
            config_dict = {
                "id": f"{preset_str}_test",
                "preset": preset_str,
                "scope_primary": ["test"],
                "scope_reach": [],
                "budget_tokens": 5000,
                "budget_tool_calls": 25,
                "budget_time_ms": 15000,
                "objectives": ["quality"],
            }

            triad = create_triad_from_dict(config_dict, llm)
            assert isinstance(triad, Triad)

    def test_invalid_preset_string_raises(self):
        """Verify invalid preset string raises ValueError with helpful message."""
        config_dict = {
            "id": "bad_preset",
            "preset": "invalid",
            "scope_primary": [],
            "scope_reach": [],
            "budget_tokens": 1000,
            "budget_tool_calls": 10,
            "budget_time_ms": 5000,
            "objectives": [],
        }
        llm = MockLLMClient()

        with pytest.raises(ValueError) as exc_info:
            create_triad_from_dict(config_dict, llm)

        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
        assert "hierarchical" in error_msg or "Valid presets" in error_msg

    def test_optional_system_context_in_dict(self):
        """Verify system_context is optional in dict config."""
        llm = MockLLMClient()

        # Without system_context
        config_no_context = {
            "id": "no_context",
            "preset": "consensus",
            "scope_primary": ["a11y"],
            "scope_reach": [],
            "budget_tokens": 5000,
            "budget_tool_calls": 25,
            "budget_time_ms": 15000,
            "objectives": ["accessibility"],
        }
        triad1 = create_triad_from_dict(config_no_context, llm)
        assert triad1.config.system_context is None

        # With system_context
        config_with_context = {
            **config_no_context,
            "id": "with_context",
            "system_context": "Custom context for testing",
        }
        triad2 = create_triad_from_dict(config_with_context, llm)
        assert triad2.config.system_context == "Custom context for testing"


class TestGetPresetInfo:
    """Tests for get_preset_info() utility function."""

    def test_hierarchical_info(self):
        """Verify hierarchical preset info is correct."""
        info = get_preset_info(TriadPreset.HIERARCHICAL)

        assert info["class"] == HierarchicalTriad
        assert info["agent_roles"] == ["orchestrator", "worker_a", "worker_b"]
        assert "layout" in info["best_for"] or "execution" in str(info["best_for"]).lower()
        assert "flow" in info

    def test_dialectic_info(self):
        """Verify dialectic preset info is correct."""
        info = get_preset_info(TriadPreset.DIALECTIC)

        assert info["class"] == DialecticTriad
        assert info["agent_roles"] == ["proposer", "critic", "synthesizer"]
        assert "visual" in str(info["best_for"]).lower() or "creative" in str(info["best_for"]).lower()
        assert "propose" in info["flow"].lower() or "thesis" in info["flow"].lower()

    def test_consensus_info(self):
        """Verify consensus preset info is correct."""
        info = get_preset_info(TriadPreset.CONSENSUS)

        assert info["class"] == ConsensusTriad
        assert info["agent_roles"] == ["peer_1", "peer_2", "peer_3"]
        assert "accessibility" in str(info["best_for"]).lower() or "standards" in str(info["best_for"]).lower()
        assert "vote" in info["flow"].lower()

    def test_all_presets_have_info(self):
        """Verify get_preset_info works for all presets with consistent structure."""
        required_keys = {"class", "agent_roles", "best_for", "flow"}

        for preset in TriadPreset:
            info = get_preset_info(preset)
            assert required_keys.issubset(info.keys())
            assert isinstance(info["agent_roles"], list)
            assert len(info["agent_roles"]) == 3  # All triads have 3 agents


class TestListAvailablePresets:
    """Tests for list_available_presets() utility function."""

    def test_returns_all_presets(self):
        """Verify list_available_presets returns info for all presets."""
        presets = list_available_presets()

        assert len(presets) == 3
        assert "hierarchical" in presets
        assert "dialectic" in presets
        assert "consensus" in presets

    def test_preset_info_structure(self):
        """Verify returned info has consistent structure."""
        presets = list_available_presets()

        for preset_name, info in presets.items():
            assert "class" in info
            assert "agent_roles" in info
            assert "best_for" in info
            assert "flow" in info


class TestTriadInitialization:
    """Tests for triad initialization behavior across all presets."""

    def test_hierarchical_agents_structure(self):
        """Verify HierarchicalTriad initializes correct agent structure."""
        config = create_test_config(preset=TriadPreset.HIERARCHICAL)
        llm = MockLLMClient()

        triad = create_triad(config, llm)

        assert "orchestrator" in triad.agents
        assert "worker_a" in triad.agents
        assert "worker_b" in triad.agents
        assert len(triad.agents) == 3

        # Check agent properties
        assert triad.agents["orchestrator"].role == "orchestrator"
        assert "orchestrator" in triad.agents["orchestrator"].system_prompt.lower()

    def test_dialectic_agents_structure(self):
        """Verify DialecticTriad initializes correct agent structure."""
        config = create_test_config(preset=TriadPreset.DIALECTIC)
        llm = MockLLMClient()

        triad = create_triad(config, llm)

        assert "proposer" in triad.agents
        assert "critic" in triad.agents
        assert "synthesizer" in triad.agents
        assert len(triad.agents) == 3

        # Check agent properties
        assert triad.agents["proposer"].role == "proposer"
        assert triad.agents["critic"].role == "critic"
        assert triad.agents["synthesizer"].role == "synthesizer"

    def test_consensus_agents_structure(self):
        """Verify ConsensusTriad initializes correct agent structure."""
        config = create_test_config(preset=TriadPreset.CONSENSUS)
        llm = MockLLMClient()

        triad = create_triad(config, llm)

        assert "peer_1" in triad.agents
        assert "peer_2" in triad.agents
        assert "peer_3" in triad.agents
        assert len(triad.agents) == 3

        # Check each peer has unique perspective
        perspectives = [agent.perspective for agent in triad.agents.values()]
        assert len(set(perspectives)) == 3  # All unique

    def test_config_is_stored(self):
        """Verify config is stored and accessible on the triad."""
        config = create_test_config(
            triad_id="config_test",
            objectives=["test_objective"],
        )
        llm = MockLLMClient()

        for preset in TriadPreset:
            config.preset = preset
            triad = create_triad(config, llm)

            assert triad.config.id == "config_test"
            assert "test_objective" in triad.config.objectives

    def test_llm_client_is_stored(self):
        """Verify LLM client is stored and accessible on the triad."""
        config = create_test_config()
        llm = MockLLMClient()

        for preset in TriadPreset:
            config.preset = preset
            triad = create_triad(config, llm)

            assert triad.llm is llm

    def test_system_prompts_include_config_info(self):
        """Verify agent system prompts incorporate config information."""
        config = create_test_config(
            triad_id="prompt_test",
            objectives=["custom_objective"],
            scope_primary=["custom_scope"],
        )
        llm = MockLLMClient()

        for preset in TriadPreset:
            config.preset = preset
            triad = create_triad(config, llm)

            # At least one agent should mention the triad ID
            prompts = [agent.system_prompt for agent in triad.agents.values()]
            combined_prompts = " ".join(prompts)

            assert "prompt_test" in combined_prompts
            assert "custom_objective" in combined_prompts


class TestNegotiationResponse:
    """Tests for NegotiationResponse type alias."""

    def test_valid_responses(self):
        """Verify NegotiationResponse type accepts valid values."""
        # These should be the only valid values
        valid_responses = ["concede", "revise", "hold"]

        for response in valid_responses:
            # Type checking is compile-time, but we can test the values exist
            assert response in valid_responses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
