# Phase 5: Model Tiers - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Role-based model selection with adaptive escalation. Config-driven system that chooses which models run for different agent roles, with permanent config evolution when failures accumulate. Dynamic task splitting belongs in a future orchestration phase.

</domain>

<decisions>
## Implementation Decisions

### Tier Structure
- 3 tiers: "reasoning" (highest capability), "general" (balanced), "fast" (speed-optimized)
- Capability-based distinction — tiers represent reasoning power, not cost or speed directly
- Descriptive names in config (reasoning, general, fast) for self-documenting YAML
- Provider-specific with multiple models per tier — each tier lists models per provider to handle inconsistent model IDs (e.g., Cerebras uses `gpt-oss-120b`, Groq uses `openai/gpt-oss-120b`)

### Role Mapping
- Orchestrator roles default to reasoning tier (highest)
- Worker roles default to general tier (middle) — need capability for code gen and analysis
- Code execution (generate_code tool) always uses fast tier — Cerebras GLM-4.7 or OSS-120b per roadmap
- Dialectic triad role mapping: Claude's discretion based on role responsibilities

### Escalation Triggers
- Both tool execution failures and task completion failures contribute to escalation
- 3 consecutive failures for same role/task triggers permanent config update
- Escalation is permanent config evolution, not temporary retry — failures "self-improve" the config
- No de-escalation — once upgraded, stays upgraded to avoid oscillation
- At highest tier: log warning, propagate failure up — let higher-level orchestration handle it

### Claude's Discretion
- Dialectic triad role-to-tier mapping (proposer, critic, synthesizer)
- Consensus triad peer tier assignment
- Exact retry logic before escalation (within the 3-failure window)
- Config file location and validation approach

</decisions>

<specifics>
## Specific Ideas

- Tiers should handle provider model ID inconsistency explicitly — same conceptual model has different IDs across providers
- Escalation should modify the actual config file, not just runtime state — permanent learning

</specifics>

<deferred>
## Deferred Ideas

- Dynamic task splitting when top-tier models fail — adjust scope via claims/sectioning system (future orchestration phase)

</deferred>

---

*Phase: 05-model-tiers*
*Context gathered: 2026-01-29*
