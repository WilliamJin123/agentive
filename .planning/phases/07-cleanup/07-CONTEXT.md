# Phase 7: Cleanup - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove MockLLMClient and enforce real API key requirements. HFS CLI fails gracefully with clear errors when API keys are missing. All tests either use real APIs or are marked as integration tests.

</domain>

<decisions>
## Implementation Decisions

### Error Messaging
- Instructive errors: list which providers need keys, show env var names, example setup commands
- Warn but don't run when keys missing — don't attempt partial execution
- Professional/neutral tone: "Error: No API keys configured. Run `hfs providers status` to see which providers are configured."
- Suggest command for next steps (e.g., `hfs providers status`)

### Test Strategy
- Delete tests that only test mock behavior — they're not valuable without the mock
- Keep unit tests that don't need LLM calls (parsing, validation, config, etc.)
- Add health check command: `hfs check` or `pytest -m smoke` that makes one real API call to verify keys work

### Deprecation Approach
- Delete MockLLMClient immediately — no deprecation period, it's internal tooling
- Audit and clean all mock/stub utilities — evaluate each for removal
- Standard commit messages — clear explanation of what was removed and why

### Claude's Discretion
- CI handling of integration tests (skip by default vs. secrets configured)
- Documentation updates where they make sense
- Specific mock utilities to remove during audit

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-cleanup*
*Context gathered: 2026-01-30*
