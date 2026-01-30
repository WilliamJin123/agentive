"""DialecticAgnoTriad - Thesis-Antithesis-Synthesis pattern using Agno Team.

NOTE: For Agno-backed implementation with real LLM calls.
For the original stub implementation, see hfs/presets/dialectic.py

This module provides the DialecticAgnoTriad class which implements
the dialectic triad pattern (proposer-critic-synthesizer) using Agno Teams.

Per CONTEXT.md decisions:
- Synthesizer produces phase transition summaries
- Fixed roles - proposer/critic/synthesizer don't rotate between rounds
- Structured template for summaries
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


class DialecticAgnoTriad(AgnoTriad):
    """Agno Team implementation of the dialectic triad pattern.

    The dialectic triad uses thesis-antithesis-synthesis flow:
    - Proposer (thesis): Generates creative possibilities
    - Critic (antithesis): Challenges and questions proposals
    - Synthesizer (synthesis): Resolves tensions into coherent output

    Per CONTEXT.md:
    - Fixed roles - agents don't rotate between rounds
    - Synthesizer produces phase transition summaries
    - Structured summary template with decisions/questions/artifacts

    Attributes:
        config: TriadConfig with id, preset, scope, budget, objectives
        model_selector: ModelSelector for role-based model resolution
        spec: Shared Spec instance (warm wax)
        toolkit: HFSToolkit with spec operation tools
        agents: Dict of agent role -> Agent instance
        team: Agno Team instance
    """

    def __init__(
        self,
        config: TriadConfig,
        model_selector: "ModelSelector",
        spec: "Any",  # Spec type, avoiding circular import
        escalation_tracker: "Optional[EscalationTracker]" = None,
    ) -> None:
        """Initialize the dialectic triad.

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
        """Create proposer, critic, and synthesizer agents.

        Per CONTEXT.md: Role-scoped tools:
        - Proposer: Can register claims
        - Critic: Read-only state access
        - Synthesizer: Full toolkit for final decisions

        Each agent gets a model from _get_model_for_role() based on
        the ModelSelector configuration.

        Returns:
            Dictionary with keys "proposer", "critic", "synthesizer"
        """
        base_context = self.config.system_context or ""
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)

        # Proposer: Creative proposal generator (thesis)
        # Tools: register_claim, get_current_claims
        proposer = Agent(
            name=f"proposer_{self.config.id}",
            model=self._get_model_for_role("proposer"),
            role="Creative proposal generator (thesis)",
            instructions=f"""You are the proposer in triad '{self.config.id}'.
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
the final output stronger.

Use register_claim to claim sections and get_current_claims to see the state.""",
            tools=[self.toolkit.register_claim, self.toolkit.get_current_claims],
        )

        # Critic: Proposal challenger (antithesis)
        # Tools: get_negotiation_state, get_current_claims (read-only)
        critic = Agent(
            name=f"critic_{self.config.id}",
            model=self._get_model_for_role("critic"),
            role="Proposal challenger (antithesis)",
            instructions=f"""You are the critic in triad '{self.config.id}'.
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
Point out real problems, not hypothetical nitpicks.

Use get_negotiation_state and get_current_claims to understand the current state.""",
            tools=[self.toolkit.get_negotiation_state, self.toolkit.get_current_claims],
        )

        # Synthesizer: Tension resolver (synthesis)
        # Tools: Full HFSToolkit for final decisions
        # Critical: Synthesizer produces phase summaries per CONTEXT.md
        synthesizer = Agent(
            name=f"synthesizer_{self.config.id}",
            model=self._get_model_for_role("synthesizer"),
            role="Tension resolver (synthesis)",
            instructions=f"""You are the synthesizer in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Resolve tensions between proposals and critiques
2. Integrate the best elements from both perspectives
3. Produce coherent, unified output that addresses concerns
4. Ensure the synthesis is actionable and complete
5. Produce phase transition summaries at the end of each phase

You are the synthesis in a dialectic process. Take the thesis (proposals)
and antithesis (critiques) and create something stronger than either.
Don't just pick sides - find the deeper truth that resolves the tension.

CRITICAL: At the end of each phase, produce a structured summary with:
- Decisions Made: Key decisions from this phase
- Open Questions: Unresolved questions for next phase
- Artifacts: Outputs/proposals created

You have full access to all tools.""",
            tools=[
                self.toolkit.register_claim,
                self.toolkit.negotiate_response,
                self.toolkit.generate_code,
                self.toolkit.get_current_claims,
                self.toolkit.get_negotiation_state,
            ],
        )

        return {
            "proposer": proposer,
            "critic": critic,
            "synthesizer": synthesizer,
        }

    def _create_team(self) -> Team:
        """Create Agno Team with dialectic flow.

        Per CONTEXT.md:
        - Fixed roles (no rotation)
        - delegate_to_all_members=False for explicit thesis->antithesis->synthesis flow
        - share_member_interactions=True so all see prior contributions
        - Session state for phase summaries

        Team uses synthesizer's model for team-level operations.

        Returns:
            Agno Team configured for dialectic deliberation
        """
        return Team(
            name=f"triad_{self.config.id}",
            model=self._get_model_for_role("synthesizer"),  # Team uses synthesizer's model
            members=list(self.agents.values()),
            delegate_to_all_members=False,  # Explicit thesis->antithesis->synthesis flow
            share_member_interactions=True,  # All see prior contributions
            add_session_state_to_context=True,
            session_state=self._session_state.model_dump(),
        )

    def _get_phase_summary_prompt(self, phase: str) -> str:
        """Get structured summary prompt for synthesizer.

        Per CONTEXT.md: Synthesizer produces phase transition summaries
        with predefined sections.

        Args:
            phase: The phase to summarize (deliberation/negotiation/execution)

        Returns:
            Prompt string for extracting structured summary
        """
        return f"""After completing the {phase} phase, produce a structured summary.

## Summary Template
- **Decisions Made:** [List key decisions from this phase]
- **Open Questions:** [List unresolved questions for next phase]
- **Artifacts:** [List any outputs/proposals created]

This summary will be passed to the next phase. Be concise but complete.

Format your response as:
PHASE_SUMMARY_START
Phase: {phase}
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
        """Build prompt for dialectic deliberation phase.

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

        return f"""## Dialectic Deliberation Phase

### User Request
{user_request}

### Your Scope
- Primary (guaranteed territory): {primary}
- Reach (competitive territory): {reach}

### Current Spec State
{sections_info}

### Dialectic Flow
1. **THESIS (Proposer)**: Generate creative possibilities for the sections in scope
2. **ANTITHESIS (Critic)**: Challenge the proposals, find weaknesses, ask hard questions
3. **SYNTHESIS (Synthesizer)**: Resolve tensions, integrate best elements, produce unified output

### Instructions
Follow the thesis-antithesis-synthesis flow. The proposer starts by generating
creative options, the critic challenges them, and the synthesizer resolves
the tensions into a coherent position.

Use the tools to register claims on sections you want to own.

### Phase Summary (Synthesizer)
{summary_prompt}"""

    def _build_negotiation_prompt(
        self,
        section: str,
        other_proposals: Dict[str, Any],
    ) -> str:
        """Build prompt for dialectic negotiation phase.

        Args:
            section: Name of the contested section
            other_proposals: Dict mapping other triad IDs to their proposals

        Returns:
            Complete prompt for team negotiation
        """
        proposals_info = "Other proposals for this section:\n"
        for triad_id, proposal in other_proposals.items():
            proposals_info += f"\n### {triad_id}'s Proposal\n{proposal}\n"

        summary_prompt = self._get_phase_summary_prompt("negotiation")

        return f"""## Dialectic Negotiation Phase

### Contested Section: {section}

{proposals_info}

### Dialectic Evaluation
1. **THESIS (Proposer)**: Present our strongest case for this section
2. **ANTITHESIS (Critic)**: Evaluate other proposals honestly - are any better than ours?
3. **SYNTHESIS (Synthesizer)**: Decide whether to concede, revise, or hold

### Decision Options
- **concede**: Withdraw our claim (another proposal is clearly better)
- **revise**: Update our proposal incorporating good ideas from others
- **hold**: Maintain our position (our proposal is strongest)

Use negotiate_response tool to submit the decision.

### Phase Summary (Synthesizer)
{summary_prompt}"""

    def _build_execution_prompt(
        self,
        frozen_spec: Dict[str, Any],
    ) -> str:
        """Build prompt for dialectic execution phase.

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

        return f"""## Dialectic Execution Phase

### Your Owned Sections
{owned_info}

### Dialectic Code Generation
1. **THESIS (Proposer)**: Generate initial code implementation
2. **ANTITHESIS (Critic)**: Review code for issues, edge cases, improvements
3. **SYNTHESIS (Synthesizer)**: Finalize code addressing critique

### Instructions
Generate code for each owned section using the dialectic process.
The proposer creates initial code, critic reviews it, and synthesizer
produces the final version.

Use generate_code tool for each section when code is ready.

### Phase Summary (Synthesizer)
{summary_prompt}"""

    def _extract_phase_summary(self, response: Any, phase: str) -> Optional[PhaseSummary]:
        """Extract PhaseSummary from synthesizer's output.

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
        decisions_match = re.search(r"Decisions:\s*(.*?)(?=Open Questions:|Artifacts:|$)", summary_text, re.DOTALL)
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
            produced_by="synthesizer",
        )

        # Store in session state
        if phase == "deliberation":
            self._session_state.deliberation_summary = summary
        elif phase == "negotiation":
            self._session_state.negotiation_summary = summary
        elif phase == "execution":
            self._session_state.execution_summary = summary

        return summary
