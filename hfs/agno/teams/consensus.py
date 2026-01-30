"""ConsensusAgnoTriad - Three equal peers with voting pattern using Agno Team.

NOTE: For Agno-backed implementation with real LLM calls.
For the original stub implementation, see hfs/presets/consensus.py

This module provides the ConsensusAgnoTriad class which implements
the consensus triad pattern (peer_1, peer_2, peer_3) using Agno Teams.
All peers have equal authority and decisions require 2/3 majority.

Per CONTEXT.md decisions:
- Parallel worker dispatch (delegate_to_all_members=True)
- Process as available (streaming approach)
- Negotiation round for conflicts
- All peers equal authority with full tool access
"""

from typing import TYPE_CHECKING, Dict, Any, Optional, List
import re

from agno.team import Team
from agno.agent import Agent

from hfs.core.triad import TriadConfig, TriadOutput, NegotiationResponse
from hfs.agno.tools import HFSToolkit
from .base import AgnoTriad
from .schemas import PhaseSummary

if TYPE_CHECKING:
    from hfs.core.model_selector import ModelSelector
    from hfs.core.escalation_tracker import EscalationTracker


class ConsensusAgnoTriad(AgnoTriad):
    """Agno Team implementation of the consensus triad pattern.

    The consensus triad uses three equal peers with democratic voting:
    - peer_1: Focus on user experience perspective
    - peer_2: Focus on technical correctness perspective
    - peer_3: Focus on maintainability perspective

    All peers have equal authority and full tool access. Decisions
    require 2/3 majority (2 of 3 peers must agree).

    Per CONTEXT.md:
    - Parallel worker dispatch (delegate_to_all_members=True)
    - All peers see each other's contributions (share_member_interactions=True)
    - Session state stores peer proposals for conflict resolution

    Attributes:
        config: TriadConfig with id, preset, scope, budget, objectives
        model_selector: ModelSelector for role-based model resolution
        spec: Shared Spec instance (warm wax)
        toolkit: HFSToolkit with spec operation tools
        agents: Dict of agent role -> Agent instance
        team: Agno Team instance
    """

    # Default perspectives for the three peers (can be customized)
    DEFAULT_PERSPECTIVES = [
        "user_experience",      # Focus on end-user experience
        "technical_correctness", # Focus on technical standards
        "maintainability",      # Focus on long-term maintainability
    ]

    def __init__(
        self,
        config: TriadConfig,
        model_selector: "ModelSelector",
        spec: "Any",  # Spec type, avoiding circular import
        escalation_tracker: "Optional[EscalationTracker]" = None,
    ) -> None:
        """Initialize the consensus triad.

        Args:
            config: Configuration for this triad
            model_selector: ModelSelector for role-based model resolution.
                Models are obtained via _get_model_for_role() in _create_agents().
            spec: Shared Spec instance for claim/negotiation operations
            escalation_tracker: Optional tracker for failure-adaptive tier escalation
        """
        super().__init__(
            config=config,
            model_selector=model_selector,
            spec=spec,
            escalation_tracker=escalation_tracker,
        )

    def _create_agents(self) -> Dict[str, Agent]:
        """Create three equal peer agents with unique perspectives.

        Per CONTEXT.md: Consensus allows direct peer communication.
        All peers have full HFSToolkit access (equal authority).

        Each agent gets a model from _get_model_for_role() based on
        the ModelSelector configuration.

        Returns:
            Dictionary with keys "peer_1", "peer_2", "peer_3"
        """
        base_context = self.config.system_context or ""
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)

        agents = {}
        perspectives = self.DEFAULT_PERSPECTIVES

        for i, perspective in enumerate(perspectives, 1):
            peer_name = f"peer_{i}"
            agent_name = f"{self.config.id}_{peer_name}"

            agent = Agent(
                name=agent_name,
                model=self._get_model_for_role(peer_name),
                role=f"Equal peer with {perspective} focus",
                instructions=self._peer_prompt(perspective, peer_name),
                tools=[self.toolkit],  # All peers have full toolkit access
            )

            agents[peer_name] = agent

        return agents

    def _peer_prompt(self, perspective: str, peer_name: str) -> str:
        """Generate system prompt for a peer agent.

        Args:
            perspective: The unique perspective this peer brings
            peer_name: The peer's identifier (peer_1, peer_2, peer_3)

        Returns:
            Complete system prompt for the peer
        """
        base_context = self.config.system_context or ""
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)

        return f"""You are {peer_name} in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
Your perspective: {perspective}
{base_context}

Your responsibilities:
1. Propose solutions from your {perspective} perspective
2. Evaluate proposals from your unique viewpoint
3. Engage constructively in debate with other peers
4. Vote honestly based on your assessment
5. Seek consensus while maintaining your perspective's concerns

EQUAL AUTHORITY:
You have EQUAL authority with the other peers. This is a democratic triad.
Decisions require 2/3 majority (2 of 3 peers must agree).
Your role is to ensure {perspective} concerns are properly considered.
Be willing to compromise but don't abandon core principles.

CONSENSUS FLOW:
1. All peers propose independently
2. Debate: discuss and refine proposals together
3. Vote: 2/3 majority required for decisions
4. Finalize: implement the consensus decision

TOOLS AVAILABLE:
- register_claim: Claim ownership of spec sections
- negotiate_response: Respond during negotiation (concede/revise/hold)
- generate_code: Generate code for owned sections
- get_current_claims: View current claim state
- get_negotiation_state: View negotiation details

When voting, be explicit about your vote (APPROVE/REJECT) and rationale."""

    def _create_team(self) -> Team:
        """Create Agno Team with parallel dispatch for consensus.

        Per CONTEXT.md:
        - delegate_to_all_members=True (parallel broadcast to all peers)
        - share_member_interactions=True (peers see each other)
        - Session state for peer proposals and voting

        NOTE: respond_directly must NOT be True with delegate_to_all_members
        as they are incompatible settings.

        Team uses peer_1's model for team-level operations.

        Returns:
            Agno Team configured for consensus deliberation
        """
        return Team(
            name=f"triad_{self.config.id}",
            model=self._get_model_for_role("peer_1"),  # Team uses peer_1's model
            members=list(self.agents.values()),
            delegate_to_all_members=True,  # Parallel broadcast to all peers
            share_member_interactions=True,  # Peers see each other
            add_session_state_to_context=True,
            session_state=self._session_state.model_dump(),
            # NOTE: Do NOT set respond_directly=True with delegate_to_all_members
        )

    def _get_phase_summary_prompt(self, phase: str) -> str:
        """Get structured summary prompt for any peer to produce.

        For consensus triads, any peer can produce the summary after
        voting is complete. The summary should reflect the consensus
        reached and the voting results.

        Args:
            phase: The phase to summarize (deliberation/negotiation/execution)

        Returns:
            Prompt string for extracting structured summary
        """
        return f"""After completing the {phase} phase, produce a structured summary.

## Summary Template
- **Voting Results:** [How did peers vote? What was the outcome?]
- **Consensus Achieved:** [What decision was reached by 2/3 majority?]
- **Decisions Made:** [List key decisions from this phase]
- **Open Questions:** [List unresolved questions for next phase]
- **Artifacts:** [List any outputs/proposals created]

This summary will be passed to the next phase. Be concise but complete.

Format your response as:
PHASE_SUMMARY_START
Phase: {phase}
Voting_Results:
- [peer_1 vote and rationale]
- [peer_2 vote and rationale]
- [peer_3 vote and rationale]
Consensus: [2/3 majority decision]
Decisions:
- [decision 1]
- [decision 2]
Open Questions:
- [question 1]
- [question 2]
Artifacts:
- [artifact 1]: [brief description]
- [artifact 2]: [brief description]
PHASE_SUMMARY_END"""

    def _build_deliberation_prompt(
        self,
        user_request: str,
        spec_state: Dict[str, Any],
    ) -> str:
        """Build prompt for consensus deliberation phase.

        Flow: All peers propose -> debate -> vote (2/3 majority) -> finalize

        Args:
            user_request: The original user request
            spec_state: Current state of the shared spec

        Returns:
            Complete prompt for team deliberation
        """
        sections_info = ""
        if spec_state.get("sections"):
            sections_info = "Available sections:\n"
            for name, info in spec_state["sections"].items():
                status = info.get("status", "unknown") if isinstance(info, dict) else "unknown"
                sections_info += f"- {name}: {status}\n"

        primary = ", ".join(self.config.scope_primary)
        reach = ", ".join(self.config.scope_reach)

        summary_prompt = self._get_phase_summary_prompt("deliberation")

        return f"""## Consensus Deliberation Phase

### User Request
{user_request}

### Your Scope
- Primary (guaranteed territory): {primary}
- Reach (competitive territory): {reach}

### Current Spec State
{sections_info}

### Consensus Flow
1. **PROPOSE (All Peers)**: Each peer proposes solutions from their perspective
2. **DEBATE (All Peers)**: Discuss proposals, identify strengths and concerns
3. **VOTE (All Peers)**: Each peer votes APPROVE or REJECT on the consolidated proposal
4. **FINALIZE**: 2/3 majority (2 of 3) required to proceed

### Instructions
All three peers work in parallel. Each peer should:
1. Propose solutions from your unique perspective
2. Consider other peers' proposals and concerns
3. Engage in constructive debate
4. Vote explicitly (APPROVE/REJECT) with clear rationale

Use the tools to register claims on sections you want to own.
Decisions require 2/3 majority - be willing to compromise!

### Phase Summary (After Voting)
{summary_prompt}"""

    def _build_negotiation_prompt(
        self,
        section: str,
        other_proposals: Dict[str, Any],
    ) -> str:
        """Build prompt for consensus negotiation phase.

        All peers vote on whether to concede, revise, or hold.

        Args:
            section: Name of the contested section
            other_proposals: Dict mapping other triad IDs to their proposals

        Returns:
            Complete prompt for team negotiation
        """
        proposals_info = "Other triads' proposals for this section:\n"
        for triad_id, proposal in other_proposals.items():
            proposals_info += f"\n### {triad_id}'s Proposal\n{proposal}\n"

        summary_prompt = self._get_phase_summary_prompt("negotiation")

        return f"""## Consensus Negotiation Phase

### Contested Section: {section}

{proposals_info}

### Consensus Evaluation
All three peers evaluate the competing proposals and vote:
1. Each peer reviews our proposal vs. others from their perspective
2. Peers debate the merits of each proposal
3. Peers vote on the decision: CONCEDE, REVISE, or HOLD

### Voting Options
- **CONCEDE**: Withdraw our claim (another proposal is clearly better)
- **REVISE**: Update our proposal incorporating good ideas from others
- **HOLD**: Maintain our position (our proposal is strongest)

### Decision Rule
2/3 majority (2 of 3 peers) required. Vote explicitly!

Example voting:
- peer_1: "VOTE: HOLD - From user_experience perspective, our proposal better serves end users"
- peer_2: "VOTE: REVISE - Technical concerns could be addressed by incorporating X"
- peer_3: "VOTE: REVISE - Maintainability would improve with changes from triad_b"
Result: 2/3 voted REVISE -> We revise

Use negotiate_response tool to submit the final decision after voting.

### Phase Summary (After Voting)
{summary_prompt}"""

    def _build_execution_prompt(
        self,
        frozen_spec: Dict[str, Any],
    ) -> str:
        """Build prompt for consensus execution phase.

        All peers generate code proposals and vote on the best.

        Args:
            frozen_spec: The frozen spec with finalized section assignments

        Returns:
            Complete prompt for team execution
        """
        # Find sections we own
        owned_sections = []
        sections_data = frozen_spec.get("sections", {})
        for section_name, section_info in sections_data.items():
            if isinstance(section_info, dict):
                if section_info.get("owner") == self.config.id:
                    owned_sections.append(section_name)

        owned_info = "Sections to generate code for:\n"
        for section in owned_sections:
            section_data = sections_data.get(section, {})
            proposal = section_data.get("proposals", {}).get(self.config.id, "No proposal")
            owned_info += f"\n### {section}\nProposal: {proposal}\n"

        summary_prompt = self._get_phase_summary_prompt("execution")

        return f"""## Consensus Execution Phase

### Your Owned Sections
{owned_info}

### Consensus Code Generation
1. **PROPOSE (All Peers)**: Each peer generates code from their perspective
2. **DEBATE (All Peers)**: Review each other's code for issues and improvements
3. **VOTE (All Peers)**: Vote on which code version (or merged version) to use
4. **FINALIZE**: 2/3 majority selects the final code

### Instructions
Generate code for each owned section using the consensus process:
- peer_1: Generate code prioritizing user_experience
- peer_2: Generate code prioritizing technical_correctness
- peer_3: Generate code prioritizing maintainability

Then vote on the best version or create a merged version that combines
the strengths from all perspectives.

Use generate_code tool for each section when consensus code is ready.

### Phase Summary (After Voting)
{summary_prompt}"""

    def _merge_peer_proposals(self, result: Any) -> Dict[str, Any]:
        """Combine parallel results from all peers.

        When delegate_to_all_members=True, all peers respond in parallel.
        This method merges their proposals into a unified structure.

        Args:
            result: Raw result from team.arun() with parallel responses

        Returns:
            Dict with merged proposals from all peers
        """
        response_str = str(result)

        # Extract peer contributions (they may be labeled)
        peer_proposals = {}

        for i in range(1, 4):
            peer_name = f"peer_{i}"
            # Look for peer-labeled sections in the response
            pattern = rf"(?:{peer_name}|Peer {i})[:\s]+(.*?)(?=(?:peer_|Peer \d|$))"
            match = re.search(pattern, response_str, re.IGNORECASE | re.DOTALL)
            if match:
                peer_proposals[peer_name] = match.group(1).strip()
            else:
                peer_proposals[peer_name] = ""

        return {
            "raw_response": response_str,
            "peer_proposals": peer_proposals,
            "has_all_peers": all(peer_proposals.values()),
        }

    def _extract_voting_results(self, result: Any) -> Dict[str, Any]:
        """Parse voting results from team response.

        Looks for explicit VOTE: statements and counts 2/3 majority.

        Args:
            result: Raw result from team.arun()

        Returns:
            Dict with vote counts, winner, and whether consensus was reached
        """
        response_str = str(result)

        votes = {
            "approve": 0,
            "reject": 0,
            "concede": 0,
            "revise": 0,
            "hold": 0,
        }

        # Look for explicit vote statements
        vote_pattern = r"VOTE:\s*(APPROVE|REJECT|CONCEDE|REVISE|HOLD)"
        matches = re.findall(vote_pattern, response_str, re.IGNORECASE)

        for vote in matches:
            vote_lower = vote.lower()
            if vote_lower in votes:
                votes[vote_lower] += 1

        # Determine winner (needs 2/3 majority = 2 of 3)
        total_votes = sum(votes.values())
        winner = None
        consensus_reached = False

        for vote_type, count in votes.items():
            if count >= 2:  # 2/3 majority
                winner = vote_type
                consensus_reached = True
                break

        return {
            "votes": votes,
            "total_votes": total_votes,
            "winner": winner,
            "consensus_reached": consensus_reached,
            "required_majority": 2,
        }

    def _handle_conflict_negotiation(
        self,
        proposals: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle conflict resolution when parallel workers produce conflicting outputs.

        Per CONTEXT.md: Negotiation round for conflicts. When peers can't reach
        consensus, this triggers additional debate and re-voting.

        Args:
            proposals: Dict of peer proposals that conflict

        Returns:
            Dict with conflict resolution strategy and merged proposal
        """
        # Identify points of conflict
        conflicts = []
        agreement_points = []

        peer_proposals = proposals.get("peer_proposals", {})

        # Simple conflict detection: check if proposals mention different approaches
        all_content = " ".join(str(v) for v in peer_proposals.values())

        return {
            "has_conflict": True,
            "resolution_strategy": "re_vote",
            "peer_proposals": peer_proposals,
            "suggested_compromise": "Consider combining the strongest elements from each perspective",
        }

    def _extract_phase_summary(self, response: Any, phase: str) -> Optional[PhaseSummary]:
        """Extract PhaseSummary from team's output.

        Parses the structured summary format from the response and
        stores it in session_state.

        Args:
            response: The team's response
            phase: Which phase this summary is for

        Returns:
            PhaseSummary if found in response, None otherwise
        """
        response_str = str(response)

        # Look for PHASE_SUMMARY_START ... PHASE_SUMMARY_END block
        pattern = r"PHASE_SUMMARY_START\s*(.*?)\s*PHASE_SUMMARY_END"
        match = re.search(pattern, response_str, re.DOTALL)

        if not match:
            return None

        summary_text = match.group(1)

        # Parse the structured summary
        decisions: List[str] = []
        open_questions: List[str] = []
        artifacts: Dict[str, str] = {}

        # Extract decisions
        decisions_match = re.search(r"Decisions:\s*(.*?)(?=Open Questions:|Artifacts:|Voting|Consensus|$)", summary_text, re.DOTALL)
        if decisions_match:
            decisions_text = decisions_match.group(1)
            decisions = [
                line.strip().lstrip("- ")
                for line in decisions_text.strip().split("\n")
                if line.strip() and line.strip() != "-"
            ]

        # Extract open questions
        questions_match = re.search(r"Open Questions:\s*(.*?)(?=Artifacts:|$)", summary_text, re.DOTALL)
        if questions_match:
            questions_text = questions_match.group(1)
            open_questions = [
                line.strip().lstrip("- ")
                for line in questions_text.strip().split("\n")
                if line.strip() and line.strip() != "-"
            ]

        # Extract artifacts
        artifacts_match = re.search(r"Artifacts:\s*(.*?)$", summary_text, re.DOTALL)
        if artifacts_match:
            artifacts_text = artifacts_match.group(1)
            for line in artifacts_text.strip().split("\n"):
                line = line.strip().lstrip("- ")
                if ":" in line:
                    key, value = line.split(":", 1)
                    artifacts[key.strip()] = value.strip()

        summary = PhaseSummary(
            phase=phase,
            decisions=decisions,
            open_questions=open_questions,
            artifacts=artifacts,
            produced_by="consensus",  # Any peer can produce for consensus
        )

        # Store in session state
        if phase == "deliberation":
            self._session_state.deliberation_summary = summary
        elif phase == "negotiation":
            self._session_state.negotiation_summary = summary
        elif phase == "execution":
            self._session_state.execution_summary = summary

        return summary
