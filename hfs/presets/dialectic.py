"""Dialectic Triad preset - thesis-antithesis-synthesis pattern.

NOTE: For Agno-backed implementation with real LLM calls, use:
from hfs.agno.teams import DialecticAgnoTriad

This module provides the original stub implementation for reference
and backwards compatibility during migration.

The DialecticTriad implements a creative tension structure:
- proposer: generates candidates and possibilities (thesis)
- critic: finds flaws, asks hard questions (antithesis)
- synthesizer: resolves tensions into coherent output (synthesis)

Flow: propose -> critique -> revise -> synthesize

Best for: visual_design, motion_design, interaction_patterns, creative_decisions
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from ..core.triad import (
    Triad,
    TriadConfig,
    TriadOutput,
    NegotiationResponse,
)


@dataclass
class Agent:
    """Simple agent representation with role and system prompt.

    Attributes:
        role: The role name for this agent.
        system_prompt: The system-level instructions for this agent.
        description: Human-readable description of this agent's purpose.
    """
    role: str
    system_prompt: str
    description: str


class DialecticTriad(Triad):
    """Triad using thesis-antithesis-synthesis deliberation.

    This preset is designed for creative and ambiguous work where
    exploring tensions and alternatives leads to better outcomes.
    The proposer generates options, critic challenges them, and
    synthesizer resolves the tension.

    Internal structure:
        - proposer: Generates possibilities (thesis)
        - critic: Challenges and questions (antithesis)
        - synthesizer: Resolves into coherent output (synthesis)

    Attributes:
        config: The TriadConfig for this triad.
        llm: The LLM client for agent interactions.
        agents: Dict of initialized Agent instances.
    """

    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize proposer, critic, and synthesizer.

        Creates three agents with specialized system prompts for
        the dialectic process.

        Returns:
            Dictionary with keys "proposer", "critic", "synthesizer"
            mapping to Agent instances.
        """
        base_context = self.config.system_context or ""
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)

        proposer = Agent(
            role="proposer",
            description="Generates candidates, possibilities, and creative options",
            system_prompt=f"""You are the proposer in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Generate multiple creative possibilities and candidates
2. Explore the design space broadly before narrowing
3. Propose bold, innovative solutions
4. Consider edge cases and alternative approaches

You are the thesis in a dialectic process. Be generative and creative.
Your proposals will be challenged by the critic - that's good, it makes
the final output stronger."""
        )

        critic = Agent(
            role="critic",
            description="Finds flaws, asks hard questions, challenges assumptions",
            system_prompt=f"""You are the critic in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Find flaws, weaknesses, and gaps in proposals
2. Ask hard questions that expose assumptions
3. Consider failure modes and edge cases
4. Challenge whether proposals truly meet objectives

You are the antithesis in a dialectic process. Be rigorous but constructive.
Your role is not to destroy but to strengthen through challenge.
Point out real problems, not hypothetical nitpicks."""
        )

        synthesizer = Agent(
            role="synthesizer",
            description="Resolves tensions into coherent, unified output",
            system_prompt=f"""You are the synthesizer in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Resolve tensions between proposals and critiques
2. Integrate the best elements from both perspectives
3. Produce coherent, unified output that addresses concerns
4. Ensure the synthesis is actionable and complete

You are the synthesis in a dialectic process. Take the thesis (proposals)
and antithesis (critiques) and create something stronger than either.
Don't just pick sides - find the deeper truth that resolves the tension."""
        )

        return {
            "proposer": proposer,
            "critic": critic,
            "synthesizer": synthesizer,
        }

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Run dialectic deliberation flow.

        Flow:
        1. Proposer generates initial candidates (thesis)
        2. Critic challenges and questions (antithesis)
        3. Proposer revises based on critique
        4. Synthesizer resolves into final output (synthesis)

        This may iterate multiple rounds if needed.

        Args:
            user_request: The original user request.
            spec_state: Current state of the shared spec.

        Returns:
            TriadOutput with synthesized position, claims, and proposals.
        """
        # Phase 1: Proposer generates initial candidates
        proposals = await self._proposer_generate(user_request, spec_state)

        # Phase 2: Critic challenges the proposals
        critique = await self._critic_challenge(proposals, user_request, spec_state)

        # Phase 3: Proposer revises based on critique
        revised_proposals = await self._proposer_revise(proposals, critique, spec_state)

        # Phase 4: Synthesizer resolves into final output
        synthesis = await self._synthesizer_resolve(
            proposals,
            critique,
            revised_proposals,
            user_request,
            spec_state
        )

        # Determine claims based on synthesis
        claims = self._determine_claims(synthesis, spec_state)

        return TriadOutput(
            position=synthesis.get("position", ""),
            claims=claims,
            proposals=synthesis.get("proposals", {})
        )

    async def _proposer_generate(
        self,
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Proposer generates initial candidates.

        Args:
            user_request: The original user request.
            spec_state: Current spec state for context.

        Returns:
            Dict with candidates, rationale, and target sections.
        """
        proposer = self.agents["proposer"]

        # TODO: Make actual LLM call
        # Stub demonstrating expected output structure
        return {
            "candidates": [
                {
                    "id": "option_a",
                    "description": f"First creative option for: {user_request[:30]}...",
                    "rationale": "Prioritizes innovation",
                },
                {
                    "id": "option_b",
                    "description": "Second alternative approach",
                    "rationale": "Prioritizes consistency",
                },
            ],
            "target_sections": list(self.config.scope_primary),
            "design_rationale": "Exploring the design space broadly",
        }

    async def _critic_challenge(
        self,
        proposals: Dict[str, Any],
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Critic challenges the proposals.

        Args:
            proposals: The proposer's initial candidates.
            user_request: Original request for context.
            spec_state: Current spec state.

        Returns:
            Dict with concerns, questions, and ratings for each candidate.
        """
        critic = self.agents["critic"]

        # TODO: Make actual LLM call
        # Stub demonstrating critique structure
        candidates = proposals.get("candidates", [])

        critique = {
            "overall_concerns": [
                "Need to verify accessibility implications",
                "Performance impact unclear",
            ],
            "candidate_critiques": {},
            "hard_questions": [
                "How does this handle edge case X?",
                "What happens when Y fails?",
            ],
        }

        for candidate in candidates:
            critique["candidate_critiques"][candidate["id"]] = {
                "strengths": ["Creative approach"],
                "weaknesses": ["May not scale"],
                "questions": ["How does this interact with...?"],
                "recommendation": "revise",
            }

        return critique

    async def _proposer_revise(
        self,
        original_proposals: Dict[str, Any],
        critique: Dict[str, Any],
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Proposer revises based on critique.

        Args:
            original_proposals: Initial proposals.
            critique: Critic's challenges.
            spec_state: Current spec state.

        Returns:
            Dict with revised candidates addressing concerns.
        """
        proposer = self.agents["proposer"]

        # TODO: Make actual LLM call
        # Stub showing revision structure
        return {
            "revised_candidates": [
                {
                    "id": "option_a_revised",
                    "original_id": "option_a",
                    "description": "Revised option A addressing concerns",
                    "changes_made": ["Added edge case handling", "Improved scalability"],
                    "concerns_addressed": critique.get("overall_concerns", []),
                },
            ],
            "unresolved_concerns": [],
            "revision_rationale": "Incorporated critic feedback while maintaining core vision",
        }

    async def _synthesizer_resolve(
        self,
        original_proposals: Dict[str, Any],
        critique: Dict[str, Any],
        revised_proposals: Dict[str, Any],
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesizer resolves the dialectic into final output.

        Args:
            original_proposals: Initial proposals (thesis).
            critique: Critic's challenges (antithesis).
            revised_proposals: Revised proposals.
            user_request: Original request.
            spec_state: Current spec state.

        Returns:
            Dict with final position, proposals, and rationale.
        """
        synthesizer = self.agents["synthesizer"]

        # TODO: Make actual LLM call
        # Stub demonstrating synthesis output
        target_sections = original_proposals.get("target_sections", [])

        proposals = {}
        for section in target_sections:
            proposals[section] = {
                "content": f"Synthesized content for {section}",
                "from_thesis": "Elements from original proposals",
                "from_antithesis": "Concerns addressed from critique",
                "resolution": "How tension was resolved",
            }

        return {
            "position": f"Triad {self.config.id} synthesized position resolving creative tensions",
            "proposals": proposals,
            "synthesis_rationale": "Integrated best elements while addressing all concerns",
            "resolution_summary": {
                "tensions_resolved": len(critique.get("overall_concerns", [])),
                "candidates_merged": True,
            },
        }

    def _determine_claims(
        self,
        synthesis: Dict[str, Any],
        spec_state: Dict[str, Any]
    ) -> List[str]:
        """Determine which sections to claim based on synthesis.

        Args:
            synthesis: The synthesized output.
            spec_state: Current spec state.

        Returns:
            List of section names to claim.
        """
        # Start with sections from synthesis proposals
        synthesis_sections = list(synthesis.get("proposals", {}).keys())

        # Ensure primary scope is included
        claims = list(set(synthesis_sections + list(self.config.scope_primary)))

        return claims

    async def negotiate(
        self,
        section: str,
        other_proposals: Dict[str, Any]
    ) -> NegotiationResponse:
        """Respond to negotiation for a contested section.

        Uses dialectic process: critic evaluates other proposals,
        synthesizer determines if we can create something better
        by incorporating their ideas.

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

        # TODO: LLM calls for critic and synthesizer evaluation
        # Critic evaluates other proposals
        # Synthesizer determines if synthesis would improve our position

        # For creative work (dialectic specialty), we're more likely
        # to revise - incorporating others' ideas often improves outcomes
        if is_primary:
            # Primary scope: attempt synthesis first
            # In production: synthesizer evaluates if combining is beneficial
            return "revise"
        else:
            # Reach scope: more willing to concede unless we have strong position
            return "concede"

    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate code for owned sections.

        Uses dialectic process even for code generation:
        - Proposer generates initial code
        - Critic reviews for issues
        - Synthesizer finalizes

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

            # Dialectic code generation flow
            initial_code = await self._proposer_generate_code(section, section_spec)
            code_critique = await self._critic_review_code(initial_code, section_spec)
            final_code = await self._synthesizer_finalize_code(
                initial_code,
                code_critique,
                section_spec
            )

            results[section] = final_code

        return results

    async def _proposer_generate_code(
        self,
        section: str,
        section_spec: Dict[str, Any]
    ) -> str:
        """Proposer generates initial code.

        Args:
            section: Section name.
            section_spec: Spec for this section.

        Returns:
            Initial code string.
        """
        # TODO: LLM call
        return f"// Initial code proposal for {section}\n// Creative implementation"

    async def _critic_review_code(
        self,
        code: str,
        section_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Critic reviews code for issues.

        Args:
            code: Code to review.
            section_spec: Spec for context.

        Returns:
            Dict with issues and suggestions.
        """
        # TODO: LLM call
        return {
            "issues": [],
            "suggestions": ["Consider edge case handling"],
            "approval": True,
        }

    async def _synthesizer_finalize_code(
        self,
        code: str,
        critique: Dict[str, Any],
        section_spec: Dict[str, Any]
    ) -> str:
        """Synthesizer finalizes code addressing critique.

        Args:
            code: Initial code.
            critique: Critic's review.
            section_spec: Spec for context.

        Returns:
            Final code string.
        """
        # TODO: LLM call
        if critique.get("approval"):
            return code + "\n// Approved by critic"
        else:
            return code + "\n// Revised based on critique"
