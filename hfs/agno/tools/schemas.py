"""Pydantic models for HFS tool inputs and outputs.

These schemas define the contracts for all HFS tools used by Agno agents.
Input models validate agent-provided data with detailed error messages.
Output models ensure consistent, typed responses.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from enum import Enum


class NegotiationDecision(str, Enum):
    """Decision options for negotiate_response tool."""
    CONCEDE = "concede"
    REVISE = "revise"
    HOLD = "hold"


# ============================================================================
# Input Models
# ============================================================================

class RegisterClaimInput(BaseModel):
    """Input for register_claim tool.

    Attributes:
        section_id: ID of the section to claim (1-128 chars, whitespace trimmed)
        proposal: Proposed content for the section (non-empty)
    """
    section_id: str = Field(..., min_length=1, max_length=128)
    proposal: str = Field(..., min_length=1)

    @field_validator('section_id')
    @classmethod
    def strip_section_id(cls, v: str) -> str:
        """Trim whitespace from section_id."""
        return v.strip()


class NegotiateResponseInput(BaseModel):
    """Input for negotiate_response tool.

    Attributes:
        section_id: ID of the section being negotiated
        decision: One of CONCEDE, REVISE, or HOLD
        revised_proposal: Required when decision is REVISE
    """
    section_id: str = Field(..., min_length=1)
    decision: NegotiationDecision
    revised_proposal: Optional[str] = None

    @model_validator(mode='after')
    def require_proposal_for_revise(self) -> 'NegotiateResponseInput':
        """Ensure revised_proposal is provided when decision is REVISE."""
        if self.decision == NegotiationDecision.REVISE and not self.revised_proposal:
            raise ValueError("revised_proposal required when decision is 'revise'")
        return self


class GenerateCodeInput(BaseModel):
    """Input for generate_code tool.

    Attributes:
        section_id: ID of the frozen section to generate code for
    """
    section_id: str = Field(..., min_length=1)


# ============================================================================
# Output Models
# ============================================================================

class ToolOutput(BaseModel):
    """Base output model for all tools.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable status message
    """
    success: bool
    message: str


class RegisterClaimOutput(ToolOutput):
    """Output for register_claim tool.

    Attributes:
        section_id: ID of the claimed section
        status: Current section status (unclaimed, claimed, contested, frozen)
        current_claimants: List of triad IDs currently claiming this section
    """
    section_id: str
    status: str
    current_claimants: List[str]


class NegotiateResponseOutput(ToolOutput):
    """Output for negotiate_response tool.

    Attributes:
        section_id: ID of the negotiated section
        decision: The decision that was applied
        round_number: Current negotiation round
        participants: List of triads participating in this negotiation
    """
    section_id: str
    decision: str
    round_number: int
    participants: List[str]


class GenerateCodeOutput(ToolOutput):
    """Output for generate_code tool.

    Attributes:
        section_id: ID of the section
        code: Generated code (placeholder for future phases)
    """
    section_id: str
    code: Optional[str] = None


class ClaimsStateOutput(ToolOutput):
    """Output for get_current_claims tool.

    Attributes:
        unclaimed: List of section IDs with no claims
        claimed: List of section IDs with single owner
        contested: List of section IDs with multiple claimants
        frozen: List of section IDs that are frozen
        your_claims: List of section IDs you have claimed
        temperature: Current spec temperature (1.0 = malleable, 0.0 = frozen)
        round: Current negotiation round number
    """
    unclaimed: List[str]
    claimed: List[str]
    contested: List[str]
    frozen: List[str]
    your_claims: List[str]
    temperature: float
    round: int


class NegotiationStateOutput(ToolOutput):
    """Output for get_negotiation_state tool.

    Attributes:
        contested_sections: Dict mapping section_id to negotiation details
        total_contested: Number of contested sections
    """
    contested_sections: Dict[str, Any]
    total_contested: int


class ErrorOutput(BaseModel):
    """Error output for validation and runtime errors.

    Attributes:
        success: Always False for errors
        error: Error type (validation_error, runtime_error)
        message: Human-readable error message
        hints: Actionable hints for fixing the error
        retry_allowed: Whether the agent should retry
    """
    success: bool = False
    error: str
    message: str
    hints: List[str] = []
    retry_allowed: bool = True
