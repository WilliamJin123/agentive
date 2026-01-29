"""Unit tests for HierarchicalAgnoTriad.

Tests the hierarchical triad implementation without making actual LLM API calls.
Uses mocked Model and Spec objects to verify structure and configuration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call

from hfs.core.triad import TriadConfig, TriadPreset
from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad, WorkerToolkit
from hfs.agno.tools import HFSToolkit


@pytest.fixture
def mock_model():
    """Create a mock Agno Model that doesn't make API calls."""
    model = Mock()
    model.id = "mock-model"
    return model


@pytest.fixture
def mock_spec():
    """Create a mock Spec with basic structure."""
    spec = Mock()
    spec.sections = {}
    spec.temperature = 1.0
    spec.round = 0
    spec.is_frozen = Mock(return_value=False)
    return spec


@pytest.fixture
def triad_config():
    """Create a standard TriadConfig for testing."""
    return TriadConfig(
        id="test_hierarchical",
        preset=TriadPreset.HIERARCHICAL,
        scope_primary=["header", "footer"],
        scope_reach=["sidebar"],
        budget_tokens=1000,
        budget_tool_calls=10,
        budget_time_ms=30000,
        objectives=["layout_quality", "performance"],
        system_context="Test context for unit testing.",
    )


def create_mock_agent(**kwargs):
    """Create a mock Agent with the provided kwargs as attributes."""
    agent = Mock()
    for key, value in kwargs.items():
        setattr(agent, key, value)
    return agent


class TestHierarchicalAgnoTriadCreation:
    """Tests for HierarchicalAgnoTriad agent creation."""

    def test_hierarchical_creates_three_agents(self, triad_config, mock_model, mock_spec):
        """Verify _create_agents returns orchestrator, worker_a, worker_b."""
        # Patch both Agent and Team to avoid actual creation issues
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        assert "orchestrator" in triad.agents
        assert "worker_a" in triad.agents
        assert "worker_b" in triad.agents
        assert len(triad.agents) == 3

    def test_agents_have_correct_names(self, triad_config, mock_model, mock_spec):
        """Verify agents are named with triad id prefix."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        assert triad.agents["orchestrator"].name == "test_hierarchical_orchestrator"
        assert triad.agents["worker_a"].name == "test_hierarchical_worker_a"
        assert triad.agents["worker_b"].name == "test_hierarchical_worker_b"

    def test_agents_have_correct_roles(self, triad_config, mock_model, mock_spec):
        """Verify agents have appropriate roles."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        assert triad.agents["orchestrator"].role == "Task coordinator and integrator"
        assert triad.agents["worker_a"].role == "Subtask executor"
        assert triad.agents["worker_b"].role == "Subtask executor"


class TestToolAssignment:
    """Tests for role-specific tool assignment."""

    def test_orchestrator_has_full_toolkit(self, triad_config, mock_model, mock_spec):
        """Verify orchestrator's tools include full HFSToolkit."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        orchestrator = triad.agents["orchestrator"]
        tools = orchestrator.tools

        # Orchestrator should have HFSToolkit
        assert len(tools) == 1
        toolkit = tools[0]
        assert isinstance(toolkit, HFSToolkit)

        # HFSToolkit should have all tools (methods have __name__ attribute)
        tool_names = [t.__name__ for t in toolkit.tools]
        assert "register_claim" in tool_names
        assert "negotiate_response" in tool_names
        assert "generate_code" in tool_names
        assert "get_current_claims" in tool_names
        assert "get_negotiation_state" in tool_names

    def test_workers_have_limited_tools(self, triad_config, mock_model, mock_spec):
        """Verify workers only have generate_code tool."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        for worker_name in ["worker_a", "worker_b"]:
            worker = triad.agents[worker_name]
            tools = worker.tools

            # Worker should have WorkerToolkit
            assert len(tools) == 1
            toolkit = tools[0]
            assert isinstance(toolkit, WorkerToolkit)

            # WorkerToolkit should only have generate_code (methods have __name__ attribute)
            tool_names = [t.__name__ for t in toolkit.tools]
            assert tool_names == ["generate_code"]
            assert "register_claim" not in tool_names
            assert "negotiate_response" not in tool_names


class TestWorkerToolkit:
    """Tests for the WorkerToolkit class."""

    def test_worker_toolkit_delegates_to_parent(self, mock_spec):
        """Verify WorkerToolkit.generate_code delegates to parent."""
        parent_toolkit = HFSToolkit(spec=mock_spec, triad_id="test")
        worker_toolkit = WorkerToolkit(parent_toolkit=parent_toolkit)

        # Mock the parent's generate_code
        parent_toolkit.generate_code = Mock(return_value='{"success": true}')

        result = worker_toolkit.generate_code("header")

        parent_toolkit.generate_code.assert_called_once_with("header")
        assert result == '{"success": true}'

    def test_worker_toolkit_only_exposes_generate_code(self, mock_spec):
        """Verify WorkerToolkit only has generate_code method exposed."""
        parent_toolkit = HFSToolkit(spec=mock_spec, triad_id="test")
        worker_toolkit = WorkerToolkit(parent_toolkit=parent_toolkit)

        # Check registered tools (methods have __name__ attribute)
        tool_names = [t.__name__ for t in worker_toolkit.tools]
        assert len(tool_names) == 1
        assert "generate_code" in tool_names


class TestTeamConfiguration:
    """Tests for Team creation and configuration."""

    def test_team_configuration(self, triad_config, mock_model, mock_spec):
        """Verify Team created with correct settings."""
        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            MockTeam.return_value = Mock()
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

            # Verify Team was called with correct config
            MockTeam.assert_called_once()
            call_kwargs = MockTeam.call_args.kwargs

            assert call_kwargs["name"] == "triad_test_hierarchical"
            assert call_kwargs["model"] == mock_model
            assert call_kwargs["delegate_to_all_members"] is False
            assert call_kwargs["share_member_interactions"] is True
            assert call_kwargs["add_session_state_to_context"] is True
            assert "session_state" in call_kwargs

    def test_team_has_all_members(self, triad_config, mock_model, mock_spec):
        """Verify Team includes all 3 agents as members."""
        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            MockTeam.return_value = Mock()
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

            call_kwargs = MockTeam.call_args.kwargs
            members = call_kwargs["members"]

            assert len(members) == 3


class TestSessionState:
    """Tests for session state management."""

    def test_session_state_initialization(self, triad_config, mock_model, mock_spec):
        """Verify _session_state starts with correct structure."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        # Check initial state
        assert triad._session_state.current_phase is None
        assert triad._session_state.deliberation_summary is None
        assert triad._session_state.negotiation_summary is None
        assert triad._session_state.execution_summary is None

    def test_session_state_passed_to_team(self, triad_config, mock_model, mock_spec):
        """Verify session state is passed to Team creation."""
        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            MockTeam.return_value = Mock()
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

            call_kwargs = MockTeam.call_args.kwargs
            session_state = call_kwargs["session_state"]

            # Should be model_dump() of TriadSessionState
            assert isinstance(session_state, dict)
            assert "current_phase" in session_state


class TestPromptBuilders:
    """Tests for prompt builder methods."""

    def test_deliberation_prompt_includes_context(self, triad_config, mock_model, mock_spec):
        """Verify _build_deliberation_prompt includes user_request, spec_state, scope."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        user_request = "Build a navigation header"
        spec_state = {"sections": {"header": {}}, "temperature": 1.0}

        prompt = triad._build_deliberation_prompt(user_request, spec_state)

        assert "Build a navigation header" in prompt
        assert "test_hierarchical" in prompt
        assert "header" in prompt
        assert "footer" in prompt
        assert "layout_quality" in prompt
        assert "performance" in prompt

    def test_negotiation_prompt_includes_section(self, triad_config, mock_model, mock_spec):
        """Verify _build_negotiation_prompt includes contested section and proposals."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        section = "header"
        other_proposals = {
            "triad_b": "Alternative header design",
            "triad_c": "Minimalist header",
        }

        prompt = triad._build_negotiation_prompt(section, other_proposals)

        assert "header" in prompt
        assert "triad_b" in prompt
        assert "triad_c" in prompt
        assert "Alternative header design" in prompt
        assert "CONCEDE" in prompt or "concede" in prompt.lower()
        assert "REVISE" in prompt or "revise" in prompt.lower()
        assert "HOLD" in prompt or "hold" in prompt.lower()

    def test_negotiation_prompt_shows_primary_scope(self, triad_config, mock_model, mock_spec):
        """Verify negotiation prompt indicates primary vs reach scope."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        # Primary scope section
        prompt_primary = triad._build_negotiation_prompt("header", {})
        assert "PRIMARY" in prompt_primary

        # Reach scope section
        prompt_reach = triad._build_negotiation_prompt("sidebar", {})
        assert "REACH" in prompt_reach

    def test_execution_prompt_includes_frozen_spec(self, triad_config, mock_model, mock_spec):
        """Verify _build_execution_prompt includes frozen spec sections."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        frozen_spec = {
            "sections": {
                "header": {"owner": "test_hierarchical", "content": "Header content"},
                "footer": {"owner": "test_hierarchical", "content": "Footer content"},
                "sidebar": {"owner": "other_triad", "content": "Sidebar content"},
            },
            "temperature": 0,
        }

        prompt = triad._build_execution_prompt(frozen_spec)

        # Should include owned sections
        assert "header" in prompt
        assert "footer" in prompt
        # Should reference owned sections
        assert "test_hierarchical" in prompt or "OWNED SECTIONS" in prompt

    def test_execution_prompt_handles_no_owned_sections(self, triad_config, mock_model, mock_spec):
        """Verify execution prompt handles case with no owned sections."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        frozen_spec = {
            "sections": {
                "header": {"owner": "other_triad"},
            },
            "temperature": 0,
        }

        prompt = triad._build_execution_prompt(frozen_spec)

        assert "No sections owned" in prompt or "no sections" in prompt.lower()


class TestPhaseSummaryPrompt:
    """Tests for phase summary prompt generation."""

    def test_phase_summary_prompt_structure(self, triad_config, mock_model, mock_spec):
        """Verify _get_phase_summary_prompt returns structured prompt."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        for phase in ["deliberation", "negotiation", "execution"]:
            prompt = triad._get_phase_summary_prompt(phase)

            assert phase in prompt
            assert "DECISIONS" in prompt
            assert "OPEN_QUESTIONS" in prompt or "QUESTIONS" in prompt
            assert "ARTIFACTS" in prompt


class TestResultParsers:
    """Tests for result parsing methods."""

    def test_parse_negotiation_result_concede(self, triad_config, mock_model, mock_spec):
        """Verify negotiation result parsing detects concede."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        result = triad._parse_negotiation_result("I will CONCEDE this section")
        assert result == "concede"

    def test_parse_negotiation_result_revise(self, triad_config, mock_model, mock_spec):
        """Verify negotiation result parsing detects revise."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        result = triad._parse_negotiation_result("Let me REVISE my proposal")
        assert result == "revise"

    def test_parse_negotiation_result_hold(self, triad_config, mock_model, mock_spec):
        """Verify negotiation result parsing defaults to hold."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        result = triad._parse_negotiation_result("I maintain my position")
        assert result == "hold"

    def test_parse_negotiation_result_empty(self, triad_config, mock_model, mock_spec):
        """Verify empty result defaults to hold."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        result = triad._parse_negotiation_result(None)
        assert result == "hold"


class TestInheritance:
    """Tests for proper inheritance from AgnoTriad."""

    def test_hierarchical_extends_agno_triad(self):
        """Verify HierarchicalAgnoTriad extends AgnoTriad."""
        from hfs.agno.teams import AgnoTriad
        assert issubclass(HierarchicalAgnoTriad, AgnoTriad)

    def test_hierarchical_implements_abstract_methods(self, triad_config, mock_model, mock_spec):
        """Verify all abstract methods are implemented."""
        with patch("hfs.agno.teams.hierarchical.Team"), \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            triad = HierarchicalAgnoTriad(triad_config, mock_model, mock_spec)

        # These should not raise NotImplementedError
        assert callable(triad._create_agents)
        assert callable(triad._create_team)
        assert callable(triad._get_phase_summary_prompt)
        assert callable(triad._build_deliberation_prompt)
        assert callable(triad._build_negotiation_prompt)
        assert callable(triad._build_execution_prompt)
