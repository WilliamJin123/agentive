# Phase 3: Agno Teams - Research

**Researched:** 2026-01-29
**Domain:** Agno Teams API, Multi-Agent Coordination, Async Execution
**Confidence:** HIGH

## Summary

This phase transforms HFS triads (HierarchicalTriad, DialecticTriad, ConsensusTriad) from the current stub implementations into fully functional Agno Teams. Research focused on understanding the Agno Team API from installed source code (v2.4.6), analyzing existing triad structures to map to Agno patterns, and identifying how to implement the decisions from CONTEXT.md.

The Agno Team class provides a comprehensive multi-agent coordination framework with built-in support for async execution (`team.arun()`), conversation history (`add_history_to_context=True`), parallel member dispatch (`delegate_to_all_members=True`), session state management, and member interaction sharing. The existing triad implementations have `TODO: Make actual LLM call` placeholders that need to be replaced with actual Agno Agent coordination.

Key insight: Agno Teams use a "leader model" that coordinates member agents via tool calls (`delegate_task_to_member`). For HFS triads, we need role-scoped history (per CONTEXT.md), which requires using session_state rather than raw `add_history_to_context` which shares ALL history with ALL members.

**Primary recommendation:** Create a base `AgnoTriad` class that wraps Agno Team, with role-specific configuration for each triad type. Use `session_state` to store role-scoped conversation summaries rather than full shared history. The synthesizer (or orchestrator in Hierarchical) produces phase transition summaries stored in structured session_state fields.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agno | 2.4.6 | Team, Agent classes for multi-agent coordination | Already installed, native framework |
| agno.team | 2.4.6 | Team class with arun(), member delegation | Core coordination API |
| agno.agent | 2.4.6 | Agent class with role, instructions, tools | Individual agent configuration |
| pydantic | 2.x | Output schemas, session state models | Validation and serialization |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| agno.db | 2.4.6 | Database abstraction (PostgresDb, MongoDb) | When persisting history to database |
| agno.run.team | 2.4.6 | TeamRunOutput, TeamRunEvent classes | Processing team execution results |
| asyncio | stdlib | Async execution | All team operations (arun()) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Team leader model | Direct agent-to-agent calls | Team provides coordination, history, error handling built-in |
| session_state for history | add_history_to_context | session_state allows role-scoping; add_history_to_context shares everything |
| In-memory state | Database persistence | In-memory simpler for single-run; DB needed for cross-run persistence |

**Installation:**
All dependencies already installed. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── agno/                    # Existing from Phase 1-2
│   ├── __init__.py          # Add AgnoTriad exports
│   ├── providers.py         # From Phase 1
│   ├── models.py            # From Phase 1
│   ├── tools/               # From Phase 2
│   │   ├── toolkit.py       # HFSToolkit
│   │   └── schemas.py       # Tool I/O models
│   └── teams/               # NEW: Team implementations
│       ├── __init__.py      # Export all triad classes
│       ├── base.py          # AgnoTriad base class
│       ├── hierarchical.py  # HierarchicalAgnoTriad
│       ├── dialectic.py     # DialecticAgnoTriad
│       ├── consensus.py     # ConsensusAgnoTriad
│       └── schemas.py       # Phase summary models
```

### Pattern 1: AgnoTriad Base Class
**What:** Abstract base class wrapping Agno Team with HFS-specific configuration
**When to use:** All triad implementations extend this
**Example:**
```python
# Source: Agno team.py Team class pattern
from abc import ABC, abstractmethod
from agno.team import Team
from agno.agent import Agent
from agno.models.base import Model
from typing import Dict, Any, List, Optional
from hfs.core.triad import TriadConfig, TriadOutput, NegotiationResponse
from hfs.agno.tools import HFSToolkit

class AgnoTriad(ABC):
    """Base class for Agno-backed HFS triads.

    Wraps an Agno Team with 3 agent members and provides
    the HFS triad interface (deliberate, negotiate, execute).
    """

    def __init__(
        self,
        config: TriadConfig,
        model: Model,
        spec: "Spec",
    ):
        self.config = config
        self.model = model
        self.spec = spec

        # Create the toolkit with spec access
        self.toolkit = HFSToolkit(spec=spec, triad_id=config.id)

        # Create member agents
        self.agents = self._create_agents()

        # Create the team
        self.team = self._create_team()

        # Phase state for summaries
        self._phase_state: Dict[str, Any] = {}

    @abstractmethod
    def _create_agents(self) -> Dict[str, Agent]:
        """Create the 3 member agents for this triad type."""
        pass

    @abstractmethod
    def _create_team(self) -> Team:
        """Create the Agno Team with role-appropriate configuration."""
        pass

    @abstractmethod
    def _get_phase_summary_prompt(self, phase: str) -> str:
        """Get prompt for producing phase transition summary."""
        pass
```

### Pattern 2: Role-Scoped History via session_state
**What:** Store role-specific conversation summaries in session_state instead of full shared history
**When to use:** Per CONTEXT.md decision - agents only see messages relevant to their role
**Example:**
```python
# Source: Agno team.py session_state pattern + CONTEXT.md decisions
from pydantic import BaseModel
from typing import Optional, Dict, List

class PhaseSummary(BaseModel):
    """Structured summary for phase transitions."""
    phase: str
    decisions: List[str]
    open_questions: List[str]
    artifacts: Dict[str, str]
    produced_by: str  # Agent role that produced this

class TriadSessionState(BaseModel):
    """Session state with role-scoped history."""
    deliberation_summary: Optional[PhaseSummary] = None
    negotiation_summary: Optional[PhaseSummary] = None
    execution_summary: Optional[PhaseSummary] = None

    # Per-agent context (role-scoped)
    orchestrator_context: Optional[str] = None
    worker_a_context: Optional[str] = None
    worker_b_context: Optional[str] = None

# Usage in team creation
team = Team(
    members=[orchestrator, worker_a, worker_b],
    session_state=TriadSessionState().model_dump(),
    add_session_state_to_context=True,  # Include in prompts
    # NOT add_history_to_context - that shares everything
)
```

### Pattern 3: Hierarchical Team with Orchestrator Control
**What:** Team where orchestrator explicitly directs workers via delegate_task_to_member
**When to use:** HierarchicalTriad - clear delegation structure
**Example:**
```python
# Source: Agno team.py delegate_task_to_member function
from agno.team import Team
from agno.agent import Agent

class HierarchicalAgnoTriad(AgnoTriad):
    def _create_agents(self) -> Dict[str, Agent]:
        orchestrator = Agent(
            name=f"{self.config.id}_orchestrator",
            role="Coordinator that decomposes tasks and integrates results",
            model=self.model,
            instructions=self._orchestrator_instructions(),
            tools=[self.toolkit],  # Orchestrator has all HFS tools
        )

        worker_a = Agent(
            name=f"{self.config.id}_worker_a",
            role="Executor for subtask A",
            model=self.model,
            instructions=self._worker_instructions("worker_a"),
            tools=[self.toolkit.generate_code],  # Workers only generate code
        )

        worker_b = Agent(
            name=f"{self.config.id}_worker_b",
            role="Executor for subtask B",
            model=self.model,
            instructions=self._worker_instructions("worker_b"),
            tools=[self.toolkit.generate_code],
        )

        return {"orchestrator": orchestrator, "worker_a": worker_a, "worker_b": worker_b}

    def _create_team(self) -> Team:
        return Team(
            name=f"triad_{self.config.id}",
            members=list(self.agents.values()),
            model=self.model,  # Leader model for coordination
            # Orchestrator decides who to delegate to
            delegate_to_all_members=False,  # Explicit delegation
            respond_directly=False,  # Process member responses
            share_member_interactions=True,  # Orchestrator sees all
            # History via session_state, not raw history
            add_session_state_to_context=True,
        )
```

### Pattern 4: Parallel Worker Dispatch for ConsensusTriad
**What:** Dispatch to all members simultaneously using delegate_to_all_members
**When to use:** ConsensusTriad - all peers contribute equally
**Example:**
```python
# Source: Agno team.py delegate_to_all_members pattern
class ConsensusAgnoTriad(AgnoTriad):
    def _create_team(self) -> Team:
        return Team(
            name=f"triad_{self.config.id}",
            members=list(self.agents.values()),
            model=self.model,
            # Broadcast to all members
            delegate_to_all_members=True,
            # Handle responses as they arrive
            share_member_interactions=True,
            add_session_state_to_context=True,
        )
```

### Pattern 5: Synthesizer Produces Phase Summary (DialecticTriad)
**What:** Synthesizer role explicitly produces structured summary for phase transitions
**When to use:** Per CONTEXT.md - synthesizer produces transition summaries
**Example:**
```python
# Source: CONTEXT.md decisions + Agno output_schema pattern
from pydantic import BaseModel

class DialecticAgnoTriad(AgnoTriad):
    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        # Run thesis-antithesis-synthesis flow
        result = await self.team.arun(
            input=self._build_deliberation_prompt(user_request, spec_state),
            session_state=self._phase_state,
        )

        # Extract summary from synthesizer's output
        summary = self._extract_phase_summary(result, phase="deliberation")
        self._phase_state["deliberation_summary"] = summary.model_dump()

        return self._parse_deliberation_result(result)

    def _get_phase_summary_prompt(self, phase: str) -> str:
        return f"""
After completing the {phase} phase, produce a structured summary:

## Summary Template
- **Decisions Made:** [List key decisions from this phase]
- **Open Questions:** [List unresolved questions for next phase]
- **Artifacts:** [List any outputs/proposals created]

This summary will be passed to the next phase. Be concise but complete.
"""
```

### Pattern 6: Failure Handling - Abort on Error
**What:** Fail fast on agent failure, preserve partial progress
**When to use:** Per CONTEXT.md - abort team run on failure, surface to orchestrator
**Example:**
```python
# Source: CONTEXT.md decisions + Agno RunStatus pattern
from agno.run.team import TeamRunOutput
from agno.run import RunStatus

class AgnoTriad(ABC):
    async def _run_with_error_handling(
        self,
        phase: str,
        prompt: str,
    ) -> TeamRunOutput:
        """Execute team with failure handling per CONTEXT.md."""
        try:
            result = await self.team.arun(
                input=prompt,
                session_state=self._phase_state,
            )

            if result.status == RunStatus.error:
                # Preserve partial progress before raising
                self._save_partial_progress(phase)
                raise TriadExecutionError(
                    triad_id=self.config.id,
                    phase=phase,
                    agent=self._identify_failed_agent(result),
                    error=self._extract_error_message(result),
                )

            return result

        except Exception as e:
            # Save state for retry
            self._save_partial_progress(phase)
            raise TriadExecutionError(
                triad_id=self.config.id,
                phase=phase,
                agent="unknown",
                error=str(e),
            ) from e

    def _save_partial_progress(self, phase: str) -> None:
        """Write progress to .planning state file."""
        state_file = f".planning/{self.config.id}_{phase}_state.json"
        with open(state_file, "w") as f:
            json.dump(self._phase_state, f)
```

### Anti-Patterns to Avoid
- **add_history_to_context=True without scoping:** This shares ALL messages with ALL agents, violating role-scoped history
- **Single agent per triad:** A triad needs 3 distinct agents, not one agent with multiple personas
- **Synchronous team.run():** Always use team.arun() for async execution
- **Ignoring member responses:** respond_directly=True skips leader processing - use False for coordination
- **Hardcoded timeouts:** Use configurable timeout values per Claude's discretion

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-agent coordination | Custom message passing | Agno Team | Built-in delegation, error handling, history |
| Parallel execution | asyncio.gather on raw calls | delegate_to_all_members | Team handles dispatch, collection, errors |
| Session state | Global variables | Team.session_state | Persists across runs, thread-safe |
| Conversation history | Manual message lists | session_state + summaries | Role-scoped per CONTEXT.md |
| Error context | Try/except with string | TeamRunOutput.status | Structured error info |
| Member dispatching | Explicit agent.arun() calls | delegate_task_to_member | Team manages context passing |

**Key insight:** Agno Teams handle most coordination complexity. Focus on configuring the team correctly rather than reimplementing coordination logic.

## Common Pitfalls

### Pitfall 1: Full History Sharing
**What goes wrong:** Using add_history_to_context=True shares all messages with all agents
**Why it happens:** Seems like the obvious way to preserve history
**How to avoid:** Use session_state with role-scoped summaries instead
**Warning signs:** Worker agents responding to orchestrator-only context, confused agent behavior

### Pitfall 2: Missing Model on Team Leader
**What goes wrong:** Team created without model parameter, no coordination possible
**Why it happens:** Assuming members' models are sufficient
**How to avoid:** Always set `model` on the Team itself for leader coordination
**Warning signs:** "No model configured" errors, team not delegating

### Pitfall 3: respond_directly With delegate_to_all_members
**What goes wrong:** These flags conflict - respond_directly disables leader processing
**Why it happens:** Wanting both broadcast AND leader control
**How to avoid:** For HFS, use delegate_to_all_members=True only for ConsensusTriad, never with respond_directly
**Warning signs:** Agno warning message, member responses returned raw without synthesis

### Pitfall 4: Not Handling Partial Failure
**What goes wrong:** One agent fails, no state preserved, entire phase must restart
**Why it happens:** Not implementing error handling per CONTEXT.md
**How to avoid:** Save _phase_state before raising, include error context
**Warning signs:** Lost work on retry, repeating successful subtasks

### Pitfall 5: Blocking in Async Context
**What goes wrong:** Using team.run() instead of team.arun() in async code
**Why it happens:** Habit from sync code
**How to avoid:** Always use arun() - AGNO-03 requirement
**Warning signs:** Event loop warnings, blocked coroutines, slow execution

### Pitfall 6: Tool Access Not Role-Scoped
**What goes wrong:** All agents have all tools, violating role boundaries
**Why it happens:** Passing full toolkit to all agents
**How to avoid:** Pass only role-appropriate tools (e.g., workers only get generate_code)
**Warning signs:** Workers making claims, orchestrator generating code directly

## Code Examples

### Complete HierarchicalAgnoTriad Implementation
```python
# Source: Agno team.py patterns + existing hfs/presets/hierarchical.py
from agno.team import Team
from agno.agent import Agent
from agno.models.base import Model
from hfs.core.triad import TriadConfig, TriadOutput, NegotiationResponse
from hfs.agno.tools import HFSToolkit
from typing import Dict, Any, List

class HierarchicalAgnoTriad:
    """Agno Team implementation of Hierarchical Triad.

    Structure: orchestrator + worker_a + worker_b
    Flow: orchestrator decomposes -> workers execute -> orchestrator integrates
    """

    def __init__(self, config: TriadConfig, model: Model, spec: "Spec"):
        self.config = config
        self.model = model
        self.toolkit = HFSToolkit(spec=spec, triad_id=config.id)

        # Create agents with role-specific tools
        self.orchestrator = Agent(
            name=f"{config.id}_orchestrator",
            role="Task coordinator and integrator",
            model=model,
            instructions=self._orchestrator_prompt(),
            tools=[self.toolkit],  # Full toolkit access
        )

        self.worker_a = Agent(
            name=f"{config.id}_worker_a",
            role="Subtask executor A",
            model=model,
            instructions=self._worker_prompt("A"),
            tools=[self.toolkit.generate_code],  # Code gen only
        )

        self.worker_b = Agent(
            name=f"{config.id}_worker_b",
            role="Subtask executor B",
            model=model,
            instructions=self._worker_prompt("B"),
            tools=[self.toolkit.generate_code],
        )

        # Create team with orchestrator as leader
        self.team = Team(
            name=f"triad_{config.id}",
            model=model,  # Leader model for coordination
            members=[self.orchestrator, self.worker_a, self.worker_b],
            delegate_to_all_members=False,  # Orchestrator directs
            share_member_interactions=True,  # Orchestrator sees worker results
            add_session_state_to_context=True,
            session_state={
                "phase": None,
                "deliberation_summary": None,
                "negotiation_summary": None,
            },
        )

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Run hierarchical deliberation via team.arun()."""
        prompt = f"""
PHASE: DELIBERATION

User Request: {user_request}
Spec State: {spec_state}
Your Scope: {self.config.scope_primary}

Orchestrator: Analyze and decompose this request into subtasks.
Then delegate to workers and integrate their outputs.

Use the HFS tools to:
1. get_current_claims() - See what's available
2. register_claim() - Claim sections in your scope
"""

        result = await self.team.arun(
            input=prompt,
            session_state={"phase": "deliberation"},
        )

        # Parse result into TriadOutput
        return self._parse_deliberation_result(result)

    async def negotiate(self, section: str, other_proposals: Dict[str, Any]) -> NegotiationResponse:
        """Orchestrator leads negotiation response."""
        prompt = f"""
PHASE: NEGOTIATION

Contested Section: {section}
Other Proposals: {other_proposals}
Your Position: Use get_negotiation_state("{section}") to see details.

Decide: concede, revise, or hold?
Use negotiate_response() tool to submit your decision.
"""

        result = await self.team.arun(
            input=prompt,
            session_state={"phase": "negotiation"},
        )

        return self._parse_negotiation_result(result)

    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        """Parallel worker execution for code generation."""
        prompt = f"""
PHASE: EXECUTION

Frozen Spec: {frozen_spec}
Generate code for sections owned by {self.config.id}.

Orchestrator: Assign sections to workers.
Workers: Use generate_code() tool for your assigned sections.
"""

        result = await self.team.arun(
            input=prompt,
            session_state={"phase": "execution"},
        )

        return self._parse_execution_result(result)
```

### DialecticAgnoTriad with Synthesizer Summary
```python
# Source: Agno patterns + CONTEXT.md synthesizer decision
class DialecticAgnoTriad:
    """Dialectic triad: proposer + critic + synthesizer."""

    def __init__(self, config: TriadConfig, model: Model, spec: "Spec"):
        self.config = config
        self.toolkit = HFSToolkit(spec=spec, triad_id=config.id)

        self.proposer = Agent(
            name=f"{config.id}_proposer",
            role="Generate creative proposals (thesis)",
            model=model,
            instructions=self._proposer_prompt(),
            tools=[self.toolkit.register_claim],
        )

        self.critic = Agent(
            name=f"{config.id}_critic",
            role="Challenge proposals (antithesis)",
            model=model,
            instructions=self._critic_prompt(),
            tools=[self.toolkit.get_negotiation_state],  # Read-only state access
        )

        self.synthesizer = Agent(
            name=f"{config.id}_synthesizer",
            role="Resolve tensions into coherent output (synthesis)",
            model=model,
            instructions=self._synthesizer_prompt(),
            tools=[self.toolkit],  # Full access for final decisions
        )

        # Fixed role assignment (per CONTEXT.md - roles don't rotate)
        self.team = Team(
            name=f"triad_{config.id}",
            model=model,
            members=[self.proposer, self.critic, self.synthesizer],
            delegate_to_all_members=False,  # Explicit flow control
            add_session_state_to_context=True,
            session_state={"phase_summaries": {}},
        )

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Thesis -> Antithesis -> Synthesis deliberation."""

        # Phase 1-3 via team orchestration
        result = await self.team.arun(
            input=self._deliberation_prompt(user_request, spec_state),
        )

        # Synthesizer produces phase summary (per CONTEXT.md)
        summary = await self._get_synthesizer_summary(result, "deliberation")

        # Store for next phase
        self.team.session_state["phase_summaries"]["deliberation"] = summary.model_dump()

        return self._parse_result(result)
```

### ConsensusAgnoTriad with Parallel Dispatch
```python
# Source: Agno delegate_to_all_members pattern
class ConsensusAgnoTriad:
    """Consensus triad: 3 equal peers with parallel dispatch."""

    def __init__(self, config: TriadConfig, model: Model, spec: "Spec"):
        self.config = config
        self.toolkit = HFSToolkit(spec=spec, triad_id=config.id)

        # All peers have equal tools and authority
        self.peers = [
            Agent(
                name=f"{config.id}_peer_{i+1}",
                role=f"Equal peer with {perspective} focus",
                model=model,
                instructions=self._peer_prompt(perspective),
                tools=[self.toolkit],  # All peers have full access
            )
            for i, perspective in enumerate([
                "user_experience",
                "technical_correctness",
                "maintainability",
            ])
        ]

        # Broadcast to all members for consensus
        self.team = Team(
            name=f"triad_{config.id}",
            model=model,
            members=self.peers,
            delegate_to_all_members=True,  # Parallel dispatch
            share_member_interactions=True,  # Peers see each other
            add_session_state_to_context=True,
        )

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        """Parallel proposal collection followed by voting."""

        # All peers propose simultaneously
        result = await self.team.arun(
            input=self._deliberation_prompt(user_request, spec_state),
        )

        # Process as results arrive (per CONTEXT.md streaming approach)
        return self._merge_peer_proposals(result)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MockLLMClient stubs | Agno Team.arun() | Phase 3 | Real multi-agent execution |
| Simple Agent dataclass | Agno Agent with tools | Agno 2.x | Full tool support, memory |
| Manual message passing | Team coordination | Agno 2.x | Built-in delegation, history |
| Full history sharing | Role-scoped session_state | CONTEXT.md | Privacy, relevance |
| Synchronous execution | Async team.arun() | AGNO-03 | Performance, non-blocking |

**Deprecated/outdated:**
- Manual LLM client calls: Use Agno Agent/Team
- Simple Agent dataclass in presets: Replace with Agno Agent
- team.run() sync method: Always use team.arun() for async

## Open Questions

1. **Timeout Values for Parallel Dispatch**
   - What we know: CONTEXT.md marks as Claude's discretion
   - Recommendation: Start with 30s per-agent timeout, 120s overall team timeout
   - Configuration via TriadConfig.budget_time_ms

2. **State File Naming**
   - What we know: CONTEXT.md says "specific markdown state files"
   - Recommendation: `.planning/{triad_id}_{phase}_state.json` pattern
   - One file per triad per phase for isolation

3. **Summary Template Schema**
   - What we know: CONTEXT.md says "predefined sections (decisions, open questions, artifacts)"
   - Recommendation: Use PhaseSummary Pydantic model with these exact fields
   - Synthesizer receives template in instructions

4. **Database for History Persistence**
   - What we know: Agno supports PostgresDb, MongoDb, etc.
   - What's unclear: Should we use database or in-memory for v1?
   - Recommendation: In-memory session_state for v1, database for future phases

## Sources

### Primary (HIGH confidence)
- Agno source code v2.4.6 (installed): `.venv/Lib/site-packages/agno/team/team.py`
  - Team class: lines 199-8700+ (full implementation)
  - arun() method: lines 3014-3163
  - delegate_to_all_members: lines 5697-5703
  - session_state: lines 243-249, 940-954
- Agno source code: `.venv/Lib/site-packages/agno/agent/agent.py`
  - Agent class structure and parameters
- CONTEXT.md decisions: `.planning/phases/03-agno-teams/03-CONTEXT.md`
- Existing HFS presets: `hfs/presets/hierarchical.py`, `dialectic.py`, `consensus.py`
- HFSToolkit from Phase 2: `hfs/agno/tools/toolkit.py`

### Secondary (MEDIUM confidence)
- [Agno Documentation](https://docs.agno.com) - Teams overview
- [Agno GitHub](https://github.com/agno-agi/agno) - Cookbook structure
- docs/AGNO.md - Project integration guide

### Tertiary (LOW confidence)
- Web search results for Agno patterns (verified against source code)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - examined installed Agno source code directly
- Architecture: HIGH - patterns derived from Team class implementation
- Pitfalls: HIGH - based on Agno source code warnings and CONTEXT.md constraints
- Code examples: HIGH - validated against actual Agno implementation

**Research date:** 2026-01-29
**Valid until:** 60 days (Agno 2.4.6 stable, already installed)
