# Phase 7: Cleanup - Research

**Researched:** 2026-01-30
**Domain:** Code Cleanup, Test Reorganization, CLI Error Handling
**Confidence:** HIGH

## Summary

This phase removes the MockLLMClient class from the codebase and establishes proper API key requirements for HFS operation. The research focused on understanding: (1) the current MockLLMClient usage patterns, (2) test organization strategies for separating unit tests from integration tests, and (3) CLI error handling best practices for missing configuration.

The codebase currently has MockLLMClient defined in two places: `hfs/cli/main.py` (production code) and `hfs/tests/test_integration.py` (test helpers). Additionally, several test files define their own mock classes (MockTriad, MockLLM, MockArbiter) for unit testing specific components without actual LLM calls. The cleanup strategy distinguishes between "MockLLMClient" (the target for removal) and legitimate unittest.mock usage (preserved for proper unit testing).

For CLI error handling, the standard pattern is fail-fast with instructive error messages that guide users to configure API keys. The existing ProviderManager already logs warnings for missing environment variables, but the CLI needs to check provider availability before attempting pipeline execution.

**Primary recommendation:** Delete MockLLMClient from cli/main.py and test_integration.py, add CLI pre-flight checks for API key configuration, use pytest markers and conftest.py to separate unit/integration tests, and preserve unittest.mock-based tests.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | installed | Test framework | Project's existing test runner |
| unittest.mock | stdlib | Mocking for unit tests | Standard Python library, already heavily used |
| keycycle | installed | API key validation | Existing provider management |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | installed | Async test support | Testing async pipeline code |
| pytest-skip-markers | optional | Skip markers plugin | CI integration (if needed) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| conftest.py markers | pytest-optional-tests | Plugin adds dependency; conftest.py is built-in and sufficient |
| Skip by default | Run by default | Skip by default protects CI runs without secrets |

**Installation:**
No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Test Organization
```
hfs/tests/                          # Unit tests (no API keys required)
    conftest.py                     # Pytest configuration, markers
    test_config.py                  # Unit tests for config loading
    test_spec.py                    # Unit tests for spec operations
    test_negotiation.py             # Unit tests with mock triads
    test_shared_state.py            # Unit tests with mock state
    ...
tests/unit/                         # Additional unit tests
    ...

# Integration tests marked with @pytest.mark.integration
hfs/tests/test_agno_providers.py    # Real API integration tests
```

### Pattern 1: Pre-flight API Key Check
**What:** Check for available providers before attempting to run the pipeline
**When to use:** CLI entry points, before creating orchestrator
**Example:**
```python
# Source: Codebase pattern extrapolated from hfs/agno/providers.py
from hfs.agno import get_provider_manager, list_available_providers

def check_api_keys() -> tuple[bool, list[str], list[str]]:
    """Check if API keys are configured.

    Returns:
        Tuple of (has_any_keys, available_providers, missing_providers)
    """
    try:
        manager = get_provider_manager()
        available = list_available_providers()
        all_providers = ["cerebras", "groq", "gemini", "openrouter"]
        missing = [p for p in all_providers if p not in available]
        return (len(available) > 0, available, missing)
    except Exception as e:
        return (False, [], ["cerebras", "groq", "gemini", "openrouter"])
```

### Pattern 2: Graceful CLI Error Handling
**What:** Professional error messages with actionable guidance
**When to use:** When API keys are missing or invalid
**Example:**
```python
# Source: Best practices from Python CLI documentation
import sys

def cmd_run(args):
    has_keys, available, missing = check_api_keys()

    if not has_keys:
        print("Error: No API keys configured.", file=sys.stderr)
        print()
        print("HFS requires at least one LLM provider to be configured.")
        print("Set up API keys using environment variables:")
        print()
        print("  NUM_CEREBRAS=N       # Number of Cerebras keys")
        print("  CEREBRAS_API_KEY_1=  # First Cerebras key")
        print("  ...")
        print()
        print("Run 'hfs providers status' to see which providers are configured.")
        return 1

    # Continue with pipeline...
```

### Pattern 3: Pytest Marker Configuration
**What:** Configure pytest to skip integration tests by default
**When to use:** Separating unit tests from tests requiring real API keys
**Example:**
```python
# Source: https://docs.pytest.org/en/stable/example/markers.html
# conftest.py

import pytest

def pytest_addoption(parser):
    """Add --run-integration option."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require API keys",
    )

def pytest_configure(config):
    """Register integration marker."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring real API keys",
    )

def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is given."""
    if config.getoption("--run-integration"):
        # Running integration tests, don't skip
        return

    skip_integration = pytest.mark.skip(
        reason="Need --run-integration option to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
```

### Anti-Patterns to Avoid
- **Deleting unittest.mock usage:** Keep Mock, MagicMock, AsyncMock, patch - these are standard testing tools, not the MockLLMClient
- **Requiring API keys for ALL tests:** Unit tests should work without any API keys
- **Silent failures:** Always explain what went wrong and how to fix it
- **Partial execution with missing keys:** Fail fast, don't attempt to run with incomplete configuration

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Provider status checking | Custom env var checks | ProviderManager.is_provider_healthy() | Already validates and tracks status |
| Test skip logic | Custom decorators | pytest.mark.skip + conftest hooks | Standard pytest pattern |
| Model factory validation | Custom initialization | get_provider_manager() | Handles all error cases |
| Environment validation | Manual os.getenv checks | ProviderManager._validate_environment() | Already implemented, logs warnings |

**Key insight:** The ProviderManager already has comprehensive environment validation. The CLI just needs to surface this information to users with clear error messages.

## Common Pitfalls

### Pitfall 1: Deleting Wrong Mock Classes
**What goes wrong:** Removing unittest.mock usage breaks legitimate unit tests
**Why it happens:** Confusion between MockLLMClient (target) and unittest.mock (standard tool)
**How to avoid:** Only remove classes literally named "MockLLMClient" from cli/main.py and test_integration.py. Keep all unittest.mock imports and Mock/MagicMock/AsyncMock/patch usage.
**Warning signs:** Unit tests fail with "Mock not defined" or similar import errors

### Pitfall 2: Breaking Unit Test Isolation
**What goes wrong:** Unit tests start requiring API keys after cleanup
**Why it happens:** Test files that used MockLLMClient now have no mock at all
**How to avoid:** Replace MockLLMClient with unittest.mock.Mock or MagicMock. Unit tests should never need real API keys.
**Warning signs:** Tests fail when run without environment variables

### Pitfall 3: CLI Blocks Useful Commands
**What goes wrong:** Commands like `hfs list-presets` fail when API keys are missing
**Why it happens:** Pre-flight check is too aggressive, runs for ALL commands
**How to avoid:** Only check API keys for commands that need them (`hfs run`). Commands like `validate-config`, `list-presets` don't need API keys.
**Warning signs:** Users can't explore the CLI without setting up keys first

### Pitfall 4: CI Pipeline Fails on Integration Tests
**What goes wrong:** CI runs integration tests and fails due to missing secrets
**Why it happens:** Default pytest behavior runs all tests
**How to avoid:** Use conftest.py to skip integration tests by default. CI only runs `pytest` without `--run-integration` flag.
**Warning signs:** CI logs show "missing API key" errors

### Pitfall 5: Incomplete Error Messages
**What goes wrong:** Users don't know which specific keys are missing
**Why it happens:** Generic "missing API keys" message without details
**How to avoid:** List specifically which providers are configured vs missing, using ProviderManager.environment_status
**Warning signs:** Users have to grep code to figure out what env vars to set

## Code Examples

Verified patterns from official sources and codebase analysis:

### CLI Pre-flight Check for API Keys
```python
# Source: Derived from hfs/agno/providers.py ProviderManager
import sys
from hfs.agno import get_provider_manager, list_available_providers

def check_providers_or_exit():
    """Check API key configuration and exit with helpful message if missing."""
    try:
        manager = get_provider_manager()
        available = manager.available_providers
        status = manager.environment_status

        if not available:
            print("Error: No API keys configured.", file=sys.stderr)
            print()
            print("HFS requires at least one LLM provider. Configure using environment variables:")
            print()
            for provider, info in status.items():
                configured = "OK" if info["configured"] else "MISSING"
                print(f"  {provider.upper()}: {configured}")
                if not info["configured"]:
                    print(f"    Set NUM_{provider.upper()} and {provider.upper()}_API_KEY_1..N")
            print()
            print("See docs/KEYCYCLE.md for detailed setup instructions.")
            sys.exit(1)

        return manager
    except Exception as e:
        print(f"Error: Failed to initialize providers: {e}", file=sys.stderr)
        sys.exit(1)
```

### Test File Pattern After Cleanup
```python
# Source: Derived from existing test patterns in hfs/tests/
"""Unit tests that don't require API keys."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from hfs.core.orchestrator import HFSOrchestrator, HFSResult


@pytest.fixture
def mock_model():
    """Create a mock model for testing without API calls."""
    model = Mock()
    model.id = "mock-model"
    return model


@pytest.fixture
def mock_spec():
    """Create a mock Spec for testing."""
    spec = Mock()
    spec.sections = {}
    spec.temperature = 1.0
    spec.is_frozen = Mock(return_value=False)
    return spec


class TestOrchestratorInit:
    """Tests for orchestrator initialization - no API keys needed."""

    def test_requires_config(self):
        """Verify initialization fails without config."""
        with pytest.raises(ValueError):
            HFSOrchestrator()  # No config
```

### Integration Test with Marker
```python
# Source: https://docs.pytest.org/en/stable/example/markers.html
"""Integration tests requiring real API keys."""

import os
import pytest
from hfs.agno import get_model, list_available_providers


@pytest.mark.integration
class TestRealProviders:
    """Integration tests that require real API keys.

    Run with: pytest --run-integration
    Skip with: pytest (default, no flag)
    """

    @pytest.fixture(autouse=True)
    def check_env(self):
        """Skip if no providers are available."""
        available = list_available_providers()
        if not available:
            pytest.skip("No API keys configured")

    def test_model_responds(self):
        """Real model can respond to a prompt."""
        from agno.agent import Agent

        provider, model = get_any_model()
        agent = Agent(model=model, instructions="Say OK")
        response = agent.run("Hello")
        assert response is not None
```

### conftest.py for Test Organization
```python
# Source: https://docs.pytest.org/en/stable/example/markers.html
"""Pytest configuration for HFS tests.

This file configures:
- Integration test markers
- Skip integration tests by default (need --run-integration)
- Smoke test markers for quick health checks
"""

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require API keys",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring real API keys (deselected by default)",
    )
    config.addinivalue_line(
        "markers",
        "smoke: mark test as smoke test (quick health check with real APIs)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested."""
    if config.getoption("--run-integration"):
        # --run-integration given, don't skip
        return

    skip_integration = pytest.mark.skip(
        reason="Need --run-integration option to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MockLLMClient in production code | Real API keys required | This phase | Cleaner production code |
| Mock tests mixed with integration | pytest markers for separation | This phase | CI-friendly test runs |
| Silent fallback to mocks | Explicit error messages | This phase | Users know what's missing |
| Tests inherit mocks from main.py | Tests use unittest.mock directly | This phase | Proper test isolation |

**Deprecated/outdated:**
- MockLLMClient class: Being removed entirely
- Implicit mock fallback in CLI: Replaced with explicit checks

## Open Questions

Things that couldn't be fully resolved:

1. **Smoke Test Implementation**
   - What we know: CONTEXT.md mentions `hfs check` or `pytest -m smoke` for quick verification
   - What's unclear: Exact implementation of smoke test (CLI command vs pytest marker)
   - Recommendation: Implement as pytest marker for now, add CLI command if needed later

2. **CI Secrets Configuration**
   - What we know: Integration tests should be skippable in CI without secrets
   - What's unclear: Specific CI platform (GitHub Actions, etc.) and secrets configuration
   - Recommendation: Skip by default, document how to configure secrets for full test runs

3. **Health Check Command Location**
   - What we know: Users want a way to verify API keys work
   - What's unclear: Should it be `hfs check`, `hfs providers status`, or both?
   - Recommendation: Add `hfs providers status` command that shows configuration and optionally tests connectivity

## Sources

### Primary (HIGH confidence)
- Codebase examination: `hfs/cli/main.py`, `hfs/tests/test_integration.py`, `hfs/agno/providers.py`
- [pytest markers documentation](https://docs.pytest.org/en/stable/example/markers.html) - Official pytest docs
- [pytest skip/xfail documentation](https://docs.pytest.org/en/stable/how-to/skipping.html) - Official pytest docs

### Secondary (MEDIUM confidence)
- Phase 07 CONTEXT.md - User decisions for implementation approach
- Prior phase research (01-RESEARCH.md) - Provider initialization patterns

### Tertiary (LOW confidence)
- WebSearch results for CLI error handling - General best practices, not HFS-specific

## Metadata

**Confidence breakdown:**
- MockLLMClient removal: HIGH - Direct codebase examination confirms locations and usage
- Test organization: HIGH - pytest documentation is authoritative, pattern matches existing code
- CLI error handling: MEDIUM - Derived from best practices and existing ProviderManager

**Research date:** 2026-01-30
**Valid until:** 90 days (stable patterns, no external dependencies)
