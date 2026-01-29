"""HFS Tools for Agno agents.

This module provides HFSToolkit - a collection of tools that enable
Agno agents to interact with the HFS spec during deliberation,
negotiation, and execution phases.

Exports:
    HFSToolkit: Main toolkit class with all HFS tools
    NegotiationDecision: Enum for negotiate_response decisions
    RegisterClaimInput: Input model for register_claim
    NegotiateResponseInput: Input model for negotiate_response
    GenerateCodeInput: Input model for generate_code
"""

from .toolkit import HFSToolkit
from .schemas import (
    NegotiationDecision,
    RegisterClaimInput,
    NegotiateResponseInput,
    GenerateCodeInput,
)

__all__ = [
    "HFSToolkit",
    "NegotiationDecision",
    "RegisterClaimInput",
    "NegotiateResponseInput",
    "GenerateCodeInput",
]
