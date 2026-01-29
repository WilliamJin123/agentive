"""Arbiter for resolving negotiation deadlocks in HFS.

When negotiation exceeds the stuck threshold (configurable rounds without
resolution), an arbiter LLM is invoked to break the deadlock. The arbiter
considers user intent, global coherence, and minimizes future conflicts.

Decision types:
- assign: Give section to one triad
- split: Divide section into sub-sections with different owners
- merge: Combine proposals and assign to one triad
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .triad import Triad
    from .spec import Spec


# Decision type literal for type hints
DecisionType = Literal["assign", "split", "merge"]


@dataclass
class ArbiterDecision:
    """Decision output from the arbiter.

    Attributes:
        type: The type of decision - "assign", "split", or "merge"
        winner: For "assign" - the triad_id that wins the section
        division: For "split" - mapping of sub_section names to triad_ids
        merged_proposal: For "merge" - the combined proposal content
        assigned_to: For "merge" - the triad_id responsible for merged content
        rationale: Explanation of why this decision was made
    """
    type: DecisionType
    winner: Optional[str] = None
    division: Optional[Dict[str, str]] = None
    merged_proposal: Optional[Any] = None
    assigned_to: Optional[str] = None
    rationale: str = ""

    def __post_init__(self) -> None:
        """Validate that the decision has the required fields for its type."""
        if self.type == "assign" and self.winner is None:
            raise ValueError("'assign' decision requires 'winner' field")
        if self.type == "split" and not self.division:
            raise ValueError("'split' decision requires 'division' field")
        if self.type == "merge" and (self.merged_proposal is None or self.assigned_to is None):
            raise ValueError("'merge' decision requires 'merged_proposal' and 'assigned_to' fields")


@dataclass
class ArbiterConfig:
    """Configuration for the arbiter.

    Attributes:
        model: The LLM model to use for arbitration
        max_tokens: Maximum tokens for arbiter responses
        temperature: LLM temperature setting (lower = more deterministic)
    """
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2000
    temperature: float = 0.3


# System prompt template for the arbiter
ARBITER_SYSTEM_PROMPT = """You are an arbiter for the Hexagonal Frontend System. Your role is to resolve
negotiation deadlocks between triads.

## Context
- User Request: {user_request}
- Contested Section: {section_name}
- Current Temperature: {temperature}
- Round: {round}

## Competing Proposals

{proposals_section}

## Negotiation History
{history}

## Current Spec State
{spec_summary}

## Your Task
Decide how to resolve this conflict. Consider:
1. Which proposal better serves the user's original intent?
2. Which approach leads to better global coherence?
3. Can the proposals be merged or the section split?
4. What minimizes future conflicts?

## Response Format
Respond with a JSON object in the following format:

For ASSIGN (give section to one winner):
```json
{{
  "type": "assign",
  "winner": "<triad_id>",
  "rationale": "<your detailed reasoning>"
}}
```

For SPLIT (divide section into sub-sections):
```json
{{
  "type": "split",
  "division": {{
    "<sub_section_name>": "<triad_id>",
    "<sub_section_name>": "<triad_id>"
  }},
  "rationale": "<your detailed reasoning>"
}}
```

For MERGE (combine proposals and assign):
```json
{{
  "type": "merge",
  "merged_proposal": <the combined proposal object>,
  "assigned_to": "<triad_id>",
  "rationale": "<your detailed reasoning>"
}}
```

Respond ONLY with the JSON object, no additional text."""


class Arbiter:
    """Arbiter that resolves stuck negotiations between triads.

    The arbiter is an external LLM that reviews competing proposals and
    makes a final decision when triads cannot reach agreement through
    normal negotiation.

    Attributes:
        llm: The LLM client for making API calls
        config: ArbiterConfig with model settings
        user_request: The original user request (set when resolve is called)
    """

    def __init__(self, llm_client: Any, config: Optional[ArbiterConfig] = None) -> None:
        """Initialize the arbiter.

        Args:
            llm_client: Client for making LLM calls (e.g., Anthropic, OpenAI).
                       Must have a method for sending messages and receiving responses.
            config: Optional ArbiterConfig. If None, uses defaults.
        """
        self.llm = llm_client
        self.config = config if config is not None else ArbiterConfig()
        self.user_request: str = ""

    async def resolve(
        self,
        section_name: str,
        claimants: List[str],
        proposals: Dict[str, Any],
        triads: Dict[str, "Triad"],
        spec_state: "Spec"
    ) -> ArbiterDecision:
        """Resolve a stuck negotiation by making a final decision.

        This is called when a section has been contested for too many rounds
        without resolution. The arbiter reviews all proposals and decides
        how to resolve the conflict.

        Args:
            section_name: Name of the contested section
            claimants: List of triad IDs claiming this section
            proposals: Dict mapping triad_id to their proposal for this section
            triads: Dict mapping triad_id to Triad instances (for accessing objectives)
            spec_state: Current state of the full spec

        Returns:
            ArbiterDecision with the resolution

        Raises:
            ValueError: If the LLM response cannot be parsed into a valid decision
        """
        # Build the prompt
        prompt = self._build_prompt(
            section_name=section_name,
            claimants=claimants,
            proposals=proposals,
            triads=triads,
            spec_state=spec_state
        )

        # Call the LLM
        response = await self._call_llm(prompt)

        # Parse and return the decision
        return self._parse_response(response, claimants)

    def _build_prompt(
        self,
        section_name: str,
        claimants: List[str],
        proposals: Dict[str, Any],
        triads: Dict[str, "Triad"],
        spec_state: "Spec"
    ) -> str:
        """Build the arbiter prompt from the template.

        Args:
            section_name: Name of the contested section
            claimants: List of triad IDs claiming this section
            proposals: Dict mapping triad_id to their proposal
            triads: Dict mapping triad_id to Triad instances
            spec_state: Current state of the spec

        Returns:
            Formatted prompt string
        """
        # Build the proposals section
        proposals_parts = []
        for triad_id in claimants:
            triad = triads.get(triad_id)
            objectives = triad.config.objectives if triad else []
            proposal = proposals.get(triad_id, {})

            proposal_str = json.dumps(proposal, indent=2) if proposal else "No proposal submitted"

            proposals_parts.append(
                f"### Triad: {triad_id}\n"
                f"Objectives: {', '.join(objectives)}\n"
                f"Proposal:\n{proposal_str}"
            )

        proposals_section = "\n\n".join(proposals_parts)

        # Build history summary from section history
        section = spec_state.sections.get(section_name)
        history_entries = []
        if section:
            for entry in section.history[-10:]:  # Last 10 entries
                action = entry.get("action", "unknown")
                by = entry.get("by", "unknown")
                round_num = entry.get("round", "?")
                history_entries.append(f"Round {round_num}: {by} -> {action}")

        history = "\n".join(history_entries) if history_entries else "No history available"

        # Build spec summary
        spec_summary_parts = []
        contested = spec_state.get_contested_sections()
        claimed = spec_state.get_claimed_sections()
        frozen = spec_state.get_frozen_sections()

        spec_summary_parts.append(f"Temperature: {spec_state.temperature}")
        spec_summary_parts.append(f"Round: {spec_state.round}")
        spec_summary_parts.append(f"Status: {spec_state.status}")
        spec_summary_parts.append(f"Contested sections: {', '.join(contested) or 'None'}")
        spec_summary_parts.append(f"Claimed sections: {', '.join(claimed) or 'None'}")
        spec_summary_parts.append(f"Frozen sections: {', '.join(frozen) or 'None'}")

        spec_summary = "\n".join(spec_summary_parts)

        # Format the prompt
        return ARBITER_SYSTEM_PROMPT.format(
            user_request=self.user_request or "Not specified",
            section_name=section_name,
            temperature=spec_state.temperature,
            round=spec_state.round,
            proposals_section=proposals_section,
            history=history,
            spec_summary=spec_summary
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the arbiter prompt.

        Args:
            prompt: The formatted prompt to send

        Returns:
            The LLM's response text
        """
        # This implementation assumes the llm_client has a messages.create method
        # similar to the Anthropic SDK. Adjust based on actual client interface.
        try:
            # Try Anthropic-style client
            if hasattr(self.llm, 'messages') and hasattr(self.llm.messages, 'create'):
                response = await self.llm.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                # Extract text from response
                if hasattr(response, 'content') and response.content:
                    return response.content[0].text
                return str(response)

            # Try OpenAI-style client
            elif hasattr(self.llm, 'chat') and hasattr(self.llm.chat, 'completions'):
                response = await self.llm.chat.completions.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content

            # Try generic async call method
            elif hasattr(self.llm, 'call') and callable(self.llm.call):
                return await self.llm.call(
                    prompt=prompt,
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )

            # Try generic generate method
            elif hasattr(self.llm, 'generate') and callable(self.llm.generate):
                return await self.llm.generate(prompt)

            else:
                raise ValueError(
                    "LLM client does not have a recognized interface. "
                    "Expected 'messages.create', 'chat.completions.create', 'call', or 'generate' method."
                )

        except Exception as e:
            raise ValueError(f"Failed to call LLM: {e}") from e

    def _parse_response(self, response: str, valid_claimants: List[str]) -> ArbiterDecision:
        """Parse the LLM response into an ArbiterDecision.

        Args:
            response: The raw LLM response text
            valid_claimants: List of valid triad IDs for validation

        Returns:
            Parsed ArbiterDecision

        Raises:
            ValueError: If the response cannot be parsed or is invalid
        """
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError(f"No JSON object found in arbiter response: {response[:200]}")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in arbiter response: {e}") from e

        # Validate required fields
        if "type" not in data:
            raise ValueError("Arbiter response missing 'type' field")

        decision_type = data["type"]
        if decision_type not in ("assign", "split", "merge"):
            raise ValueError(f"Invalid decision type: {decision_type}")

        rationale = data.get("rationale", "No rationale provided")

        # Parse based on decision type
        if decision_type == "assign":
            winner = data.get("winner")
            if not winner:
                raise ValueError("'assign' decision missing 'winner' field")
            if winner not in valid_claimants:
                raise ValueError(f"Invalid winner '{winner}'. Must be one of: {valid_claimants}")

            return ArbiterDecision(
                type="assign",
                winner=winner,
                rationale=rationale
            )

        elif decision_type == "split":
            division = data.get("division")
            if not division or not isinstance(division, dict):
                raise ValueError("'split' decision missing or invalid 'division' field")

            # Validate all assigned triads are valid
            for sub_section, triad_id in division.items():
                if triad_id not in valid_claimants:
                    raise ValueError(
                        f"Invalid triad '{triad_id}' in division for '{sub_section}'. "
                        f"Must be one of: {valid_claimants}"
                    )

            return ArbiterDecision(
                type="split",
                division=division,
                rationale=rationale
            )

        elif decision_type == "merge":
            merged_proposal = data.get("merged_proposal")
            assigned_to = data.get("assigned_to")

            if merged_proposal is None:
                raise ValueError("'merge' decision missing 'merged_proposal' field")
            if not assigned_to:
                raise ValueError("'merge' decision missing 'assigned_to' field")
            if assigned_to not in valid_claimants:
                raise ValueError(
                    f"Invalid assigned_to '{assigned_to}'. Must be one of: {valid_claimants}"
                )

            return ArbiterDecision(
                type="merge",
                merged_proposal=merged_proposal,
                assigned_to=assigned_to,
                rationale=rationale
            )

        # Should never reach here due to earlier validation
        raise ValueError(f"Unhandled decision type: {decision_type}")

    def set_user_request(self, user_request: str) -> None:
        """Set the user request for context in arbitration.

        Args:
            user_request: The original user request describing what to build
        """
        self.user_request = user_request
