"""Tests for HFS AgnoTriad OpenTelemetry instrumentation.

This module tests:
- Triad span "hfs.triad.{id}" is created for triad execution
- Triad spans have required attributes (id, type, phase, prompt_snippet, duration_s, success)
- Token usage is extracted and recorded as span attributes
- Error handling via record_exception and set_status(ERROR)
- Agent span helper method _create_agent_span_context works correctly
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

import hfs.agno.teams.base as base_module


# Module-level setup - configure OTel once for all tests
_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


@pytest.fixture
def span_exporter():
    """Provide the shared in-memory span exporter for tests.

    Clears spans before each test to ensure isolation, and resets
    the module-level tracer to force re-initialization.
    """
    # Clear any spans from previous tests
    _exporter.clear()

    # Reset module-level tracer so it picks up the provider
    base_module._tracer = None
    base_module._meter = None
    base_module._triad_duration = None
    base_module._agent_duration = None
    base_module._tokens_prompt = None
    base_module._tokens_completion = None

    yield _exporter

    # Clear after test
    _exporter.clear()


@pytest.fixture
def mock_model_selector():
    """Mock ModelSelector for testing without real provider setup."""
    selector = Mock()
    selector.get_model.return_value = Mock()  # Mock Agno model
    selector.get_current_tier.return_value = "general"
    return selector


@pytest.fixture
def mock_spec():
    """Mock Spec for testing without real spec implementation."""
    spec = Mock()
    spec.sections = {}
    return spec


@pytest.fixture
def triad_config():
    """Standard TriadConfig for testing."""
    from hfs.core.triad import TriadConfig, TriadPreset
    return TriadConfig(
        id="test-triad",
        preset=TriadPreset.HIERARCHICAL,
        scope_primary=["header"],
        scope_reach=[],
        budget_tokens=10000,
        budget_tool_calls=20,
        budget_time_ms=15000,
        objectives=["Test objective"],
    )


def create_mock_agent(**kwargs):
    """Create a mock Agent with the provided kwargs as attributes."""
    agent = Mock()
    for key, value in kwargs.items():
        setattr(agent, key, value)
    return agent


class TestTriadSpanCreation:
    """Tests for triad span creation during execution."""

    @pytest.mark.asyncio
    async def test_triad_span_created(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that triad execution creates triad span 'hfs.triad.{id}'."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        # Patch Agent and Team to avoid actual Agno initialization
        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            # Configure mock team
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value="test response")
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_spans = [s for s in spans if s.name.startswith("hfs.triad.")]
        assert len(triad_spans) >= 1
        assert triad_spans[0].attributes.get("hfs.triad.id") == "test-triad"

    @pytest.mark.asyncio
    async def test_triad_span_attributes(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that triad spans have all required attributes."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value="response")
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        # Check all required attributes
        assert "hfs.triad.id" in triad_span.attributes
        assert "hfs.triad.type" in triad_span.attributes
        assert "hfs.triad.phase" in triad_span.attributes
        assert "hfs.triad.prompt_snippet" in triad_span.attributes
        assert "hfs.triad.duration_s" in triad_span.attributes
        assert "hfs.triad.success" in triad_span.attributes
        assert "hfs.triad.agent_roles" in triad_span.attributes

        # Verify correct values
        assert triad_span.attributes["hfs.triad.id"] == "test-triad"
        assert triad_span.attributes["hfs.triad.type"] == "hierarchical"
        assert triad_span.attributes["hfs.triad.phase"] == "deliberation"
        assert triad_span.attributes["hfs.triad.success"] is True
        assert triad_span.attributes["hfs.triad.duration_s"] >= 0

    @pytest.mark.asyncio
    async def test_triad_span_has_agent_roles(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that triad span includes agent roles list."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value="response")
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        agent_roles = triad_span.attributes.get("hfs.triad.agent_roles")
        assert agent_roles is not None
        # Hierarchical triad has orchestrator, worker_a, worker_b
        assert "orchestrator" in agent_roles
        assert "worker_a" in agent_roles
        assert "worker_b" in agent_roles

    @pytest.mark.asyncio
    async def test_triad_span_has_tier_from_model_selector(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that triad span includes tier from model_selector."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        # Mock model_selector to return a tier
        mock_model_selector.get_current_tier.return_value = "reasoning"

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value="response")
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        assert triad_span.attributes.get("hfs.triad.tier") == "reasoning"


class TestTokenUsageRecording:
    """Tests for token usage extraction and recording."""

    @pytest.mark.asyncio
    async def test_token_usage_recorded_from_response_usage(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that token usage is extracted from response.usage."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        # Mock response with usage data
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value=mock_response)
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        # Token attributes should be set
        assert triad_span.attributes.get("hfs.tokens.prompt") == 100
        assert triad_span.attributes.get("hfs.tokens.completion") == 50
        assert triad_span.attributes.get("hfs.tokens.total") == 150

    @pytest.mark.asyncio
    async def test_token_usage_recorded_from_messages(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that token usage is extracted from response.messages[-1].usage."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        # Mock response with usage in last message
        mock_response = Mock()
        mock_response.usage = None
        last_msg = Mock()
        last_msg.usage = Mock()
        last_msg.usage.prompt_tokens = 200
        last_msg.usage.completion_tokens = 75
        mock_response.messages = [last_msg]

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value=mock_response)
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        assert triad_span.attributes.get("hfs.tokens.prompt") == 200
        assert triad_span.attributes.get("hfs.tokens.completion") == 75
        assert triad_span.attributes.get("hfs.tokens.total") == 275

    @pytest.mark.asyncio
    async def test_no_token_usage_when_not_available(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that missing token usage is handled gracefully."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        # Simple string response without usage data
        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value="simple string response")
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)
            await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        # Token attributes should not be set (or be 0/None)
        assert triad_span.attributes.get("hfs.tokens.prompt") is None
        assert triad_span.attributes.get("hfs.tokens.completion") is None


class TestErrorHandling:
    """Tests for error handling and span status."""

    @pytest.mark.asyncio
    async def test_error_creates_error_span(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that errors set span status to ERROR and record exception."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad
        from hfs.agno.teams.schemas import TriadExecutionError

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(side_effect=RuntimeError("Test error"))
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)

            with pytest.raises(TriadExecutionError):
                await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        assert triad_span.attributes.get("hfs.triad.success") is False
        assert triad_span.status.status_code == StatusCode.ERROR
        # Duration should still be recorded
        assert triad_span.attributes.get("hfs.triad.duration_s") is not None

    @pytest.mark.asyncio
    async def test_error_span_has_duration(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that duration is recorded even on error."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad
        from hfs.agno.teams.schemas import TriadExecutionError

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(side_effect=ValueError("Failure"))
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)

            with pytest.raises(TriadExecutionError):
                await triad.deliberate("test request", {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        assert triad_span.attributes.get("hfs.triad.duration_s") >= 0


class TestAgentSpanHelper:
    """Tests for the _create_agent_span_context helper method."""

    def test_agent_span_context_manager(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that _create_agent_span_context creates proper agent span."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            MockTeam.return_value = MagicMock()

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)

            # Use the agent span context manager directly
            with triad._create_agent_span_context("orchestrator", model_name="gpt-4", provider="openai"):
                pass  # Simulate agent work

        spans = span_exporter.get_finished_spans()
        agent_spans = [s for s in spans if s.name.startswith("hfs.agent.")]
        assert len(agent_spans) >= 1

        agent_span = agent_spans[0]
        assert agent_span.attributes.get("hfs.agent.role") == "orchestrator"
        assert agent_span.attributes.get("hfs.agent.model") == "gpt-4"
        assert agent_span.attributes.get("hfs.agent.provider") == "openai"
        assert agent_span.attributes.get("hfs.agent.triad_id") == "test-triad"
        assert agent_span.attributes.get("hfs.agent.success") is True

    def test_agent_span_records_duration(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that agent span records duration."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            MockTeam.return_value = MagicMock()

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)

            with triad._create_agent_span_context("worker_a"):
                import time
                time.sleep(0.01)  # Small delay

        spans = span_exporter.get_finished_spans()
        agent_span = [s for s in spans if s.name.startswith("hfs.agent.")][0]

        assert agent_span.attributes.get("hfs.agent.duration_s") >= 0.01

    def test_agent_span_error_handling(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that agent span handles errors correctly."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            MockTeam.return_value = MagicMock()

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)

            with pytest.raises(RuntimeError):
                with triad._create_agent_span_context("worker_b"):
                    raise RuntimeError("Agent error")

        spans = span_exporter.get_finished_spans()
        agent_span = [s for s in spans if s.name.startswith("hfs.agent.")][0]

        assert agent_span.attributes.get("hfs.agent.success") is False
        assert agent_span.status.status_code == StatusCode.ERROR
        assert agent_span.attributes.get("hfs.agent.duration_s") is not None


class TestPromptTruncation:
    """Tests for prompt snippet truncation in span attributes."""

    @pytest.mark.asyncio
    async def test_prompt_snippet_truncated(self, span_exporter, mock_model_selector, mock_spec, triad_config):
        """Test that long prompts are truncated in span attributes."""
        from hfs.agno.teams.hierarchical import HierarchicalAgnoTriad

        with patch("hfs.agno.teams.hierarchical.Team") as MockTeam, \
             patch("hfs.agno.teams.hierarchical.Agent", side_effect=create_mock_agent):
            mock_team_instance = MagicMock()
            mock_team_instance.arun = AsyncMock(return_value="response")
            MockTeam.return_value = mock_team_instance

            triad = HierarchicalAgnoTriad(triad_config, mock_model_selector, mock_spec)

            # Long request that will generate long prompt
            long_request = "A" * 500

            await triad.deliberate(long_request, {"sections": {}})

        spans = span_exporter.get_finished_spans()
        triad_span = [s for s in spans if s.name.startswith("hfs.triad.")][0]

        prompt_snippet = triad_span.attributes.get("hfs.triad.prompt_snippet")
        assert prompt_snippet is not None
        # truncate_prompt has default max_length of 200
        assert len(prompt_snippet) <= 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
