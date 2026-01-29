"""HFS Agno Teams package.

This package provides the Agno Team infrastructure for HFS triads,
including the AgnoTriad base class, all three preset implementations,
and supporting schemas.

Exports:
    AgnoTriad: Abstract base class for Agno-based triads
    HierarchicalAgnoTriad: Orchestrator + 2 workers pattern implementation
    DialecticAgnoTriad: Thesis-antithesis-synthesis pattern implementation
    ConsensusAgnoTriad: Three equal peers with voting pattern implementation
    PhaseSummary: Structured summary for phase transitions
    TriadSessionState: Session state with role-scoped history
    TriadExecutionError: Exception for triad execution failures
"""

from .schemas import PhaseSummary, TriadSessionState, TriadExecutionError
from .base import AgnoTriad
from .hierarchical import HierarchicalAgnoTriad
from .dialectic import DialecticAgnoTriad
from .consensus import ConsensusAgnoTriad

__all__ = [
    "AgnoTriad",
    "HierarchicalAgnoTriad",
    "DialecticAgnoTriad",
    "ConsensusAgnoTriad",
    "PhaseSummary",
    "TriadSessionState",
    "TriadExecutionError",
]
