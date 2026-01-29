"""Presets module for HFS negotiation preset configurations.

This module provides the three triad preset implementations and
factory functions for creating triad instances.

Preset Types:
    - HierarchicalTriad: Orchestrator + 2 workers pattern
      Best for: layout, state_management, performance, code_generation

    - DialecticTriad: Proposer + critic + synthesizer pattern
      Best for: visual_design, motion_design, interaction_patterns

    - ConsensusTriad: 3 equal peers with 2/3 majority voting
      Best for: accessibility_decisions, standards_compliance

Factory Functions:
    - create_triad(): Create triad from TriadConfig
    - create_triad_from_dict(): Create triad from dictionary config
    - get_preset_info(): Get metadata about a preset
    - list_available_presets(): List all available presets
"""

from .hierarchical import HierarchicalTriad
from .dialectic import DialecticTriad
from .consensus import ConsensusTriad, VoteChoice, Vote
from .triad_factory import (
    create_triad,
    create_triad_from_dict,
    get_preset_info,
    list_available_presets,
    TRIAD_REGISTRY,
)

__all__ = [
    # Triad preset classes
    "HierarchicalTriad",
    "DialecticTriad",
    "ConsensusTriad",
    # Consensus helpers
    "VoteChoice",
    "Vote",
    # Factory functions
    "create_triad",
    "create_triad_from_dict",
    "get_preset_info",
    "list_available_presets",
    "TRIAD_REGISTRY",
]
