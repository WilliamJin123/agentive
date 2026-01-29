"""Hexagonal Frontend System (HFS) - A bio-inspired multi-agent architecture.

HFS is a system for building frontend components using multiple AI agents
organized into triads. Each triad handles a specific concern (layout, visual,
interaction) and they negotiate to produce coherent, integrated output.

Main entry points:
    - HFSOrchestrator: The main class for running the HFS pipeline
    - run_hfs(): Convenience function for quick runs

Example:
    ```python
    from hfs import HFSOrchestrator

    orchestrator = HFSOrchestrator(
        config_path="config/dashboard.yaml",
        llm_client=my_llm_client
    )
    result = await orchestrator.run("Create a responsive dashboard")
    ```
"""

__version__ = "0.1.0"

# Main entry points
from .core.orchestrator import HFSOrchestrator, HFSResult, run_hfs

# Core components (for advanced usage)
from .core import (
    # Spec management
    Spec,
    SectionStatus,
    Section,
    # Triads
    Triad,
    TriadConfig,
    TriadPreset,
    TriadOutput,
    # Negotiation
    NegotiationEngine,
    NegotiationResult,
    # Arbiter
    Arbiter,
    ArbiterConfig,
    ArbiterDecision,
    # Emergent
    EmergentObserver,
    EmergentReport,
    # Configuration
    HFSConfig,
    load_config,
    load_config_dict,
    ConfigError,
)

# Presets (for creating triads manually)
from .presets import (
    create_triad,
    HierarchicalTriad,
    DialecticTriad,
    ConsensusTriad,
)

# Integration (for custom integration)
from .integration import (
    CodeMerger,
    MergedArtifact,
    Validator,
    ValidationResult,
)

__all__ = [
    # Version
    "__version__",
    # Main entry points
    "HFSOrchestrator",
    "HFSResult",
    "run_hfs",
    # Spec
    "Spec",
    "SectionStatus",
    "Section",
    # Triads
    "Triad",
    "TriadConfig",
    "TriadPreset",
    "TriadOutput",
    "create_triad",
    "HierarchicalTriad",
    "DialecticTriad",
    "ConsensusTriad",
    # Negotiation
    "NegotiationEngine",
    "NegotiationResult",
    # Arbiter
    "Arbiter",
    "ArbiterConfig",
    "ArbiterDecision",
    # Emergent
    "EmergentObserver",
    "EmergentReport",
    # Configuration
    "HFSConfig",
    "load_config",
    "load_config_dict",
    "ConfigError",
    # Integration
    "CodeMerger",
    "MergedArtifact",
    "Validator",
    "ValidationResult",
]
