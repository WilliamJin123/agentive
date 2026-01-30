"""HFS Orchestrator - Main entry point for the Hexagonal Frontend System.

The HFSOrchestrator coordinates the entire 9-phase pipeline:
1. INPUT - receive request, config, constraints
2. SPAWN TRIADS - create triad instances based on config
3. INTERNAL DELIBERATION - each triad deliberates on the request
4. CLAIM REGISTRATION - register claims on the shared spec
5. NEGOTIATION ROUNDS - resolve contested sections via NegotiationEngine
6. FREEZE - lock spec via spec.freeze()
7. EXECUTION - triads generate code for their owned sections
8. INTEGRATION - CodeMerger combines, Validator verifies
9. OUTPUT - return final artifact with metadata

This is the main class that users interact with to run HFS.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from opentelemetry.trace import Status, StatusCode

from ..observability import get_tracer, get_meter
from .arbiter import Arbiter, ArbiterConfig
from .config import HFSConfig, load_config, load_config_dict
from .emergent import EmergentObserver, EmergentReport
from .escalation_tracker import EscalationTracker
from .model_selector import ModelSelector
from .model_tiers import ModelTiersConfig
from .negotiation import NegotiationEngine, NegotiationResult
from .spec import Spec
from .triad import Triad, TriadConfig, TriadPreset, TriadOutput
from ..agno.providers import ProviderManager
from ..presets.triad_factory import create_triad, create_agno_triad
from ..integration.merger import CodeMerger, MergedArtifact
from ..integration.validator import Validator, ValidationResult


logger = logging.getLogger(__name__)


# Module-level observability handles (lazy initialization)
_tracer = None
_meter = None
_phase_duration = None
_phase_success = None
_phase_failure = None


def _get_tracer():
    """Get tracer instance, initializing on first access."""
    global _tracer
    if _tracer is None:
        _tracer = get_tracer("hfs.orchestrator")
    return _tracer


def _get_phase_metrics():
    """Get phase metrics instruments, initializing on first access."""
    global _meter, _phase_duration, _phase_success, _phase_failure
    if _meter is None:
        _meter = get_meter("hfs.orchestrator")
        _phase_duration = _meter.create_histogram(
            "hfs.phase.duration",
            description="Duration of HFS pipeline phases",
            unit="s"
        )
        _phase_success = _meter.create_counter(
            "hfs.phase.success.count",
            description="Count of successful phase completions",
            unit="{execution}"
        )
        _phase_failure = _meter.create_counter(
            "hfs.phase.failure.count",
            description="Count of failed phase executions",
            unit="{execution}"
        )
    return _phase_duration, _phase_success, _phase_failure


def _record_phase_metrics(phase_name: str, duration_s: float, success: bool):
    """Record phase metrics for both histogram and counters."""
    phase_duration, phase_success, phase_failure = _get_phase_metrics()
    phase_duration.record(duration_s, {"hfs.phase.name": phase_name})
    if success:
        phase_success.add(1, {"hfs.phase.name": phase_name})
    else:
        phase_failure.add(1, {"hfs.phase.name": phase_name})


@dataclass
class HFSResult:
    """Result from running the HFS pipeline.

    Contains all outputs from the orchestration process including the
    merged artifact, validation results, emergent observations, and
    detailed logs for debugging and analysis.

    Attributes:
        artifact: The merged code artifact from all triads.
        validation: Validation results from the quality checks.
        emergent: Emergent center observations and recommendations.
        spec: The frozen spec with final section assignments.
        negotiation_log: Detailed log of the negotiation process.
        phase_timings: Dict mapping phase names to execution time in ms.
        success: Whether the pipeline completed successfully.
        error: Error message if success is False.
    """
    artifact: Optional[MergedArtifact] = None
    validation: Optional[ValidationResult] = None
    emergent: Optional[EmergentReport] = None
    spec: Optional[Spec] = None
    negotiation_log: Optional[NegotiationResult] = None
    phase_timings: Dict[str, float] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "artifact": self.artifact.to_dict() if self.artifact else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "emergent": self.emergent.to_dict() if self.emergent else None,
            "spec": self._spec_to_dict() if self.spec else None,
            "negotiation_log": self._negotiation_log_to_dict(),
            "phase_timings": self.phase_timings,
            "success": self.success,
            "error": self.error,
        }

    def _spec_to_dict(self) -> Dict[str, Any]:
        """Convert spec to serializable dict."""
        if not self.spec:
            return {}
        return {
            "temperature": self.spec.temperature,
            "round": self.spec.round,
            "status": self.spec.status,
            "sections": {
                name: {
                    "status": section.status.value,
                    "owner": section.owner,
                    "claims": section.claims,
                    "content": section.content,
                }
                for name, section in self.spec.sections.items()
            },
            "coverage_report": self.spec.get_coverage_report(),
        }

    def _negotiation_log_to_dict(self) -> Optional[Dict[str, Any]]:
        """Convert negotiation log to serializable dict."""
        if not self.negotiation_log:
            return None
        return {
            "total_rounds": self.negotiation_log.total_rounds,
            "sections_resolved": self.negotiation_log.sections_resolved,
            "sections_escalated": self.negotiation_log.sections_escalated,
            "final_temperature": self.negotiation_log.final_temperature,
            "round_count": len(self.negotiation_log.round_history),
        }


class HFSOrchestrator:
    """Main orchestrator for the Hexagonal Frontend System.

    The HFSOrchestrator is the entry point for running the HFS pipeline.
    It coordinates triads through the 9-phase process: input, spawn,
    deliberation, claims, negotiation, freeze, execution, integration,
    and output.

    Example usage:
        ```python
        from hfs.core.orchestrator import HFSOrchestrator

        orchestrator = HFSOrchestrator(
            config_path="config/dashboard.yaml",
            llm_client=my_llm_client
        )

        result = await orchestrator.run(
            "Create a responsive dashboard with data visualization"
        )

        if result.success:
            print(f"Generated {result.artifact.file_count} files")
        ```

    Attributes:
        config: Validated HFSConfig object.
        llm: The LLM client for agent interactions.
        triads: Dict mapping triad_id to Triad instances.
        spec: The shared Spec document.
        arbiter: Arbiter for resolving negotiation deadlocks.
        observer: EmergentObserver for analyzing outputs.
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        llm_client: Any = None,
        model_selector: Optional[ModelSelector] = None,
        escalation_tracker: Optional[EscalationTracker] = None,
    ) -> None:
        """Initialize the HFS Orchestrator.

        Either config_path or config_dict must be provided.

        Args:
            config_path: Path to YAML configuration file.
            config_dict: Configuration as a dictionary (alternative to file).
            llm_client: The LLM client for agent interactions. Must support
                async message creation (e.g., Anthropic, OpenAI clients).
            model_selector: Optional ModelSelector for role-based model resolution.
                If not provided but config has model_tiers section, one will be
                created automatically during run().
            escalation_tracker: Optional EscalationTracker for failure-adaptive
                tier escalation. If not provided but model_selector is available,
                one will be created automatically during run().

        Raises:
            ValueError: If neither config_path nor config_dict is provided.
            ConfigError: If configuration is invalid.
        """
        if config_path is None and config_dict is None:
            raise ValueError("Either config_path or config_dict must be provided")

        # Load configuration
        if config_path is not None:
            self.config = load_config(config_path)
            self._config_path: Optional[Path] = Path(config_path)
        else:
            self.config = load_config_dict(config_dict)
            self._config_path = None

        self.llm = llm_client
        self.model_selector = model_selector
        self.escalation_tracker = escalation_tracker

        # Initialize components (triads are spawned in run())
        self.triads: Dict[str, Union[Triad, Any]] = {}
        self.spec = Spec()

        # Initialize arbiter with config
        arbiter_config = ArbiterConfig(
            model=self.config.arbiter.model,
            max_tokens=self.config.arbiter.max_tokens,
            temperature=self.config.arbiter.temperature,
        )
        self.arbiter = Arbiter(llm_client, arbiter_config)

        # Initialize emergent observer
        self.observer = EmergentObserver()

        # Store raw config for model_tiers access (HFSConfig doesn't include it)
        if config_path is not None:
            with open(config_path, 'r', encoding='utf-8') as f:
                import yaml
                raw = yaml.safe_load(f)
                self._raw_config = raw.get('config', raw)
        else:
            self._raw_config = config_dict.get('config', config_dict) if config_dict else {}

        # Internal state
        self._negotiation_result: Optional[NegotiationResult] = None
        self._deliberation_results: Dict[str, TriadOutput] = {}
        self._artifacts: Dict[str, Dict[str, str]] = {}

        logger.info(
            f"HFSOrchestrator initialized with {len(self.config.triads)} triads "
            f"and {len(self.config.sections)} sections"
        )

    async def run(self, user_request: str) -> HFSResult:
        """Run the full HFS 9-phase pipeline.

        This is the main entry point for executing the HFS system.
        It coordinates all phases from input to final output.

        Args:
            user_request: The user's request describing what to build.
                Example: "Create a dashboard with charts and tables"

        Returns:
            HFSResult containing the merged artifact, validation results,
            emergent observations, and full negotiation log.
        """
        result = HFSResult()
        phase_timings: Dict[str, float] = {}
        tracer = _get_tracer()
        run_id = str(uuid.uuid4())[:8]

        with tracer.start_as_current_span("hfs.run") as run_span:
            run_span.set_attribute("hfs.run.id", run_id)
            run_span.set_attribute("hfs.run.request_summary", user_request[:100])
            run_span.set_attribute("hfs.run.triad_count", len(self.config.triads))

            try:
                # ============================================================
                # LAZY INITIALIZATION: ModelSelector and EscalationTracker
                # ============================================================
                # Create ModelSelector if not provided but model_tiers exists in config
                if self.model_selector is None and 'model_tiers' in self._raw_config:
                    self.model_selector = self._create_default_model_selector()
                    logger.info("Created default ModelSelector from config model_tiers section")

                # Create EscalationTracker if not provided but model_selector exists
                if self.escalation_tracker is None and self.model_selector is not None:
                    if self._config_path is not None:
                        self.escalation_tracker = EscalationTracker(
                            self._config_path,
                            self.model_selector.config,
                        )
                        logger.info("Created default EscalationTracker for failure-adaptive escalation")

                # ============================================================
                # PHASE 1: INPUT
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.input") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "input")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 1: INPUT - Receiving request and config")

                        # Set user request on arbiter for context during escalation
                        self.arbiter.set_user_request(user_request)

                        duration = time.time() - phase_start
                        phase_timings["input"] = duration * 1000  # ms for backward compat
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        _record_phase_metrics("input", duration, success=True)
                        logger.debug(f"Input phase completed in {phase_timings['input']:.2f}ms")
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("input", duration, success=False)
                        raise

                # ============================================================
                # PHASE 2: SPAWN TRIADS
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.spawn") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "spawn")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 2: SPAWN TRIADS - Creating triad instances")

                        self._spawn_triads()
                        self._initialize_spec()

                        duration = time.time() - phase_start
                        phase_timings["spawn"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        phase_span.set_attribute("hfs.phase.triad_count", len(self.triads))
                        _record_phase_metrics("spawn", duration, success=True)
                        logger.info(
                            f"Spawned {len(self.triads)} triads in {phase_timings['spawn']:.2f}ms"
                        )
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("spawn", duration, success=False)
                        raise

                # ============================================================
                # PHASE 3: INTERNAL DELIBERATION
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.deliberation") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "deliberation")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 3: INTERNAL DELIBERATION - Triads analyze request")

                        self._deliberation_results = await self._deliberate(user_request)

                        duration = time.time() - phase_start
                        phase_timings["deliberation"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        _record_phase_metrics("deliberation", duration, success=True)
                        logger.info(
                            f"Deliberation completed in {phase_timings['deliberation']:.2f}ms"
                        )
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("deliberation", duration, success=False)
                        raise

                # ============================================================
                # PHASE 4: CLAIM REGISTRATION
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.claims") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "claims")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 4: CLAIM REGISTRATION - Registering section claims")

                        self._register_claims(self._deliberation_results)

                        contested_count = len(self.spec.get_contested_sections())
                        claimed_count = len(self.spec.get_claimed_sections())

                        duration = time.time() - phase_start
                        phase_timings["claims"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        phase_span.set_attribute("hfs.phase.claimed_count", claimed_count)
                        phase_span.set_attribute("hfs.phase.contested_count", contested_count)
                        _record_phase_metrics("claims", duration, success=True)
                        logger.info(
                            f"Claims registered: {claimed_count} claimed, {contested_count} contested "
                            f"in {phase_timings['claims']:.2f}ms"
                        )
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("claims", duration, success=False)
                        raise

                # ============================================================
                # PHASE 5: NEGOTIATION ROUNDS
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.negotiation") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "negotiation")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 5: NEGOTIATION - Resolving contested sections")

                        if contested_count > 0:
                            negotiation_engine = NegotiationEngine(
                                triads=self.triads,
                                spec=self.spec,
                                arbiter=self.arbiter,
                                config={
                                    "temperature_decay": self.config.pressure.temperature_decay,
                                    "max_negotiation_rounds": self.config.pressure.max_negotiation_rounds,
                                    "escalation_threshold": self.config.pressure.escalation_threshold,
                                }
                            )
                            self.spec = await negotiation_engine.run()
                            self._negotiation_result = negotiation_engine.get_result()
                            phase_span.set_attribute(
                                "hfs.phase.negotiation_rounds",
                                self._negotiation_result.total_rounds
                            )
                        else:
                            logger.info("No contested sections - skipping negotiation")
                            # Manually freeze if no negotiation needed
                            self.spec.freeze()
                            self._negotiation_result = NegotiationResult()
                            phase_span.set_attribute("hfs.phase.negotiation_rounds", 0)

                        duration = time.time() - phase_start
                        phase_timings["negotiation"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        _record_phase_metrics("negotiation", duration, success=True)
                        logger.info(
                            f"Negotiation completed in {phase_timings['negotiation']:.2f}ms"
                        )
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("negotiation", duration, success=False)
                        raise

                # ============================================================
                # PHASE 6: FREEZE
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.freeze") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "freeze")
                    phase_start = time.time()
                    try:
                        # Already handled by negotiation engine or above
                        logger.info("Phase 6: FREEZE - Spec is frozen")
                        phase_span.set_attribute("hfs.phase.spec_status", self.spec.status)

                        duration = time.time() - phase_start
                        phase_timings["freeze"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        _record_phase_metrics("freeze", duration, success=True)
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("freeze", duration, success=False)
                        raise

                # ============================================================
                # PHASE 7: EXECUTION
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.execution") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "execution")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 7: EXECUTION - Generating code artifacts")

                        self._artifacts = await self._execute()

                        artifact_count = sum(len(a) for a in self._artifacts.values())
                        duration = time.time() - phase_start
                        phase_timings["execution"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        phase_span.set_attribute("hfs.phase.artifact_count", artifact_count)
                        _record_phase_metrics("execution", duration, success=True)
                        logger.info(
                            f"Execution completed: {artifact_count} artifacts "
                            f"in {phase_timings['execution']:.2f}ms"
                        )
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("execution", duration, success=False)
                        raise

                # ============================================================
                # PHASE 8: INTEGRATION
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.integration") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "integration")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 8: INTEGRATION - Merging and validating")

                        # Merge artifacts
                        merger = CodeMerger(output_format=self.config.output.format)
                        merged = merger.merge(self._artifacts, self.spec)

                        # Validate
                        validator = Validator()
                        validation = validator.validate(merged)

                        duration = time.time() - phase_start
                        phase_timings["integration"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        phase_span.set_attribute("hfs.phase.file_count", merged.file_count)
                        phase_span.set_attribute("hfs.phase.validation_passed", validation.passed)
                        _record_phase_metrics("integration", duration, success=True)
                        logger.info(
                            f"Integration completed: {merged.file_count} files, "
                            f"validation {'passed' if validation.passed else 'failed'} "
                            f"in {phase_timings['integration']:.2f}ms"
                        )
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("integration", duration, success=False)
                        raise

                # ============================================================
                # PHASE 9: OUTPUT
                # ============================================================
                with tracer.start_as_current_span("hfs.phase.output") as phase_span:
                    phase_span.set_attribute("hfs.phase.name", "output")
                    phase_start = time.time()
                    try:
                        logger.info("Phase 9: OUTPUT - Generating final report")

                        # Observe emergent properties
                        emergent = self.observer.observe(
                            spec=self.spec,
                            artifacts=self._artifacts,
                            merged=merged,
                            validation=validation
                        )

                        duration = time.time() - phase_start
                        phase_timings["output"] = duration * 1000
                        phase_span.set_attribute("hfs.phase.duration_s", duration)
                        phase_span.set_attribute("hfs.phase.success", True)
                        phase_span.set_attribute("hfs.phase.health", emergent.overall_health)
                        _record_phase_metrics("output", duration, success=True)
                    except Exception as e:
                        duration = time.time() - phase_start
                        phase_span.record_exception(e)
                        phase_span.set_status(Status(StatusCode.ERROR, str(e)))
                        phase_span.set_attribute("hfs.phase.success", False)
                        _record_phase_metrics("output", duration, success=False)
                        raise

                # Build result
                result.artifact = merged
                result.validation = validation
                result.emergent = emergent
                result.spec = self.spec
                result.negotiation_log = self._negotiation_result
                result.phase_timings = phase_timings
                result.success = True

                total_time = sum(phase_timings.values())
                run_span.set_attribute("hfs.run.total_duration_ms", total_time)
                run_span.set_attribute("hfs.run.success", True)
                run_span.set_status(Status(StatusCode.OK))
                logger.info(
                    f"HFS pipeline completed successfully in {total_time:.2f}ms. "
                    f"Health: {emergent.overall_health}"
                )

            except Exception as e:
                logger.error(f"HFS pipeline failed: {e}", exc_info=True)
                result.success = False
                result.error = str(e)
                result.phase_timings = phase_timings

                run_span.record_exception(e)
                run_span.set_status(Status(StatusCode.ERROR, str(e)))
                run_span.set_attribute("hfs.run.success", False)
                run_span.set_attribute("hfs.run.error", str(e))

        return result

    def _spawn_triads(self) -> None:
        """Spawn triad instances based on configuration.

        Creates Triad instances for each triad defined in the config,
        using the appropriate preset class (hierarchical, dialectic, consensus).

        If model_selector is available, uses create_agno_triad for role-based
        model selection. Otherwise falls back to create_triad with self.llm
        for backward compatibility.
        """
        self.triads = {}

        for triad_config in self.config.triads:
            # Build TriadConfig from the pydantic model
            config = TriadConfig(
                id=triad_config.id,
                preset=TriadPreset(triad_config.preset),
                scope_primary=triad_config.scope.primary,
                scope_reach=triad_config.scope.reach,
                budget_tokens=triad_config.budget.tokens,
                budget_tool_calls=triad_config.budget.tool_calls,
                budget_time_ms=triad_config.budget.time_ms,
                objectives=triad_config.objectives,
                system_context=triad_config.system_context,
            )

            # Create triad using appropriate factory based on model_selector availability
            if self.model_selector is not None:
                # Use new Agno-based triads with role-based model selection
                triad = create_agno_triad(
                    config,
                    self.model_selector,
                    self.spec,
                    escalation_tracker=self.escalation_tracker,
                )
                logger.debug(
                    f"Spawned AgnoTriad '{triad_config.id}' with preset '{triad_config.preset}' "
                    f"(model_selector enabled)"
                )
            else:
                # Backward compatibility: use legacy single-model triads
                triad = create_triad(config, self.llm)
                logger.debug(
                    f"Spawned triad '{triad_config.id}' with preset '{triad_config.preset}'"
                )

            self.triads[triad_config.id] = triad

    def _initialize_spec(self) -> None:
        """Initialize the spec with sections from config.

        Sets up the shared spec document with all sections defined
        in the configuration. Also sets initial temperature from config.
        """
        # Initialize sections
        self.spec.initialize_sections(self.config.sections)

        # Set initial temperature from config
        self.spec.temperature = self.config.pressure.initial_temperature
        self.spec.status = "initializing"

        logger.debug(
            f"Initialized spec with {len(self.config.sections)} sections, "
            f"temperature={self.spec.temperature}"
        )

    async def _deliberate(self, user_request: str) -> Dict[str, TriadOutput]:
        """Run internal deliberation for all triads.

        Each triad analyzes the user request and current spec state
        to produce their position, claims, and proposals.

        Args:
            user_request: The user's request.

        Returns:
            Dict mapping triad_id to their TriadOutput.
        """
        results: Dict[str, TriadOutput] = {}

        # Build current spec state for triads
        spec_state = self._build_spec_state()

        # Run deliberation for all triads (can be parallelized)
        async def deliberate_triad(triad_id: str, triad: Triad) -> tuple:
            try:
                output = await triad.deliberate(user_request, spec_state)
                return (triad_id, output)
            except Exception as e:
                logger.error(f"Deliberation failed for triad '{triad_id}': {e}")
                # Return empty output on failure
                return (triad_id, TriadOutput(position="", claims=[], proposals={}))

        # Execute deliberations in parallel
        tasks = [
            deliberate_triad(tid, triad)
            for tid, triad in self.triads.items()
        ]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        for item in outputs:
            if isinstance(item, Exception):
                logger.error(f"Deliberation task exception: {item}")
                continue
            triad_id, output = item
            results[triad_id] = output
            logger.debug(
                f"Triad '{triad_id}' deliberation: {len(output.claims)} claims"
            )

        return results

    def _build_spec_state(self) -> Dict[str, Any]:
        """Build a dictionary representation of current spec state.

        Returns:
            Dict with spec state information for triads to consume.
        """
        return {
            "temperature": self.spec.temperature,
            "round": self.spec.round,
            "status": self.spec.status,
            "sections": {
                name: {
                    "status": section.status.value,
                    "owner": section.owner,
                    "claims": list(section.claims),
                }
                for name, section in self.spec.sections.items()
            },
            "contested": self.spec.get_contested_sections(),
            "unclaimed": self.spec.get_unclaimed_sections(),
            "claimed": self.spec.get_claimed_sections(),
        }

    def _register_claims(self, deliberation_results: Dict[str, TriadOutput]) -> None:
        """Register claims from deliberation results on the spec.

        For each triad's output, register their claims and proposals
        on the corresponding spec sections.

        Args:
            deliberation_results: Dict mapping triad_id to TriadOutput.
        """
        for triad_id, output in deliberation_results.items():
            for section_name in output.claims:
                # Get proposal for this section if available
                proposal = output.proposals.get(section_name, {
                    "position": output.position,
                    "from_triad": triad_id,
                })

                # Register claim on spec
                self.spec.register_claim(triad_id, section_name, proposal)

                logger.debug(
                    f"Registered claim: triad '{triad_id}' -> section '{section_name}'"
                )

    async def _execute(self) -> Dict[str, Dict[str, str]]:
        """Execute code generation for all triads.

        Each triad generates code for the sections they own
        after the spec is frozen.

        Returns:
            Dict mapping triad_id -> Dict mapping section -> code.
        """
        artifacts: Dict[str, Dict[str, str]] = {}

        # Build frozen spec state
        frozen_spec = self._build_frozen_spec_state()

        # Execute all triads
        async def execute_triad(triad_id: str, triad: Triad) -> tuple:
            try:
                output = await triad.execute(frozen_spec)
                return (triad_id, output)
            except Exception as e:
                logger.error(f"Execution failed for triad '{triad_id}': {e}")
                return (triad_id, {})

        tasks = [
            execute_triad(tid, triad)
            for tid, triad in self.triads.items()
        ]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        for item in outputs:
            if isinstance(item, Exception):
                logger.error(f"Execution task exception: {item}")
                continue
            triad_id, output = item
            if output:  # Only include non-empty outputs
                artifacts[triad_id] = output
                logger.debug(
                    f"Triad '{triad_id}' execution: {len(output)} sections"
                )

        return artifacts

    def _build_frozen_spec_state(self) -> Dict[str, Any]:
        """Build the frozen spec state for execution phase.

        Returns:
            Dict with frozen spec information including section contents.
        """
        return {
            "temperature": self.spec.temperature,
            "round": self.spec.round,
            "status": self.spec.status,
            "sections": {
                name: {
                    "status": section.status.value,
                    "owner": section.owner,
                    "content": section.content,
                    "proposals": dict(section.proposals),
                }
                for name, section in self.spec.sections.items()
            },
        }

    def _get_negotiation_log(self) -> Optional[NegotiationResult]:
        """Get the negotiation result log.

        Returns:
            NegotiationResult if negotiation occurred, None otherwise.
        """
        return self._negotiation_result

    def get_triad(self, triad_id: str) -> Optional[Triad]:
        """Get a triad instance by ID.

        Args:
            triad_id: The triad identifier.

        Returns:
            The Triad instance if found, None otherwise.
        """
        return self.triads.get(triad_id)

    def get_spec(self) -> Spec:
        """Get the current spec state.

        Returns:
            The Spec instance.
        """
        return self.spec

    def get_config(self) -> HFSConfig:
        """Get the validated configuration.

        Returns:
            The HFSConfig instance.
        """
        return self.config

    def _create_default_model_selector(self) -> ModelSelector:
        """Create a ModelSelector from config's model_tiers section.

        Called during lazy initialization in run() when model_selector is None
        but config has a model_tiers section.

        Returns:
            ModelSelector instance configured from model_tiers

        Raises:
            ValueError: If model_tiers section is missing or invalid
        """
        model_tiers_data = self._raw_config.get('model_tiers')
        if not model_tiers_data:
            raise ValueError("Cannot create ModelSelector: model_tiers section missing from config")

        # Parse model_tiers into ModelTiersConfig
        model_tiers_config = ModelTiersConfig(**model_tiers_data)

        # Create ProviderManager
        provider_manager = ProviderManager()

        logger.debug(
            f"Created default ModelSelector with tiers: {list(model_tiers_config.tiers.keys())}"
        )

        return ModelSelector(model_tiers_config, provider_manager)


# Convenience function for quick runs
async def run_hfs(
    config_path: Union[str, Path],
    user_request: str,
    llm_client: Any = None
) -> HFSResult:
    """Convenience function to run HFS pipeline.

    Creates an orchestrator and runs the full pipeline in one call.

    Args:
        config_path: Path to YAML configuration file.
        user_request: The user's request describing what to build.
        llm_client: The LLM client for agent interactions.

    Returns:
        HFSResult with all outputs.

    Example:
        result = await run_hfs(
            "config/dashboard.yaml",
            "Create a responsive dashboard",
            my_llm_client
        )
    """
    orchestrator = HFSOrchestrator(config_path=config_path, llm_client=llm_client)
    return await orchestrator.run(user_request)
