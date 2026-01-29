"""HFS Agno Teams package.

This package provides the Agno Team infrastructure for HFS triads,
including the AgnoTriad base class and supporting schemas.

Exports:
    AgnoTriad: Abstract base class for Agno-based triads
    PhaseSummary: Structured summary for phase transitions
    TriadSessionState: Session state with role-scoped history
    TriadExecutionError: Exception for triad execution failures
"""

from .schemas import PhaseSummary, TriadSessionState, TriadExecutionError
from .base import AgnoTriad

__all__ = [
    "AgnoTriad",
    "PhaseSummary",
    "TriadSessionState",
    "TriadExecutionError",
]
