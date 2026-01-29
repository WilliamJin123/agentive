"""Consensus Triad preset - three equal peers with voting pattern.

NOTE: For Agno-backed implementation with real LLM calls, use:
    from hfs.agno.teams import ConsensusAgnoTriad

This module provides the original stub implementation for reference
and backwards compatibility during migration.

---

The ConsensusTriad implements a democratic structure:
- peer_1, peer_2, peer_3: equal voice, 2/3 majority decides

Flow: all propose -> debate -> vote (2/3 majority) -> finalize

Best for: accessibility_decisions, standards_compliance, coherence_checking
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum

from ..core.triad import (
    Triad,
    TriadConfig,
    TriadOutput,
    NegotiationResponse,
)


class VoteChoice(Enum):
    """Vote choices for consensus building."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Agent:
    """Simple agent representation with role and system prompt.

    Attributes:
        role: The role name for this agent.
        system_prompt: The system-level instructions for this agent.
        description: Human-readable description of this agent's purpose.
        perspective: Unique perspective this peer brings to deliberation.
    """
    role: str
    system_prompt: str
    description: str
    perspective: str = ""


@dataclass
class Vote:
    """A vote cast by a peer.

    Attributes:
        peer: Which peer cast this vote.
        choice: The vote choice (approve/reject/abstain).
        rationale: Why they voted this way.
    """
    peer: str
    choice: VoteChoice
    rationale: str


class ConsensusTriad(Triad):
    """Triad using democratic voting among three equal peers.

    This preset is designed for decisions requiring broad agreement,
    especially cross-cutting concerns like accessibility or standards
    compliance. All three peers have equal voice and 2/3 majority
    is required for decisions.

    Internal structure:
        - peer_1: First peer with unique perspective
        - peer_2: Second peer with unique perspective
        - peer_3: Third peer with unique perspective

    Attributes:
        config: The TriadConfig for this triad.
        llm: The LLM client for agent interactions.
        agents: Dict of initialized Agent instances.
    """

    # Perspectives for each peer (can be customized based on config)
    DEFAULT_PERSPECTIVES = [
        "user_experience",  # Focus on end-user experience
        "technical_correctness",  # Focus on technical standards
        "maintainability",  # Focus on long-term maintainability
    ]

    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize three peer agents with equal authority.

        Creates three agents with specialized perspectives but equal
        voting power.

        Returns:
            Dictionary with keys "peer_1", "peer_2", "peer_3"
            mapping to Agent instances.
        """
        base_context = self.config.system_context or ""
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)

        agents = {}

        for i, perspective in enumerate(self.DEFAULT_PERSPECTIVES, 1):
            peer_name = f"peer_{i}"

            agent = Agent(
                role=peer_name,
                perspective=perspective,
                description=f"Equal peer focusing on {perspective} perspective",
                system_prompt=f"""You are {peer_name} in triad '{self.config.id}'.
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

You have EQUAL authority with the other peers. Decisions require 2/3 majority.
Your role is to ensure {perspective} concerns are properly considered.
Be willing to compromise but don't abandon core principles."""
            )

            agents[peer_name] = agent

        return agents

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Run consensus deliberation flow.

        Flow:
        1. All peers propose independently
        2. Debate: peers discuss and refine
        3. Vote: 2/3 majority required
        4. Finalize: winning proposal becomes output

        Args:
            user_request: The original user request.
            spec_state: Current state of the shared spec.

        Returns:
            TriadOutput with consensus position, claims, and proposals.
        """
        # Phase 1: All peers propose independently
        peer_proposals = await self._collect_proposals(user_request, spec_state)

        # Phase 2: Debate and refine
        debated_proposals = await self._debate(peer_proposals, user_request, spec_state)

        # Phase 3: Vote on final proposal
        final_proposal, vote_result = await self._vote(debated_proposals, spec_state)

        # Phase 4: Finalize
        claims = self._determine_claims(final_proposal, spec_state)

        return TriadOutput(
            position=final_proposal.get("position", ""),
            claims=claims,
            proposals=final_proposal.get("proposals", {})
        )

    async def _collect_proposals(
        self,
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Collect independent proposals from all peers.

        Args:
            user_request: The original user request.
            spec_state: Current spec state.

        Returns:
            Dict mapping peer names to their proposals.
        """
        proposals = {}

        for peer_name, peer_agent in self.agents.items():
            proposal = await self._peer_propose(peer_agent, user_request, spec_state)
            proposals[peer_name] = proposal

        return proposals

    async def _peer_propose(
        self,
        peer: Agent,
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Single peer generates their proposal.

        Args:
            peer: The peer agent.
            user_request: Original request.
            spec_state: Current spec state.

        Returns:
            Dict with proposal from this peer's perspective.
        """
        # TODO: Make actual LLM call
        # Stub demonstrating expected output
        return {
            "perspective": peer.perspective,
            "proposal": f"Proposal from {peer.role} ({peer.perspective} focus)",
            "key_concerns": [f"{peer.perspective} consideration 1"],
            "target_sections": list(self.config.scope_primary),
            "confidence": 0.8,
        }

    async def _debate(
        self,
        proposals: Dict[str, Dict[str, Any]],
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Peers debate and refine proposals.

        Each peer can respond to others' proposals, leading to
        refinement and potential convergence.

        Args:
            proposals: Initial proposals from all peers.
            user_request: Original request.
            spec_state: Current spec state.

        Returns:
            Refined proposals after debate.
        """
        # TODO: Multiple rounds of LLM calls for debate
        # Stub: One round of responses

        refined_proposals = {}

        for peer_name, peer_agent in self.agents.items():
            # Peer reviews others' proposals
            other_proposals = {
                k: v for k, v in proposals.items() if k != peer_name
            }

            refined = await self._peer_respond_to_debate(
                peer_agent,
                proposals[peer_name],
                other_proposals,
                spec_state
            )
            refined_proposals[peer_name] = refined

        return refined_proposals

    async def _peer_respond_to_debate(
        self,
        peer: Agent,
        own_proposal: Dict[str, Any],
        other_proposals: Dict[str, Dict[str, Any]],
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Peer refines proposal based on debate.

        Args:
            peer: The peer agent.
            own_proposal: This peer's original proposal.
            other_proposals: Other peers' proposals.
            spec_state: Current spec state.

        Returns:
            Refined proposal.
        """
        # TODO: LLM call
        # Stub showing refinement
        return {
            **own_proposal,
            "refined": True,
            "incorporated_from_others": [
                f"Consideration from {other}"
                for other in other_proposals.keys()
            ],
        }

    async def _vote(
        self,
        proposals: Dict[str, Dict[str, Any]],
        spec_state: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Vote]]:
        """Peers vote to reach consensus.

        Attempts to find a proposal that achieves 2/3 majority.
        May synthesize a compromise proposal if needed.

        Args:
            proposals: Refined proposals from debate.
            spec_state: Current spec state.

        Returns:
            Tuple of (winning proposal, vote results).
        """
        # Generate a merged proposal for voting
        merged_proposal = await self._merge_proposals(proposals, spec_state)

        # Collect votes
        votes = {}
        for peer_name, peer_agent in self.agents.items():
            vote = await self._peer_vote(peer_agent, merged_proposal, spec_state)
            votes[peer_name] = vote

        # Count approvals
        approvals = sum(1 for v in votes.values() if v.choice == VoteChoice.APPROVE)

        # 2/3 majority = at least 2 of 3
        if approvals >= 2:
            # Consensus reached
            return merged_proposal, votes
        else:
            # No consensus - attempt compromise
            compromise = await self._build_compromise(proposals, votes, spec_state)

            # Re-vote on compromise
            revotes = {}
            for peer_name, peer_agent in self.agents.items():
                vote = await self._peer_vote(peer_agent, compromise, spec_state)
                revotes[peer_name] = vote

            return compromise, revotes

    async def _merge_proposals(
        self,
        proposals: Dict[str, Dict[str, Any]],
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge peer proposals into a unified proposal for voting.

        Args:
            proposals: All peer proposals.
            spec_state: Current spec state.

        Returns:
            Merged proposal incorporating all perspectives.
        """
        # TODO: LLM call to intelligently merge
        # Stub: Combine key elements
        all_concerns = []
        all_sections = set()

        for peer_name, proposal in proposals.items():
            all_concerns.extend(proposal.get("key_concerns", []))
            all_sections.update(proposal.get("target_sections", []))

        merged_proposals = {}
        for section in all_sections:
            merged_proposals[section] = {
                "content": f"Merged content for {section}",
                "addresses_concerns": all_concerns,
            }

        return {
            "position": f"Triad {self.config.id} consensus position",
            "proposals": merged_proposals,
            "incorporated_perspectives": list(proposals.keys()),
            "consensus_approach": "Merged all peer perspectives",
        }

    async def _peer_vote(
        self,
        peer: Agent,
        proposal: Dict[str, Any],
        spec_state: Dict[str, Any]
    ) -> Vote:
        """Peer votes on a proposal.

        Args:
            peer: The voting peer.
            proposal: Proposal to vote on.
            spec_state: Current spec state.

        Returns:
            Vote object with choice and rationale.
        """
        # TODO: LLM call
        # Stub: Approve by default if concerns are addressed
        concerns_addressed = proposal.get("addresses_concerns", [])
        peer_concern = f"{peer.perspective} consideration 1"

        if peer_concern in str(concerns_addressed):
            return Vote(
                peer=peer.role,
                choice=VoteChoice.APPROVE,
                rationale=f"My {peer.perspective} concerns are addressed"
            )
        else:
            return Vote(
                peer=peer.role,
                choice=VoteChoice.APPROVE,  # Default to approve for stub
                rationale=f"Acceptable from {peer.perspective} perspective"
            )

    async def _build_compromise(
        self,
        proposals: Dict[str, Dict[str, Any]],
        votes: Dict[str, Vote],
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build compromise proposal when initial vote fails.

        Args:
            proposals: Original proposals.
            votes: Initial vote results.
            spec_state: Current spec state.

        Returns:
            Compromise proposal addressing rejecting peers' concerns.
        """
        # TODO: LLM call to build targeted compromise
        # Identify rejecting peers
        rejectors = [
            peer for peer, vote in votes.items()
            if vote.choice == VoteChoice.REJECT
        ]

        # Stub: Add explicit addressing of rejectors' concerns
        return {
            "position": f"Triad {self.config.id} compromise position",
            "proposals": {},
            "compromise_for": rejectors,
            "additional_considerations": [
                f"Added consideration for {r}" for r in rejectors
            ],
        }

    def _determine_claims(
        self,
        final_proposal: Dict[str, Any],
        spec_state: Dict[str, Any]
    ) -> List[str]:
        """Determine which sections to claim based on consensus.

        Args:
            final_proposal: The consensus proposal.
            spec_state: Current spec state.

        Returns:
            List of section names to claim.
        """
        proposal_sections = list(final_proposal.get("proposals", {}).keys())
        claims = list(set(proposal_sections + list(self.config.scope_primary)))
        return claims

    async def negotiate(
        self,
        section: str,
        other_proposals: Dict[str, Any]
    ) -> NegotiationResponse:
        """Respond to negotiation for a contested section.

        Peers vote on whether to concede, revise, or hold.

        Args:
            section: Name of the contested section.
            other_proposals: Dict mapping other triad IDs to their proposals.

        Returns:
            "concede", "revise", or "hold"
        """
        is_primary = section in self.config.scope_primary
        is_reach = section in self.config.scope_reach

        if not is_primary and not is_reach:
            return "concede"

        # TODO: LLM calls for peer voting on negotiation response
        # Each peer evaluates and votes

        # For consensus-based decisions (this triad's specialty),
        # we evaluate others' proposals carefully

        if is_primary:
            # Primary scope - vote on whether others' proposals are acceptable
            # In production: peers evaluate and vote
            # Default: hold primary scope claims
            return "hold"
        else:
            # Reach scope - more collaborative
            return "revise"

    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate code for owned sections.

        All peers contribute and vote on final code.

        Args:
            frozen_spec: The frozen spec with finalized assignments.

        Returns:
            Dict mapping section names to generated code strings.
        """
        # Identify sections we own
        owned_sections = []
        sections_data = frozen_spec.get("sections", {})

        for section_name, section_info in sections_data.items():
            if isinstance(section_info, dict):
                if section_info.get("owner") == self.config.id:
                    owned_sections.append(section_name)

        if not owned_sections:
            return {}

        results = {}
        for section in owned_sections:
            section_spec = sections_data.get(section, {})

            # Collect code proposals from all peers
            code_proposals = {}
            for peer_name, peer_agent in self.agents.items():
                code = await self._peer_generate_code(peer_agent, section, section_spec)
                code_proposals[peer_name] = code

            # Vote on best code
            final_code = await self._vote_on_code(code_proposals, section_spec)
            results[section] = final_code

        return results

    async def _peer_generate_code(
        self,
        peer: Agent,
        section: str,
        section_spec: Dict[str, Any]
    ) -> str:
        """Peer generates code from their perspective.

        Args:
            peer: The generating peer.
            section: Section name.
            section_spec: Spec for this section.

        Returns:
            Generated code string.
        """
        # TODO: LLM call
        return f"// Code from {peer.role} ({peer.perspective})\n// {section} implementation"

    async def _vote_on_code(
        self,
        code_proposals: Dict[str, str],
        section_spec: Dict[str, Any]
    ) -> str:
        """Peers vote on which code to use (or merge).

        Args:
            code_proposals: Code from each peer.
            section_spec: Spec for context.

        Returns:
            Final code string.
        """
        # TODO: LLM calls for voting
        # Stub: Merge all perspectives
        merged_code = "// Consensus code combining all perspectives\n"
        for peer_name, code in code_proposals.items():
            merged_code += f"\n// From {peer_name}:\n{code}\n"

        return merged_code
