"""Schema models for HFS Agno Teams.

This module provides Pydantic models for session state management,
phase transition summaries, and error handling in Agno Team triads.

Models:
    PhaseSummary: Structured summary for phase transitions
    TriadSessionState: Session state with role-scoped history
    TriadExecutionError: Exception for triad execution failures
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PhaseSummary(BaseModel):
    """Structured summary for phase transitions.

    Per CONTEXT.md: Synthesizer agent produces phase transition summaries
    with predefined sections (decisions, open questions, artifacts).

    Attributes:
        phase: Phase name (deliberation, negotiation, execution)
        decisions: Key decisions made during this phase
        open_questions: Unresolved questions for next phase
        artifacts: Outputs created (section -> content preview)
        produced_by: Agent role that produced this summary
    """
    phase: str = Field(
        ...,
        description="Phase name: deliberation, negotiation, or execution"
    )
    decisions: List[str] = Field(
        default_factory=list,
        description="Key decisions made during this phase"
    )
    open_questions: List[str] = Field(
        default_factory=list,
        description="Unresolved questions for next phase"
    )
    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="Outputs created (section -> content preview)"
    )
    produced_by: str = Field(
        ...,
        description="Agent role that produced this summary"
    )


class TriadSessionState(BaseModel):
    """Session state with role-scoped history for each HFS phase.

    Per CONTEXT.md: Role-scoped history - agents only see messages
    relevant to their role. Summarized handoff between phases.

    Attributes:
        current_phase: Current HFS phase (None if not started)
        deliberation_summary: Summary from deliberation phase
        negotiation_summary: Summary from negotiation phase
        execution_summary: Summary from execution phase
    """
    current_phase: Optional[str] = Field(
        default=None,
        description="Current HFS phase"
    )
    deliberation_summary: Optional[PhaseSummary] = Field(
        default=None,
        description="Summary from deliberation phase"
    )
    negotiation_summary: Optional[PhaseSummary] = Field(
        default=None,
        description="Summary from negotiation phase"
    )
    execution_summary: Optional[PhaseSummary] = Field(
        default=None,
        description="Summary from execution phase"
    )

    def get_phase_context(self, phase: str) -> Dict:
        """Get context to pass to a phase based on previous summaries.

        Args:
            phase: The phase requesting context

        Returns:
            Dict with relevant context from previous phases
        """
        context: Dict = {"phase": phase}

        if phase == "deliberation":
            # Deliberation gets no prior context
            pass
        elif phase == "negotiation":
            # Negotiation gets deliberation summary
            if self.deliberation_summary:
                context["prior_decisions"] = self.deliberation_summary.decisions
                context["open_questions"] = self.deliberation_summary.open_questions
                context["artifacts"] = self.deliberation_summary.artifacts
        elif phase == "execution":
            # Execution gets negotiation summary (which should incorporate deliberation)
            if self.negotiation_summary:
                context["prior_decisions"] = self.negotiation_summary.decisions
                context["open_questions"] = self.negotiation_summary.open_questions
                context["artifacts"] = self.negotiation_summary.artifacts
            # Also include deliberation decisions for full context
            if self.deliberation_summary:
                context["deliberation_decisions"] = self.deliberation_summary.decisions

        return context


class TriadExecutionError(Exception):
    """Exception for triad execution failures.

    Per CONTEXT.md: Abort team run on agent failure, surface error to
    orchestrator level. Include which agent failed, what phase, and
    error message (not full trace). Preserve partial progress.

    Attributes:
        triad_id: Which triad failed
        phase: Which phase (deliberation/negotiation/execution)
        agent: Which agent failed (or "unknown")
        error: Error message (not full trace)
        partial_state: State preserved for retry
    """

    def __init__(
        self,
        triad_id: str,
        phase: str,
        agent: str = "unknown",
        error: str = "",
        partial_state: Optional[Dict] = None,
    ):
        self.triad_id = triad_id
        self.phase = phase
        self.agent = agent
        self.error = error
        self.partial_state = partial_state

        # Build message for Exception base class
        message = f"Triad '{triad_id}' failed in {phase} phase"
        if agent != "unknown":
            message += f" (agent: {agent})"
        if error:
            message += f": {error}"

        super().__init__(message)
