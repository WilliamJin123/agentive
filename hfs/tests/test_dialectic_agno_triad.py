"""Unit tests for DialecticAgnoTriad.

Tests the dialectic triad implementation with mocked models.
No actual API calls - validates structure, tools, and prompts.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from agno.models.base import Model

from hfs.agno.teams import DialecticAgnoTriad, AgnoTriad
from hfs.agno.teams.schemas import PhaseSummary, TriadSessionState
from hfs.core.triad import TriadConfig, TriadPreset


class MockAgnoModel(Model):
    """Mock Agno Model that passes Agno's type validation.

    Inherits from agno.models.base.Model to pass isinstance checks
    but doesn't make actual API calls.
    """

    id: str = "mock-model"

    def invoke(self, *args, **kwargs):
        """Mock invoke - returns empty response."""
        return Mock(content="Mock response")

    async def ainvoke(self, *args, **kwargs):
        """Mock async invoke - returns empty response."""
        return Mock(content="Mock response")

    def invoke_stream(self, *args, **kwargs):
        """Mock stream invoke - yields empty response."""
        yield Mock(content="Mock response")

    async def ainvoke_stream(self, *args, **kwargs):
        """Mock async stream invoke - yields empty response."""
        yield Mock(content="Mock response")

    def _parse_provider_response(self, response):
        """Mock parse provider response."""
        return Mock(content="Mock response")

    def _parse_provider_response_delta(self, response):
        """Mock parse provider response delta."""
        return Mock(content="Mock response")


@pytest.fixture
def mock_model():
    """Create a mock ModelSelector that returns MockAgnoModel instances."""
    model_selector = Mock()
    model_selector.get_model.return_value = MockAgnoModel(id="mock-model")
    return model_selector


@pytest.fixture
def mock_spec():
    """Create a mock Spec with sections."""
    spec = Mock()
    spec.sections = {
        "visual_design": Mock(status=Mock(value="unclaimed"), claims=set(), proposals={}, owner=None),
        "motion_design": Mock(status=Mock(value="unclaimed"), claims=set(), proposals={}, owner=None),
        "typography": Mock(status=Mock(value="unclaimed"), claims=set(), proposals={}, owner=None),
    }
    spec.temperature = 1.0
    spec.round = 0
    spec.get_unclaimed_sections.return_value = ["visual_design", "motion_design", "typography"]
    spec.get_claimed_sections.return_value = []
    spec.get_contested_sections.return_value = []
    spec.get_frozen_sections.return_value = []
    return spec


@pytest.fixture
def dialectic_config():
    """Create a TriadConfig for dialectic preset."""
    return TriadConfig(
        id="test_dialectic",
        preset=TriadPreset.DIALECTIC,
        scope_primary=["visual_design"],
        scope_reach=["motion_design"],
        budget_tokens=1000,
        budget_tool_calls=10,
        budget_time_ms=30000,
        objectives=["aesthetic_quality", "consistency"],
    )


class TestDialecticAgnoTriadCreation:
    """Tests for DialecticAgnoTriad initialization and agent creation."""

    def test_dialectic_extends_agno_triad(self):
        """Verify DialecticAgnoTriad extends AgnoTriad base class."""
        assert issubclass(DialecticAgnoTriad, AgnoTriad)

    def test_dialectic_creates_three_agents(self, mock_model, mock_spec, dialectic_config):
        """Verify _create_agents returns proposer, critic, synthesizer."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        agents = triad.agents
        assert len(agents) == 3
        assert "proposer" in agents
        assert "critic" in agents
        assert "synthesizer" in agents

    def test_agent_names_include_triad_id(self, mock_model, mock_spec, dialectic_config):
        """Verify agent names include the triad ID for identification."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        assert triad.agents["proposer"].name == "proposer_test_dialectic"
        assert triad.agents["critic"].name == "critic_test_dialectic"
        assert triad.agents["synthesizer"].name == "synthesizer_test_dialectic"

    def test_agent_roles_are_correct(self, mock_model, mock_spec, dialectic_config):
        """Verify agents have correct role descriptions."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        assert "thesis" in triad.agents["proposer"].role.lower()
        assert "antithesis" in triad.agents["critic"].role.lower()
        assert "synthesis" in triad.agents["synthesizer"].role.lower()


class TestDialecticAgentTools:
    """Tests for agent tool assignments."""

    def test_proposer_can_register_claims(self, mock_model, mock_spec, dialectic_config):
        """Verify proposer has register_claim tool."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)
        proposer = triad.agents["proposer"]

        tool_names = [t.__name__ for t in proposer.tools]
        assert "register_claim" in tool_names
        assert "get_current_claims" in tool_names

    def test_critic_has_readonly_tools(self, mock_model, mock_spec, dialectic_config):
        """Verify critic only has get_negotiation_state, get_current_claims."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)
        critic = triad.agents["critic"]

        tool_names = [t.__name__ for t in critic.tools]
        assert "get_negotiation_state" in tool_names
        assert "get_current_claims" in tool_names
        # Critic should NOT have write tools
        assert "register_claim" not in tool_names
        assert "negotiate_response" not in tool_names
        assert "generate_code" not in tool_names

    def test_synthesizer_has_full_toolkit(self, mock_model, mock_spec, dialectic_config):
        """Verify synthesizer has full HFSToolkit access."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)
        synthesizer = triad.agents["synthesizer"]

        tool_names = [t.__name__ for t in synthesizer.tools]
        # Synthesizer should have all tools
        assert "register_claim" in tool_names
        assert "negotiate_response" in tool_names
        assert "generate_code" in tool_names
        assert "get_current_claims" in tool_names
        assert "get_negotiation_state" in tool_names


class TestDialecticTeamConfiguration:
    """Tests for Team configuration."""

    def test_team_not_broadcast(self, mock_model, mock_spec, dialectic_config):
        """Verify delegate_to_all_members=False for explicit flow."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        # delegate_to_all_members should be False for explicit thesis->antithesis->synthesis flow
        assert triad.team.delegate_to_all_members == False

    def test_team_shares_interactions(self, mock_model, mock_spec, dialectic_config):
        """Verify share_member_interactions=True so all see prior contributions."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        assert triad.team.share_member_interactions == True

    def test_team_has_session_state(self, mock_model, mock_spec, dialectic_config):
        """Verify team has session state for phase context."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        assert triad.team.add_session_state_to_context == True
        assert triad.team.session_state is not None


class TestPhaseSummaryPrompt:
    """Tests for phase summary prompt generation."""

    def test_phase_summary_prompt_structure(self, mock_model, mock_spec, dialectic_config):
        """Verify _get_phase_summary_prompt includes required sections."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        prompt = triad._get_phase_summary_prompt("deliberation")

        assert "Decisions Made" in prompt
        assert "Open Questions" in prompt
        assert "Artifacts" in prompt
        assert "deliberation" in prompt
        assert "PHASE_SUMMARY_START" in prompt
        assert "PHASE_SUMMARY_END" in prompt

    def test_phase_summary_prompt_for_each_phase(self, mock_model, mock_spec, dialectic_config):
        """Verify prompt works for all three phases."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        for phase in ["deliberation", "negotiation", "execution"]:
            prompt = triad._get_phase_summary_prompt(phase)
            assert phase in prompt


class TestSessionState:
    """Tests for session state and summary storage."""

    def test_session_state_stores_summaries(self, mock_model, mock_spec, dialectic_config):
        """Verify session state has fields for each phase's summary."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        state = triad._session_state
        assert hasattr(state, "deliberation_summary")
        assert hasattr(state, "negotiation_summary")
        assert hasattr(state, "execution_summary")

    def test_extract_phase_summary_parses_response(self, mock_model, mock_spec, dialectic_config):
        """Test _extract_phase_summary correctly parses structured output."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        response = """
        Here is my analysis...

        PHASE_SUMMARY_START
        Phase: deliberation
        Decisions:
        - Chose color palette A for consistency
        - Using grid-based layout
        Open Questions:
        - Should we use animation for transitions?
        Artifacts:
        - color_spec: RGB values for primary colors
        - layout_grid: 12-column grid definition
        PHASE_SUMMARY_END

        Additional discussion...
        """

        summary = triad._extract_phase_summary(response, "deliberation")

        assert summary is not None
        assert summary.phase == "deliberation"
        assert len(summary.decisions) == 2
        assert "Chose color palette A" in summary.decisions[0]
        assert len(summary.open_questions) == 1
        assert len(summary.artifacts) == 2
        assert summary.produced_by == "synthesizer"

    def test_extract_phase_summary_stores_in_session(self, mock_model, mock_spec, dialectic_config):
        """Verify extracted summary is stored in session state."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        response = """
        PHASE_SUMMARY_START
        Phase: deliberation
        Decisions:
        - Decision 1
        Open Questions:
        - Question 1
        Artifacts:
        - artifact: description
        PHASE_SUMMARY_END
        """

        triad._extract_phase_summary(response, "deliberation")

        assert triad._session_state.deliberation_summary is not None
        assert triad._session_state.deliberation_summary.phase == "deliberation"

    def test_extract_phase_summary_returns_none_if_not_found(self, mock_model, mock_spec, dialectic_config):
        """Verify None returned if summary block not in response."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        response = "Just regular output without summary markers"
        summary = triad._extract_phase_summary(response, "deliberation")

        assert summary is None


class TestDialecticPrompts:
    """Tests for prompt builders."""

    def test_deliberation_prompt_dialectic_flow(self, mock_model, mock_spec, dialectic_config):
        """Verify prompt mentions thesis->antithesis->synthesis."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        prompt = triad._build_deliberation_prompt(
            user_request="Create a modern dashboard",
            spec_state={"sections": {}}
        )

        assert "THESIS" in prompt
        assert "ANTITHESIS" in prompt
        assert "SYNTHESIS" in prompt
        assert "Proposer" in prompt
        assert "Critic" in prompt
        assert "Synthesizer" in prompt

    def test_negotiation_prompt_includes_options(self, mock_model, mock_spec, dialectic_config):
        """Verify negotiation prompt includes concede/revise/hold options."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        prompt = triad._build_negotiation_prompt(
            section="visual_design",
            other_proposals={"triad_2": "Their proposal for visual design"}
        )

        assert "concede" in prompt.lower()
        assert "revise" in prompt.lower()
        assert "hold" in prompt.lower()
        assert "visual_design" in prompt

    def test_execution_prompt_identifies_owned_sections(self, mock_model, mock_spec, dialectic_config):
        """Verify execution prompt includes owned sections."""
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        frozen_spec = {
            "sections": {
                "visual_design": {
                    "owner": "test_dialectic",
                    "proposals": {"test_dialectic": "Our proposal"}
                },
                "typography": {
                    "owner": "other_triad",
                    "proposals": {"other_triad": "Their proposal"}
                }
            }
        }

        prompt = triad._build_execution_prompt(frozen_spec)

        assert "visual_design" in prompt
        # Should not include sections we don't own
        assert "typography" not in prompt or "other_triad" in prompt


class TestFixedRoles:
    """Tests for fixed role behavior."""

    def test_fixed_roles_not_rotating(self, mock_model, mock_spec, dialectic_config):
        """Verify agent roles don't change between phases.

        Per CONTEXT.md: Fixed roles - proposer/critic/synthesizer don't rotate.
        The same agents handle all phases with the same roles.
        """
        triad = DialecticAgnoTriad(dialectic_config, mock_model, mock_spec)

        # Get initial agents
        initial_proposer = triad.agents["proposer"]
        initial_critic = triad.agents["critic"]
        initial_synthesizer = triad.agents["synthesizer"]

        # Simulate building prompts for different phases (doesn't change agents)
        triad._build_deliberation_prompt("request", {})
        triad._build_negotiation_prompt("section", {})
        triad._build_execution_prompt({"sections": {}})

        # Agents should be the same objects
        assert triad.agents["proposer"] is initial_proposer
        assert triad.agents["critic"] is initial_critic
        assert triad.agents["synthesizer"] is initial_synthesizer

        # Roles should be unchanged
        assert "thesis" in triad.agents["proposer"].role.lower()
        assert "antithesis" in triad.agents["critic"].role.lower()
        assert "synthesis" in triad.agents["synthesizer"].role.lower()


class TestDialecticExports:
    """Tests for package exports."""

    def test_exportable_from_hfs_agno_teams(self):
        """Verify DialecticAgnoTriad is exportable from hfs.agno.teams."""
        from hfs.agno.teams import DialecticAgnoTriad as Exported
        assert Exported is DialecticAgnoTriad
