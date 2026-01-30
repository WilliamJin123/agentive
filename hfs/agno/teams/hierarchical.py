"""HierarchicalAgnoTriad - Orchestrator + 2 workers pattern as Agno Team.

This module implements the hierarchical triad preset where an orchestrator
decomposes tasks, delegates to workers, and integrates results. Uses Agno Team
for real LLM coordination with orchestrator-directed delegation (not broadcast).

Per CONTEXT.md decisions:
- Orchestrator-directed turns (delegate_to_all_members=False)
- Role-specific tools (orchestrator: full toolkit, workers: generate_code only)
- Session state for context (add_session_state_to_context=True)
"""

from typing import TYPE_CHECKING, Dict, Any, List, Callable, Optional

from agno.team import Team
from agno.agent import Agent
from agno.tools.toolkit import Toolkit

from hfs.core.triad import TriadConfig, TriadOutput, NegotiationResponse
from hfs.agno.tools import HFSToolkit
from .base import AgnoTriad
from .schemas import PhaseSummary

if TYPE_CHECKING:
    from hfs.core.model_selector import ModelSelector
    from hfs.core.escalation_tracker import EscalationTracker


class WorkerToolkit(Toolkit):
    """Limited toolkit for workers - only generate_code access.

    Per CONTEXT.md: Workers have limited tools (generate_code only),
    while orchestrator has full toolkit access.
    """

    def __init__(self, parent_toolkit: HFSToolkit, **kwargs):
        """Initialize worker toolkit with limited tools.

        Args:
            parent_toolkit: The HFSToolkit to extract generate_code from
            **kwargs: Additional args passed to Toolkit base
        """
        self._parent = parent_toolkit

        tools: List[Callable] = [
            self.generate_code,
        ]

        super().__init__(name="worker_tools", tools=tools, **kwargs)

    def generate_code(self, section_id: str) -> str:
        """Generate implementation code for a section.

        Delegates to the parent toolkit's generate_code method.

        Args:
            section_id: The section to generate code for

        Returns:
            JSON with generated code or error.
        """
        return self._parent.generate_code(section_id)


class HierarchicalAgnoTriad(AgnoTriad):
    """Hierarchical triad with orchestrator directing two workers.

    This preset implements clear delegation where the orchestrator:
    - Decomposes tasks into subtasks
    - Delegates to worker_a and worker_b
    - Integrates worker outputs
    - Validates the merged result

    Team Configuration:
    - delegate_to_all_members=False (orchestrator directs explicitly)
    - share_member_interactions=True (orchestrator sees worker results)
    - add_session_state_to_context=True (pass state to prompts)

    Attributes:
        config: TriadConfig with id, preset, scope, budget, objectives
        model_selector: ModelSelector for role-based model resolution
        spec: Shared Spec instance (warm wax)
        toolkit: HFSToolkit with full spec operation tools
        worker_toolkit: WorkerToolkit with limited tools (generate_code only)
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
        """Initialize the hierarchical triad.

        Creates worker toolkit before calling parent init.

        Args:
            config: Configuration for this triad
            model_selector: ModelSelector for role-based model resolution.
                Models are obtained via _get_model_for_role() in _create_agents().
            spec: Shared Spec instance for claim/negotiation operations
            escalation_tracker: Optional tracker for failure-adaptive tier escalation
        """
        # Call parent init (which creates toolkit, agents, team)
        super().__init__(
            config=config,
            model_selector=model_selector,
            spec=spec,
            escalation_tracker=escalation_tracker,
        )

    def _create_agents(self) -> Dict[str, Agent]:
        """Create orchestrator and two worker agents.

        Per CONTEXT.md:
        - Orchestrator: Full HFSToolkit access, coordinates work
        - Workers: Limited tools (generate_code only), execute subtasks

        Each agent gets a model from _get_model_for_role() based on
        the ModelSelector configuration.

        Returns:
            Dictionary with keys "orchestrator", "worker_a", "worker_b"
        """
        # Build context strings from config
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)
        reach_scope = ", ".join(self.config.scope_reach) if self.config.scope_reach else "none"
        base_context = self.config.system_context or ""

        # Create worker toolkit with limited tools
        worker_toolkit = WorkerToolkit(parent_toolkit=self.toolkit)

        # Create orchestrator with full toolkit
        orchestrator = Agent(
            name=f"{self.config.id}_orchestrator",
            role="Task coordinator and integrator",
            model=self._get_model_for_role("orchestrator"),
            tools=[self.toolkit],
            instructions=f"""You are the orchestrator of triad '{self.config.id}'.

OBJECTIVES: {objectives_str}
PRIMARY SCOPE (owned sections): {primary_scope}
REACH SCOPE (can claim): {reach_scope}
{base_context}

YOUR RESPONSIBILITIES:
1. Analyze incoming tasks and decompose them into subtasks
2. Delegate subtasks to worker_a and worker_b appropriately
3. Use your tools to register claims and manage spec sections
4. Integrate worker outputs into coherent results
5. Validate the merged output meets quality standards
6. Produce phase summaries with decisions, open questions, and artifacts

TOOLS AVAILABLE:
- register_claim: Claim ownership of spec sections
- negotiate_response: Respond during negotiation (concede/revise/hold)
- generate_code: Generate code for owned sections
- get_current_claims: View current claim state
- get_negotiation_state: View negotiation details

You think strategically about task decomposition and ensure workers
have clear, actionable instructions. Always produce structured outputs.""",
            add_datetime_to_context=True,
        )

        # Create worker_a with limited tools
        worker_a = Agent(
            name=f"{self.config.id}_worker_a",
            role="Subtask executor",
            model=self._get_model_for_role("worker_a"),
            tools=[worker_toolkit],
            instructions=f"""You are worker_a in triad '{self.config.id}'.

OBJECTIVES: {objectives_str}
PRIMARY SCOPE: {primary_scope}
{base_context}

YOUR RESPONSIBILITIES:
1. Execute subtasks assigned by the orchestrator
2. Focus on your assigned portion of the work
3. Return clear, well-structured outputs
4. Flag any issues or blockers to the orchestrator

You work in parallel with worker_b. Focus ONLY on your specific assignment.
Do not attempt to coordinate with worker_b directly - let the orchestrator handle that.

TOOL AVAILABLE:
- generate_code: Generate implementation code for sections""",
            add_datetime_to_context=True,
        )

        # Create worker_b with limited tools
        worker_b = Agent(
            name=f"{self.config.id}_worker_b",
            role="Subtask executor",
            model=self._get_model_for_role("worker_b"),
            tools=[worker_toolkit],
            instructions=f"""You are worker_b in triad '{self.config.id}'.

OBJECTIVES: {objectives_str}
PRIMARY SCOPE: {primary_scope}
{base_context}

YOUR RESPONSIBILITIES:
1. Execute subtasks assigned by the orchestrator
2. Focus on your assigned portion of the work
3. Return clear, well-structured outputs
4. Flag any issues or blockers to the orchestrator

You work in parallel with worker_a. Focus ONLY on your specific assignment.
Do not attempt to coordinate with worker_a directly - let the orchestrator handle that.

TOOL AVAILABLE:
- generate_code: Generate implementation code for sections""",
            add_datetime_to_context=True,
        )

        return {
            "orchestrator": orchestrator,
            "worker_a": worker_a,
            "worker_b": worker_b,
        }

    def _create_team(self) -> Team:
        """Create Agno Team with orchestrator-directed delegation.

        Per CONTEXT.md:
        - delegate_to_all_members=False (orchestrator directs explicitly)
        - share_member_interactions=True (orchestrator sees worker results)
        - add_session_state_to_context=True (pass state to prompts)

        Team uses orchestrator's model for team-level operations.

        Returns:
            Configured Agno Team instance
        """
        return Team(
            name=f"triad_{self.config.id}",
            model=self._get_model_for_role("orchestrator"),  # Team uses orchestrator's model
            members=list(self.agents.values()),
            delegate_to_all_members=False,  # Orchestrator directs explicitly
            share_member_interactions=True,  # Orchestrator sees worker results
            add_session_state_to_context=True,  # Pass state to prompts
            session_state=self._session_state.model_dump(),
            instructions=f"""This is hierarchical triad '{self.config.id}'.

The orchestrator decomposes tasks, delegates to workers, and integrates results.
Workers execute their assigned subtasks and report back.

OBJECTIVES: {", ".join(self.config.objectives)}
PRIMARY SCOPE: {", ".join(self.config.scope_primary)}

Work together to produce high-quality outputs for your assigned sections.""",
        )

    def _get_phase_summary_prompt(self, phase: str) -> str:
        """Get prompt for orchestrator to produce structured phase summary.

        Args:
            phase: The phase to summarize (deliberation/negotiation/execution)

        Returns:
            Prompt string for extracting structured summary
        """
        return f"""Summarize the {phase} phase that just completed.

Produce a structured summary with:
1. KEY DECISIONS: List the most important decisions made
2. OPEN QUESTIONS: Any unresolved issues for the next phase
3. ARTIFACTS: What was produced (section -> brief description)

Format your response as:
PHASE: {phase}
PRODUCED_BY: orchestrator

DECISIONS:
- [decision 1]
- [decision 2]
...

OPEN_QUESTIONS:
- [question 1]
...

ARTIFACTS:
- [section]: [description]
..."""

    def _build_deliberation_prompt(
        self,
        user_request: str,
        spec_state: Dict[str, Any],
    ) -> str:
        """Build prompt for hierarchical deliberation.

        Flow:
        1. Orchestrator analyzes request and decomposes
        2. Orchestrator delegates to workers
        3. Workers execute subtasks
        4. Orchestrator integrates and validates

        Args:
            user_request: The original user request
            spec_state: Current state of the shared spec

        Returns:
            Complete prompt for team deliberation
        """
        sections_str = ", ".join(spec_state.get("sections", {}).keys()) if spec_state.get("sections") else "none defined yet"

        return f"""DELIBERATION PHASE for triad '{self.config.id}'

USER REQUEST:
{user_request}

CURRENT SPEC STATE:
- Sections: {sections_str}
- Temperature: {spec_state.get("temperature", "unknown")}

YOUR TASK:
1. Orchestrator: Analyze the request and identify which sections to claim
2. Orchestrator: Decompose work into subtasks for workers
3. Orchestrator: Delegate subtask A to worker_a, subtask B to worker_b
4. Workers: Execute your assigned subtasks
5. Orchestrator: Integrate worker outputs and register claims

OBJECTIVES: {", ".join(self.config.objectives)}
PRIMARY SCOPE (must claim): {", ".join(self.config.scope_primary)}
REACH SCOPE (can claim): {", ".join(self.config.scope_reach) if self.config.scope_reach else "none"}

Use register_claim to claim sections and submit proposals.
Return your integrated position, claims list, and proposals."""

    def _build_negotiation_prompt(
        self,
        section: str,
        other_proposals: Dict[str, Any],
    ) -> str:
        """Build prompt for hierarchical negotiation.

        The orchestrator leads the negotiation decision, evaluating
        other proposals against our own.

        Args:
            section: Name of the contested section
            other_proposals: Dict mapping other triad IDs to their proposals

        Returns:
            Complete prompt for team negotiation
        """
        proposals_str = "\n".join([
            f"- {triad_id}: {str(proposal)[:200]}..."
            for triad_id, proposal in other_proposals.items()
        ])

        is_primary = section in self.config.scope_primary
        scope_type = "PRIMARY (high priority)" if is_primary else "REACH (lower priority)"

        return f"""NEGOTIATION PHASE for triad '{self.config.id}'

CONTESTED SECTION: {section}
SECTION IMPORTANCE: {scope_type}

OTHER PROPOSALS:
{proposals_str}

YOUR TASK:
Orchestrator: Evaluate the competing proposals and decide:
- CONCEDE: If another proposal is clearly better for this section
- REVISE: If we can improve our proposal based on others
- HOLD: If our proposal is strong and worth defending

Consider:
1. How well does each proposal serve the section's purpose?
2. Is our proposal stronger or weaker than competitors?
3. Strategic importance based on scope (primary vs reach)

Use negotiate_response tool to submit your decision.
If revising, include an improved proposal."""

    def _build_execution_prompt(
        self,
        frozen_spec: Dict[str, Any],
    ) -> str:
        """Build prompt for hierarchical execution.

        Orchestrator assigns sections to workers for code generation.

        Args:
            frozen_spec: The frozen spec with finalized section assignments

        Returns:
            Complete prompt for team execution
        """
        # Identify owned sections
        owned_sections = []
        sections_data = frozen_spec.get("sections", {})

        for section_name, section_info in sections_data.items():
            if isinstance(section_info, dict):
                if section_info.get("owner") == self.config.id:
                    owned_sections.append(section_name)

        if not owned_sections:
            return f"""EXECUTION PHASE for triad '{self.config.id}'

No sections owned by this triad. Execution complete."""

        sections_str = ", ".join(owned_sections)

        return f"""EXECUTION PHASE for triad '{self.config.id}'

OWNED SECTIONS: {sections_str}

FROZEN SPEC:
{frozen_spec}

YOUR TASK:
1. Orchestrator: Plan code generation, assign sections to workers
2. Orchestrator: Delegate specific sections to worker_a and worker_b
3. Workers: Generate code using generate_code tool for assigned sections
4. Orchestrator: Review and integrate generated code

Use generate_code tool for each owned section.
Return the generated code mapped to section names."""

    def _parse_deliberation_result(self, result: Any) -> TriadOutput:
        """Parse team deliberation result into TriadOutput.

        Args:
            result: Raw result from team.arun()

        Returns:
            Structured TriadOutput
        """
        # Extract position from result
        position = str(result) if result else ""

        # Claims should have been registered via tools
        # Check spec for our claims
        claims = [
            name for name, section in self.spec.sections.items()
            if self.config.id in section.claims
        ] if hasattr(self.spec, 'sections') else []

        # Proposals from spec
        proposals = {}
        if hasattr(self.spec, 'sections'):
            for name, section in self.spec.sections.items():
                if self.config.id in section.claims:
                    proposals[name] = section.proposals.get(self.config.id, "")

        return TriadOutput(
            position=position,
            claims=claims,
            proposals=proposals,
        )

    def _parse_negotiation_result(self, result: Any) -> NegotiationResponse:
        """Parse team negotiation result into NegotiationResponse.

        Args:
            result: Raw result from team.arun()

        Returns:
            One of "concede", "revise", or "hold"
        """
        response_str = str(result).lower().strip() if result else ""

        if "concede" in response_str:
            return "concede"
        elif "revise" in response_str:
            return "revise"
        else:
            return "hold"

    def _parse_execution_result(self, result: Any) -> Dict[str, str]:
        """Parse team execution result into code mapping.

        Args:
            result: Raw result from team.arun()

        Returns:
            Dictionary mapping section names to generated code
        """
        # Placeholder - actual parsing depends on result format
        # In production, parse structured output from team
        return {}
