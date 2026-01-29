"""Triad base classes and configuration for HFS.

This module defines the fundamental building blocks of the Hexagonal Frontend System:
- TriadPreset: The three preset types for triad internal structure
- TriadConfig: Configuration dataclass for triad initialization
- TriadOutput: Output structure from triad deliberation
- Triad: Abstract base class that all preset implementations must inherit
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Literal
from enum import Enum


class TriadPreset(Enum):
    """Preset types defining the internal structure of a triad.

    HIERARCHICAL: Clear delegation with orchestrator and two workers.
                  Best for execution-heavy work like layout, state, performance.

    DIALECTIC: Thesis-antithesis-synthesis with proposer, critic, synthesizer.
               Best for creative/ambiguous work like visual, motion design.

    CONSENSUS: Three equal peers that vote and argue positions.
               Best for cross-cutting concerns like accessibility, standards.
    """
    HIERARCHICAL = "hierarchical"
    DIALECTIC = "dialectic"
    CONSENSUS = "consensus"


@dataclass
class TriadConfig:
    """Configuration for initializing a triad.

    Attributes:
        id: Unique identifier for this triad.
        preset: Which internal structure preset to use.
        scope_primary: Sections this triad owns by default (guaranteed territory).
        scope_reach: Sections this triad can claim (aspirational territory).
        budget_tokens: Maximum tokens this triad can consume.
        budget_tool_calls: Maximum tool invocations allowed.
        budget_time_ms: Maximum execution time in milliseconds.
        objectives: What this triad optimizes for (e.g., aesthetic_quality, performance).
        system_context: Optional additional context for the triad's system prompts.
    """
    id: str
    preset: TriadPreset
    scope_primary: List[str]
    scope_reach: List[str]
    budget_tokens: int
    budget_tool_calls: int
    budget_time_ms: int
    objectives: List[str]
    system_context: Optional[str] = None


@dataclass
class TriadOutput:
    """Output from triad deliberation.

    Attributes:
        position: What this triad thinks should happen (position statement).
        claims: List of section names being claimed by this triad.
        proposals: Content proposals for each claimed section.
    """
    position: str
    claims: List[str]
    proposals: Dict[str, Any]


# Type alias for negotiation response
NegotiationResponse = Literal["concede", "revise", "hold"]


class Triad(ABC):
    """Abstract base class for all triads.

    A triad is the atomic working unit of HFS, consisting of three sub-agents
    that collaborate internally before interacting with other triads externally.

    Each preset (hierarchical, dialectic, consensus) provides a different
    internal structure and deliberation flow, but all triads expose the same
    external interface defined by this base class.

    Attributes:
        config: The TriadConfig used to initialize this triad.
        llm: The LLM client used for agent interactions.
        agents: Dictionary of initialized internal agents.
    """

    def __init__(self, config: TriadConfig, llm_client: Any) -> None:
        """Initialize the triad with configuration and LLM client.

        Args:
            config: Configuration specifying preset, scope, budget, and objectives.
            llm_client: Client for making LLM calls (e.g., Anthropic, OpenAI).
        """
        self.config = config
        self.llm = llm_client
        self.agents = self._initialize_agents()

    @abstractmethod
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize the three internal agents based on preset.

        Returns:
            Dictionary mapping agent role names to agent instances.
            The structure depends on the preset:
            - hierarchical: {"orchestrator": ..., "worker_a": ..., "worker_b": ...}
            - dialectic: {"proposer": ..., "critic": ..., "synthesizer": ...}
            - consensus: {"peer_1": ..., "peer_2": ..., "peer_3": ...}
        """
        pass

    @abstractmethod
    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Run internal deliberation and produce unified output.

        This is where the three internal agents collaborate according to their
        preset's flow to analyze the user request and current spec state,
        then produce a unified position with claims and proposals.

        Args:
            user_request: The original user request describing what to build.
            spec_state: Current state of the shared spec document.

        Returns:
            TriadOutput containing the triad's position, claims, and proposals.
        """
        pass

    @abstractmethod
    async def negotiate(
        self,
        section: str,
        other_proposals: Dict[str, Any]
    ) -> NegotiationResponse:
        """Respond to a negotiation round for a contested section.

        Called when this triad has a competing claim on a section. The triad
        reviews other proposals and decides whether to:
        - "concede": Withdraw claim from this section
        - "revise": Update proposal based on other proposals
        - "hold": Maintain current position

        Args:
            section: Name of the contested section.
            other_proposals: Dict mapping other triad IDs to their proposals.

        Returns:
            One of "concede", "revise", or "hold".
        """
        pass

    @abstractmethod
    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate code for owned sections.

        Called after the spec is frozen and all section ownership is finalized.
        The triad generates actual code/content for the sections it owns.

        Args:
            frozen_spec: The frozen spec with finalized section assignments.

        Returns:
            Dictionary mapping section names to generated code/content.
        """
        pass
