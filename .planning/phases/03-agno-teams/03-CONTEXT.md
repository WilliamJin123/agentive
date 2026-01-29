# Phase 3: Agno Teams - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Triads execute as Agno Teams with 3 agent members, async execution, and conversation history preserved across deliberate/negotiate/execute phases. This covers HierarchicalTriad, DialecticTriad, and ConsensusTriad implementations.

</domain>

<decisions>
## Implementation Decisions

### Conversation Memory
- Role-scoped history — agents only see messages relevant to their role, not full shared history
- Summarized handoff between phases — previous phase produces a summary, next phase consumes it
- Synthesizer agent produces the phase transition summary (not orchestrator, not system-generated)
- Structured template for summaries — predefined sections (decisions, open questions, artifacts) for consistency

### Failure Handling
- Abort team run on agent failure — fail fast, surface error to orchestrator level for retry decisions
- Summary + error context — include which agent failed, what phase, and the error message (not full trace, not error only)
- Preserve partial progress — save completed work so retry can resume from last good state
- Specific markdown state files — write progress to different .planning files for different parts of the multi-agent system

### Team Coordination
- Orchestrator-directed turns — orchestrator explicitly assigns who speaks next
- Parallel worker dispatch — orchestrator can run multiple workers simultaneously
- Process as available — orchestrator handles each worker result as it arrives (streaming approach)
- Negotiation round for conflicts — when parallel workers produce conflicting outputs, trigger follow-up where workers negotiate

### Role Boundaries
- Communication depends on triad type — Hierarchical uses orchestrator; Consensus allows direct peer communication
- Role-specific tools — certain tools restricted to certain roles (e.g., only orchestrator can claim sections)
- Smart context segregation — agents have specific tasks, prompts, and tools scoped to their role (enforced through design, not just prompts)
- Fixed roles in DialecticTriad — proposer/critic/synthesizer roles don't rotate between rounds

### Claude's Discretion
- Exact Agno Team API usage patterns
- Summary template schema details
- State file naming and structure within .planning
- Timeout values for parallel worker dispatch

</decisions>

<specifics>
## Specific Ideas

- Phase transitions should produce clean handoffs — the next phase shouldn't need to parse through conversation noise
- Parallel execution is important for speed, but conflicts should be resolved through agent negotiation rather than arbitrary priority
- Each triad type has its own communication topology — don't force a one-size-fits-all pattern

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-agno-teams*
*Context gathered: 2026-01-29*
