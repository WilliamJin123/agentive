# Hexagonal Frontend System (HFS)

## A Bio-Inspired Multi-Agent Architecture for Frontend Development

**Version:** 1.0  
**Status:** Design Phase

---

## Table of Contents

1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Architectural Inspiration](#architectural-inspiration)
4. [System Components](#system-components)
5. [Triad Architecture](#triad-architecture)
6. [The Spec (Shared Mutable State)](#the-spec-shared-mutable-state)
7. [Pressure Mechanics](#pressure-mechanics)
8. [Negotiation Protocol](#negotiation-protocol)
9. [System Flow](#system-flow)
10. [Emergent Center](#emergent-center)
11. [Configuration Schema](#configuration-schema)
12. [Implementation Guide](#implementation-guide)
13. [Example Configurations](#example-configurations)
14. [Future Considerations](#future-considerations)

---

## Overview

HFS is a multi-agent system for end-to-end frontend development that draws inspiration from natural structures—specifically triangular stability and hexagonal emergence in beehives. The system uses "triads" (3-agent units) as its atomic building blocks, with hexagonal-like coordination patterns emerging from resource pressure and negotiation.

### Why This Architecture?

Traditional multi-agent systems often suffer from:
- Coordination overhead that scales poorly
- Unclear ownership leading to gaps or redundancy
- Brittle handoffs between specialized agents
- No natural mechanism for coherence

HFS addresses these through:
- **Triads as stable atoms**: Three agents working as one unit, providing internal redundancy and consensus
- **Pressure-driven boundaries**: Scarcity of resources forces agents to negotiate territory
- **Emergent coherence**: Global quality arises from local interactions, not top-down control
- **Observable structure**: The system's coordination patterns reveal insights about the problem domain

---

## Core Principles

### 1. Triad as Atom
The fundamental unit is not a single agent, but three sub-agents working as one. This provides:
- Internal error correction (3 perspectives catch mistakes)
- Natural consensus mechanism (2-1 voting)
- Structural stability (like physical triangles)

### 2. Pressure Creates Structure
Agents don't coordinate because they're told to—they coordinate because resources are scarce. Limited tokens, time, and scope force negotiation and boundary formation.

### 3. Boundaries Are Soft Until Frozen
During negotiation, territories are contested and malleable. Only after sufficient rounds do boundaries "freeze" into final ownership. This mimics how bee cells deform under pressure before hardening.

### 4. Center Emerges, Not Assigned
No agent owns "design coherence" or "overall quality." These properties emerge from the interactions between triads and are observed, not controlled.

---

## Architectural Inspiration

### From Nature

**Triangles in Nature:**
- Bone structures use triangular lattices for strength
- Crystal formations rely on triangular stability
- Engineering trusses use triangles because they can't deform without breaking

**Hexagonal Beehives:**
- Bees build circular cells
- Body heat softens the wax
- Packing pressure deforms circles into hexagons
- Optimal coverage emerges without planning

### Translation to Multi-Agent Systems

| Natural Element | HFS Equivalent |
|-----------------|----------------|
| Circular cell | Triad with scope.reach (aspirational territory) |
| Wax medium | Shared specification document |
| Body heat | Active negotiation rounds |
| Packing pressure | Resource scarcity + coverage requirements |
| Hexagonal emergence | Stable boundary patterns after negotiation |
| Hive coherence | Emergent center (observed quality metrics) |

---

## System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HFS SYSTEM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   TRIAD 1   │  │   TRIAD 2   │  │   TRIAD 3   │  │   TRIAD N   │ │
│  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │ │
│  │  │ ○ ○ ○ │  │  │  │ ○ ○ ○ │  │  │  │ ○ ○ ○ │  │  │  │ ○ ○ ○ │  │ │
│  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │        │
│         └────────────────┼────────────────┼────────────────┘        │
│                          │                │                          │
│                          ▼                ▼                          │
│              ┌───────────────────────────────────────┐               │
│              │          SHARED SPEC (WARM WAX)       │               │
│              │  ┌─────────────────────────────────┐  │               │
│              │  │ Sections: layout, visual,       │  │               │
│              │  │ motion, interaction, state,     │  │               │
│              │  │ performance, accessibility      │  │               │
│              │  │                                 │  │               │
│              │  │ Temperature: 0.0 - 1.0         │  │               │
│              │  │ Status: contested → frozen     │  │               │
│              │  └─────────────────────────────────┘  │               │
│              └───────────────────────────────────────┘               │
│                                   │                                  │
│                                   ▼                                  │
│              ┌───────────────────────────────────────┐               │
│              │           PRESSURE SYSTEM             │               │
│              │  • Resource budgets (tokens, time)   │               │
│              │  • Coverage requirements             │               │
│              │  • Quality thresholds                │               │
│              │  • Coherence constraints             │               │
│              └───────────────────────────────────────┘               │
│                                   │                                  │
│                                   ▼                                  │
│              ┌───────────────────────────────────────┐               │
│              │         ARBITER (ESCALATION)          │               │
│              │  Resolves stuck negotiations          │               │
│              └───────────────────────────────────────┘               │
│                                   │                                  │
│                                   ▼                                  │
│              ┌───────────────────────────────────────┐               │
│              │         EMERGENT CENTER               │               │
│              │  (Observed, not controlled)          │               │
│              │  • Coherence score                   │               │
│              │  • Style consistency                 │               │
│              │  • Coverage gaps                     │               │
│              │  • Natural cluster patterns          │               │
│              └───────────────────────────────────────┘               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Triad Architecture

### What is a Triad?

A triad is the atomic working unit of HFS. It consists of three sub-agents that collaborate internally before interacting with other triads externally.

```
         ┌─────────┐
         │ Agent A │
         └────┬────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───┴───┐           ┌───┴───┐
│Agent B│───────────│Agent C│
└───────┘           └───────┘

The triad operates as ONE UNIT externally.
Internal deliberation produces unified output.
```

### Triad Presets

#### Preset: Hierarchical

```yaml
hierarchical:
  description: "Clear delegation, good for execution-heavy work"
  
  structure:
    orchestrator:
      role: "Plans, delegates, integrates results"
      capabilities:
        - decompose_task
        - assign_subtasks
        - merge_outputs
        - quality_check
      
    worker_a:
      role: "Executes subtask A"
      capabilities:
        - execute
        - report_status
        - flag_blockers
      
    worker_b:
      role: "Executes subtask B"  
      capabilities:
        - execute
        - report_status
        - flag_blockers
  
  flow: |
    1. Orchestrator receives task
    2. Orchestrator decomposes into subtasks
    3. Workers execute in parallel
    4. Workers report results
    5. Orchestrator merges and validates
    6. Triad outputs unified result
  
  best_for:
    - layout
    - state_management
    - performance_optimization
    - code_generation
```

#### Preset: Dialectic

```yaml
dialectic:
  description: "Thesis-antithesis-synthesis for creative/ambiguous work"
  
  structure:
    proposer:
      role: "Generates candidates and possibilities"
      capabilities:
        - brainstorm
        - draft
        - explore_alternatives
      
    critic:
      role: "Finds flaws, asks hard questions"
      capabilities:
        - evaluate
        - challenge
        - identify_risks
        - stress_test
      
    synthesizer:
      role: "Resolves tensions into coherent output"
      capabilities:
        - merge
        - refine
        - balance_tradeoffs
        - finalize
  
  flow: |
    1. Proposer generates initial options
    2. Critic evaluates and challenges
    3. Proposer may revise based on critique
    4. Synthesizer resolves remaining tensions
    5. Triad outputs refined result
  
  best_for:
    - visual_design
    - motion_design
    - interaction_patterns
    - creative_decisions
```

#### Preset: Consensus

```yaml
consensus:
  description: "Three peers with equal voice, majority decides"
  
  structure:
    peer_1:
      role: "Perspective A"
      capabilities:
        - propose
        - vote
        - argue_position
      
    peer_2:
      role: "Perspective B"
      capabilities:
        - propose
        - vote
        - argue_position
      
    peer_3:
      role: "Perspective C"
      capabilities:
        - propose
        - vote
        - argue_position
  
  flow: |
    1. All peers propose independently
    2. Peers discuss and debate
    3. Vote taken (2/3 majority needed)
    4. If no majority, another round of discussion
    5. Final vote or fallback to first peer's proposal
  
  best_for:
    - accessibility_decisions
    - standards_compliance
    - coherence_checking
    - cross_cutting_concerns
```

### Triad Configuration Schema

```yaml
triad:
  # Unique identifier
  id: string
  
  # Which preset to use
  preset: "hierarchical" | "dialectic" | "consensus"
  
  # Territory definition
  scope:
    # Sections this triad can write directly
    primary: string[]
    
    # Sections this triad wants to influence (can propose claims)
    reach: string[]
  
  # Resource constraints
  budget:
    tokens: int          # Max tokens for this triad
    tool_calls: int      # Max tool invocations
    time_ms: int         # Max execution time
  
  # Available operations
  tools:
    - read_spec          # Read current spec state
    - write_spec         # Write to owned sections
    - propose_claim      # Propose ownership of contested sections
    - negotiate          # Engage in negotiation with other triads
    - escalate           # Request arbiter intervention
  
  # What this triad optimizes for
  objectives: string[]
  
  # System prompt additions for this triad's agents
  system_context: string
```

---

## The Spec (Shared Mutable State)

The spec is the shared document that all triads read from and write to. It serves as the "warm wax" that allows boundaries to deform during negotiation before freezing into final assignments.

### Spec Schema

```yaml
spec:
  # Global state
  metadata:
    temperature: float     # 1.0 = fully malleable, 0.0 = frozen
    round: int             # Current negotiation round
    status: "initializing" | "negotiating" | "cooling" | "frozen" | "executing"
  
  # The territorial divisions
  sections:
    layout:
      status: "unclaimed" | "contested" | "claimed" | "frozen"
      owner: triad_id | null
      claims: triad_id[]           # Triads that want this section
      content: object | null       # Actual spec content when written
      proposals:                   # Competing proposals during negotiation
        [triad_id]: object
      history:                     # Audit trail
        - { round: int, action: string, by: triad_id }
    
    visual:
      # Same structure...
    
    motion:
      # Same structure...
    
    interaction:
      # Same structure...
    
    state:
      # Same structure...
    
    performance:
      # Same structure...
    
    accessibility:
      # Same structure...
    
    # Sections can be nested
    layout/grid:
      # Sub-section...
    
    layout/spacing:
      # Sub-section...
```

### Section Statuses

```
unclaimed ──► contested ──► claimed ──► frozen
    │              │            │
    │              │            └── Ownership accepted, content set
    │              │
    │              └── Multiple triads want this section
    │
    └── No triad has claimed this yet
```

### Temperature Mechanics

Temperature controls how malleable boundaries are:

```
Temperature 1.0 (Hot):
  - Any triad can claim any section
  - Claims easily displaced
  - Boundaries highly fluid

Temperature 0.5 (Warm):
  - Claims require justification
  - Existing claims have inertia
  - Negotiation becomes more serious

Temperature 0.0 (Frozen):
  - No more claims accepted
  - Boundaries are final
  - Execution begins
```

Temperature decay formula:
```
temperature(round) = max(0, initial_temp - (decay_rate * round))
```

---

## Pressure Mechanics

Pressure is what forces triads to negotiate rather than simply coexist. Without pressure, each triad would claim everything. With pressure, they must make tradeoffs.

### Types of Pressure

#### 1. Resource Pressure

```yaml
resource_pressure:
  # Global budget that must be divided
  total_budget:
    tokens: 100000        # Total tokens for all triads combined
    time_ms: 60000        # Total wall-clock time
    
  # Per-triad limits
  per_triad_max:
    tokens: 20000         # No single triad can exceed this
    tool_calls: 50
    
  # Enforcement
  enforcement: "hard"     # "hard" = strict cutoff, "soft" = warning + degraded priority
```

#### 2. Coverage Pressure

```yaml
coverage_pressure:
  # Every section must be owned before execution
  requirement: "all_sections_owned"
  
  # Sections that exist (defines the "space" to cover)
  sections:
    - layout/*
    - visual/*
    - motion/*
    - interaction/*
    - state/*
    - performance/*
    - accessibility/*
  
  # Triads naturally want more than their primary scope
  # This creates overlapping claims and forces negotiation
  natural_expansion: true
```

#### 3. Quality Pressure

```yaml
quality_pressure:
  # Final output must pass these validations
  validation:
    - must_compile        # Code must be syntactically valid
    - must_render         # Must produce visible output
    - no_contradictions   # Spec sections must be compatible
    - accessibility_a11y  # Must pass basic a11y checks
    - performance_budget  # Must meet performance thresholds
  
  # Quality metrics that triads are optimizing
  # Different triads have different objectives, creating tension
  triad_objectives:
    visual:
      - aesthetic_quality
      - brand_alignment
      - visual_hierarchy
    performance:
      - load_time
      - bundle_size
      - runtime_efficiency
    accessibility:
      - wcag_compliance
      - keyboard_navigation
      - screen_reader_support
```

#### 4. Coherence Pressure

```yaml
coherence_pressure:
  # Output must be unified, not just assembled
  requirements:
    - single_artifact      # One final output, not fragments
    - consistent_styling   # Visual language must cohere
    - unified_behavior     # Interactions must feel of-a-piece
  
  # Measured but not directly optimized by any triad
  emergent_metrics:
    - design_coherence_score
    - interaction_consistency
    - cognitive_load_estimate
```

---

## Negotiation Protocol

When two or more triads claim the same section, they must negotiate.

### Negotiation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NEGOTIATION PROTOCOL                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  TRIGGER: Section has multiple claims                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ ROUND 1                                                      │    │
│  │                                                              │    │
│  │  1. Each claimant submits proposal for section              │    │
│  │  2. Proposals shared with all claimants                     │    │
│  │  3. Each claimant can:                                      │    │
│  │     • CONCEDE - Withdraw claim                              │    │
│  │     • REVISE  - Update proposal based on others             │    │
│  │     • HOLD    - Maintain current position                   │    │
│  │  4. Check resolution                                        │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│              ┌───────────────┴───────────────┐                      │
│              │                               │                       │
│              ▼                               ▼                       │
│        ┌──────────┐                  ┌──────────────┐                │
│        │ RESOLVED │                  │ STILL STUCK  │                │
│        │          │                  │              │                │
│        │ One      │                  │ Multiple     │                │
│        │ claimant │                  │ claimants    │                │
│        │ remains  │                  │ remain       │                │
│        └────┬─────┘                  └──────┬───────┘                │
│             │                               │                        │
│             ▼                               ▼                        │
│     Winner owns                    Round < threshold?               │
│     section                               │                         │
│                               ┌───────────┴───────────┐             │
│                               │                       │              │
│                               ▼                       ▼              │
│                         ┌──────────┐          ┌────────────┐        │
│                         │ ROUND N  │          │ ESCALATE   │        │
│                         │ (repeat) │          │ TO ARBITER │        │
│                         └──────────┘          └────────────┘        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Negotiation Actions

```yaml
negotiation_actions:
  
  concede:
    description: "Withdraw claim from section"
    effect: "Triad removed from claimants list"
    when_to_use:
      - "Other triad's proposal is clearly better"
      - "Section is outside core competency"
      - "Preserving resources for more important battles"
  
  revise:
    description: "Update proposal based on new information"
    effect: "Triad's proposal replaced with new version"
    when_to_use:
      - "Saw merit in another triad's approach"
      - "Found way to merge perspectives"
      - "Narrowing scope to reduce conflict"
  
  hold:
    description: "Maintain current position"
    effect: "No change, signals firm commitment"
    when_to_use:
      - "Core to triad's objectives"
      - "Already optimal proposal"
      - "Waiting for others to concede"
```

### Escalation to Arbiter

When negotiation exceeds the stuck threshold (configurable rounds without resolution), an arbiter LLM is invoked.

```yaml
arbiter:
  description: "External LLM that resolves stuck negotiations"
  
  inputs:
    - original_user_request    # What the user actually asked for
    - current_spec_state       # Full spec with all sections
    - competing_proposals      # Each triad's proposal for contested section
    - triad_objectives         # What each triad is optimizing for
    - negotiation_history      # What's been tried
    - global_coherence_score   # Current emergent quality metrics
  
  outputs:
    decision:
      type: "assign" | "split" | "merge"
      details:
        assign:
          winner: triad_id
          rationale: string
        split:
          division: { [sub_section]: triad_id }
          rationale: string
        merge:
          merged_proposal: object
          assigned_to: triad_id
          rationale: string
  
  principles:
    - "Prioritize user intent over triad preferences"
    - "Consider global coherence, not just local optimality"
    - "Prefer solutions that minimize future conflicts"
    - "Explain reasoning for transparency"
```

### Arbiter System Prompt Template

```
You are an arbiter for the Hexagonal Frontend System. Your role is to resolve
negotiation deadlocks between triads.

## Context
- User Request: {user_request}
- Contested Section: {section_name}
- Current Temperature: {temperature}
- Round: {round}

## Competing Proposals

### Triad: {triad_1_id}
Objectives: {triad_1_objectives}
Proposal:
{triad_1_proposal}

### Triad: {triad_2_id}
Objectives: {triad_2_objectives}
Proposal:
{triad_2_proposal}

## Negotiation History
{history}

## Current Coherence Metrics
{coherence_metrics}

## Your Task
Decide how to resolve this conflict. Consider:
1. Which proposal better serves the user's original intent?
2. Which approach leads to better global coherence?
3. Can the proposals be merged or the section split?
4. What minimizes future conflicts?

Respond with your decision and clear rationale.
```

---

## System Flow

### Complete Execution Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: INPUT                                                      │
│                                                                      │
│ Receive:                                                            │
│   • User request (what to build)                                    │
│   • Configuration (triad count, presets, budgets)                   │
│   • Constraints (must-haves, style preferences)                     │
│                                                                      │
│ Output: Initialized system state                                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SPAWN TRIADS                                               │
│                                                                      │
│ For each triad in config:                                           │
│   • Instantiate based on preset (hierarchical/dialectic/consensus)  │
│   • Assign scope.primary (guaranteed territory)                     │
│   • Assign scope.reach (aspirational territory)                     │
│   • Allocate budget                                                 │
│   • Initialize internal agents with system prompts                  │
│                                                                      │
│ Output: N triads ready to operate                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: INTERNAL DELIBERATION                                      │
│                                                                      │
│ Each triad (in parallel):                                           │
│   • Reads user request                                              │
│   • Runs internal protocol (per preset)                             │
│   • Produces:                                                       │
│     - Position statement (what they think should happen)            │
│     - Claims (which sections they want)                             │
│     - Initial proposals (content for claimed sections)              │
│                                                                      │
│ Output: Triad positions and claims                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: CLAIM REGISTRATION                                         │
│                                                                      │
│ System:                                                             │
│   • Collects all claims from all triads                             │
│   • Registers claims in spec                                        │
│   • Identifies overlaps (contested sections)                        │
│   • Marks sections as claimed/contested/unclaimed                   │
│   • Initializes temperature to 1.0                                  │
│                                                                      │
│ Output: Spec with claim status for all sections                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 5: NEGOTIATION ROUNDS                                         │
│                                                                      │
│ While (contested sections exist AND temperature > 0):               │
│                                                                      │
│   For each contested section:                                       │
│     • Claimants exchange proposals                                  │
│     • Each claimant chooses: CONCEDE / REVISE / HOLD                │
│     • Update section status                                         │
│     • If stuck for N rounds → escalate to arbiter                   │
│                                                                      │
│   Decrease temperature by decay_rate                                │
│   Increment round counter                                           │
│                                                                      │
│ Output: All sections have single owner                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 6: FREEZE                                                     │
│                                                                      │
│ System:                                                             │
│   • Sets temperature to 0                                           │
│   • Marks all sections as frozen                                    │
│   • Locks spec from further modifications                           │
│   • Validates coverage (all sections owned)                         │
│                                                                      │
│ Output: Frozen spec ready for execution                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 7: EXECUTION                                                  │
│                                                                      │
│ Each triad (can be parallel or ordered):                            │
│   • Reads frozen spec                                               │
│   • Generates code/content for owned sections                       │
│   • Defines interfaces at section boundaries                        │
│   • Outputs artifacts                                               │
│                                                                      │
│ Output: Code artifacts from each triad                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 8: INTEGRATION                                                │
│                                                                      │
│ System:                                                             │
│   • Merges all artifacts into single codebase                       │
│   • Resolves import/export boundaries                               │
│   • Runs validation suite:                                          │
│     - Syntax check                                                  │
│     - Render test                                                   │
│     - Accessibility audit                                           │
│     - Performance check                                             │
│   • Computes emergent metrics                                       │
│                                                                      │
│ Output: Integrated artifact + validation results                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 9: OUTPUT                                                     │
│                                                                      │
│ Deliver:                                                            │
│   • Final artifact (the frontend code)                              │
│   • Emergent observations (coherence metrics, patterns)             │
│   • Negotiation summary (how boundaries formed)                     │
│   • Recommendations (suggestions for future runs)                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Emergent Center

The "emergent center" is the quality that no triad owns but all triads affect. It's observed, not controlled.

### What Gets Observed

```yaml
emergent_center:
  
  # Quantitative metrics
  metrics:
    coherence_score:
      description: "How well do sections fit together?"
      range: 0.0 - 1.0
      computation: "TBD - could use embedding similarity, style analysis, etc."
    
    style_consistency:
      description: "Is there a unified visual/tonal language?"
      range: 0.0 - 1.0
      signals:
        - color_palette_variance
        - typography_consistency
        - spacing_rhythm_regularity
    
    interaction_consistency:
      description: "Do interactions feel of-a-piece?"
      range: 0.0 - 1.0
      signals:
        - animation_timing_variance
        - feedback_pattern_similarity
        - state_transition_smoothness
  
  # Qualitative observations
  detected_patterns:
    implicit_style:
      description: "What emerged without being specified?"
      examples:
        - "minimal"
        - "dark-mode-first"
        - "motion-forward"
        - "content-dense"
    
    natural_clusters:
      description: "Which triads ended up collaborating most?"
      format: "[[triad_ids], [triad_ids], ...]"
      insight: "Reveals actual problem structure vs assumed structure"
  
  # Gaps and tensions
  issues:
    coverage_gaps:
      description: "Things no triad addressed"
      examples:
        - "error-states"
        - "empty-states"
        - "loading-transitions"
        - "edge-cases"
    
    unresolved_tensions:
      description: "Conflicts that persisted into final output"
      examples:
        - "visual wants slow transitions, interaction wants snappy feedback"
        - "accessibility needs high contrast, visual wants subtle palette"
  
  # Learning for future runs
  recommendations:
    - description: "Suggested improvements based on this run"
      examples:
        - "visual and motion triads had 5 escalations—consider merging scope"
        - "accessibility concerns appeared late—spawn earlier with broader reach"
        - "performance triad was under-utilized—reduce budget or expand scope"
```

### Using Emergent Observations

The emergent center data can be used for:

1. **Quality Assessment**: Is the output actually coherent, or just assembled?
2. **Architecture Learning**: Do the triad boundaries match the problem structure?
3. **Iteration**: Adjust configuration for future runs based on patterns
4. **Debugging**: Understand why certain outputs feel "off"

---

## Configuration Schema

### Full Configuration Structure

```yaml
# HFS Configuration Schema
# Version: 1.0

config:
  
  # ============================================================
  # TRIADS
  # ============================================================
  triads:
    - id: string                    # Unique identifier
      preset: string                # "hierarchical" | "dialectic" | "consensus"
      scope:
        primary: string[]           # Sections this triad owns by default
        reach: string[]             # Sections this triad can claim
      budget:
        tokens: int                 # Max tokens
        tool_calls: int             # Max tool invocations
        time_ms: int                # Max execution time
      objectives: string[]          # What this triad optimizes for
      system_context: string        # Additional context for prompts (optional)
  
  # ============================================================
  # PRESSURE
  # ============================================================
  pressure:
    # Temperature settings
    initial_temperature: float      # Starting temperature (default: 1.0)
    temperature_decay: float        # Decrease per round (default: 0.15)
    freeze_threshold: float         # Freeze when below this (default: 0.1)
    
    # Negotiation settings
    max_negotiation_rounds: int     # Hard cap on rounds (default: 10)
    escalation_threshold: int       # Rounds stuck before escalate (default: 2)
    
    # Resource constraints
    global_budget:
      tokens: int                   # Total for all triads
      time_ms: int                  # Total wall-clock time
    
    # Quality requirements
    validation:
      - string                      # List of validation checks
  
  # ============================================================
  # SPEC SECTIONS
  # ============================================================
  sections:
    # Define the "territory" that triads will divide
    # Can be flat or hierarchical
    - layout
    - layout/grid
    - layout/spacing
    - layout/responsive
    - visual
    - visual/colors
    - visual/typography
    - visual/imagery
    - motion
    - motion/transitions
    - motion/animations
    - motion/gestures
    - interaction
    - interaction/inputs
    - interaction/feedback
    - interaction/navigation
    - state
    - state/data_flow
    - state/persistence
    - state/sync
    - performance
    - performance/loading
    - performance/runtime
    - performance/bundle
    - accessibility
    - accessibility/semantic
    - accessibility/keyboard
    - accessibility/screen_reader
  
  # ============================================================
  # ARBITER
  # ============================================================
  arbiter:
    model: string                   # LLM to use for arbitration
    max_tokens: int                 # Token limit for arbiter responses
    temperature: float              # LLM temperature (default: 0.3)
  
  # ============================================================
  # OUTPUT
  # ============================================================
  output:
    format: string                  # "react" | "vue" | "svelte" | "html" | "vanilla"
    style_system: string            # "tailwind" | "css-modules" | "styled-components" | "vanilla"
    include_emergent_report: bool   # Include emergent center analysis
    include_negotiation_log: bool   # Include full negotiation history
```

---

## Implementation Guide

### Directory Structure

```
hfs/
├── README.md
├── pyproject.toml (or package.json)
│
├── core/
│   ├── __init__.py
│   ├── triad.py              # Triad base class and presets
│   ├── spec.py               # Spec management
│   ├── pressure.py           # Pressure mechanics
│   ├── negotiation.py        # Negotiation protocol
│   ├── arbiter.py            # Arbiter implementation
│   └── emergent.py           # Emergent center observation
│
├── triads/
│   ├── __init__.py
│   ├── layout.py             # Layout triad implementation
│   ├── visual.py             # Visual triad implementation
│   ├── motion.py             # Motion triad implementation
│   ├── interaction.py        # Interaction triad implementation
│   ├── state.py              # State triad implementation
│   ├── performance.py        # Performance triad implementation
│   └── accessibility.py      # Accessibility triad implementation
│
├── presets/
│   ├── __init__.py
│   ├── hierarchical.py       # Hierarchical preset logic
│   ├── dialectic.py          # Dialectic preset logic
│   └── consensus.py          # Consensus preset logic
│
├── prompts/
│   ├── system/
│   │   ├── orchestrator.md   # Orchestrator system prompt
│   │   ├── worker.md         # Worker system prompt
│   │   ├── proposer.md       # Proposer system prompt
│   │   ├── critic.md         # Critic system prompt
│   │   ├── synthesizer.md    # Synthesizer system prompt
│   │   ├── peer.md           # Peer system prompt
│   │   └── arbiter.md        # Arbiter system prompt
│   │
│   └── domain/
│       ├── layout.md         # Layout domain context
│       ├── visual.md         # Visual domain context
│       ├── motion.md         # Motion domain context
│       ├── interaction.md    # Interaction domain context
│       ├── state.md          # State domain context
│       ├── performance.md    # Performance domain context
│       └── accessibility.md  # Accessibility domain context
│
├── integration/
│   ├── __init__.py
│   ├── merger.py             # Code merging logic
│   ├── validator.py          # Validation suite
│   └── renderer.py           # Test rendering
│
├── config/
│   ├── default.yaml          # Default configuration
│   └── examples/
│       ├── minimal.yaml      # Minimal 2-triad setup
│       ├── standard.yaml     # Standard 6-triad setup
│       └── comprehensive.yaml # Full 8-triad setup
│
├── cli/
│   ├── __init__.py
│   └── main.py               # CLI entry point
│
└── tests/
    ├── test_triad.py
    ├── test_spec.py
    ├── test_negotiation.py
    └── test_integration.py
```

### Key Implementation Components

#### 1. Triad Base Class

```python
# core/triad.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class TriadPreset(Enum):
    HIERARCHICAL = "hierarchical"
    DIALECTIC = "dialectic"
    CONSENSUS = "consensus"

@dataclass
class TriadConfig:
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
    position: str                    # What this triad thinks should happen
    claims: List[str]                # Sections being claimed
    proposals: Dict[str, Any]        # Content proposals for claimed sections

class Triad(ABC):
    """Base class for all triads."""
    
    def __init__(self, config: TriadConfig, llm_client: Any):
        self.config = config
        self.llm = llm_client
        self.agents = self._initialize_agents()
    
    @abstractmethod
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize the three internal agents based on preset."""
        pass
    
    @abstractmethod
    async def deliberate(self, user_request: str, spec_state: Dict) -> TriadOutput:
        """Run internal deliberation and produce unified output."""
        pass
    
    @abstractmethod
    async def negotiate(
        self, 
        section: str, 
        other_proposals: Dict[str, Any]
    ) -> str:  # "concede" | "revise" | "hold"
        """Respond to negotiation round."""
        pass
    
    @abstractmethod
    async def execute(self, frozen_spec: Dict) -> Dict[str, str]:
        """Generate code for owned sections."""
        pass
```

#### 2. Spec Manager

```python
# core/spec.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

class SectionStatus(Enum):
    UNCLAIMED = "unclaimed"
    CONTESTED = "contested"
    CLAIMED = "claimed"
    FROZEN = "frozen"

@dataclass
class Section:
    status: SectionStatus = SectionStatus.UNCLAIMED
    owner: Optional[str] = None
    claims: List[str] = field(default_factory=list)
    content: Optional[Any] = None
    proposals: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)

@dataclass
class Spec:
    temperature: float = 1.0
    round: int = 0
    status: str = "initializing"
    sections: Dict[str, Section] = field(default_factory=dict)
    
    def register_claim(self, triad_id: str, section_name: str, proposal: Any):
        """Register a triad's claim on a section."""
        section = self.sections.get(section_name, Section())
        
        if triad_id not in section.claims:
            section.claims.append(triad_id)
        
        section.proposals[triad_id] = proposal
        
        if len(section.claims) > 1:
            section.status = SectionStatus.CONTESTED
        elif len(section.claims) == 1:
            section.status = SectionStatus.CLAIMED
            section.owner = triad_id
        
        section.history.append({
            "round": self.round,
            "action": "claim",
            "by": triad_id
        })
        
        self.sections[section_name] = section
    
    def concede(self, triad_id: str, section_name: str):
        """Triad withdraws claim from section."""
        section = self.sections[section_name]
        
        if triad_id in section.claims:
            section.claims.remove(triad_id)
            del section.proposals[triad_id]
        
        if len(section.claims) == 1:
            section.status = SectionStatus.CLAIMED
            section.owner = section.claims[0]
        elif len(section.claims) == 0:
            section.status = SectionStatus.UNCLAIMED
            section.owner = None
        
        section.history.append({
            "round": self.round,
            "action": "concede",
            "by": triad_id
        })
    
    def freeze(self):
        """Freeze all sections, ending negotiation."""
        self.temperature = 0.0
        self.status = "frozen"
        
        for section in self.sections.values():
            if section.status != SectionStatus.UNCLAIMED:
                section.status = SectionStatus.FROZEN
                if section.owner and section.owner in section.proposals:
                    section.content = section.proposals[section.owner]
    
    def get_contested_sections(self) -> List[str]:
        """Return list of sections still being contested."""
        return [
            name for name, section in self.sections.items()
            if section.status == SectionStatus.CONTESTED
        ]
```

#### 3. Negotiation Engine

```python
# core/negotiation.py

from typing import Dict, List, Any
from .spec import Spec, SectionStatus
from .triad import Triad
from .arbiter import Arbiter

class NegotiationEngine:
    """Manages negotiation rounds between triads."""
    
    def __init__(
        self,
        triads: Dict[str, Triad],
        spec: Spec,
        arbiter: Arbiter,
        config: Dict[str, Any]
    ):
        self.triads = triads
        self.spec = spec
        self.arbiter = arbiter
        self.temperature_decay = config.get("temperature_decay", 0.15)
        self.max_rounds = config.get("max_negotiation_rounds", 10)
        self.escalation_threshold = config.get("escalation_threshold", 2)
        self.stuck_counters: Dict[str, int] = {}  # section -> rounds stuck
    
    async def run(self) -> Spec:
        """Run negotiation until all sections resolved or max rounds reached."""
        
        while (
            self.spec.get_contested_sections() 
            and self.spec.round < self.max_rounds
            and self.spec.temperature > 0
        ):
            await self._run_round()
            self.spec.round += 1
            self.spec.temperature = max(
                0, 
                self.spec.temperature - self.temperature_decay
            )
        
        self.spec.freeze()
        return self.spec
    
    async def _run_round(self):
        """Execute one negotiation round."""
        
        contested = self.spec.get_contested_sections()
        
        for section_name in contested:
            section = self.spec.sections[section_name]
            claimants = section.claims
            
            # Gather other proposals for each claimant
            responses = {}
            for triad_id in claimants:
                other_proposals = {
                    tid: section.proposals[tid] 
                    for tid in claimants 
                    if tid != triad_id
                }
                response = await self.triads[triad_id].negotiate(
                    section_name, 
                    other_proposals
                )
                responses[triad_id] = response
            
            # Process responses
            for triad_id, response in responses.items():
                if response == "concede":
                    self.spec.concede(triad_id, section_name)
            
            # Check if still stuck
            if section.status == SectionStatus.CONTESTED:
                self.stuck_counters[section_name] = \
                    self.stuck_counters.get(section_name, 0) + 1
                
                if self.stuck_counters[section_name] >= self.escalation_threshold:
                    await self._escalate(section_name)
    
    async def _escalate(self, section_name: str):
        """Escalate stuck negotiation to arbiter."""
        
        section = self.spec.sections[section_name]
        
        decision = await self.arbiter.resolve(
            section_name=section_name,
            claimants=section.claims,
            proposals=section.proposals,
            triads={tid: self.triads[tid] for tid in section.claims},
            spec_state=self.spec
        )
        
        # Apply arbiter decision
        if decision.type == "assign":
            winner = decision.winner
            for tid in section.claims:
                if tid != winner:
                    self.spec.concede(tid, section_name)
        
        elif decision.type == "split":
            # Create sub-sections and assign
            for sub_section, owner in decision.division.items():
                self.spec.sections[sub_section] = Section(
                    status=SectionStatus.CLAIMED,
                    owner=owner,
                    claims=[owner],
                    proposals={owner: decision.proposals.get(sub_section)}
                )
            # Remove original contested section
            del self.spec.sections[section_name]
        
        elif decision.type == "merge":
            # Use merged proposal, assign to specified triad
            section.proposals[decision.assigned_to] = decision.merged_proposal
            for tid in section.claims:
                if tid != decision.assigned_to:
                    self.spec.concede(tid, section_name)
        
        # Reset stuck counter
        self.stuck_counters[section_name] = 0
```

#### 4. Main Orchestrator

```python
# core/orchestrator.py

from typing import Dict, Any
from .config import load_config
from .triad import Triad, TriadConfig
from .spec import Spec
from .negotiation import NegotiationEngine
from .arbiter import Arbiter
from .emergent import EmergentObserver
from .integration import CodeMerger, Validator

class HFSOrchestrator:
    """Main orchestrator for the Hexagonal Frontend System."""
    
    def __init__(self, config_path: str, llm_client: Any):
        self.config = load_config(config_path)
        self.llm = llm_client
        self.triads: Dict[str, Triad] = {}
        self.spec = Spec()
        self.arbiter = Arbiter(llm_client, self.config.get("arbiter", {}))
        self.observer = EmergentObserver()
    
    async def run(self, user_request: str) -> Dict[str, Any]:
        """Execute full HFS pipeline."""
        
        # Phase 1-2: Initialize
        self._spawn_triads()
        self._initialize_spec()
        
        # Phase 3: Internal deliberation
        deliberation_results = await self._deliberate(user_request)
        
        # Phase 4: Register claims
        self._register_claims(deliberation_results)
        
        # Phase 5: Negotiation
        negotiation_engine = NegotiationEngine(
            triads=self.triads,
            spec=self.spec,
            arbiter=self.arbiter,
            config=self.config.get("pressure", {})
        )
        self.spec = await negotiation_engine.run()
        
        # Phase 6: Already frozen by negotiation engine
        
        # Phase 7: Execution
        artifacts = await self._execute()
        
        # Phase 8: Integration
        merged = CodeMerger().merge(artifacts, self.spec)
        validation = Validator().validate(merged)
        
        # Phase 9: Observe emergent properties
        emergent = self.observer.observe(
            spec=self.spec,
            artifacts=artifacts,
            merged=merged,
            validation=validation
        )
        
        return {
            "artifact": merged,
            "validation": validation,
            "emergent": emergent,
            "spec": self.spec,
            "negotiation_log": self._get_negotiation_log()
        }
    
    def _spawn_triads(self):
        """Instantiate triads from configuration."""
        from .triad_factory import create_triad
        
        for triad_config in self.config["triads"]:
            config = TriadConfig(**triad_config)
            self.triads[config.id] = create_triad(config, self.llm)
    
    def _initialize_spec(self):
        """Set up initial spec with configured sections."""
        from .spec import Section
        
        for section_name in self.config.get("sections", []):
            self.spec.sections[section_name] = Section()
    
    async def _deliberate(self, user_request: str) -> Dict[str, Any]:
        """Run internal deliberation for all triads."""
        import asyncio
        
        tasks = {
            tid: triad.deliberate(user_request, self.spec.__dict__)
            for tid, triad in self.triads.items()
        }
        
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))
    
    def _register_claims(self, deliberation_results: Dict[str, Any]):
        """Register all claims from deliberation."""
        for triad_id, output in deliberation_results.items():
            for section in output.claims:
                proposal = output.proposals.get(section)
                self.spec.register_claim(triad_id, section, proposal)
    
    async def _execute(self) -> Dict[str, Dict[str, str]]:
        """Execute code generation for all triads."""
        import asyncio
        
        tasks = {
            tid: triad.execute(self.spec.__dict__)
            for tid, triad in self.triads.items()
        }
        
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))
    
    def _get_negotiation_log(self) -> List[Dict]:
        """Compile full negotiation history."""
        log = []
        for section_name, section in self.spec.sections.items():
            for entry in section.history:
                log.append({
                    "section": section_name,
                    **entry
                })
        return sorted(log, key=lambda x: x["round"])
```

---

## Example Configurations

### Minimal Configuration (2 Triads)

```yaml
# config/examples/minimal.yaml

config:
  triads:
    - id: "design"
      preset: "dialectic"
      scope:
        primary: ["visual", "layout", "motion"]
        reach: ["interaction", "accessibility"]
      budget:
        tokens: 30000
        tool_calls: 30
        time_ms: 30000
      objectives:
        - aesthetic_quality
        - visual_coherence
        - user_delight
    
    - id: "engineering"
      preset: "hierarchical"
      scope:
        primary: ["state", "interaction", "performance"]
        reach: ["layout", "accessibility"]
      budget:
        tokens: 30000
        tool_calls: 30
        time_ms: 30000
      objectives:
        - code_quality
        - performance
        - maintainability
  
  pressure:
    initial_temperature: 1.0
    temperature_decay: 0.2
    max_negotiation_rounds: 5
    escalation_threshold: 2
  
  sections:
    - layout
    - visual
    - motion
    - interaction
    - state
    - performance
    - accessibility
  
  output:
    format: "react"
    style_system: "tailwind"
```

### Standard Configuration (6 Triads)

```yaml
# config/examples/standard.yaml

config:
  triads:
    - id: "layout"
      preset: "hierarchical"
      scope:
        primary: ["layout", "layout/grid", "layout/spacing", "layout/responsive"]
        reach: ["visual/spacing", "accessibility/structure"]
      budget:
        tokens: 15000
        tool_calls: 20
        time_ms: 15000
      objectives:
        - spatial_clarity
        - responsive_adaptability
        - structural_soundness
    
    - id: "visual"
      preset: "dialectic"
      scope:
        primary: ["visual", "visual/colors", "visual/typography", "visual/imagery"]
        reach: ["layout/spacing", "motion/aesthetics"]
      budget:
        tokens: 15000
        tool_calls: 20
        time_ms: 15000
      objectives:
        - aesthetic_quality
        - brand_alignment
        - visual_hierarchy
    
    - id: "motion"
      preset: "dialectic"
      scope:
        primary: ["motion", "motion/transitions", "motion/animations"]
        reach: ["interaction/feedback", "performance/animation"]
      budget:
        tokens: 15000
        tool_calls: 20
        time_ms: 15000
      objectives:
        - motion_quality
        - purposeful_animation
        - performance_awareness
    
    - id: "interaction"
      preset: "hierarchical"
      scope:
        primary: ["interaction", "interaction/inputs", "interaction/feedback", "interaction/navigation"]
        reach: ["state/user_input", "motion/feedback", "accessibility/keyboard"]
      budget:
        tokens: 15000
        tool_calls: 20
        time_ms: 15000
      objectives:
        - usability
        - responsiveness
        - intuitive_patterns
    
    - id: "state"
      preset: "hierarchical"
      scope:
        primary: ["state", "state/data_flow", "state/persistence"]
        reach: ["interaction/data", "performance/reactivity"]
      budget:
        tokens: 15000
        tool_calls: 20
        time_ms: 15000
      objectives:
        - data_integrity
        - predictable_flow
        - efficient_updates
    
    - id: "accessibility"
      preset: "consensus"
      scope:
        primary: ["accessibility", "accessibility/semantic", "accessibility/keyboard", "accessibility/screen_reader"]
        reach: ["layout", "visual", "interaction"]
      budget:
        tokens: 15000
        tool_calls: 20
        time_ms: 15000
      objectives:
        - wcag_compliance
        - inclusive_design
        - universal_usability
  
  pressure:
    initial_temperature: 1.0
    temperature_decay: 0.15
    max_negotiation_rounds: 7
    escalation_threshold: 2
    global_budget:
      tokens: 100000
      time_ms: 90000
    validation:
      - must_compile
      - must_render
      - accessibility_basic
      - performance_budget
  
  sections:
    - layout
    - layout/grid
    - layout/spacing
    - layout/responsive
    - visual
    - visual/colors
    - visual/typography
    - visual/imagery
    - motion
    - motion/transitions
    - motion/animations
    - interaction
    - interaction/inputs
    - interaction/feedback
    - interaction/navigation
    - state
    - state/data_flow
    - state/persistence
    - performance
    - accessibility
    - accessibility/semantic
    - accessibility/keyboard
    - accessibility/screen_reader
  
  arbiter:
    model: "claude-sonnet-4-20250514"
    max_tokens: 2000
    temperature: 0.3
  
  output:
    format: "react"
    style_system: "tailwind"
    include_emergent_report: true
    include_negotiation_log: true
```

---

## Future Considerations

### Potential Extensions

1. **Learning from Emergence**
   - Track which boundary configurations produce best results
   - Adjust default scopes based on historical patterns
   - Auto-tune pressure parameters

2. **Dynamic Triad Spawning**
   - Analyze user request to determine optimal triad count
   - Spawn specialized triads for unusual requirements
   - Merge underutilized triads mid-run

3. **Cross-Run Memory**
   - Remember successful patterns for similar requests
   - Build library of proven configurations
   - Share learnings across users/projects

4. **Real-Time Collaboration**
   - Human designer as additional "triad" in negotiation
   - Live intervention during negotiation rounds
   - Approval gates at phase transitions

5. **Specialized Domains**
   - Game development variant
   - Data visualization variant
   - Mobile-first variant
   - Design system variant

### Research Questions

1. Does hexagonal structure actually emerge, or do we get different patterns?
2. What's the optimal temperature decay rate for different complexity levels?
3. How does triad preset choice affect output quality?
4. Can we measure "coherence" reliably and automatically?
5. What's the relationship between negotiation rounds and output quality?

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **Triad** | Atomic unit of 3 sub-agents working together |
| **Preset** | Configuration template for triad internal structure |
| **Scope (Primary)** | Sections a triad owns by default |
| **Scope (Reach)** | Sections a triad can claim but doesn't own by default |
| **Spec** | Shared mutable document defining section ownership and content |
| **Temperature** | Measure of boundary malleability (1.0 = fluid, 0.0 = frozen) |
| **Pressure** | Forces that compel triads to negotiate (resource scarcity, coverage requirements) |
| **Negotiation** | Process by which triads resolve competing claims |
| **Arbiter** | External LLM that resolves deadlocked negotiations |
| **Emergent Center** | Quality properties that arise from triad interactions but aren't owned by any triad |
| **Freeze** | Point at which boundaries become permanent and execution begins |

---

*End of Design Document*