"""Core module for HFS triad execution and coordination."""

from .spec import (
    SectionStatus,
    Section,
    Spec,
)
from .triad import (
    TriadPreset,
    TriadConfig,
    TriadOutput,
    Triad,
    NegotiationResponse,
)
from .arbiter import (
    ArbiterDecision,
    ArbiterConfig,
    Arbiter,
)
from .pressure import (
    ValidationCheck,
    ResourceBudget,
    PressureConfig,
    ValidationResult,
    CoverageReport,
    PressureSystem,
)
from .emergent import (
    EmergentMetrics,
    DetectedPatterns,
    EmergentIssues,
    EmergentReport,
    EmergentObserver,
)
from .negotiation import (
    NegotiationRoundResult,
    NegotiationResult,
    NegotiationEngine,
)
from .config import (
    ConfigError,
    ScopeConfigModel,
    BudgetConfigModel,
    TriadConfigModel,
    GlobalBudgetConfigModel,
    PressureConfigModel,
    ArbiterConfigModel,
    OutputConfigModel,
    HFSConfig,
    load_config,
    load_config_dict,
)
from .orchestrator import (
    HFSResult,
    HFSOrchestrator,
    run_hfs,
)

__all__ = [
    # Spec management
    "SectionStatus",
    "Section",
    "Spec",
    # Triad classes
    "TriadPreset",
    "TriadConfig",
    "TriadOutput",
    "Triad",
    "NegotiationResponse",
    # Arbiter
    "ArbiterDecision",
    "ArbiterConfig",
    "Arbiter",
    # Pressure mechanics
    "ValidationCheck",
    "ResourceBudget",
    "PressureConfig",
    "ValidationResult",
    "CoverageReport",
    "PressureSystem",
    # Emergent center
    "EmergentMetrics",
    "DetectedPatterns",
    "EmergentIssues",
    "EmergentReport",
    "EmergentObserver",
    # Negotiation
    "NegotiationRoundResult",
    "NegotiationResult",
    "NegotiationEngine",
    # Configuration
    "ConfigError",
    "ScopeConfigModel",
    "BudgetConfigModel",
    "TriadConfigModel",
    "GlobalBudgetConfigModel",
    "PressureConfigModel",
    "ArbiterConfigModel",
    "OutputConfigModel",
    "HFSConfig",
    "load_config",
    "load_config_dict",
    # Orchestrator
    "HFSResult",
    "HFSOrchestrator",
    "run_hfs",
]
