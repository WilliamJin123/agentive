"""Hierarchical Triad preset - orchestrator + 2 workers pattern.

The HierarchicalTriad implements a clear delegation structure:
- orchestrator: plans, decomposes tasks, delegates, integrates results
- worker_a: executes subtask A
- worker_b: executes subtask B

Flow: receive task -> decompose -> parallel execute -> merge -> validate

Best for: layout, state_management, performance, code_generation
"""

from dataclasses import dataclass
from typing import Dict, Any, List

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


class HierarchicalTriad(Triad):
    """Triad with orchestrator directing two workers.

    This preset is designed for execution-heavy work where clear
    delegation and parallel execution are beneficial. The orchestrator
    breaks down work, assigns to workers, and integrates their outputs.

    Internal structure:
        - orchestrator: Plans and coordinates
        - worker_a: Executes first work stream
        - worker_b: Executes second work stream

    Attributes:
        config: The TriadConfig for this triad.
        llm: The LLM client for agent interactions.
        agents: Dict of initialized Agent instances.
    """

    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize orchestrator and two workers.

        Creates three agents with specialized system prompts based on
        the triad's configuration (objectives, scope, etc.).

        Returns:
            Dictionary with keys "orchestrator", "worker_a", "worker_b"
            mapping to Agent instances.
        """
        base_context = self.config.system_context or ""
        objectives_str = ", ".join(self.config.objectives)
        primary_scope = ", ".join(self.config.scope_primary)

        orchestrator = Agent(
            role="orchestrator",
            description="Plans, decomposes tasks, delegates to workers, integrates results",
            system_prompt=f"""You are the orchestrator of triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Analyze incoming tasks and decompose them into subtasks
2. Delegate subtasks to worker_a and worker_b appropriately
3. Integrate worker outputs into coherent results
4. Validate the merged output meets quality standards

You think strategically about task decomposition and ensure workers
have clear, actionable instructions."""
        )

        worker_a = Agent(
            role="worker_a",
            description="Executes first work stream as directed by orchestrator",
            system_prompt=f"""You are worker_a in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Execute subtasks assigned by the orchestrator
2. Focus on your assigned portion of the work
3. Return clear, well-structured outputs
4. Flag any issues or blockers to the orchestrator

You work in parallel with worker_b. Focus on your specific assignment."""
        )

        worker_b = Agent(
            role="worker_b",
            description="Executes second work stream as directed by orchestrator",
            system_prompt=f"""You are worker_b in triad '{self.config.id}'.
Your objectives: {objectives_str}
Your primary scope: {primary_scope}
{base_context}

Your responsibilities:
1. Execute subtasks assigned by the orchestrator
2. Focus on your assigned portion of the work
3. Return clear, well-structured outputs
4. Flag any issues or blockers to the orchestrator

You work in parallel with worker_a. Focus on your specific assignment."""
        )

        return {
            "orchestrator": orchestrator,
            "worker_a": worker_a,
            "worker_b": worker_b,
        }

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Run hierarchical deliberation flow.

        Flow:
        1. Orchestrator analyzes request and decomposes into subtasks
        2. Workers execute their assigned subtasks in parallel
        3. Orchestrator merges worker outputs
        4. Orchestrator validates merged result

        Args:
            user_request: The original user request.
            spec_state: Current state of the shared spec.

        Returns:
            TriadOutput with unified position, claims, and proposals.
        """
        # Phase 1: Orchestrator decomposes the task
        decomposition = await self._orchestrator_decompose(user_request, spec_state)

        # Phase 2: Workers execute their subtasks (conceptually parallel)
        worker_a_output = await self._worker_execute(
            "worker_a",
            decomposition.get("subtask_a", ""),
            spec_state
        )
        worker_b_output = await self._worker_execute(
            "worker_b",
            decomposition.get("subtask_b", ""),
            spec_state
        )

        # Phase 3: Orchestrator merges and validates
        merged_output = await self._orchestrator_merge(
            decomposition,
            worker_a_output,
            worker_b_output,
            spec_state
        )

        # Determine claims based on primary scope and decomposition
        claims = self._determine_claims(decomposition, spec_state)

        return TriadOutput(
            position=merged_output.get("position", ""),
            claims=claims,
            proposals=merged_output.get("proposals", {})
        )

    async def _orchestrator_decompose(
        self,
        user_request: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrator analyzes and decomposes the task.

        Args:
            user_request: The original user request.
            spec_state: Current spec state for context.

        Returns:
            Decomposition dict with subtask_a, subtask_b, and strategy.
        """
        # TODO: Make actual LLM call when llm client is fully integrated
        # For now, return structured stub that demonstrates the flow
        orchestrator = self.agents["orchestrator"]

        # Stub: In production, this would call self.llm with orchestrator.system_prompt
        # and get back a structured decomposition
        return {
            "strategy": f"Decomposition strategy for: {user_request[:50]}...",
            "subtask_a": f"First subtask derived from request",
            "subtask_b": f"Second subtask derived from request",
            "target_sections": list(self.config.scope_primary),
        }

    async def _worker_execute(
        self,
        worker_role: str,
        subtask: str,
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Worker executes their assigned subtask.

        Args:
            worker_role: Either "worker_a" or "worker_b".
            subtask: The subtask to execute.
            spec_state: Current spec state for context.

        Returns:
            Worker's output for their subtask.
        """
        worker = self.agents[worker_role]

        # TODO: Make actual LLM call
        # Stub demonstrating the expected output structure
        return {
            "role": worker_role,
            "completed_subtask": subtask,
            "output": f"Output from {worker_role} for subtask",
            "artifacts": {},
        }

    async def _orchestrator_merge(
        self,
        decomposition: Dict[str, Any],
        worker_a_output: Dict[str, Any],
        worker_b_output: Dict[str, Any],
        spec_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrator merges worker outputs and validates.

        Args:
            decomposition: Original task decomposition.
            worker_a_output: Output from worker_a.
            worker_b_output: Output from worker_b.
            spec_state: Current spec state.

        Returns:
            Merged and validated output with position and proposals.
        """
        # TODO: Make actual LLM call to merge and validate
        # Stub demonstrating the merge flow
        target_sections = decomposition.get("target_sections", [])

        proposals = {}
        for section in target_sections:
            proposals[section] = {
                "from_worker_a": worker_a_output.get("output"),
                "from_worker_b": worker_b_output.get("output"),
                "merged": f"Merged content for {section}",
            }

        return {
            "position": f"Triad {self.config.id} position based on merged worker outputs",
            "proposals": proposals,
            "validation_passed": True,
        }

    def _determine_claims(
        self,
        decomposition: Dict[str, Any],
        spec_state: Dict[str, Any]
    ) -> List[str]:
        """Determine which sections to claim based on decomposition.

        Starts with primary scope, may extend to reach scope based
        on task analysis.

        Args:
            decomposition: Task decomposition from orchestrator.
            spec_state: Current spec state.

        Returns:
            List of section names to claim.
        """
        claims = list(self.config.scope_primary)

        # Could potentially extend to reach scope based on decomposition
        # For now, stick to primary scope

        return claims

    async def negotiate(
        self,
        section: str,
        other_proposals: Dict[str, Any]
    ) -> NegotiationResponse:
        """Respond to negotiation for a contested section.

        Orchestrator evaluates competing proposals and decides strategy:
        - concede: If other proposal is clearly better for this section
        - revise: If we can improve our proposal based on others
        - hold: If our proposal is strong and worth defending

        Args:
            section: Name of the contested section.
            other_proposals: Dict mapping other triad IDs to their proposals.

        Returns:
            "concede", "revise", or "hold"
        """
        # Check if section is in our primary scope (higher priority)
        is_primary = section in self.config.scope_primary
        is_reach = section in self.config.scope_reach

        # TODO: Make LLM call to evaluate proposals
        # Orchestrator evaluates based on:
        # 1. How well other proposals serve the section's needs
        # 2. Whether our proposal is stronger
        # 3. Strategic importance (primary vs reach scope)

        if not is_primary and not is_reach:
            # Outside our scope entirely - shouldn't happen but concede
            return "concede"

        if is_primary:
            # Primary scope - hold by default, may revise
            # In production: LLM evaluates if revision would help
            return "hold"
        else:
            # Reach scope - more willing to concede
            # In production: LLM evaluates strength of our vs their proposal
            return "revise"

    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate code for owned sections.

        After spec is frozen, orchestrator coordinates workers to
        generate actual code/content for sections this triad owns.

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

        # Orchestrator plans code generation
        generation_plan = await self._plan_code_generation(owned_sections, frozen_spec)

        # Workers generate code for their assigned sections
        results = {}
        for section in owned_sections:
            assignment = generation_plan.get(section, {})
            assigned_worker = assignment.get("worker", "worker_a")

            code = await self._generate_section_code(
                assigned_worker,
                section,
                frozen_spec.get("sections", {}).get(section, {})
            )
            results[section] = code

        return results

    async def _plan_code_generation(
        self,
        owned_sections: List[str],
        frozen_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrator plans how to distribute code generation.

        Args:
            owned_sections: Sections this triad owns.
            frozen_spec: The frozen spec.

        Returns:
            Dict mapping section names to generation assignments.
        """
        # TODO: LLM call to plan distribution
        # Stub: Alternate between workers
        plan = {}
        for i, section in enumerate(owned_sections):
            worker = "worker_a" if i % 2 == 0 else "worker_b"
            plan[section] = {"worker": worker, "priority": i}
        return plan

    async def _generate_section_code(
        self,
        worker_role: str,
        section: str,
        section_spec: Dict[str, Any]
    ) -> str:
        """Worker generates code for a specific section.

        Args:
            worker_role: Which worker is generating.
            section: Section name.
            section_spec: Spec content for this section.

        Returns:
            Generated code as string.
        """
        worker = self.agents[worker_role]

        # TODO: LLM call to generate actual code
        # Stub demonstrating expected output
        return f"// Generated by {worker_role} for section: {section}\n// TODO: Actual implementation"
