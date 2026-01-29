"""Negotiation engine for HFS - manages negotiation rounds between triads.

When two or more triads claim the same section, they must negotiate.
The NegotiationEngine manages this process through rounds of proposals
and responses (CONCEDE/REVISE/HOLD) until sections are resolved or
escalated to the arbiter.

Protocol flow:
1. Each claimant submits proposal for section
2. Proposals shared with all claimants
3. Each claimant can: CONCEDE (withdraw), REVISE (update proposal), HOLD (maintain)
4. Check resolution - if one claimant remains, they win
5. If still stuck after threshold rounds, escalate to arbiter
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .spec import Spec, Section, SectionStatus

if TYPE_CHECKING:
    from .triad import Triad
    from .arbiter import Arbiter, ArbiterDecision


logger = logging.getLogger(__name__)


@dataclass
class NegotiationRoundResult:
    """Result of a single negotiation round for a section.

    Attributes:
        section_name: Name of the section being negotiated
        responses: Dict mapping triad_id -> their response (concede/revise/hold)
        resolved: Whether the section was resolved this round
        escalated: Whether the section was escalated to arbiter
        winner: The winning triad_id if resolved, None otherwise
    """
    section_name: str
    responses: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    escalated: bool = False
    winner: Optional[str] = None


@dataclass
class NegotiationResult:
    """Final result of the negotiation process.

    Attributes:
        total_rounds: Number of rounds executed
        sections_resolved: List of sections resolved through negotiation
        sections_escalated: List of sections resolved through arbitration
        final_temperature: Temperature when negotiation ended
        round_history: List of results per round
    """
    total_rounds: int = 0
    sections_resolved: List[str] = field(default_factory=list)
    sections_escalated: List[str] = field(default_factory=list)
    final_temperature: float = 0.0
    round_history: List[List[NegotiationRoundResult]] = field(default_factory=list)


class NegotiationEngine:
    """Manages negotiation rounds between triads for contested sections.

    The engine runs negotiation rounds until all contested sections are resolved
    (have a single owner) or the maximum number of rounds is reached. During each
    round, triads can CONCEDE (withdraw), REVISE (update proposal), or HOLD
    (maintain position).

    When a section is stuck (no progress for escalation_threshold rounds),
    the engine escalates to an arbiter for a final decision.

    Attributes:
        triads: Dict mapping triad_id -> Triad instance
        spec: The shared Spec document being negotiated
        arbiter: Arbiter for resolving stuck negotiations
        temperature_decay: Amount to decrease temperature per round
        max_rounds: Maximum negotiation rounds allowed
        escalation_threshold: Rounds without progress before escalating
        stuck_counters: Dict mapping section_name -> rounds without progress
    """

    def __init__(
        self,
        triads: Dict[str, "Triad"],
        spec: Spec,
        arbiter: "Arbiter",
        config: Dict[str, Any]
    ):
        """Initialize the negotiation engine.

        Args:
            triads: Dict mapping triad_id -> Triad instance
            spec: The shared Spec document to negotiate
            arbiter: Arbiter instance for escalation
            config: Configuration dict with optional keys:
                - temperature_decay: Decay per round (default 0.15)
                - max_negotiation_rounds: Max rounds (default 10)
                - escalation_threshold: Stuck rounds before escalate (default 2)
        """
        self.triads = triads
        self.spec = spec
        self.arbiter = arbiter
        self.temperature_decay = config.get("temperature_decay", 0.15)
        self.max_rounds = config.get("max_negotiation_rounds", 10)
        self.escalation_threshold = config.get("escalation_threshold", 2)
        self.stuck_counters: Dict[str, int] = {}
        self._result = NegotiationResult()

    async def run(self) -> Spec:
        """Run negotiation until all sections resolved or max rounds reached.

        The negotiation loop continues while:
        - There are contested sections
        - We haven't exceeded max_rounds
        - Temperature is above 0

        After negotiation completes (or max rounds), the spec is frozen.

        Returns:
            The frozen Spec with all sections resolved
        """
        logger.info(
            f"Starting negotiation: {len(self.spec.get_contested_sections())} "
            f"contested sections, temperature={self.spec.temperature}"
        )

        # Update spec status to negotiating
        if self.spec.status == "initializing":
            self.spec.status = "negotiating"

        while (
            self.spec.get_contested_sections()
            and self.spec.round < self.max_rounds
            and self.spec.temperature > 0
        ):
            round_results = await self._run_round()
            self._result.round_history.append(round_results)

            # Advance to next round
            self.spec.round += 1
            self.spec.temperature = max(0, self.spec.temperature - self.temperature_decay)

            # Update spec status based on temperature
            if self.spec.temperature <= 0.1 and self.spec.status == "negotiating":
                self.spec.status = "cooling"

            logger.info(
                f"Round {self.spec.round} complete: "
                f"{len(self.spec.get_contested_sections())} sections still contested, "
                f"temperature={self.spec.temperature:.2f}"
            )

        # Store final results
        self._result.total_rounds = self.spec.round
        self._result.final_temperature = self.spec.temperature

        # Freeze the spec
        self.spec.freeze()
        logger.info(
            f"Negotiation complete after {self.spec.round} rounds. "
            f"Resolved: {len(self._result.sections_resolved)}, "
            f"Escalated: {len(self._result.sections_escalated)}"
        )

        return self.spec

    async def _run_round(self) -> List[NegotiationRoundResult]:
        """Execute one negotiation round for all contested sections.

        For each contested section:
        1. Gather all proposals from claimants
        2. Have each claimant review other proposals and respond
        3. Process responses (CONCEDE removes claimant, REVISE updates proposal)
        4. Check if section is resolved (single claimant wins)
        5. Track if stuck and potentially escalate

        Returns:
            List of NegotiationRoundResult for each contested section
        """
        contested = self.spec.get_contested_sections()
        round_results: List[NegotiationRoundResult] = []

        for section_name in contested:
            result = await self._negotiate_section(section_name)
            round_results.append(result)

        return round_results

    async def _negotiate_section(self, section_name: str) -> NegotiationRoundResult:
        """Run negotiation for a single contested section.

        Args:
            section_name: Name of the section to negotiate

        Returns:
            NegotiationRoundResult with the outcome
        """
        result = NegotiationRoundResult(section_name=section_name)
        section = self.spec.sections[section_name]
        claimants = list(section.claims)  # Copy to avoid mutation issues

        if len(claimants) < 2:
            # Already resolved or no claimants
            result.resolved = True
            result.winner = claimants[0] if claimants else None
            return result

        logger.debug(
            f"Negotiating section '{section_name}' with claimants: {claimants}"
        )

        # Gather responses from all claimants
        responses = await self._gather_responses(section_name, claimants, section)
        result.responses = responses

        # Process responses
        await self._process_responses(section_name, responses, section)

        # Check if section is now resolved
        section = self.spec.sections.get(section_name)
        if section is None:
            # Section was deleted (e.g., split by arbiter)
            result.resolved = True
            return result

        remaining_claimants = len(section.claims)

        if remaining_claimants == 1:
            # Section resolved - single winner
            result.resolved = True
            result.winner = section.owner
            self._result.sections_resolved.append(section_name)
            # Reset stuck counter
            if section_name in self.stuck_counters:
                del self.stuck_counters[section_name]
            logger.info(
                f"Section '{section_name}' resolved: winner is '{result.winner}'"
            )

        elif remaining_claimants == 0:
            # All claimants conceded - section is unclaimed
            result.resolved = True
            if section_name in self.stuck_counters:
                del self.stuck_counters[section_name]
            logger.warning(
                f"Section '{section_name}' has no claimants after negotiation"
            )

        else:
            # Still contested - check if stuck
            self.stuck_counters[section_name] = (
                self.stuck_counters.get(section_name, 0) + 1
            )

            if self.stuck_counters[section_name] >= self.escalation_threshold:
                # Escalate to arbiter
                logger.info(
                    f"Section '{section_name}' stuck for "
                    f"{self.stuck_counters[section_name]} rounds, escalating to arbiter"
                )
                await self._escalate(section_name)
                result.escalated = True
                self._result.sections_escalated.append(section_name)

                # Check resolution after escalation
                section = self.spec.sections.get(section_name)
                if section is None or section.status != SectionStatus.CONTESTED:
                    result.resolved = True
                    if section and section.owner:
                        result.winner = section.owner

        return result

    async def _gather_responses(
        self,
        section_name: str,
        claimants: List[str],
        section: Section
    ) -> Dict[str, str]:
        """Gather negotiation responses from all claimants.

        Each claimant is shown the other proposals and asked to respond
        with CONCEDE, REVISE, or HOLD.

        Args:
            section_name: Name of the contested section
            claimants: List of triad IDs claiming this section
            section: The Section object with proposals

        Returns:
            Dict mapping triad_id -> response ("concede", "revise", or "hold")
        """
        responses: Dict[str, str] = {}

        # Create tasks for parallel negotiation
        async def get_response(triad_id: str) -> tuple:
            # Build other proposals dict (excluding this triad's proposal)
            other_proposals = {
                tid: section.proposals[tid]
                for tid in claimants
                if tid != triad_id and tid in section.proposals
            }

            try:
                triad = self.triads.get(triad_id)
                if triad is None:
                    logger.warning(
                        f"Triad '{triad_id}' not found, treating as HOLD"
                    )
                    return (triad_id, "hold")

                response = await triad.negotiate(section_name, other_proposals)

                # Validate response
                if response not in ("concede", "revise", "hold"):
                    logger.warning(
                        f"Invalid response '{response}' from triad '{triad_id}', "
                        f"treating as HOLD"
                    )
                    response = "hold"

                return (triad_id, response)

            except Exception as e:
                logger.error(
                    f"Error getting response from triad '{triad_id}': {e}. "
                    f"Treating as HOLD"
                )
                return (triad_id, "hold")

        # Execute negotiations in parallel
        tasks = [get_response(triad_id) for triad_id in claimants]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                logger.error(f"Negotiation task failed: {item}")
                continue
            triad_id, response = item
            responses[triad_id] = response

        return responses

    async def _process_responses(
        self,
        section_name: str,
        responses: Dict[str, str],
        section: Section
    ) -> None:
        """Process negotiation responses from claimants.

        - CONCEDE: Remove claimant from section
        - REVISE: Get updated proposal from triad and update spec
        - HOLD: No action needed

        Args:
            section_name: Name of the section
            responses: Dict mapping triad_id -> response
            section: The Section object
        """
        for triad_id, response in responses.items():
            if response == "concede":
                # Triad withdraws claim
                logger.debug(
                    f"Triad '{triad_id}' CONCEDES section '{section_name}'"
                )
                self.spec.concede(triad_id, section_name)

            elif response == "revise":
                # Triad wants to update their proposal
                logger.debug(
                    f"Triad '{triad_id}' REVISES proposal for '{section_name}'"
                )
                # Get the updated proposal from the triad
                triad = self.triads.get(triad_id)
                if triad:
                    try:
                        # The triad should have already prepared the revised
                        # proposal during negotiate() call. We need to get it.
                        # For now, we check if the triad has a revised_proposal
                        # attribute or call a method to get it.
                        revised_proposal = await self._get_revised_proposal(
                            triad, section_name, section
                        )
                        if revised_proposal is not None:
                            self.spec.update_proposal(
                                triad_id, section_name, revised_proposal
                            )
                    except Exception as e:
                        logger.error(
                            f"Error getting revised proposal from '{triad_id}': {e}"
                        )

            elif response == "hold":
                # Triad maintains current position - no action needed
                logger.debug(
                    f"Triad '{triad_id}' HOLDS position on '{section_name}'"
                )

    async def _get_revised_proposal(
        self,
        triad: "Triad",
        section_name: str,
        section: Section
    ) -> Optional[Any]:
        """Get a revised proposal from a triad.

        This method handles getting the updated proposal when a triad
        chooses to REVISE. The triad may have the proposal prepared
        or we may need to call a method to generate it.

        Args:
            triad: The Triad instance
            section_name: Name of the section
            section: The Section object with current proposals

        Returns:
            The revised proposal, or None if unavailable
        """
        # Check if triad has a pending revised proposal
        if hasattr(triad, 'pending_revised_proposal'):
            proposal = getattr(triad, 'pending_revised_proposal', {}).get(section_name)
            if proposal is not None:
                # Clear the pending proposal
                triad.pending_revised_proposal.pop(section_name, None)
                return proposal

        # Check if triad has a get_revised_proposal method
        if hasattr(triad, 'get_revised_proposal') and callable(triad.get_revised_proposal):
            return await triad.get_revised_proposal(section_name)

        # Fallback: return the existing proposal (no actual revision)
        # This shouldn't happen in practice if triads are implemented correctly
        logger.warning(
            f"Triad '{triad.config.id}' chose REVISE but no revised proposal "
            f"available for '{section_name}'"
        )
        return section.proposals.get(triad.config.id)

    async def _escalate(self, section_name: str) -> None:
        """Escalate a stuck negotiation to the arbiter.

        The arbiter makes a final decision on how to resolve the conflict:
        - assign: Give section to one triad
        - split: Divide section into sub-sections
        - merge: Combine proposals and assign to one triad

        Args:
            section_name: Name of the section to escalate
        """
        section = self.spec.sections[section_name]

        logger.info(
            f"Escalating section '{section_name}' to arbiter. "
            f"Claimants: {section.claims}"
        )

        try:
            decision = await self.arbiter.resolve(
                section_name=section_name,
                claimants=list(section.claims),
                proposals=dict(section.proposals),
                triads={tid: self.triads[tid] for tid in section.claims if tid in self.triads},
                spec_state=self.spec
            )

            # Apply the arbiter's decision
            await self._apply_arbiter_decision(section_name, decision)

            # Reset stuck counter
            self.stuck_counters[section_name] = 0

            logger.info(
                f"Arbiter decision for '{section_name}': {decision.type} - "
                f"{decision.rationale[:100]}..."
            )

        except Exception as e:
            logger.error(
                f"Arbiter escalation failed for '{section_name}': {e}. "
                f"Falling back to first claimant."
            )
            # Fallback: assign to first claimant
            if section.claims:
                winner = section.claims[0]
                for tid in list(section.claims):
                    if tid != winner:
                        self.spec.concede(tid, section_name)

    async def _apply_arbiter_decision(
        self,
        section_name: str,
        decision: "ArbiterDecision"
    ) -> None:
        """Apply an arbiter's decision to resolve a contested section.

        Args:
            section_name: Name of the section
            decision: The ArbiterDecision to apply
        """
        section = self.spec.sections[section_name]

        if decision.type == "assign":
            # Give section to the winner, others concede
            winner = decision.winner
            logger.debug(
                f"Arbiter assigns '{section_name}' to '{winner}'"
            )
            for tid in list(section.claims):
                if tid != winner:
                    self.spec.concede(tid, section_name)

        elif decision.type == "split":
            # Create sub-sections and assign to different triads
            logger.debug(
                f"Arbiter splits '{section_name}' into: {decision.division}"
            )

            # Create new sub-sections
            for sub_section_name, owner in decision.division.items():
                # Get proposal for the sub-section if available
                # The arbiter might provide sub-proposals, or we use the
                # owner's original proposal as a base
                sub_proposal = None
                if owner in section.proposals:
                    sub_proposal = section.proposals[owner]

                # Create the new sub-section
                new_section = Section(
                    status=SectionStatus.CLAIMED,
                    owner=owner,
                    claims=[owner],
                    proposals={owner: sub_proposal} if sub_proposal else {},
                    history=[{
                        "round": self.spec.round,
                        "action": "split_from_arbiter",
                        "by": "arbiter",
                        "original_section": section_name,
                    }]
                )
                self.spec.sections[sub_section_name] = new_section

            # Remove the original contested section
            del self.spec.sections[section_name]

        elif decision.type == "merge":
            # Use the merged proposal and assign to specified triad
            assigned_to = decision.assigned_to
            merged_proposal = decision.merged_proposal

            logger.debug(
                f"Arbiter merges proposals for '{section_name}', "
                f"assigns to '{assigned_to}'"
            )

            # Update the proposal to the merged version
            section.proposals[assigned_to] = merged_proposal

            # Have all other claimants concede
            for tid in list(section.claims):
                if tid != assigned_to:
                    self.spec.concede(tid, section_name)

    def get_result(self) -> NegotiationResult:
        """Get the negotiation result summary.

        Returns:
            NegotiationResult with statistics and history
        """
        return self._result

    def get_stuck_sections(self) -> Dict[str, int]:
        """Get sections that are currently stuck and their stuck counts.

        Returns:
            Dict mapping section_name -> rounds stuck
        """
        return dict(self.stuck_counters)
