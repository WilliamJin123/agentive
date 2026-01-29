# Architecture

**Analysis Date:** 2026-01-29

## Pattern Overview

**Overall:** Multi-Agent Negotiation Pipeline with Distributed Ownership

**Key Characteristics:**
- **Actor Model**: Three independent agent triads (Hierarchical, Dialectic, Consensus) operate as autonomous units that negotiate over shared spec
- **Warm Wax Model**: Spec sections exist in malleable state (temperature: 1.0) where claims can be registered, negotiated, and ownership transferred via temperature decay
- **Arbiter-Mediated Conflict Resolution**: When negotiation deadlocks (no progress for `escalation_threshold` rounds), an LLM arbiter breaks the tie via decisional authority
- **Emergent Center Observation**: Quality metrics (coherence, style consistency, interaction consistency) emerge from triad interactions without central control

## Layers

**Input/Configuration Layer:**
- Purpose: Load, validate, and prepare execution context
- Location: `hfs/core/config.py`, `hfs/config/`
- Contains: Pydantic models for TriadConfig, PressureConfig, OutputConfig; YAML parsing and validation
- Depends on: External YAML files, Pydantic framework
- Used by: HFSOrchestrator initialization

**Orchestration Layer:**
- Purpose: Coordinate the 9-phase pipeline and state transitions
- Location: `hfs/core/orchestrator.py`
- Contains: HFSOrchestrator class, HFSResult dataclass, phase coordination logic
- Depends on: All lower layers (Spec, Negotiation, Triads, Integration)
- Used by: CLI (`hfs/cli/main.py`), external callers

**Triad & Preset Layer:**
- Purpose: Define working units with internal agent structures and negotiation interfaces
- Location: `hfs/core/triad.py`, `hfs/presets/hierarchical.py`, `hfs/presets/dialectic.py`, `hfs/presets/consensus.py`
- Contains: TriadPreset enum, Triad ABC with deliberate/negotiate/execute methods; three concrete preset implementations
- Depends on: LLM client for agent communication
- Used by: Orchestrator during spawn, deliberation, and execution phases

**Negotiation & Arbitration Layer:**
- Purpose: Manage boundary deformation (claim registration, proposal exchange, concession) and conflict resolution
- Location: `hfs/core/negotiation.py`, `hfs/core/arbiter.py`, `hfs/core/spec.py`
- Contains: NegotiationEngine (manages rounds), Spec (shared mutable state with temperature), Arbiter (LLM-mediated decisions)
- Depends on: Triad negotiation responses, LLM client for arbiter decisions
- Used by: Orchestrator during negotiation rounds and freeze

**Quality Observation Layer:**
- Purpose: Observe emergent properties without controlling them
- Location: `hfs/core/emergent.py`
- Contains: EmergentObserver, EmergentMetrics, DetectedPatterns, EmergentReport
- Depends on: Final spec, merged artifact, triad metadata
- Used by: Orchestrator during output phase

**Integration & Validation Layer:**
- Purpose: Merge artifacts from all triads and validate output quality
- Location: `hfs/integration/merger.py`, `hfs/integration/validator.py`, `hfs/integration/renderer.py`
- Contains: CodeMerger (combines artifacts), Validator (runs quality checks), Renderer (optional format conversion)
- Depends on: TriadOutput artifacts, MergedArtifact
- Used by: Orchestrator during integration phase

## Data Flow

**Pipeline Phase: INPUT (Phase 1)**
1. User provides request string and config path
2. Config loaded and validated via `load_config(config_path)` → HFSConfig
3. LLM client injected into orchestrator
4. State: HFSOrchestrator initialized with config, spec created with temperature=1.0

**Pipeline Phase: SPAWN TRIADS (Phase 2)**
1. For each triad config in HFSConfig.triads:
   - `create_triad(config, llm_client)` instantiates preset (Hierarchical|Dialectic|Consensus)
   - Triad initializes its 3 agents with role-specific system prompts
   - Agents cached for reuse across phases
2. State: `triads` dict ready for deliberation

**Pipeline Phase: INTERNAL DELIBERATION (Phase 3)**
1. Each triad calls `triad.deliberate(user_request, spec)` independently and concurrently
2. Triad returns TriadOutput: position, claims (list of section names), proposals (dict of section→content)
3. State: All triad outputs collected; spec still unmodified

**Pipeline Phase: CLAIM REGISTRATION (Phase 4)**
1. For each triad's output:
   - For each claimed section: `spec.register_claim(triad_id, section_name, proposal)`
   - Section created if new, proposal stored, claimants list updated
   - Status flow: UNCLAIMED → (CONTESTED if 2+ claimants else CLAIMED)
2. State: Spec sections now contain proposals and claimant lists

**Pipeline Phase: NEGOTIATION ROUNDS (Phase 5)**
1. NegotiationEngine iterates while contested sections exist:
   - Round 1...N (up to config.pressure.max_negotiation_rounds):
     - Decrement spec.temperature by config.pressure.temperature_decay
     - For each contested section:
       - Share proposal summary with all claimants
       - Call `triad.negotiate(section_name, competing_proposals, spec)` for each claimant
       - Collect responses: "concede" (withdraw), "revise" (update proposal), "hold" (maintain)
       - Update claimants list based on concessions
       - If single claimant remains: section resolved, status→CLAIMED
     - Check stuck: if no sections resolved this round and stuck_count >= escalation_threshold:
       - Escalate to `arbiter.decide(section_name, proposals, context)`
       - Arbiter returns ArbiterDecision (assign|split|merge)
       - Apply decision to spec
     - Increment stuck_count; reset if progress made
   - Exit if all sections resolved OR temperature drops below freeze_threshold
2. State: Spec sections have single owner but not yet frozen

**Pipeline Phase: FREEZE (Phase 6)**
1. Call `spec.freeze()`:
   - For each section: status CLAIMED → FROZEN, content set from owner's proposal
   - spec.temperature = 0.0
   - No further negotiation allowed
2. State: Spec locked; ownership finalized

**Pipeline Phase: EXECUTION (Phase 7)**
1. For each triad:
   - Call `triad.execute(owned_sections, user_request, spec)` where owned_sections are sections with owner=triad_id
   - Triad generates code/content for its owned sections
   - Returns TriadOutput with code proposals
2. State: All triads have generated code; ready for merge

**Pipeline Phase: INTEGRATION (Phase 8)**
1. CodeMerger.merge(all_triad_outputs, output_config):
   - Combine artifacts from all triads into unified codebase
   - Resolve imports/exports between components
   - Deduplicate styles, utilities
   - Organize files into output structure
   - Returns MergedArtifact
2. Validator.validate(merged_artifact):
   - Run syntax, render, accessibility, performance checks
   - Return ValidationResult with issues list
3. State: Single unified artifact with validation metadata

**Pipeline Phase: OUTPUT (Phase 9)**
1. EmergentObserver.observe(spec, merged_artifact, triads):
   - Calculate coherence, style_consistency, interaction_consistency metrics
   - Detect implicit styles, natural clusters, collaboration patterns
   - Generate recommendations
   - Return EmergentReport
2. Assemble HFSResult with artifact, validation, emergent report, phase timings
3. CLI or caller serializes/saves result
4. State: Pipeline complete; result ready for consumption

## State Management

**Spec (Shared Mutable State):**
- Type: `hfs/core/spec.py::Spec` dataclass
- Lifespan: Initialized phase 1, frozen phase 6
- Temperature: 1.0 (malleable) → 0.0 (frozen) across negotiation
- Sections: Dict[str_name → Section] containing status, owner, claims, proposals, content
- Mutations:
  - Phase 4: `register_claim()` populates proposals, updates status
  - Phase 5: `register_negotiation_response()` removes claimants, updates proposals
  - Phase 6: `freeze()` locks content, finalizes ownership
- Access Pattern: Read by triads in deliberate/negotiate, written by engine/arbiter

**Triad Instance State:**
- Type: Subclass of `hfs/core/triad.py::Triad`
- Lifespan: Created phase 2, destroyed after phase 7
- Instance Variables: config, llm_client, agents (initialized on first deliberate)
- Stateless Methods: deliberate, negotiate, execute all accept inputs, return outputs
- Internal Pattern: Agents communicate with llm_client but don't share state between phases

**Orchestrator State:**
- Type: `hfs/core/orchestrator.py::HFSOrchestrator`
- Lifespan: Created per user request
- Holds: config, llm_client, triads dict, spec, phase timings
- Coordination: Transitions between phases via explicit phase functions

## Key Abstractions

**Spec (Warm Wax Model):**
- Purpose: Represents shared territory that triads negotiate over
- Location: `hfs/core/spec.py`
- Pattern: Ownership transfers happen via claim registration and negotiation; temperature controls malleability
- Lifecycle: UNCLAIMED → CONTESTED → CLAIMED → FROZEN

**TriadPreset (Three Patterns):**
- Purpose: Different internal agent structures for different problem types
- Hierarchical (Location: `hfs/presets/hierarchical.py`): Clear delegation; orchestrator + 2 workers
  - Best for: layout, state_management, performance (execution-heavy)
- Dialectic (Location: `hfs/presets/dialectic.py`): Thesis-antithesis-synthesis; proposer + critic + synthesizer
  - Best for: visual, motion, interaction (creative/ambiguous)
- Consensus (Location: `hfs/presets/consensus.py`): Three equal peers voting
  - Best for: accessibility, standards, cross-cutting concerns
- Pattern: All inherit from Triad ABC; implement deliberate, negotiate, execute

**NegotiationResponse Enum:**
- Purpose: Standardized vocabulary for triad responses during contested rounds
- Values: "concede" (withdraw claim), "revise" (update proposal), "hold" (maintain position)
- Location: `hfs/core/triad.py`

**ArbiterDecision Types:**
- Purpose: Standardized decisions when negotiation deadlocks
- Types: "assign" (give to one triad), "split" (divide section), "merge" (combine proposals)
- Pattern: Arbiter uses LLM to reason about user intent and minimize future conflicts
- Location: `hfs/core/arbiter.py`

**EmergentMetrics:**
- Purpose: Quantify emergent properties without controlling them
- Metrics: coherence_score (0.0-1.0), style_consistency, interaction_consistency
- Location: `hfs/core/emergent.py`
- Pattern: Observed POST-execution, not tuned during runtime

## Entry Points

**HFSOrchestrator.run(user_request: str):**
- Location: `hfs/core/orchestrator.py`
- Triggers: Called by CLI or external code
- Responsibilities: Execute entire 9-phase pipeline, return HFSResult
- Signature: `async def run(self, user_request: str) → HFSResult`

**run_hfs(config_path, user_request, llm_client):**
- Location: `hfs/core/orchestrator.py`
- Triggers: Convenience function for one-off runs
- Responsibilities: Create orchestrator and run, simplifying API
- Pattern: Wraps HFSOrchestrator initialization and execution

**CLI Commands:**
- Location: `hfs/cli/main.py`
- `hfs run --config config.yaml --request "..." --output-dir ./output`
- `hfs validate-config config.yaml`
- `hfs list-presets [--preset <name>]`

## Error Handling

**Strategy:** Explicit validation at config load time; phase failures surface in HFSResult

**Patterns:**
- ConfigError: Raised by `load_config()` on invalid YAML or schema violations
  - Caught in CLI via try/except in cmd_run, cmd_validate_config
- TriadNegotiationTimeout: Implied (not yet explicit in code) when phase exceeds budget
- ArbiterDecisionError: Could occur if arbiter response doesn't parse; currently caught as generic Exception
- ValidationFailure: Non-fatal; issues appended to ValidationResult, pipeline continues

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module
- Setup: `hfs/cli/main.py` configures root logger at INFO level
- Usage: Each module has `logger = logging.getLogger(__name__)`
- Levels: INFO for phase transitions, DEBUG for detailed negotiation steps

**Validation:**
- Phase-Level: `load_config()` validates config schema immediately
- Section-Level: `spec.register_claim()` prevents claims on frozen sections
- Output-Level: `Validator.validate()` runs syntax, render, accessibility, performance checks in phase 8

**Authentication:**
- No auth in core system (stateless pipeline)
- Config allows arbitrary LLM client injection; auth deferred to client impl
- CLI uses MockLLMClient for demo; production uses actual Anthropic client

**Async/Concurrency:**
- Pattern: `async def` for orchestrator.run(); triads.deliberate() concurrent via asyncio.gather()
- Triads execute sequentially during negotiation (one round at a time)
- No explicit locking; spec mutations guarded by phase ordering (claim→negotiate→freeze)

---

*Architecture analysis: 2026-01-29*
