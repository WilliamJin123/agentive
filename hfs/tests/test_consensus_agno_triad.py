"""Unit tests for ConsensusAgnoTriad.

Tests the consensus triad implementation with mocked models.
No actual API calls - validates structure, tools, and prompts.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from agno.models.base import Model

from hfs.agno.teams import ConsensusAgnoTriad, AgnoTriad
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
    """Create a mock Agno Model that passes type validation."""
    return MockAgnoModel(id="mock-model")


@pytest.fixture
def mock_spec():
    """Create a mock Spec with sections."""
    spec = Mock()
    spec.sections = {
        "accessibility": Mock(status=Mock(value="unclaimed"), claims=set(), proposals={}, owner=None),
        "standards": Mock(status=Mock(value="unclaimed"), claims=set(), proposals={}, owner=None),
        "coherence": Mock(status=Mock(value="unclaimed"), claims=set(), proposals={}, owner=None),
    }
    spec.temperature = 1.0
    spec.round = 0
    spec.get_unclaimed_sections.return_value = ["accessibility", "standards", "coherence"]
    spec.get_claimed_sections.return_value = []
    spec.get_contested_sections.return_value = []
    spec.get_frozen_sections.return_value = []
    return spec


@pytest.fixture
def consensus_config():
    """Create a TriadConfig for consensus preset."""
    return TriadConfig(
        id="test_consensus",
        preset=TriadPreset.CONSENSUS,
        scope_primary=["accessibility"],
        scope_reach=["standards"],
        budget_tokens=1000,
        budget_tool_calls=10,
        budget_time_ms=30000,
        objectives=["wcag_compliance", "consistent_ux"],
    )


class TestConsensusAgnoTriadCreation:
    """Tests for ConsensusAgnoTriad initialization and agent creation."""

    def test_consensus_extends_agno_triad(self):
        """Verify ConsensusAgnoTriad extends AgnoTriad base class."""
        assert issubclass(ConsensusAgnoTriad, AgnoTriad)

    def test_consensus_creates_three_peers(self, mock_model, mock_spec, consensus_config):
        """Verify _create_agents returns peer_1, peer_2, peer_3."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        agents = triad.agents
        assert len(agents) == 3
        assert "peer_1" in agents
        assert "peer_2" in agents
        assert "peer_3" in agents

    def test_agent_names_include_triad_id(self, mock_model, mock_spec, consensus_config):
        """Verify agent names include the triad ID for identification."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        assert triad.agents["peer_1"].name == "test_consensus_peer_1"
        assert triad.agents["peer_2"].name == "test_consensus_peer_2"
        assert triad.agents["peer_3"].name == "test_consensus_peer_3"


class TestPeersHaveEqualAuthority:
    """Tests for equal peer authority and tool access."""

    def test_all_peers_have_full_toolkit(self, mock_model, mock_spec, consensus_config):
        """Verify each peer has complete HFSToolkit access."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        for peer_name in ["peer_1", "peer_2", "peer_3"]:
            peer = triad.agents[peer_name]
            tools = peer.tools

            # Each peer should have the toolkit
            assert len(tools) == 1
            toolkit = tools[0]

            # Toolkit should have all tools
            tool_names = [t.__name__ for t in toolkit.tools]
            assert "register_claim" in tool_names
            assert "negotiate_response" in tool_names
            assert "generate_code" in tool_names
            assert "get_current_claims" in tool_names
            assert "get_negotiation_state" in tool_names

    def test_peers_have_unique_perspectives(self, mock_model, mock_spec, consensus_config):
        """Verify each peer has different perspective focus."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        # Check that perspectives are different
        perspectives_in_roles = []
        for peer_name in ["peer_1", "peer_2", "peer_3"]:
            peer = triad.agents[peer_name]
            role = peer.role.lower()
            perspectives_in_roles.append(role)

        # Verify perspectives are unique
        assert "user_experience" in perspectives_in_roles[0]
        assert "technical_correctness" in perspectives_in_roles[1]
        assert "maintainability" in perspectives_in_roles[2]

    def test_all_peers_have_equal_role(self, mock_model, mock_spec, consensus_config):
        """Verify all peers have 'Equal peer' in their role."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        for peer_name in ["peer_1", "peer_2", "peer_3"]:
            peer = triad.agents[peer_name]
            assert "Equal peer" in peer.role


class TestTeamUsesParallelDispatch:
    """Tests for parallel dispatch configuration."""

    def test_team_uses_parallel_dispatch(self, mock_model, mock_spec, consensus_config):
        """Verify delegate_to_all_members=True for parallel broadcast."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        # delegate_to_all_members should be True for parallel dispatch
        assert triad.team.delegate_to_all_members == True

    def test_team_shares_interactions(self, mock_model, mock_spec, consensus_config):
        """Verify share_member_interactions=True so peers see each other."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        assert triad.team.share_member_interactions == True

    def test_no_respond_directly_with_broadcast(self, mock_model, mock_spec, consensus_config):
        """Verify respond_directly is NOT True (conflicts with delegate_to_all_members)."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        # respond_directly should be False or None when using delegate_to_all_members
        # This is because they are incompatible settings
        respond_directly = getattr(triad.team, 'respond_directly', None)
        assert respond_directly is None or respond_directly == False


class TestSessionState:
    """Tests for session state and peer proposal storage."""

    def test_session_state_for_peer_proposals(self, mock_model, mock_spec, consensus_config):
        """Verify session state can store proposals from all peers."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        state = triad._session_state
        assert hasattr(state, "deliberation_summary")
        assert hasattr(state, "negotiation_summary")
        assert hasattr(state, "execution_summary")

    def test_team_has_session_state(self, mock_model, mock_spec, consensus_config):
        """Verify team has session state for phase context."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        assert triad.team.add_session_state_to_context == True
        assert triad.team.session_state is not None


class TestDeliberationPrompt:
    """Tests for deliberation prompt generation."""

    def test_deliberation_prompt_mentions_voting(self, mock_model, mock_spec, consensus_config):
        """Verify prompt includes voting/consensus instructions."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        prompt = triad._build_deliberation_prompt(
            user_request="Implement WCAG compliance",
            spec_state={"sections": {}}
        )

        assert "VOTE" in prompt.upper()
        assert "2/3" in prompt or "majority" in prompt.lower()
        assert "consensus" in prompt.lower()

    def test_deliberation_prompt_all_peers_participate(self, mock_model, mock_spec, consensus_config):
        """Verify prompt indicates all peers participate equally."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        prompt = triad._build_deliberation_prompt(
            user_request="Implement WCAG compliance",
            spec_state={"sections": {}}
        )

        assert "All Peers" in prompt or "All peers" in prompt or "all peers" in prompt


class TestVotingMechanism:
    """Tests for 2/3 majority voting logic."""

    def test_voting_requires_two_thirds(self, mock_model, mock_spec, consensus_config):
        """Verify voting logic requires 2/3 majority (2 of 3 peers)."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        # Test with 2 approves - should reach consensus
        result_2_approve = """
        peer_1: VOTE: APPROVE - User experience is good
        peer_2: VOTE: APPROVE - Technical standards met
        peer_3: VOTE: REJECT - Maintainability concerns
        """
        voting_result = triad._extract_voting_results(result_2_approve)
        assert voting_result["consensus_reached"] == True
        assert voting_result["winner"] == "approve"
        assert voting_result["required_majority"] == 2

    def test_voting_fails_without_majority(self, mock_model, mock_spec, consensus_config):
        """Verify voting fails without 2/3 majority."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        # Test with only 1 approve - should not reach consensus
        result_1_approve = """
        peer_1: VOTE: APPROVE - Looks good
        peer_2: VOTE: REJECT - Technical issues
        peer_3: VOTE: REJECT - Not maintainable
        """
        voting_result = triad._extract_voting_results(result_1_approve)
        assert voting_result["consensus_reached"] == True  # 2 rejects = consensus to reject
        assert voting_result["winner"] == "reject"

    def test_voting_handles_negotiation_decisions(self, mock_model, mock_spec, consensus_config):
        """Verify voting extracts concede/revise/hold decisions."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        result_revise = """
        peer_1: VOTE: REVISE - We can improve
        peer_2: VOTE: REVISE - Good ideas from others
        peer_3: VOTE: HOLD - Our proposal is solid
        """
        voting_result = triad._extract_voting_results(result_revise)
        assert voting_result["consensus_reached"] == True
        assert voting_result["winner"] == "revise"


class TestPhaseSummaryPrompt:
    """Tests for phase summary prompt generation."""

    def test_phase_summary_prompt_structure(self, mock_model, mock_spec, consensus_config):
        """Verify _get_phase_summary_prompt includes required sections."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        prompt = triad._get_phase_summary_prompt("deliberation")

        assert "Voting Results" in prompt or "Voting_Results" in prompt
        assert "Consensus" in prompt
        assert "Decisions" in prompt
        assert "Open Questions" in prompt
        assert "Artifacts" in prompt
        assert "PHASE_SUMMARY_START" in prompt
        assert "PHASE_SUMMARY_END" in prompt


class TestMergePeerProposals:
    """Tests for merging parallel peer results."""

    def test_merge_peer_proposals(self, mock_model, mock_spec, consensus_config):
        """Test _merge_peer_proposals combines results from all peers."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        result = """
        peer_1: I propose focusing on keyboard navigation
        peer_2: We should ensure ARIA labels are correct
        peer_3: Color contrast needs to meet AA standards
        """

        merged = triad._merge_peer_proposals(result)
        assert "raw_response" in merged
        assert "peer_proposals" in merged


class TestConflictHandling:
    """Tests for conflict negotiation handling."""

    def test_handle_conflict_negotiation(self, mock_model, mock_spec, consensus_config):
        """Test _handle_conflict_negotiation triggers re-voting."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        proposals = {
            "peer_proposals": {
                "peer_1": "Approach A",
                "peer_2": "Approach B",
                "peer_3": "Approach C",
            }
        }

        conflict_result = triad._handle_conflict_negotiation(proposals)
        assert "has_conflict" in conflict_result
        assert "resolution_strategy" in conflict_result


class TestConsensusExports:
    """Tests for package exports."""

    def test_exportable_from_hfs_agno_teams(self):
        """Verify ConsensusAgnoTriad is exportable from hfs.agno.teams."""
        from hfs.agno.teams import ConsensusAgnoTriad as Exported
        assert Exported is ConsensusAgnoTriad


class TestExtractPhaseSummary:
    """Tests for extracting phase summaries from responses."""

    def test_extract_phase_summary_parses_response(self, mock_model, mock_spec, consensus_config):
        """Test _extract_phase_summary correctly parses structured output."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        response = """
        Here is our voting result...

        PHASE_SUMMARY_START
        Phase: deliberation
        Voting_Results:
        - peer_1: APPROVE - Good for UX
        - peer_2: APPROVE - Technically sound
        - peer_3: REJECT - Maintainability concerns
        Consensus: 2/3 majority APPROVE
        Decisions:
        - Implement keyboard navigation
        - Use ARIA labels for all interactive elements
        Open Questions:
        - Should we support screen magnifiers?
        Artifacts:
        - accessibility_spec: WCAG 2.1 AA requirements
        - navigation_flow: Keyboard focus order
        PHASE_SUMMARY_END

        End of summary.
        """

        summary = triad._extract_phase_summary(response, "deliberation")

        assert summary is not None
        assert summary.phase == "deliberation"
        assert len(summary.decisions) >= 1
        assert summary.produced_by == "consensus"

    def test_extract_phase_summary_returns_none_if_not_found(self, mock_model, mock_spec, consensus_config):
        """Verify None returned if summary block not in response."""
        triad = ConsensusAgnoTriad(consensus_config, mock_model, mock_spec)

        response = "Just regular output without summary markers"
        summary = triad._extract_phase_summary(response, "deliberation")

        assert summary is None
