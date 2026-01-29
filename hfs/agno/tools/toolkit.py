"""HFSToolkit - Agno toolkit for HFS spec operations.

This module provides the HFSToolkit class which extends Agno's Toolkit
to provide HFS-specific tools for agents during deliberation, negotiation,
and execution phases.

NOTE: This module must be imported from the project root (e.g., `from hfs.agno.tools import HFSToolkit`)
to avoid name collision with the local hfs/agno/tools directory shadowing the external agno package.
"""

from agno.tools.toolkit import Toolkit
from typing import Callable, List, Optional, TYPE_CHECKING
from pydantic import ValidationError
import json

from .schemas import (
    RegisterClaimInput, RegisterClaimOutput,
    NegotiateResponseInput, NegotiateResponseOutput, NegotiationDecision,
    GenerateCodeInput, GenerateCodeOutput,
    ClaimsStateOutput, NegotiationStateOutput,
)
from .errors import format_validation_error, format_runtime_error

if TYPE_CHECKING:
    from hfs.core.spec import Spec


class HFSToolkit(Toolkit):
    """HFS operation tools with shared spec state access.

    Provides tools for Agno agents to interact with the HFS spec during
    deliberation, negotiation, and execution phases.

    Tools:
        - register_claim: Claim ownership of a spec section
        - negotiate_response: Respond to negotiation (concede/revise/hold)
        - generate_code: Generate code for owned section (placeholder)
        - get_current_claims: Get all claims grouped by status
        - get_negotiation_state: Get details of contested sections

    All tools validate inputs with Pydantic and return JSON strings.
    ValidationError returns retry_allowed=True with hints.
    RuntimeError returns retry_allowed=False.
    """

    def __init__(self, spec: "Spec", triad_id: str, **kwargs):
        """Initialize HFS toolkit with shared state.

        Args:
            spec: The shared Spec instance (warm wax)
            triad_id: Identifier of the triad using these tools
            **kwargs: Additional args passed to Toolkit base
        """
        self._spec = spec
        self._triad_id = triad_id

        tools: List[Callable] = [
            self.register_claim,
            self.negotiate_response,
            self.generate_code,
            self.get_current_claims,
            self.get_negotiation_state,
        ]

        super().__init__(name="hfs_tools", tools=tools, **kwargs)

    def register_claim(self, section_id: str, proposal: str) -> str:
        """Register your claim on a section of the spec.

        WHEN TO USE: Call this during the deliberation phase when you want to
        claim ownership of a section. You can claim sections in your scope_primary
        (guaranteed) or scope_reach (competitive).

        IMPORTANT CONSTRAINTS:
        - section_id must be a non-empty string (max 128 chars)
        - proposal must contain complete content for the section
        - You cannot claim frozen sections
        - If another agent already claimed this section, it becomes "contested"

        EXAMPLE:
        >>> register_claim(section_id="header", proposal="Navigation bar with logo and links")

        Args:
            section_id: The section to claim. Must match a section name in the spec.
            proposal: Your complete proposed content for this section.

        Returns:
            JSON with success status, section status, and current claimants.
            On validation error, returns error message with correction hints.
        """
        # Validate input
        try:
            input_model = RegisterClaimInput(section_id=section_id, proposal=proposal)
        except ValidationError as e:
            return format_validation_error(e)

        # Execute claim
        try:
            self._spec.register_claim(self._triad_id, input_model.section_id, input_model.proposal)

            section = self._spec.sections.get(input_model.section_id)
            output = RegisterClaimOutput(
                success=True,
                message=f"Claim registered for {input_model.section_id}",
                section_id=input_model.section_id,
                status=section.status.value if section else "unknown",
                current_claimants=list(section.claims) if section else [],
            )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, f"register_claim({input_model.section_id})")

    def negotiate_response(
        self,
        section_id: str,
        decision: str,
        revised_proposal: Optional[str] = None,
    ) -> str:
        """Submit your negotiation response for a contested section.

        WHEN TO USE: Call this when you're in a negotiation round and need to
        respond to other agents' proposals for a section you've claimed.

        DECISIONS:
        - "concede": Withdraw your claim. Use when another proposal is clearly better.
        - "revise": Update your proposal. Provide revised_proposal with improvements.
        - "hold": Maintain your current position. Use when your proposal is strongest.

        IMPORTANT CONSTRAINTS:
        - decision must be exactly one of: "concede", "revise", "hold"
        - If decision is "revise", you MUST provide revised_proposal
        - If decision is "concede" or "hold", revised_proposal is ignored
        - You must have a claim on this section to negotiate

        EXAMPLE:
        >>> negotiate_response(section_id="header", decision="revise",
        ...                    revised_proposal="Updated navigation with improved accessibility")

        Args:
            section_id: The contested section's identifier
            decision: Your response - "concede", "revise", or "hold"
            revised_proposal: New proposal content (required for "revise")

        Returns:
            JSON with decision status, round number, and participants.
            On validation error, returns error message with correction hints.
        """
        # Validate input
        try:
            input_model = NegotiateResponseInput(
                section_id=section_id,
                decision=decision,
                revised_proposal=revised_proposal,
            )
        except ValidationError as e:
            return format_validation_error(e)

        # Execute negotiation action
        try:
            section = self._spec.sections.get(input_model.section_id)
            if not section:
                return format_runtime_error(
                    ValueError(f"Section '{input_model.section_id}' not found"),
                    "negotiate_response"
                )

            participants = list(section.claims)

            if input_model.decision == NegotiationDecision.CONCEDE:
                success = self._spec.concede(self._triad_id, input_model.section_id)
                if not success:
                    return format_runtime_error(
                        ValueError(f"Could not concede - not a claimant of '{input_model.section_id}'"),
                        "negotiate_response.concede"
                    )
                message = f"Conceded claim on {input_model.section_id}"

            elif input_model.decision == NegotiationDecision.REVISE:
                success = self._spec.update_proposal(
                    self._triad_id,
                    input_model.section_id,
                    input_model.revised_proposal,
                )
                if not success:
                    return format_runtime_error(
                        ValueError(f"Could not revise - not a claimant of '{input_model.section_id}'"),
                        "negotiate_response.revise"
                    )
                message = f"Revised proposal for {input_model.section_id}"

            else:  # HOLD
                if self._triad_id not in section.claims:
                    return format_runtime_error(
                        ValueError(f"Cannot hold - not a claimant of '{input_model.section_id}'"),
                        "negotiate_response.hold"
                    )
                message = f"Holding position on {input_model.section_id}"

            output = NegotiateResponseOutput(
                success=True,
                message=message,
                section_id=input_model.section_id,
                decision=input_model.decision.value,
                round_number=self._spec.round,
                participants=participants,
            )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, f"negotiate_response({input_model.section_id})")

    def generate_code(self, section_id: str) -> str:
        """Generate implementation code for a section you own.

        WHEN TO USE: During execution phase after spec is frozen.
        Only call for sections where you are the owner.

        IMPORTANT CONSTRAINTS:
        - Spec must be frozen (temperature = 0)
        - You must be the owner of the section
        - Section must have FROZEN status
        - Code generation is a placeholder for future phases

        EXAMPLE:
        >>> generate_code(section_id="header")

        Args:
            section_id: The section to generate code for

        Returns:
            JSON with generated code or error.
            Returns error if spec not frozen or you don't own the section.
        """
        # Validate input
        try:
            input_model = GenerateCodeInput(section_id=section_id)
        except ValidationError as e:
            return format_validation_error(e)

        # Check preconditions
        try:
            if not self._spec.is_frozen():
                return format_runtime_error(
                    ValueError("Spec must be frozen before generating code"),
                    "generate_code.precondition"
                )

            section = self._spec.sections.get(input_model.section_id)
            if not section:
                return format_runtime_error(
                    ValueError(f"Section '{input_model.section_id}' not found"),
                    "generate_code"
                )

            if section.owner != self._triad_id:
                return format_runtime_error(
                    ValueError(f"Not owner of section '{input_model.section_id}' (owner: {section.owner})"),
                    "generate_code.ownership"
                )

            # Placeholder for actual code generation in future phases
            output = GenerateCodeOutput(
                success=True,
                message=f"Code generation placeholder for {input_model.section_id}",
                section_id=input_model.section_id,
                code=None,  # Will be implemented in Phase 3+
            )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, f"generate_code({input_model.section_id})")

    def get_current_claims(self) -> str:
        """Get all current claims in the spec grouped by status.

        WHEN TO USE: To understand the current state before claiming or negotiating.
        Call this to see what's available, what you've claimed, and what's contested.

        IMPORTANT CONSTRAINTS:
        - No input parameters needed
        - Returns sections grouped by their current status
        - your_claims shows sections where you have a claim

        EXAMPLE:
        >>> get_current_claims()

        Returns:
            JSON with sections grouped by status (unclaimed, claimed, contested, frozen),
            your_claims list, current temperature, and round number.
        """
        try:
            your_claims = [
                name for name, section in self._spec.sections.items()
                if self._triad_id in section.claims
            ]

            output = ClaimsStateOutput(
                success=True,
                message="Current claims retrieved",
                unclaimed=self._spec.get_unclaimed_sections(),
                claimed=self._spec.get_claimed_sections(),
                contested=self._spec.get_contested_sections(),
                frozen=self._spec.get_frozen_sections(),
                your_claims=your_claims,
                temperature=self._spec.temperature,
                round=self._spec.round,
            )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, "get_current_claims")

    def get_negotiation_state(self, section_id: Optional[str] = None) -> str:
        """Get negotiation state for a section or all contested sections.

        WHEN TO USE: Before responding in a negotiation round to see other proposals.
        Call with section_id for specific section details, or without for all contested.

        IMPORTANT CONSTRAINTS:
        - If section_id provided, returns detailed state for that section
        - If section_id is None, returns summary of all contested sections
        - Proposals are truncated to prevent overly long responses

        EXAMPLE:
        >>> get_negotiation_state()  # All contested sections
        >>> get_negotiation_state(section_id="header")  # Specific section

        Args:
            section_id: Optional specific section. If None, returns all contested.

        Returns:
            JSON with proposals, claimants, and details for requested sections.
        """
        try:
            if section_id:
                section = self._spec.sections.get(section_id)
                if not section:
                    return format_runtime_error(
                        ValueError(f"Section '{section_id}' not found"),
                        "get_negotiation_state"
                    )

                # Return single section with detail
                return json.dumps({
                    "success": True,
                    "message": f"Negotiation state for {section_id}",
                    "section_id": section_id,
                    "status": section.status.value,
                    "claimants": list(section.claims),
                    "proposals": {k: str(v)[:500] for k, v in section.proposals.items()},
                    "owner": section.owner,
                    "contested_sections": {section_id: {
                        "claimants": list(section.claims),
                        "proposals": {k: str(v)[:200] for k, v in section.proposals.items()},
                    }},
                    "total_contested": 1 if len(section.claims) > 1 else 0,
                })

            # Return all contested sections
            contested = {}
            for name in self._spec.get_contested_sections():
                section = self._spec.sections[name]
                contested[name] = {
                    "claimants": list(section.claims),
                    "proposals": {k: str(v)[:200] for k, v in section.proposals.items()},
                }

            output = NegotiationStateOutput(
                success=True,
                message="Negotiation state retrieved",
                contested_sections=contested,
                total_contested=len(contested),
            )
            return output.model_dump_json()

        except Exception as e:
            return format_runtime_error(e, "get_negotiation_state")
