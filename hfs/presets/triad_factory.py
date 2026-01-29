"""Factory for creating triad instances based on configuration.

This module provides the create_triad() function which instantiates
the correct triad preset class based on the provided configuration.
"""

from typing import Any, Dict, Optional, Type

from ..core.triad import Triad, TriadConfig, TriadPreset
from .hierarchical import HierarchicalTriad
from .dialectic import DialecticTriad
from .consensus import ConsensusTriad


# Registry mapping preset types to their implementing classes
TRIAD_REGISTRY: Dict[TriadPreset, Type[Triad]] = {
    TriadPreset.HIERARCHICAL: HierarchicalTriad,
    TriadPreset.DIALECTIC: DialecticTriad,
    TriadPreset.CONSENSUS: ConsensusTriad,
}


def create_triad(config: TriadConfig, llm_client: Any) -> Triad:
    """Create a triad instance based on configuration.

    Factory function that instantiates the correct triad preset class
    based on the preset specified in the configuration.

    Args:
        config: TriadConfig specifying the preset type and other settings.
        llm_client: The LLM client to use for agent interactions.

    Returns:
        An instance of the appropriate Triad subclass (HierarchicalTriad,
        DialecticTriad, or ConsensusTriad).

    Raises:
        ValueError: If the preset type in config is not recognized.

    Example:
        >>> from hfs.core.triad import TriadConfig, TriadPreset
        >>> config = TriadConfig(
        ...     id="layout_triad",
        ...     preset=TriadPreset.HIERARCHICAL,
        ...     scope_primary=["layout", "grid"],
        ...     scope_reach=["spacing"],
        ...     budget_tokens=10000,
        ...     budget_tool_calls=50,
        ...     budget_time_ms=30000,
        ...     objectives=["performance", "responsiveness"]
        ... )
        >>> triad = create_triad(config, llm_client)
        >>> isinstance(triad, HierarchicalTriad)
        True
    """
    preset = config.preset

    if preset not in TRIAD_REGISTRY:
        valid_presets = [p.value for p in TriadPreset]
        raise ValueError(
            f"Unknown triad preset: {preset}. "
            f"Valid presets are: {valid_presets}"
        )

    triad_class = TRIAD_REGISTRY[preset]
    return triad_class(config, llm_client)


def create_triad_from_dict(config_dict: Dict[str, Any], llm_client: Any) -> Triad:
    """Create a triad from a dictionary configuration.

    Convenience function that constructs a TriadConfig from a dictionary
    and then creates the appropriate triad instance.

    Args:
        config_dict: Dictionary with triad configuration. Must include:
            - id: Unique identifier
            - preset: Preset name ("hierarchical", "dialectic", "consensus")
            - scope_primary: List of primary scope sections
            - scope_reach: List of reach scope sections
            - budget_tokens: Token budget
            - budget_tool_calls: Tool call budget
            - budget_time_ms: Time budget in milliseconds
            - objectives: List of objective names
            - system_context (optional): Additional context string
        llm_client: The LLM client to use.

    Returns:
        An instance of the appropriate Triad subclass.

    Raises:
        ValueError: If preset is invalid or required fields are missing.
        KeyError: If required configuration keys are missing.

    Example:
        >>> config = {
        ...     "id": "visual_triad",
        ...     "preset": "dialectic",
        ...     "scope_primary": ["colors", "typography"],
        ...     "scope_reach": ["spacing"],
        ...     "budget_tokens": 15000,
        ...     "budget_tool_calls": 75,
        ...     "budget_time_ms": 45000,
        ...     "objectives": ["aesthetic_quality", "brand_consistency"]
        ... }
        >>> triad = create_triad_from_dict(config, llm_client)
        >>> isinstance(triad, DialecticTriad)
        True
    """
    # Parse preset string to enum
    preset_str = config_dict.get("preset", "")
    try:
        preset = TriadPreset(preset_str)
    except ValueError:
        valid_presets = [p.value for p in TriadPreset]
        raise ValueError(
            f"Invalid preset '{preset_str}'. "
            f"Valid presets are: {valid_presets}"
        )

    # Build TriadConfig
    config = TriadConfig(
        id=config_dict["id"],
        preset=preset,
        scope_primary=config_dict["scope_primary"],
        scope_reach=config_dict["scope_reach"],
        budget_tokens=config_dict["budget_tokens"],
        budget_tool_calls=config_dict["budget_tool_calls"],
        budget_time_ms=config_dict["budget_time_ms"],
        objectives=config_dict["objectives"],
        system_context=config_dict.get("system_context"),
    )

    return create_triad(config, llm_client)


def get_preset_info(preset: TriadPreset) -> Dict[str, Any]:
    """Get information about a triad preset.

    Returns metadata about the preset including its implementing class,
    agent roles, and recommended use cases.

    Args:
        preset: The preset to get information about.

    Returns:
        Dictionary with preset information:
            - class: The implementing class
            - agent_roles: List of agent role names
            - best_for: List of recommended use cases
            - flow: Description of the deliberation flow

    Raises:
        ValueError: If preset is not recognized.
    """
    info_registry = {
        TriadPreset.HIERARCHICAL: {
            "class": HierarchicalTriad,
            "agent_roles": ["orchestrator", "worker_a", "worker_b"],
            "best_for": ["layout", "state_management", "performance", "code_generation"],
            "flow": "receive task -> decompose -> parallel execute -> merge -> validate",
        },
        TriadPreset.DIALECTIC: {
            "class": DialecticTriad,
            "agent_roles": ["proposer", "critic", "synthesizer"],
            "best_for": ["visual_design", "motion_design", "interaction_patterns", "creative_decisions"],
            "flow": "propose -> critique -> revise -> synthesize",
        },
        TriadPreset.CONSENSUS: {
            "class": ConsensusTriad,
            "agent_roles": ["peer_1", "peer_2", "peer_3"],
            "best_for": ["accessibility_decisions", "standards_compliance", "coherence_checking"],
            "flow": "all propose -> debate -> vote (2/3 majority) -> finalize",
        },
    }

    if preset not in info_registry:
        raise ValueError(f"Unknown preset: {preset}")

    return info_registry[preset]


def list_available_presets() -> Dict[str, Dict[str, Any]]:
    """List all available triad presets with their information.

    Returns:
        Dictionary mapping preset names to their information dicts.

    Example:
        >>> presets = list_available_presets()
        >>> list(presets.keys())
        ['hierarchical', 'dialectic', 'consensus']
    """
    return {
        preset.value: get_preset_info(preset)
        for preset in TriadPreset
    }
