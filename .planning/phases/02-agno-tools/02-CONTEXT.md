# Phase 2: Agno Tools - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

HFS operations available as Agno tools that agents can invoke. Core tools: register_claim, negotiate_response, generate_code. Plus state query tools for agent awareness. Tools validate inputs and return structured responses.

</domain>

<decisions>
## Implementation Decisions

### Tool Input Contracts
- Strict validation — reject invalid/missing fields immediately with detailed error
- Pydantic models for input schemas with field validators
- Automatic retry on validation errors — return error to model so it can try again
- Default retry limit: 3 attempts for validation failures
- Shared state injection — tools access current spec from Team/Agent context (not explicit parameters)

### Tool Output Structure
- Pydantic models for outputs — typed, serializable, consistent with inputs
- negotiate_response returns: decision (CONCEDE/REVISE/HOLD) + metadata (round number, history summary, participants)
- generate_code returns: code only — validation happens elsewhere
- Wrapper structure: Claude's discretion based on Agno patterns

### Error Handling
- Different exception types: ValidationError triggers retry loop, RuntimeError fails immediately
- Error messages include actionable hints (e.g., "Try: provide section_id as string, not int")
- Claim conflict handling: Claude's discretion based on negotiation flow design
- Error logging: Claude's discretion based on observability phase integration

### Tool Granularity
- Include state query tools: get_current_claims(), get_negotiation_state() for agent awareness
- Negotiation tool design: Claude's discretion (one tool vs three separate)
- Module organization: Claude's discretion based on growth patterns
- LLM-optimized docstrings — written for agent understanding with clear examples and explicit constraints

### Claude's Discretion
- Output wrapper structure (consistent vs tool-specific)
- Negotiation tool split (one vs three)
- Module organization (single file vs split by domain)
- Claim conflict retryability
- Error logging strategy

</decisions>

<specifics>
## Specific Ideas

- Retry mechanism for validation errors is key — agents should self-correct on menial mistakes
- Docstrings should be optimized for LLM comprehension, not just human developers

</specifics>

<deferred>
## Deferred Ideas

- **Shared State Coordination Layer** — Markdown files as sources of truth with read/write tools that handle async locking for multi-agent collaboration. IP/done/pending markers. Queue-based edits for conflict resolution. Consider as Phase 3.5 or new Phase 4 after Agno Teams.

</deferred>

---

*Phase: 02-agno-tools*
*Context gathered: 2026-01-29*
