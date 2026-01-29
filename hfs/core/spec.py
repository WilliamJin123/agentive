"""Spec management for HFS - the shared mutable state (warm wax).

The Spec is the shared document that all triads read from and write to.
It serves as the "warm wax" that allows boundaries to deform during
negotiation before freezing into final assignments.

Key concepts:
- Temperature: 1.0 = fully malleable, 0.0 = frozen
- Section statuses flow: unclaimed -> contested -> claimed -> frozen
- Claims are registered during deliberation phase
- Concession happens during negotiation
- Freeze happens when negotiation ends
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time


class SectionStatus(Enum):
    """Status of a spec section in the negotiation lifecycle.

    Flow: UNCLAIMED -> CONTESTED -> CLAIMED -> FROZEN
    """
    UNCLAIMED = "unclaimed"   # No triad has claimed this yet
    CONTESTED = "contested"   # Multiple triads want this section
    CLAIMED = "claimed"       # Single owner, but not yet frozen
    FROZEN = "frozen"         # Ownership finalized, content locked


@dataclass
class Section:
    """A single section of the spec that triads can claim and own.

    Attributes:
        status: Current status in the negotiation lifecycle
        owner: Triad ID that owns this section (only set when CLAIMED or FROZEN)
        claims: List of triad IDs that have claimed this section
        content: Final content after freezing (from winning proposal)
        proposals: Dict mapping triad_id -> their proposed content
        history: Audit trail of all actions on this section
    """
    status: SectionStatus = SectionStatus.UNCLAIMED
    owner: Optional[str] = None
    claims: List[str] = field(default_factory=list)
    content: Optional[Any] = None
    proposals: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def _record_history(self, round_num: int, action: str, by: str, **extra: Any) -> None:
        """Record an action in the section history."""
        entry = {
            "round": round_num,
            "action": action,
            "by": by,
            "timestamp": time.time(),
            **extra
        }
        self.history.append(entry)


@dataclass
class Spec:
    """The shared mutable specification document.

    This is the "warm wax" that all triads read from and write to.
    Temperature controls malleability - high temperature means fluid
    boundaries, zero temperature means frozen/locked.

    Attributes:
        temperature: Current temperature (1.0 = malleable, 0.0 = frozen)
        round: Current negotiation round number
        status: Overall spec status (initializing/negotiating/cooling/frozen/executing)
        sections: Dict mapping section_name -> Section
    """
    temperature: float = 1.0
    round: int = 0
    status: str = "initializing"
    sections: Dict[str, Section] = field(default_factory=dict)

    def register_claim(self, triad_id: str, section_name: str, proposal: Any) -> None:
        """Register a triad's claim on a section.

        Creates the section if it doesn't exist. Adds the triad to claimants
        and stores their proposal. Updates section status based on number
        of claimants.

        Args:
            triad_id: ID of the triad making the claim
            section_name: Name of the section being claimed
            proposal: The triad's proposed content for this section
        """
        # Get or create section
        if section_name not in self.sections:
            self.sections[section_name] = Section()

        section = self.sections[section_name]

        # Don't allow claims on frozen sections
        if section.status == SectionStatus.FROZEN:
            section._record_history(
                self.round, "claim_rejected", triad_id,
                reason="section_frozen"
            )
            return

        # Add triad to claimants if not already present
        if triad_id not in section.claims:
            section.claims.append(triad_id)

        # Store/update the proposal
        section.proposals[triad_id] = proposal

        # Update status based on number of claimants
        num_claimants = len(section.claims)
        if num_claimants > 1:
            section.status = SectionStatus.CONTESTED
            section.owner = None  # No single owner when contested
        elif num_claimants == 1:
            section.status = SectionStatus.CLAIMED
            section.owner = triad_id

        # Record in history
        section._record_history(
            self.round, "claim", triad_id,
            num_claimants=num_claimants,
            status=section.status.value
        )

    def concede(self, triad_id: str, section_name: str) -> bool:
        """Triad withdraws claim from a section.

        Removes the triad from claimants and deletes their proposal.
        Updates section status: if one claimant remains, they become
        owner; if zero remain, section becomes unclaimed.

        Args:
            triad_id: ID of the triad conceding
            section_name: Name of the section being conceded

        Returns:
            True if concession was successful, False if section doesn't
            exist or triad wasn't a claimant
        """
        # Check section exists
        if section_name not in self.sections:
            return False

        section = self.sections[section_name]

        # Don't allow concession on frozen sections
        if section.status == SectionStatus.FROZEN:
            section._record_history(
                self.round, "concede_rejected", triad_id,
                reason="section_frozen"
            )
            return False

        # Check triad is actually a claimant
        if triad_id not in section.claims:
            return False

        # Remove from claimants and delete proposal
        section.claims.remove(triad_id)
        if triad_id in section.proposals:
            del section.proposals[triad_id]

        # Update status based on remaining claimants
        num_remaining = len(section.claims)
        if num_remaining == 1:
            section.status = SectionStatus.CLAIMED
            section.owner = section.claims[0]
        elif num_remaining == 0:
            section.status = SectionStatus.UNCLAIMED
            section.owner = None
        # If still > 1, stays CONTESTED

        # Record in history
        section._record_history(
            self.round, "concede", triad_id,
            remaining_claimants=num_remaining,
            status=section.status.value,
            new_owner=section.owner
        )

        return True

    def update_proposal(self, triad_id: str, section_name: str, proposal: Any) -> bool:
        """Update a triad's proposal for a section (REVISE action).

        Args:
            triad_id: ID of the triad updating their proposal
            section_name: Name of the section
            proposal: The new proposed content

        Returns:
            True if update was successful, False if section doesn't exist
            or triad isn't a claimant
        """
        if section_name not in self.sections:
            return False

        section = self.sections[section_name]

        if section.status == SectionStatus.FROZEN:
            return False

        if triad_id not in section.claims:
            return False

        old_proposal = section.proposals.get(triad_id)
        section.proposals[triad_id] = proposal

        section._record_history(
            self.round, "revise", triad_id,
            had_previous=old_proposal is not None
        )

        return True

    def freeze(self) -> None:
        """Freeze all sections, ending negotiation.

        Sets temperature to 0, marks status as frozen, and for each
        non-unclaimed section:
        - Sets status to FROZEN
        - Copies the owner's proposal to content (if owner exists)

        Sections with no owner remain UNCLAIMED (this represents a
        coverage gap that should be flagged).
        """
        self.temperature = 0.0
        self.status = "frozen"

        for section_name, section in self.sections.items():
            if section.status == SectionStatus.UNCLAIMED:
                # Coverage gap - section has no owner
                section._record_history(
                    self.round, "freeze_unclaimed", "system",
                    warning="coverage_gap"
                )
                continue

            # Freeze the section
            section.status = SectionStatus.FROZEN

            # Lock in the owner's proposal as final content
            if section.owner and section.owner in section.proposals:
                section.content = section.proposals[section.owner]

            section._record_history(
                self.round, "freeze", "system",
                final_owner=section.owner,
                has_content=section.content is not None
            )

    def get_contested_sections(self) -> List[str]:
        """Return list of section names that are still contested.

        Returns:
            List of section names with CONTESTED status
        """
        return [
            name for name, section in self.sections.items()
            if section.status == SectionStatus.CONTESTED
        ]

    def get_unclaimed_sections(self) -> List[str]:
        """Return list of section names that have no claims.

        Returns:
            List of section names with UNCLAIMED status
        """
        return [
            name for name, section in self.sections.items()
            if section.status == SectionStatus.UNCLAIMED
        ]

    def get_claimed_sections(self) -> List[str]:
        """Return list of section names that have a single owner but aren't frozen.

        Returns:
            List of section names with CLAIMED status
        """
        return [
            name for name, section in self.sections.items()
            if section.status == SectionStatus.CLAIMED
        ]

    def get_frozen_sections(self) -> List[str]:
        """Return list of section names that are frozen.

        Returns:
            List of section names with FROZEN status
        """
        return [
            name for name, section in self.sections.items()
            if section.status == SectionStatus.FROZEN
        ]

    def get_section_owner(self, section_name: str) -> Optional[str]:
        """Get the owner of a section.

        Args:
            section_name: Name of the section

        Returns:
            Triad ID of owner, or None if no owner/section doesn't exist
        """
        section = self.sections.get(section_name)
        return section.owner if section else None

    def get_section_claimants(self, section_name: str) -> List[str]:
        """Get all claimants for a section.

        Args:
            section_name: Name of the section

        Returns:
            List of triad IDs that have claimed this section
        """
        section = self.sections.get(section_name)
        return list(section.claims) if section else []

    def get_section_proposals(self, section_name: str) -> Dict[str, Any]:
        """Get all proposals for a section.

        Args:
            section_name: Name of the section

        Returns:
            Dict mapping triad_id -> proposal
        """
        section = self.sections.get(section_name)
        return dict(section.proposals) if section else {}

    def initialize_sections(self, section_names: List[str]) -> None:
        """Initialize empty sections from a list of names.

        This is typically called at the start to define the "territory"
        that triads will divide up.

        Args:
            section_names: List of section names to initialize
        """
        for name in section_names:
            if name not in self.sections:
                self.sections[name] = Section()

    def advance_round(self, temperature_decay: float = 0.15) -> None:
        """Advance to the next negotiation round.

        Increments round counter and decreases temperature.

        Args:
            temperature_decay: Amount to decrease temperature (default 0.15)
        """
        self.round += 1
        self.temperature = max(0.0, self.temperature - temperature_decay)

        if self.status == "initializing":
            self.status = "negotiating"
        elif self.temperature <= 0.1 and self.status == "negotiating":
            self.status = "cooling"

    def is_frozen(self) -> bool:
        """Check if the spec is frozen.

        Returns:
            True if temperature is 0 and status is frozen
        """
        return self.temperature == 0.0 and self.status == "frozen"

    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate a coverage report showing section ownership.

        Returns:
            Dict with sections grouped by status and owner information
        """
        return {
            "total_sections": len(self.sections),
            "unclaimed": self.get_unclaimed_sections(),
            "contested": self.get_contested_sections(),
            "claimed": self.get_claimed_sections(),
            "frozen": self.get_frozen_sections(),
            "ownership": {
                name: section.owner
                for name, section in self.sections.items()
                if section.owner
            },
            "coverage_gaps": len(self.get_unclaimed_sections()),
            "unresolved_conflicts": len(self.get_contested_sections()),
        }

    def get_full_history(self) -> List[Dict[str, Any]]:
        """Compile full negotiation history across all sections.

        Returns:
            List of history entries sorted by round and timestamp
        """
        history = []
        for section_name, section in self.sections.items():
            for entry in section.history:
                history.append({
                    "section": section_name,
                    **entry
                })

        return sorted(history, key=lambda x: (x["round"], x.get("timestamp", 0)))
