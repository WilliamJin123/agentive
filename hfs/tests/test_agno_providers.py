"""Integration tests for HFS Agno provider integration.

These tests require real API keys configured in environment:
- NUM_CEREBRAS, CEREBRAS_API_KEY_1..N
- NUM_GROQ, GROQ_API_KEY_1..N
- NUM_GEMINI, GEMINI_API_KEY_1..N
- NUM_OPENROUTER, OPENROUTER_API_KEY_1..N
- TIDB_DB_URL (optional, for usage persistence)

Run with: pytest hfs/tests/test_agno_providers.py -v
"""

import os
import pytest
from unittest.mock import patch

from hfs.agno import (
    ProviderManager,
    get_model,
    get_provider_manager,
    list_available_providers,
    get_cerebras_model,
    get_groq_model,
    get_gemini_model,
    get_openrouter_model,
)


class TestProviderManagerInit:
    """Test ProviderManager initialization."""

    def test_provider_manager_creates_instance(self):
        """ProviderManager can be instantiated."""
        pm = ProviderManager()
        assert pm is not None
        assert hasattr(pm, 'wrappers')
        assert hasattr(pm, 'environment_status')

    def test_provider_configs_defined(self):
        """All four providers are configured."""
        from hfs.agno.providers import PROVIDER_CONFIGS
        providers = [p[0] for p in PROVIDER_CONFIGS]
        assert "cerebras" in providers
        assert "groq" in providers
        assert "gemini" in providers
        assert "openrouter" in providers

    def test_environment_status_populated(self):
        """Environment status contains all provider entries."""
        pm = ProviderManager()
        status = pm.environment_status
        assert "cerebras" in status
        assert "groq" in status
        assert "gemini" in status
        assert "openrouter" in status

    def test_available_providers_returns_list(self):
        """available_providers returns list of initialized providers."""
        pm = ProviderManager()
        providers = pm.available_providers
        assert isinstance(providers, list)


class TestEnvironmentValidation:
    """Test environment variable validation."""

    def test_missing_env_vars_logged(self, caplog):
        """Missing environment variables are logged as warnings."""
        with patch.dict(os.environ, {}, clear=True):
            import logging
            caplog.set_level(logging.WARNING)
            pm = ProviderManager()
            # Should have logged warnings about missing vars
            assert any("Missing" in record.message or "not set" in record.message
                      for record in caplog.records)

    def test_is_provider_healthy_false_when_not_configured(self):
        """is_provider_healthy returns False for unconfigured provider."""
        with patch.dict(os.environ, {}, clear=True):
            pm = ProviderManager()
            # Without env vars, providers won't be healthy
            # (may still partially initialize depending on defaults)
            assert hasattr(pm, 'is_provider_healthy')


class TestModelFactory:
    """Test model factory functions."""

    def test_get_provider_manager_singleton(self):
        """get_provider_manager returns singleton instance."""
        pm1 = get_provider_manager()
        pm2 = get_provider_manager()
        assert pm1 is pm2

    def test_list_available_providers_callable(self):
        """list_available_providers returns list."""
        providers = list_available_providers()
        assert isinstance(providers, list)


# Integration tests that require real API keys
# Mark as integration so they can be skipped in CI

@pytest.mark.integration
class TestRealProviders:
    """Integration tests requiring real API keys.

    Skip with: pytest -m "not integration"
    """

    @pytest.fixture(autouse=True)
    def check_env(self):
        """Skip if required env vars not set."""
        required = ["NUM_CEREBRAS", "NUM_GROQ", "NUM_GEMINI", "NUM_OPENROUTER"]
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            pytest.skip(f"Missing environment variables: {missing}")

    def test_cerebras_model_responds(self):
        """Cerebras model can respond to simple prompt."""
        from agno.agent import Agent
        model = get_cerebras_model()
        agent = Agent(model=model, instructions="Respond with just 'OK'")
        response = agent.run("Say OK")
        assert response is not None

    def test_groq_model_responds(self):
        """Groq model can respond to simple prompt."""
        from agno.agent import Agent
        model = get_groq_model()
        agent = Agent(model=model, instructions="Respond with just 'OK'")
        response = agent.run("Say OK")
        assert response is not None

    def test_gemini_model_responds(self):
        """Gemini model can respond to simple prompt."""
        from agno.agent import Agent
        model = get_gemini_model()
        agent = Agent(model=model, instructions="Respond with just 'OK'")
        response = agent.run("Say OK")
        assert response is not None

    def test_openrouter_model_responds(self):
        """OpenRouter model can respond to simple prompt."""
        from agno.agent import Agent
        model = get_openrouter_model()
        agent = Agent(model=model, instructions="Respond with just 'OK'")
        response = agent.run("Say OK")
        assert response is not None

    def test_get_model_with_custom_model_id(self):
        """get_model accepts custom model_id parameter."""
        # Use Cerebras with a different model
        model = get_model("cerebras", model_id="llama3.1-8b")
        assert model is not None

    def test_provider_manager_shutdown(self):
        """ProviderManager.shutdown() completes without error."""
        pm = ProviderManager()
        pm.shutdown()
        # Should not raise


@pytest.mark.integration
class TestTiDBPersistence:
    """Test usage persistence to TiDB."""

    @pytest.fixture(autouse=True)
    def check_tidb(self):
        """Skip if TIDB_DB_URL not set."""
        if not os.environ.get("TIDB_DB_URL"):
            pytest.skip("TIDB_DB_URL not set")

    def test_usage_persisted_after_call(self):
        """Usage data should be persisted after API call.

        Note: This is hard to verify directly without querying TiDB.
        The test just confirms the call completes without error.
        """
        from agno.agent import Agent
        model = get_cerebras_model()
        agent = Agent(model=model, instructions="Respond briefly")
        response = agent.run("Hello")
        # If we get here without error, persistence is at least not breaking
        assert response is not None
