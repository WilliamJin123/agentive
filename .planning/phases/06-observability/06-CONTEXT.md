# Phase 6: Observability - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Full visibility into HFS agent runs, token usage, and phase timing via custom OpenTelemetry instrumentation. Tracing captures the hierarchy from run down to individual agents with rich attributes. Token counts and timing metrics exposed via OTel APIs.

</domain>

<decisions>
## Implementation Decisions

### Trace Structure
- Full custom OpenTelemetry (not Agno's setup_tracing)
- 4-level span hierarchy: Run → Phase → Triad → Agent
- Rich span attributes including:
  - IDs: run_id, phase, triad_id, agent_role
  - Status: success/error, duration
  - Model info: model name, provider, tier used, tokens
  - Context: phase goal summary, triad type, agent prompt snippet (truncated)

### Token Tracking
- Capture from LLM API response metadata (usage.prompt_tokens, usage.completion_tokens)
- Track at per-agent granularity
- Report via span attributes only (no console summary)
- Separate prompt_tokens and completion_tokens attributes

### Output Destinations
- Console exporter as default (development-friendly)
- OTLP endpoint configurable via OTEL_EXPORTER_OTLP_ENDPOINT env var
- Console verbosity configurable with logging-style levels (e.g., minimal/standard/verbose)

### Metric Granularity
- Timing at all levels: phase, triad, and agent
- Separate success/failure counters for error rate analysis
- Expose via both span attributes AND OTel metrics API (histograms, counters)
- LLM-appropriate latency buckets: 100ms, 500ms, 1s, 2s, 5s, 10s, 30s, 60s

### Claude's Discretion
- Exact span naming convention (e.g., "hfs.run.deliberation.hierarchical.orchestrator")
- How to truncate prompt snippets for context attribute
- Whether to use BatchSpanProcessor or SimpleSpanProcessor
- Meter naming and metric unit conventions

</decisions>

<specifics>
## Specific Ideas

- Console verbosity should feel like logging levels — configurable modes for different debugging needs
- Latency buckets tuned for LLM calls which can take up to 60s

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-observability*
*Context gathered: 2026-01-30*
