---
phase: 07-cleanup
plan: 02
subsystem: cli
tags: [pytest, integration-tests, api-keys, cli]

# Dependency graph
requires:
  - phase: 01-agno-integration
    provides: ProviderManager and get_provider_manager()
provides:
  - CLI pre-flight API key check for graceful failure
  - Pytest conftest.py with integration marker support
  - --run-integration flag for running API-dependent tests
affects: [testing, ci-cd, developer-experience]

# Tech tracking
tech-stack:
  added: []
  patterns: [pre-flight-validation, pytest-markers]

key-files:
  created:
    - hfs/tests/conftest.py
  modified:
    - hfs/cli/main.py

key-decisions:
  - "Only cmd_run needs API key check - other commands work without keys"
  - "Integration tests skip by default, require --run-integration flag"

patterns-established:
  - "CLI pre-flight validation: check_providers_or_exit() before expensive operations"
  - "Pytest marker convention: @pytest.mark.integration for API-dependent tests"

# Metrics
duration: 5min
completed: 2026-01-30
---

# Phase 07 Plan 02: CLI Pre-flight Check and Pytest Integration Marker Summary

**CLI graceful failure with check_providers_or_exit() and pytest conftest.py with --run-integration flag**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-30T18:30:00Z
- **Completed:** 2026-01-30T18:35:00Z
- **Tasks:** 2
- **Files modified:** 1 created, 1 modified

## Accomplishments

- Added check_providers_or_exit() function for graceful API key validation
- CLI run command now fails with actionable error message when no providers configured
- Other CLI commands (list-presets, validate-config) continue to work without API keys
- Created conftest.py with --run-integration flag for pytest
- Integration tests skip by default, can be enabled with --run-integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CLI pre-flight API key check** - `b02baac` (feat)
2. **Task 2: Create pytest conftest.py with integration marker** - `cbec0c8` (feat)

## Files Created/Modified

- `hfs/cli/main.py` - Added check_providers_or_exit() and updated cmd_run() to use it
- `hfs/tests/conftest.py` - Pytest configuration with integration marker support

## Decisions Made

- **Only cmd_run checks for API keys:** Other commands like list-presets and validate-config are useful for testing without API keys configured
- **Integration marker approach:** Use pytest markers instead of skip decorators for cleaner separation of unit vs integration tests
- **Smoke marker registered:** Future support for quick health checks with real APIs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CLI now has graceful failure for API key validation
- Pytest test suite separates unit and integration tests cleanly
- Ready for CI/CD integration where unit tests run without API keys

---
*Phase: 07-cleanup*
*Completed: 2026-01-30*
