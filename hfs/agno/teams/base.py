"""AgnoTriad base class for HFS triads.

This module provides the abstract base class that wraps Agno Team for HFS triads.
All three triad implementations (Hierarchical, Dialectic, Consensus) extend this.

Per CONTEXT.md decisions:
- Role-scoped history via session_state (NOT add_history_to_context)
- Abort on failure, preserve partial progress
- Synthesizer/orchestrator produces phase summaries

Use create_agno_triad() for ModelSelector-based triads (new API).
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Dict, Any, Optional, TYPE_CHECKING
import json
import os
import time
from pathlib import Path

from opentelemetry.trace import Status, StatusCode

from hfs.observability import get_tracer, get_meter
from hfs.observability.tracing import truncate_prompt

from agno.team import Team
from agno.agent import Agent
from agno.models.base import Model

from hfs.core.triad import TriadConfig, TriadOutput, NegotiationResponse
from hfs.agno.tools import HFSToolkit
from .schemas import PhaseSummary, TriadSessionState, TriadExecutionError

if TYPE_CHECKING:
    from hfs.core.spec import Spec
    from hfs.core.model_selector import ModelSelector
    from hfs.core.escalation_tracker import EscalationTracker


# Module-level tracer and metrics (lazy initialization)
_tracer = None
_meter = None
_triad_duration = None
_agent_duration = None
_tokens_prompt = None
_tokens_completion = None


def _get_tracer():
    """Get tracer for triad spans, initializing lazily."""
    global _tracer
    if _tracer is None:
        _tracer = get_tracer("hfs.agno.triad")
    return _tracer


def _get_agent_metrics():
    """Get metrics instruments for triad/agent tracking, initializing lazily."""
    global _meter, _triad_duration, _agent_duration, _tokens_prompt, _tokens_completion
    if _meter is None:
        _meter = get_meter("hfs.agno.triad")
        _triad_duration = _meter.create_histogram(
            "hfs.triad.duration", unit="s", description="Duration of triad execution"
        )
        _agent_duration = _meter.create_histogram(
            "hfs.agent.duration", unit="s", description="Duration of agent execution"
        )
        _tokens_prompt = _meter.create_counter(
            "hfs.tokens.prompt", unit="{token}", description="Prompt tokens used"
        )
        _tokens_completion = _meter.create_counter(
            "hfs.tokens.completion", unit="{token}", description="Completion tokens used"
        )
    return _triad_duration, _agent_duration, _tokens_prompt, _tokens_completion


class AgnoTriad(ABC):
    """Abstract base class for Agno-based HFS triads.

    Wraps Agno Team to provide HFS-specific functionality including
    session state management, error handling, and phase transitions.

    Subclasses must implement:
    - _create_agents(): Create the 3 agents for this triad type
    - _create_team(): Create the Agno Team with agents
    - _get_phase_summary_prompt(): Template for summary extraction
    - _build_deliberation_prompt(): Prompt for deliberation phase
    - _build_negotiation_prompt(): Prompt for negotiation phase
    - _build_execution_prompt(): Prompt for execution phase

    Attributes:
        config: TriadConfig with id, preset, scope, budget, objectives
        model_selector: ModelSelector for role-based model resolution
        model: Legacy attribute, set to None (subclasses should use _get_model_for_role)
        spec: Shared Spec instance (warm wax)
        toolkit: HFSToolkit with spec operation tools
        escalation_tracker: Optional EscalationTracker for failure-adaptive escalation
        agents: Dict of agent role -> Agent instance
        team: Agno Team instance
        _session_state: TriadSessionState for phase context
    """

    def __init__(
        self,
        config: TriadConfig,
        model_selector: "ModelSelector",
        spec: "Spec",
        escalation_tracker: Optional["EscalationTracker"] = None,
    ) -> None:
        """Initialize the Agno-based triad.

        Args:
            config: Configuration for this triad
            model_selector: ModelSelector for role-based model resolution.
                Subclasses should call _get_model_for_role(role_name) to get
                models for each agent in _create_agents().
            spec: Shared Spec instance for claim/negotiation operations
            escalation_tracker: Optional tracker for failure-adaptive tier escalation.
                If provided, success/failure will be recorded after phase execution.
        """
        self.config = config
        self.model_selector = model_selector
        self.spec = spec
        self.escalation_tracker = escalation_tracker

        # Legacy attribute - kept for backward compat, subclasses should use _get_model_for_role
        self.model = None

        # Create toolkit with spec access
        self.toolkit = HFSToolkit(spec=spec, triad_id=config.id)

        # Initialize session state BEFORE creating team (team may need it)
        self._session_state = TriadSessionState()

        # Initialize agents and team (subclass implementations)
        self.agents = self._create_agents()
        self.team = self._create_team()

    def _get_model_for_role(self, role: str, phase: Optional[str] = None) -> Model:
        """Get model for a specific agent role using ModelSelector.

        Subclasses should call this method in _create_agents() to get
        the appropriate model for each agent role.

        Args:
            role: Agent role name (e.g., "orchestrator", "worker_a")
            phase: Optional phase name for phase-specific tier overrides

        Returns:
            Agno Model instance for the specified role

        Note:
            The phase parameter currently only applies at triad instantiation time
            (when _create_agents is called), NOT at execution runtime. This is because
            Agno agents are created once with their model assignment and cannot be
            dynamically swapped during execution. For execution-phase specific models,
            use the "code_execution" role in role_defaults and call this method with
            role="code_execution" when creating agents that run during execution phase.
            Dynamic phase-based model swapping is planned for a future release.
        """
        return self.model_selector.get_model(self.config.id, role, phase)

    @abstractmethod
    def _create_agents(self) -> Dict[str, Agent]:
        """Create the 3 agents for this triad type.

        Subclasses should call self._get_model_for_role(role_name) to get
        the appropriate model for each agent based on the ModelSelector.

        Returns:
            Dictionary mapping agent role names to Agent instances.
            The structure depends on the preset:
            - hierarchical: {"orchestrator", "worker_a", "worker_b"}
            - dialectic: {"proposer", "critic", "synthesizer"}
            - consensus: {"peer_1", "peer_2", "peer_3"}
        """
        pass

    @abstractmethod
    def _create_team(self) -> Team:
        """Create the Agno Team with configured agents.

        Returns:
            Agno Team instance configured for this triad type
        """
        pass

    @abstractmethod
    def _get_phase_summary_prompt(self, phase: str) -> str:
        """Get the prompt template for extracting phase summary.

        Per CONTEXT.md: Synthesizer agent produces phase transition
        summaries with predefined sections.

        Args:
            phase: The phase to summarize (deliberation/negotiation/execution)

        Returns:
            Prompt string for extracting structured summary
        """
        pass

    @abstractmethod
    def _build_deliberation_prompt(
        self,
        user_request: str,
        spec_state: Dict[str, Any],
    ) -> str:
        """Build the prompt for deliberation phase.

        Args:
            user_request: The original user request
            spec_state: Current state of the shared spec

        Returns:
            Complete prompt for team deliberation
        """
        pass

    @abstractmethod
    def _build_negotiation_prompt(
        self,
        section: str,
        other_proposals: Dict[str, Any],
    ) -> str:
        """Build the prompt for negotiation phase.

        Args:
            section: Name of the contested section
            other_proposals: Dict mapping other triad IDs to their proposals

        Returns:
            Complete prompt for team negotiation
        """
        pass

    @abstractmethod
    def _build_execution_prompt(
        self,
        frozen_spec: Dict[str, Any],
    ) -> str:
        """Build the prompt for execution phase.

        Args:
            frozen_spec: The frozen spec with finalized section assignments

        Returns:
            Complete prompt for team execution
        """
        pass

    async def _run_with_error_handling(
        self,
        phase: str,
        prompt: str,
    ) -> Any:
        """Run team with error handling, state preservation, and tracing.

        Per CONTEXT.md: Abort on failure, preserve partial progress,
        raise TriadExecutionError with context.

        Creates a triad-level span that wraps the entire execution and
        records token usage, duration, and success/failure status.

        Args:
            phase: Current phase name
            prompt: The prompt to send to the team

        Returns:
            Team response on success

        Raises:
            TriadExecutionError: On any failure with context preserved
        """
        tracer = _get_tracer()
        triad_duration, agent_duration, tokens_prompt, tokens_completion = _get_agent_metrics()

        with tracer.start_as_current_span(f"hfs.triad.{self.config.id}") as triad_span:
            # Set triad span attributes
            triad_span.set_attribute("hfs.triad.id", self.config.id)
            triad_span.set_attribute("hfs.triad.type", self.config.preset.value)
            triad_span.set_attribute("hfs.triad.phase", phase)
            triad_span.set_attribute("hfs.triad.prompt_snippet", truncate_prompt(prompt))
            triad_span.set_attribute("hfs.triad.agent_roles", list(self.agents.keys()))

            # Record tier info if model_selector available
            if self.model_selector:
                agent_roles = list(self.agents.keys())
                if agent_roles:
                    lead_role = agent_roles[0]  # e.g., "orchestrator"
                    tier = self.model_selector.get_current_tier(self.config.id, lead_role)
                    if tier:
                        triad_span.set_attribute("hfs.triad.tier", tier)

            triad_start = time.time()
            try:
                # Update current phase in session state
                self._session_state.current_phase = phase

                # Run the team
                response = await self.team.arun(prompt)

                duration = time.time() - triad_start
                triad_span.set_attribute("hfs.triad.duration_s", duration)
                triad_span.set_attribute("hfs.triad.success", True)
                triad_duration.record(duration, {"hfs.triad.id": self.config.id, "hfs.triad.phase": phase})

                # Extract and record token usage if available
                self._record_token_usage(triad_span, response)

                # Record success for all agent roles if tracker exists
                if self.escalation_tracker is not None:
                    for role in self.agents.keys():
                        self.escalation_tracker.record_success(self.config.id, role)

                return response

            except Exception as e:
                duration = time.time() - triad_start
                triad_span.record_exception(e)
                triad_span.set_status(Status(StatusCode.ERROR, str(e)))
                triad_span.set_attribute("hfs.triad.success", False)
                triad_span.set_attribute("hfs.triad.duration_s", duration)
                triad_duration.record(duration, {"hfs.triad.id": self.config.id, "hfs.triad.phase": phase})

                # Record failure if tracker exists
                if self.escalation_tracker is not None:
                    # Record failure for team-level error
                    self.escalation_tracker.record_failure(self.config.id, "team")

                # Save partial progress before raising
                self._save_partial_progress(phase)

                # Extract agent name if available
                agent = "unknown"
                error_str = str(e)

                # Raise structured error
                raise TriadExecutionError(
                    triad_id=self.config.id,
                    phase=phase,
                    agent=agent,
                    error=error_str,
                    partial_state=self._session_state.model_dump(),
                ) from e

    def _record_token_usage(self, span, response: Any) -> None:
        """Record token usage from LLM response if available.

        Extracts usage data from Agno team response and records as span attributes.
        Per CONTEXT.md: Track prompt_tokens and completion_tokens separately.

        Args:
            span: OpenTelemetry span to record attributes on
            response: Response from team.arun() that may contain usage data
        """
        triad_duration, agent_duration, tokens_prompt, tokens_completion = _get_agent_metrics()

        # Try to extract usage from response
        # Agno may store this in response.usage or response.messages[-1].usage
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
        elif hasattr(response, 'messages') and response.messages:
            last_msg = response.messages[-1]
            if hasattr(last_msg, 'usage') and last_msg.usage:
                usage = last_msg.usage

        if usage:
            prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
            completion_tokens = getattr(usage, 'completion_tokens', 0) or 0

            span.set_attribute("hfs.tokens.prompt", prompt_tokens)
            span.set_attribute("hfs.tokens.completion", completion_tokens)
            span.set_attribute("hfs.tokens.total", prompt_tokens + completion_tokens)

            # Record metrics
            labels = {"hfs.triad.id": self.config.id}
            tokens_prompt.add(prompt_tokens, labels)
            tokens_completion.add(completion_tokens, labels)

    def _create_agent_span_context(
        self,
        role: str,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Create context manager for agent-level spans.

        Can be used by subclasses for finer-grained tracing if they
        override execution methods to call agents individually.

        Args:
            role: Agent role name (orchestrator, worker_a, etc.)
            model_name: Optional model name for the agent
            provider: Optional provider name

        Returns:
            Context manager that creates agent span

        Example:
            with self._create_agent_span_context("orchestrator", "gpt-4", "openai"):
                # Agent work here
                pass
        """
        tracer = _get_tracer()
        triad_duration, agent_duration, tokens_prompt, tokens_completion = _get_agent_metrics()

        @contextmanager
        def agent_span():
            with tracer.start_as_current_span(f"hfs.agent.{role}") as span:
                span.set_attribute("hfs.agent.role", role)
                span.set_attribute("hfs.agent.triad_id", self.config.id)
                if model_name:
                    span.set_attribute("hfs.agent.model", model_name)
                if provider:
                    span.set_attribute("hfs.agent.provider", provider)

                start = time.time()
                try:
                    yield span
                    duration = time.time() - start
                    span.set_attribute("hfs.agent.duration_s", duration)
                    span.set_attribute("hfs.agent.success", True)
                    agent_duration.record(duration, {"hfs.agent.role": role, "hfs.triad.id": self.config.id})
                except Exception as e:
                    duration = time.time() - start
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("hfs.agent.success", False)
                    span.set_attribute("hfs.agent.duration_s", duration)
                    agent_duration.record(duration, {"hfs.agent.role": role, "hfs.triad.id": self.config.id})
                    raise

        return agent_span()

    def _save_partial_progress(self, phase: str) -> None:
        """Save session state to file for recovery.

        Per CONTEXT.md: Write progress to specific markdown state files
        in .planning directory.

        Args:
            phase: Current phase being saved
        """
        state_dir = Path(".planning")
        state_dir.mkdir(exist_ok=True)

        state_file = state_dir / f"{self.config.id}_{phase}_state.json"
        state_data = {
            "triad_id": self.config.id,
            "phase": phase,
            "session_state": self._session_state.model_dump(),
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)

    def _load_partial_progress(self, phase: str) -> bool:
        """Load session state from file if exists.

        Args:
            phase: Phase to load state for

        Returns:
            True if state was loaded, False otherwise
        """
        state_file = Path(".planning") / f"{self.config.id}_{phase}_state.json"

        if not state_file.exists():
            return False

        try:
            with open(state_file, "r") as f:
                state_data = json.load(f)

            self._session_state = TriadSessionState(**state_data.get("session_state", {}))
            return True

        except (json.JSONDecodeError, KeyError, TypeError):
            return False

    async def deliberate(
        self,
        user_request: str,
        spec_state: Dict[str, Any],
    ) -> TriadOutput:
        """Run internal deliberation and produce unified output.

        Args:
            user_request: The original user request describing what to build
            spec_state: Current state of the shared spec document

        Returns:
            TriadOutput containing position, claims, and proposals
        """
        # Check for partial progress to resume
        self._load_partial_progress("deliberation")

        # Get phase context
        context = self._session_state.get_phase_context("deliberation")

        # Build prompt
        prompt = self._build_deliberation_prompt(user_request, spec_state)

        # Run with error handling
        response = await self._run_with_error_handling("deliberation", prompt)

        # TODO: Parse response into TriadOutput
        # This will be implemented by subclasses based on their output format
        return TriadOutput(
            position=str(response),
            claims=[],
            proposals={},
        )

    async def negotiate(
        self,
        section: str,
        other_proposals: Dict[str, Any],
    ) -> NegotiationResponse:
        """Respond to a negotiation round for a contested section.

        Args:
            section: Name of the contested section
            other_proposals: Dict mapping other triad IDs to their proposals

        Returns:
            One of "concede", "revise", or "hold"
        """
        # Check for partial progress to resume
        self._load_partial_progress("negotiation")

        # Get phase context
        context = self._session_state.get_phase_context("negotiation")

        # Build prompt
        prompt = self._build_negotiation_prompt(section, other_proposals)

        # Run with error handling
        response = await self._run_with_error_handling("negotiation", prompt)

        # TODO: Parse response into NegotiationResponse
        # This will be implemented by subclasses based on their output format
        response_str = str(response).lower().strip()
        if "concede" in response_str:
            return "concede"
        elif "revise" in response_str:
            return "revise"
        else:
            return "hold"

    async def execute(
        self,
        frozen_spec: Dict[str, Any],
    ) -> Dict[str, str]:
        """Generate code for owned sections.

        Args:
            frozen_spec: The frozen spec with finalized section assignments

        Returns:
            Dictionary mapping section names to generated code/content
        """
        # Check for partial progress to resume
        self._load_partial_progress("execution")

        # Get phase context
        context = self._session_state.get_phase_context("execution")

        # Build prompt
        prompt = self._build_execution_prompt(frozen_spec)

        # Run with error handling
        response = await self._run_with_error_handling("execution", prompt)

        # TODO: Parse response into Dict[str, str]
        # This will be implemented by subclasses based on their output format
        return {}
