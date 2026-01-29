# Agno Integration Guide for HFS

## Overview

This document outlines how to integrate [Agno](https://github.com/agno-agi/agno) as the execution backend for the Hierarchical Fractal System (HFS). Agno is a Python framework for building multi-agent systems with memory, knowledge bases, and tool integrations.

**Why Agno?**
- High-performance multi-agent runtime
- Built-in session management and memory
- 100+ tool integrations and MCP support
- Model-agnostic (OpenAI, Anthropic, Google, local models)
- Production-ready with FastAPI runtime

## Core Agno Concepts

### 1. Agent Creation

```python
from agno.agent import Agent
from agno.models.anthropic import Claude

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    instructions="You are a specialized worker agent...",
    tools=[...],
    add_history_to_context=True,
    markdown=True
)

# Run the agent
response = agent.run("Complete this task...")
```

### 2. Teams (Multi-Agent Coordination)

```python
from agno.team import Team

team = Team(
    name="DialecticTriad",
    model=Claude(id="claude-sonnet-4-5"),
    members=[proposer, critic, synthesizer],
    add_history_to_context=True
)

result = team.run("Design a component...")
```

### 3. Tools

```python
from agno.tools import tool

@tool
def claim_section(section_id: str, proposal: str) -> dict:
    """Claim a section of the spec with a proposal."""
    return {"section": section_id, "proposal": proposal, "status": "claimed"}
```

### 4. Memory & Storage

```python
from agno.db.sqlite import SqliteDb

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="hfs_sessions.db"),
    learning=True  # Agent improves over time
)
```

---

## HFS Integration Architecture

### Current HFS Structure

```
HFSOrchestrator
├── Phase: SPAWN      → Create triads
├── Phase: DELIBERATE → Each triad analyzes request
├── Phase: CLAIMS     → Register section claims
├── Phase: NEGOTIATE  → Resolve contested sections
├── Phase: FREEZE     → Lock spec
├── Phase: EXECUTE    → Generate code
└── Phase: INTEGRATE  → Merge artifacts
```

### Proposed Agno Integration

```
hfs/
├── agno/                          # New: Agno integration layer
│   ├── __init__.py
│   ├── agents.py                  # Agno agent wrappers
│   ├── tools.py                   # HFS-specific tools
│   ├── teams.py                   # Triad-to-Team mapping
│   └── client.py                  # LLM client adapter
```

---

## Integration Strategy

### Option A: Agent-per-Role (Recommended)

Each role within a triad becomes an Agno agent. The triad becomes an Agno team.

```python
# hfs/agno/teams.py

from agno.agent import Agent
from agno.team import Team
from agno.models.anthropic import Claude

class AgnoTriadFactory:
    """Create Agno teams from HFS triad configs."""

    def create_hierarchical_team(self, config: TriadConfig) -> Team:
        orchestrator = Agent(
            name="orchestrator",
            model=Claude(id="claude-sonnet-4-5"),
            instructions=self._load_prompt("hierarchical/orchestrator.md"),
            tools=[self.claim_tool, self.delegate_tool, self.merge_tool]
        )

        worker_a = Agent(
            name="worker_a",
            model=Claude(id="claude-sonnet-4-5"),
            instructions=self._load_prompt("hierarchical/worker.md"),
            tools=[self.execute_tool, self.report_tool]
        )

        worker_b = Agent(
            name="worker_b",
            model=Claude(id="claude-sonnet-4-5"),
            instructions=self._load_prompt("hierarchical/worker.md"),
            tools=[self.execute_tool, self.report_tool]
        )

        return Team(
            name=config.id,
            members=[orchestrator, worker_a, worker_b],
            add_history_to_context=True
        )
```


## HFS-Specific Tools

Define tools that agents use during HFS phases:

```python
# hfs/agno/tools.py

from agno.tools import tool
from typing import Dict, List, Any

@tool
def register_claim(
    spec: dict,
    section_id: str,
    proposal: str,
    confidence: float
) -> dict:
    """
    Register a claim on a spec section.

    Args:
        spec: Current spec state
        section_id: Section to claim
        proposal: Content proposal for the section
        confidence: Confidence level (0.0-1.0)

    Returns:
        Updated claim status
    """
    return {
        "section": section_id,
        "status": "claimed",
        "proposal": proposal,
        "confidence": confidence
    }

@tool
def negotiate_response(
    action: str,  # "CONCEDE" | "REVISE" | "HOLD"
    section_id: str,
    revised_proposal: str = None,
    rationale: str = None
) -> dict:
    """
    Respond during negotiation round.

    Args:
        action: CONCEDE (withdraw), REVISE (update proposal), or HOLD (maintain)
        section_id: Section being negotiated
        revised_proposal: New proposal if action is REVISE
        rationale: Reasoning for the action

    Returns:
        Negotiation response
    """
    return {
        "action": action,
        "section": section_id,
        "proposal": revised_proposal,
        "rationale": rationale
    }

@tool
def generate_code(
    section_id: str,
    language: str,
    code: str,
    exports: List[str] = None,
    imports: List[str] = None
) -> dict:
    """
    Generate code artifact for a frozen section.

    Args:
        section_id: Section this code belongs to
        language: Programming language (tsx, css, etc.)
        code: The generated code
        exports: Symbols exported by this code
        imports: Symbols imported from other sections

    Returns:
        Code artifact
    """
    return {
        "section": section_id,
        "language": language,
        "code": code,
        "exports": exports or [],
        "imports": imports or []
    }
```

---

## Triad Implementations with Agno

### Hierarchical Triad

```python
# hfs/agno/presets/hierarchical.py

from agno.agent import Agent
from agno.team import Team
from hfs.agno.tools import register_claim, negotiate_response, generate_code

class HierarchicalAgnoTriad:
    """Hierarchical triad: orchestrator + 2 workers."""

    def __init__(self, config, model):
        self.config = config
        self.model = model
        self.team = self._build_team()

    def _build_team(self) -> Team:
        orchestrator = Agent(
            name="orchestrator",
            role="Coordinator that decomposes tasks and integrates results",
            model=self.model,
            instructions=f"""
You are the orchestrator for the {self.config.id} triad.
Your scope: {self.config.scope}
Your objectives: {self.config.objectives}

During DELIBERATION:
- Analyze the user request
- Identify which sections from your scope are relevant
- Decompose work into subtasks for workers

During NEGOTIATION:
- Defend claims on your primary scope
- Consider conceding reach scope if others have stronger proposals

During EXECUTION:
- Delegate subtasks to workers
- Integrate their outputs into coherent artifacts
""",
            tools=[register_claim, negotiate_response]
        )

        worker_a = Agent(
            name="worker_a",
            role="Executor for subtask A",
            model=self.model,
            instructions="Execute assigned subtasks and report results.",
            tools=[generate_code]
        )

        worker_b = Agent(
            name="worker_b",
            role="Executor for subtask B",
            model=self.model,
            instructions="Execute assigned subtasks and report results.",
            tools=[generate_code]
        )

        return Team(
            name=f"triad_{self.config.id}",
            members=[orchestrator, worker_a, worker_b],
            add_history_to_context=True
        )

    async def deliberate(self, user_request: str, spec_state: dict) -> dict:
        """Analyze request and generate claims."""
        prompt = f"""
PHASE: DELIBERATION

User Request: {user_request}
Current Spec State: {spec_state}

Analyze this request and:
1. Identify relevant sections from your scope
2. Generate proposals for each section you want to claim
3. Return your claims with confidence levels
"""
        result = await self.team.arun(prompt)
        return self._parse_deliberation(result)

    async def negotiate(self, section: str, other_proposals: dict) -> dict:
        """Respond to contested section."""
        prompt = f"""
PHASE: NEGOTIATION

Contested Section: {section}
Other Proposals: {other_proposals}

Decide your response:
- CONCEDE: If others have better proposals
- REVISE: If you can improve your proposal
- HOLD: If your proposal is strongest
"""
        result = await self.team.arun(prompt)
        return self._parse_negotiation(result)

    async def execute(self, frozen_spec: dict) -> dict:
        """Generate code for owned sections."""
        owned = [s for s, v in frozen_spec["sections"].items()
                 if v.get("owner") == self.config.id]

        prompt = f"""
PHASE: EXECUTION

Your Owned Sections: {owned}
Frozen Spec: {frozen_spec}

Generate code for each owned section.
Ensure exports/imports align with other sections.
"""
        result = await self.team.arun(prompt)
        return self._parse_execution(result)
```

### Dialectic Triad

```python
# hfs/agno/presets/dialectic.py

class DialecticAgnoTriad:
    """Dialectic triad: proposer + critic + synthesizer."""

    def _build_team(self) -> Team:
        proposer = Agent(
            name="proposer",
            role="Generate creative proposals (thesis)",
            model=self.model,
            instructions="""
You are the proposer (thesis) in a dialectic triad.
Generate bold, creative proposals without self-censoring.
Push boundaries and explore unconventional approaches.
""",
            tools=[register_claim, generate_code]
        )

        critic = Agent(
            name="critic",
            role="Challenge and stress-test proposals (antithesis)",
            model=self.model,
            instructions="""
You are the critic (antithesis) in a dialectic triad.
Challenge every proposal. Find weaknesses, edge cases, and flaws.
Your job is NOT to reject, but to strengthen through critique.
""",
            tools=[negotiate_response]
        )

        synthesizer = Agent(
            name="synthesizer",
            role="Resolve tensions and integrate insights (synthesis)",
            model=self.model,
            instructions="""
You are the synthesizer in a dialectic triad.
Take the best from proposals and critiques.
Resolve contradictions into coherent, improved solutions.
""",
            tools=[generate_code]
        )

        return Team(
            name=f"triad_{self.config.id}",
            members=[proposer, critic, synthesizer],
            add_history_to_context=True
        )
```

### Consensus Triad

```python
# hfs/agno/presets/consensus.py

class ConsensusAgnoTriad:
    """Consensus triad: 3 equal peers with voting."""

    def _build_team(self) -> Team:
        peers = []
        for i in range(3):
            peer = Agent(
                name=f"peer_{i+1}",
                role=f"Equal voice in consensus (peer {i+1})",
                model=self.model,
                instructions=f"""
You are peer {i+1} in a consensus triad.
All peers have equal voice. Decisions require 2/3 majority.
Focus on {self.config.objectives}.
Engage in good-faith deliberation. Be willing to change your position.
""",
                tools=[register_claim, negotiate_response, generate_code]
            )
            peers.append(peer)

        return Team(
            name=f"triad_{self.config.id}",
            members=peers,
            add_history_to_context=True
        )

    async def vote(self, proposals: List[dict]) -> dict:
        """Run voting round among peers."""
        prompt = f"""
PHASE: VOTING

Proposals to vote on:
{proposals}

Each peer must vote for exactly one proposal.
A proposal wins with 2/3 majority (2+ votes).
If no majority, explain dissent and try to converge.
"""
        result = await self.team.arun(prompt)
        return self._tally_votes(result)
```

---

## Updated Orchestrator

```python
# hfs/core/orchestrator.py (updated)

from hfs.agno.teams import AgnoTriadFactory

class HFSOrchestrator:
    def __init__(self, config: HFSConfig, use_agno: bool = True):
        self.config = config
        self.use_agno = use_agno

        if use_agno:
            from agno.models.anthropic import Claude
            self.model = Claude(id="claude-sonnet-4-5")
            self.triad_factory = AgnoTriadFactory(self.model)
        else:
            self.triad_factory = TriadFactory(self.llm_client)

    async def _spawn_triads(self) -> List[Triad]:
        """Create triad instances from config."""
        triads = []
        for triad_config in self.config.triads:
            if self.use_agno:
                triad = self.triad_factory.create_agno_triad(triad_config)
            else:
                triad = self.triad_factory.create_triad(triad_config)
            triads.append(triad)
        return triads
```

---

## Configuration Updates

Add Agno settings to the config schema:

```yaml
# hfs/config/default.yaml

agno:
  enabled: true
  model:
    provider: "anthropic"
    id: "claude-sonnet-4-5"
  storage:
    backend: "sqlite"
    path: "hfs_sessions.db"
  learning: false  # Enable for agents to improve over time

triads:
  - id: "layout"
    preset: "hierarchical"
    # ... existing config
```

```python
# hfs/core/config.py (additions)

class AgnoConfigModel(BaseModel):
    enabled: bool = True
    model: ModelConfigModel = ModelConfigModel()
    storage: StorageConfigModel = StorageConfigModel()
    learning: bool = False

class ModelConfigModel(BaseModel):
    provider: str = "anthropic"
    id: str = "claude-sonnet-4-5"

class StorageConfigModel(BaseModel):
    backend: str = "sqlite"
    path: str = "hfs_sessions.db"
```

---

## Implementation Phases

### Phase 1: Foundation (Start Here)
1. Create `hfs/agno/` directory structure
3. Add Agno to dependencies in `pyproject.toml`
4. Write basic integration tests

### Phase 2: Tools
1. Implement HFS-specific tools in `hfs/agno/tools.py`
2. Create tool registry for each triad type
3. Add tool validation and error handling

### Phase 3: Triad Implementations
1. Implement `HierarchicalAgnoTriad`
2. Implement `DialecticAgnoTriad`
3. Implement `ConsensusAgnoTriad`
4. Create factory for Agno triads

### Phase 4: Orchestrator Integration
1. Update orchestrator to use Agno triads
3. REMOVE backward compatibility with mock client (clean up the code)

### Phase 5: Production Features
1. Add persistent storage for sessions
2. DO NOT ENABLE learning mode for agent improvement
3. Add monitoring and observability (setup_tracing on the dbs using opentelemetry)
4. Performance optimization

#### Tracing Setup (Phase 5.3)

Agno uses OpenTelemetry for tracing. All trace data stays in your database (never sent to third parties).

**Dependencies:**
```bash
pip install opentelemetry-api opentelemetry-sdk openinference-instrumentation-agno
```

**Setup in orchestrator initialization:**
```python
# hfs/agno/tracing.py

from agno.tracing import setup_tracing
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb

def init_hfs_tracing(backend: str = "sqlite", path: str = "hfs_traces.db"):
    """Initialize tracing for HFS orchestrator."""
    if backend == "sqlite":
        db = SqliteDb(db_file=path)
    elif backend == "postgres":
        db = PostgresDb(connection_string=path)
    else:
        raise ValueError(f"Unknown tracing backend: {backend}")

    setup_tracing(db=db)
    return db

# Usage in orchestrator
class HFSOrchestrator:
    def __init__(self, config: HFSConfig):
        # ... existing init ...

        # Initialize tracing
        if config.agno.tracing.enabled:
            self.trace_db = init_hfs_tracing(
                backend=config.agno.tracing.backend,
                path=config.agno.tracing.path
            )
```

**What gets traced automatically:**
- Agent runs with full execution context
- Model calls (prompts, responses, token usage)
- Tool executions (arguments and results)
- Team and workflow coordination

**Querying traces:**
```python
# Get recent traces for a specific triad
traces = trace_db.get_traces(agent_id=triad.team.id, limit=10)

# Export to external tools (Arize Phoenix, Langfuse) via OpenTelemetry
```

**Config schema addition:**
```yaml
agno:
  tracing:
    enabled: true
    backend: "sqlite"  # or "postgres"
    path: "hfs_traces.db"
```

---

## Testing Strategy

```python
# hfs/tests/test_agno_integration.py

import pytest
from hfs.agno.client import AgnoLLMClient
from hfs.agno.presets.hierarchical import HierarchicalAgnoTriad

@pytest.mark.asyncio
async def test_agno_client_adapter():
    """Test that Agno client matches HFS interface."""
    client = AgnoLLMClient(model_id="claude-sonnet-4-5")

    response = await client.messages_create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[
            {"role": "system", "content": "You are a test agent."},
            {"role": "user", "content": "Say hello."}
        ]
    )

    assert "content" in response
    assert len(response["content"]) > 0

@pytest.mark.asyncio
async def test_hierarchical_triad_deliberation():
    """Test hierarchical triad deliberation phase."""
    config = TriadConfig(
        id="test_layout",
        preset=TriadPreset.HIERARCHICAL,
        scope=ScopeConfig(primary=["layout"], reach=["visual"])
    )

    triad = HierarchicalAgnoTriad(config, model)

    result = await triad.deliberate(
        "Create a responsive grid layout",
        {"sections": {"layout": {"status": "unclaimed"}}}
    )

    assert "claims" in result
    assert "layout" in result["claims"]
```

---

## Open Questions

1. **Session Persistence**: Should each HFS run create a new session, or should agents accumulate knowledge across runs?

2. **Learning Mode**: When enabled, how should agent improvements propagate to other triads?

3. **Tool Execution**: Should tools execute immediately or queue for human approval (human-in-the-loop)?

4. **Model Selection**: Should different roles use different models (e.g., Claude Opus for orchestrators, Claude Sonnet for workers)?

5. **Parallel Execution**: During execution phase, should worker agents run in parallel or sequentially?

---

## Resources

- [Agno Documentation](https://docs.agno.com)
- [Agno GitHub](https://github.com/agno-agi/agno)
- [HFS Design Doc](./DESIGN.md)
- [HFS Philosophy](./PHILOSOPHY.md)

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-28 | Claude | Initial draft |
