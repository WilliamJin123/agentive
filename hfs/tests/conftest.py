"""Pytest configuration for HFS tests.

This file configures:
- Integration test markers (skip by default)
- Smoke test markers for quick health checks
- Common fixtures for test isolation

Run integration tests with: pytest --run-integration
Run unit tests only with: pytest (default)
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
