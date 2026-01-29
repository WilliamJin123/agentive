"""Pressure mechanics for HFS - forces that compel triads to negotiate.

Pressure is what forces triads to negotiate rather than simply coexist.
Without pressure, each triad would claim everything. With pressure, they
must make tradeoffs.

Types of Pressure:
1. Resource Pressure - Global budget that must be divided (tokens, time)
2. Coverage Pressure - Every section must be owned before execution
3. Quality Pressure - Final output must pass validations
4. Coherence Pressure - Output must be unified, not just assembled
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum


class ValidationCheck(Enum):
    """Standard validation checks that can be run against artifacts."""
    MUST_COMPILE = "must_compile"
    MUST_RENDER = "must_render"
    NO_CONTRADICTIONS = "no_contradictions"
    ACCESSIBILITY_A11Y = "accessibility_a11y"
    PERFORMANCE_BUDGET = "performance_budget"
    ACCESSIBILITY_BASIC = "accessibility_basic"


@dataclass
class ResourceBudget:
    """Track resource usage for a single triad or globally.

    Attributes:
        tokens: Token budget/usage
        time_ms: Time budget/usage in milliseconds
        tool_calls: Tool call budget/usage
    """
    tokens: int = 0
    time_ms: int = 0
    tool_calls: int = 0

    def add(self, tokens: int = 0, time_ms: int = 0, tool_calls: int = 0) -> None:
        """Add usage to the budget."""
        self.tokens += tokens
        self.time_ms += time_ms
        self.tool_calls += tool_calls

    def exceeds(self, limit: "ResourceBudget") -> bool:
        """Check if this usage exceeds the given limit."""
        return (
            self.tokens > limit.tokens or
            self.time_ms > limit.time_ms or
            self.tool_calls > limit.tool_calls
        )

    def remaining(self, limit: "ResourceBudget") -> "ResourceBudget":
        """Calculate remaining budget given a limit."""
        return ResourceBudget(
            tokens=max(0, limit.tokens - self.tokens),
            time_ms=max(0, limit.time_ms - self.time_ms),
            tool_calls=max(0, limit.tool_calls - self.tool_calls),
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary representation."""
        return {
            "tokens": self.tokens,
            "time_ms": self.time_ms,
            "tool_calls": self.tool_calls,
        }


@dataclass
class PressureConfig:
    """Configuration for pressure mechanics.

    Attributes:
        initial_temperature: Starting temperature (default: 1.0)
        temperature_decay: Decrease per round (default: 0.15)
        freeze_threshold: Freeze when below this (default: 0.1)
        max_negotiation_rounds: Hard cap on rounds (default: 10)
        escalation_threshold: Rounds stuck before escalate (default: 2)
        global_budget: Total budget for all triads combined
        per_triad_max: Maximum budget any single triad can use
        validation_checks: List of validation checks to run
        enforcement: "hard" for strict cutoff, "soft" for warning + degraded priority
    """
    initial_temperature: float = 1.0
    temperature_decay: float = 0.15
    freeze_threshold: float = 0.1
    max_negotiation_rounds: int = 10
    escalation_threshold: int = 2
    global_budget: ResourceBudget = field(default_factory=lambda: ResourceBudget(
        tokens=100000,
        time_ms=60000,
        tool_calls=500,
    ))
    per_triad_max: ResourceBudget = field(default_factory=lambda: ResourceBudget(
        tokens=20000,
        time_ms=15000,
        tool_calls=50,
    ))
    validation_checks: List[str] = field(default_factory=list)
    enforcement: str = "hard"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PressureConfig":
        """Create PressureConfig from a dictionary (e.g., from YAML config)."""
        global_budget_data = data.get("global_budget", {})
        per_triad_data = data.get("per_triad_max", {})

        return cls(
            initial_temperature=data.get("initial_temperature", 1.0),
            temperature_decay=data.get("temperature_decay", 0.15),
            freeze_threshold=data.get("freeze_threshold", 0.1),
            max_negotiation_rounds=data.get("max_negotiation_rounds", 10),
            escalation_threshold=data.get("escalation_threshold", 2),
            global_budget=ResourceBudget(
                tokens=global_budget_data.get("tokens", 100000),
                time_ms=global_budget_data.get("time_ms", 60000),
                tool_calls=global_budget_data.get("tool_calls", 500),
            ),
            per_triad_max=ResourceBudget(
                tokens=per_triad_data.get("tokens", 20000),
                time_ms=per_triad_data.get("time_ms", 15000),
                tool_calls=per_triad_data.get("tool_calls", 50),
            ),
            validation_checks=data.get("validation", []),
            enforcement=data.get("enforcement", "hard"),
        )


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        check: Name of the validation check
        passed: Whether the check passed
        message: Optional message explaining the result
        details: Optional additional details
    """
    check: str
    passed: bool
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class CoverageReport:
    """Report on section coverage status.

    Attributes:
        total_sections: Total number of sections defined
        owned_sections: Sections that have an owner
        unclaimed_sections: Sections with no claims
        contested_sections: Sections with multiple claims
        coverage_complete: True if all sections are owned
    """
    total_sections: int
    owned_sections: List[str]
    unclaimed_sections: List[str]
    contested_sections: List[str]

    @property
    def coverage_complete(self) -> bool:
        """Check if all sections have been assigned ownership."""
        return len(self.unclaimed_sections) == 0 and len(self.contested_sections) == 0


class PressureSystem:
    """Manages pressure mechanics for HFS negotiation.

    The pressure system tracks resource usage, calculates temperature decay,
    validates coverage requirements, and runs quality checks.
    """

    def __init__(self, config: Optional[PressureConfig] = None):
        """Initialize the pressure system.

        Args:
            config: Pressure configuration. Uses defaults if not provided.
        """
        self.config = config or PressureConfig()
        self._triad_usage: Dict[str, ResourceBudget] = {}
        self._validation_hooks: Dict[str, Callable[[Any], ValidationResult]] = {}
        self._register_default_validators()

    def _register_default_validators(self) -> None:
        """Register default validation hooks."""
        # These are placeholder validators that can be overridden
        self._validation_hooks["must_compile"] = self._validate_must_compile
        self._validation_hooks["must_render"] = self._validate_must_render
        self._validation_hooks["no_contradictions"] = self._validate_no_contradictions
        self._validation_hooks["accessibility_a11y"] = self._validate_accessibility
        self._validation_hooks["accessibility_basic"] = self._validate_accessibility
        self._validation_hooks["performance_budget"] = self._validate_performance

    def calculate_temperature(self, round_num: int) -> float:
        """Calculate temperature for a given round.

        Uses the formula: temperature(round) = max(0, initial_temp - (decay_rate * round))

        Args:
            round_num: The current negotiation round (0-indexed)

        Returns:
            Temperature value between 0.0 and initial_temperature
        """
        return max(
            0.0,
            self.config.initial_temperature - (self.config.temperature_decay * round_num)
        )

    def should_freeze(self, round_num: int) -> bool:
        """Check if negotiation should freeze based on temperature or rounds.

        Args:
            round_num: The current negotiation round

        Returns:
            True if temperature is below freeze threshold or max rounds reached
        """
        temp = self.calculate_temperature(round_num)
        return (
            temp <= self.config.freeze_threshold or
            round_num >= self.config.max_negotiation_rounds
        )

    def check_coverage(self, spec: Any) -> CoverageReport:
        """Check coverage status of the spec.

        Args:
            spec: The Spec object to check coverage for

        Returns:
            CoverageReport with details on section coverage
        """
        owned = []
        unclaimed = []
        contested = []

        for section_name, section in spec.sections.items():
            status = section.status.value if hasattr(section.status, 'value') else section.status

            if status in ("claimed", "frozen"):
                owned.append(section_name)
            elif status == "unclaimed":
                unclaimed.append(section_name)
            elif status == "contested":
                contested.append(section_name)

        return CoverageReport(
            total_sections=len(spec.sections),
            owned_sections=owned,
            unclaimed_sections=unclaimed,
            contested_sections=contested,
        )

    def validate_quality(self, artifact: Any) -> List[ValidationResult]:
        """Run all configured validation checks against an artifact.

        Args:
            artifact: The artifact to validate (code, spec content, etc.)

        Returns:
            List of ValidationResult objects for each check
        """
        results = []

        for check_name in self.config.validation_checks:
            if check_name in self._validation_hooks:
                result = self._validation_hooks[check_name](artifact)
            else:
                # Unknown check - mark as passed with warning
                result = ValidationResult(
                    check=check_name,
                    passed=True,
                    message=f"Unknown validation check: {check_name} (skipped)",
                )
            results.append(result)

        return results

    def register_validation_hook(
        self,
        check_name: str,
        validator: Callable[[Any], ValidationResult]
    ) -> None:
        """Register a custom validation hook.

        Args:
            check_name: Name of the validation check
            validator: Function that takes an artifact and returns ValidationResult
        """
        self._validation_hooks[check_name] = validator

    def track_usage(
        self,
        triad_id: str,
        tokens: int = 0,
        time_ms: int = 0,
        tool_calls: int = 0
    ) -> None:
        """Track resource usage for a triad.

        Args:
            triad_id: ID of the triad to track
            tokens: Number of tokens used
            time_ms: Time used in milliseconds
            tool_calls: Number of tool calls made
        """
        if triad_id not in self._triad_usage:
            self._triad_usage[triad_id] = ResourceBudget()

        self._triad_usage[triad_id].add(tokens, time_ms, tool_calls)

    def get_triad_usage(self, triad_id: str) -> ResourceBudget:
        """Get current resource usage for a triad.

        Args:
            triad_id: ID of the triad

        Returns:
            ResourceBudget with current usage (empty if triad not tracked)
        """
        return self._triad_usage.get(triad_id, ResourceBudget())

    def is_budget_exceeded(self, triad_id: str) -> bool:
        """Check if a triad has exceeded its budget.

        Args:
            triad_id: ID of the triad to check

        Returns:
            True if triad has exceeded per_triad_max limits
        """
        usage = self.get_triad_usage(triad_id)
        return usage.exceeds(self.config.per_triad_max)

    def get_remaining_budget(self, triad_id: str) -> ResourceBudget:
        """Get remaining budget for a triad.

        Args:
            triad_id: ID of the triad

        Returns:
            ResourceBudget with remaining allocation
        """
        usage = self.get_triad_usage(triad_id)
        return usage.remaining(self.config.per_triad_max)

    def get_global_usage(self) -> ResourceBudget:
        """Get total resource usage across all triads.

        Returns:
            ResourceBudget with combined usage from all triads
        """
        total = ResourceBudget()
        for usage in self._triad_usage.values():
            total.add(usage.tokens, usage.time_ms, usage.tool_calls)
        return total

    def is_global_budget_exceeded(self) -> bool:
        """Check if global budget has been exceeded.

        Returns:
            True if combined usage exceeds global_budget limits
        """
        return self.get_global_usage().exceeds(self.config.global_budget)

    def get_usage_report(self) -> Dict[str, Any]:
        """Generate a comprehensive usage report.

        Returns:
            Dictionary with global and per-triad usage information
        """
        global_usage = self.get_global_usage()
        global_remaining = global_usage.remaining(self.config.global_budget)

        return {
            "global": {
                "used": global_usage.to_dict(),
                "limit": self.config.global_budget.to_dict(),
                "remaining": global_remaining.to_dict(),
                "exceeded": self.is_global_budget_exceeded(),
            },
            "per_triad": {
                triad_id: {
                    "used": usage.to_dict(),
                    "limit": self.config.per_triad_max.to_dict(),
                    "remaining": usage.remaining(self.config.per_triad_max).to_dict(),
                    "exceeded": usage.exceeds(self.config.per_triad_max),
                }
                for triad_id, usage in self._triad_usage.items()
            },
        }

    def reset_usage(self, triad_id: Optional[str] = None) -> None:
        """Reset usage tracking.

        Args:
            triad_id: If provided, reset only that triad. Otherwise reset all.
        """
        if triad_id:
            self._triad_usage[triad_id] = ResourceBudget()
        else:
            self._triad_usage.clear()

    # Default validation hooks (can be overridden via register_validation_hook)

    def _validate_must_compile(self, artifact: Any) -> ValidationResult:
        """Check if the artifact compiles/is syntactically valid."""
        # Placeholder implementation - actual validation would depend on artifact type
        return ValidationResult(
            check="must_compile",
            passed=True,
            message="Compilation check passed (placeholder)",
        )

    def _validate_must_render(self, artifact: Any) -> ValidationResult:
        """Check if the artifact produces visible output."""
        # Placeholder implementation
        return ValidationResult(
            check="must_render",
            passed=True,
            message="Render check passed (placeholder)",
        )

    def _validate_no_contradictions(self, artifact: Any) -> ValidationResult:
        """Check if spec sections are compatible."""
        # Placeholder implementation
        return ValidationResult(
            check="no_contradictions",
            passed=True,
            message="No contradictions found (placeholder)",
        )

    def _validate_accessibility(self, artifact: Any) -> ValidationResult:
        """Check basic accessibility requirements."""
        # Placeholder implementation
        return ValidationResult(
            check="accessibility",
            passed=True,
            message="Accessibility check passed (placeholder)",
        )

    def _validate_performance(self, artifact: Any) -> ValidationResult:
        """Check if performance budget is met."""
        # Placeholder implementation
        return ValidationResult(
            check="performance_budget",
            passed=True,
            message="Performance check passed (placeholder)",
        )
