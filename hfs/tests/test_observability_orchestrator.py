"""Tests for HFS Orchestrator OpenTelemetry instrumentation.

This module tests:
- Root span "hfs.run" is created for pipeline execution
- All 9 phase spans are created with correct names
- Phase spans have required attributes (name, duration_s, success)
- Span hierarchy (phase spans are children of run span)
- Error handling via record_exception and set_status
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from hfs.core.orchestrator import HFSOrchestrator, HFSResult
import hfs.core.orchestrator as orchestrator_module


# Module-level setup - configure OTel once for all tests
_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


# Test fixtures

@pytest.fixture
def span_exporter():
    """Provide the shared in-memory span exporter for tests.

    Clears spans before each test to ensure isolation, and resets
    the module-level tracer to force re-initialization.
    """
    # Clear any spans from previous tests
    _exporter.clear()

    # Reset module-level tracer so it picks up the provider
    orchestrator_module._tracer = None
    orchestrator_module._meter = None
    orchestrator_module._phase_duration = None
    orchestrator_module._phase_success = None
    orchestrator_module._phase_failure = None

    yield _exporter

    # Clear after test
    _exporter.clear()


@pytest.fixture
def mock_config():
    """Minimal valid configuration for orchestrator testing."""
    return {
        "triads": [
            {
                "id": "test-triad",
                "preset": "hierarchical",
                "scope": {"primary": ["layout"], "reach": []},
                "budget": {"tokens": 10000, "tool_calls": 20, "time_ms": 15000},
                "objectives": ["quality"],
            }
        ],
        "sections": ["layout", "visual"],
        "pressure": {
            "initial_temperature": 1.0,
            "temperature_decay": 0.15,
            "max_negotiation_rounds": 3,
            "escalation_threshold": 2,
            "freeze_threshold": 0.1,
        },
        "arbiter": {
            "model": "test-model",
            "max_tokens": 1000,
            "temperature": 0.0,
        },
        "output": {
            "format": "react",
            "style_system": "tailwind",
        },
    }


class MockLLM:
    """Mock LLM client for orchestrator tests."""

    def __init__(self):
        self.calls = []

    async def create_message(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": "Mock response"}


class MockTriad:
    """Mock triad for testing orchestrator phases without real LLM calls."""

    def __init__(self, config, llm):
        self.config = config
        self.llm = llm
        self.deliberate_called = False
        self.negotiate_called = False
        self.execute_called = False

    async def deliberate(self, user_request, spec_state):
        self.deliberate_called = True
        # Return a mock TriadOutput-like dict
        from hfs.core.triad import TriadOutput
        return TriadOutput(
            position="Mock position",
            claims=["layout"],
            proposals={"layout": {"type": "grid"}},
        )

    async def negotiate(self, section, round_num, temperature, other_proposals):
        self.negotiate_called = True
        return ("concede", None)

    async def execute(self, frozen_spec):
        self.execute_called = True
        return {"layout": "<div>Mock code</div>"}


class TestOrchestratorTracing:
    """Tests for orchestrator OpenTelemetry tracing."""

    @pytest.mark.asyncio
    async def test_run_creates_root_span(self, span_exporter, mock_config):
        """Test that run() creates root span 'hfs.run' with run_id attribute."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        # Patch _spawn_triads to use MockTriad
        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            result = await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()
        run_spans = [s for s in spans if s.name == "hfs.run"]

        assert len(run_spans) == 1, "Expected exactly one hfs.run span"
        assert run_spans[0].attributes.get("hfs.run.id") is not None
        assert run_spans[0].attributes.get("hfs.run.request_summary") == "test request"
        assert run_spans[0].attributes.get("hfs.run.triad_count") == 1

    @pytest.mark.asyncio
    async def test_all_phase_spans_created(self, span_exporter, mock_config):
        """Test that all 9 phase spans are created during run()."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()

        # All 9 phase names should be present
        phase_names = {
            "input", "spawn", "deliberation", "claims", "negotiation",
            "freeze", "execution", "integration", "output"
        }
        found_phases = set()
        for span in spans:
            if span.name.startswith("hfs.phase."):
                phase = span.name.replace("hfs.phase.", "")
                found_phases.add(phase)

        assert found_phases == phase_names, f"Missing phases: {phase_names - found_phases}"

    @pytest.mark.asyncio
    async def test_phase_span_attributes(self, span_exporter, mock_config):
        """Test that phase spans have required attributes."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()

        # Check input phase span as representative example
        input_spans = [s for s in spans if s.name == "hfs.phase.input"]
        assert len(input_spans) == 1

        input_span = input_spans[0]
        assert input_span.attributes.get("hfs.phase.name") == "input"
        assert "hfs.phase.duration_s" in input_span.attributes
        assert input_span.attributes.get("hfs.phase.duration_s") >= 0
        assert input_span.attributes.get("hfs.phase.success") is True

    @pytest.mark.asyncio
    async def test_spawn_phase_has_triad_count(self, span_exporter, mock_config):
        """Test that spawn phase span includes triad_count attribute."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()
        spawn_spans = [s for s in spans if s.name == "hfs.phase.spawn"]

        assert len(spawn_spans) == 1
        assert spawn_spans[0].attributes.get("hfs.phase.triad_count") == 1

    @pytest.mark.asyncio
    async def test_claims_phase_attributes(self, span_exporter, mock_config):
        """Test that claims phase span includes claimed/contested counts."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()
        claims_spans = [s for s in spans if s.name == "hfs.phase.claims"]

        assert len(claims_spans) == 1
        assert "hfs.phase.claimed_count" in claims_spans[0].attributes
        assert "hfs.phase.contested_count" in claims_spans[0].attributes

    @pytest.mark.asyncio
    async def test_integration_phase_attributes(self, span_exporter, mock_config):
        """Test that integration phase span includes file_count and validation_passed."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()
        integration_spans = [s for s in spans if s.name == "hfs.phase.integration"]

        assert len(integration_spans) == 1
        assert "hfs.phase.file_count" in integration_spans[0].attributes
        assert "hfs.phase.validation_passed" in integration_spans[0].attributes

    @pytest.mark.asyncio
    async def test_span_hierarchy(self, span_exporter, mock_config):
        """Test that phase spans are children of the run span."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run("test request")

        spans = span_exporter.get_finished_spans()

        # Find the run span
        run_spans = [s for s in spans if s.name == "hfs.run"]
        assert len(run_spans) == 1
        run_span = run_spans[0]
        run_span_context = run_span.get_span_context()

        # All phase spans should have the run span as parent
        phase_spans = [s for s in spans if s.name.startswith("hfs.phase.")]
        for phase_span in phase_spans:
            parent = phase_span.parent
            assert parent is not None, f"{phase_span.name} should have a parent"
            assert parent.trace_id == run_span_context.trace_id

    @pytest.mark.asyncio
    async def test_successful_run_sets_ok_status(self, span_exporter, mock_config):
        """Test that successful run sets OK status on run span."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            result = await orchestrator.run("test request")

        assert result.success is True

        spans = span_exporter.get_finished_spans()
        run_spans = [s for s in spans if s.name == "hfs.run"]
        assert len(run_spans) == 1
        assert run_spans[0].status.status_code == StatusCode.OK

    @pytest.mark.asyncio
    async def test_failed_run_sets_error_status(self, span_exporter, mock_config):
        """Test that failed run sets ERROR status on run span."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        # Make spawn fail to trigger error handling
        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = RuntimeError("Test error")

            result = await orchestrator.run("test request")

        assert result.success is False
        assert "Test error" in result.error

        spans = span_exporter.get_finished_spans()
        run_spans = [s for s in spans if s.name == "hfs.run"]
        assert len(run_spans) == 1
        assert run_spans[0].status.status_code == StatusCode.ERROR
        assert run_spans[0].attributes.get("hfs.run.success") is False
        assert "Test error" in run_spans[0].attributes.get("hfs.run.error", "")

    @pytest.mark.asyncio
    async def test_phase_failure_records_exception(self, span_exporter, mock_config):
        """Test that phase failure records exception and sets error status."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        # Make spawn phase fail
        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = ValueError("Spawn failed")

            result = await orchestrator.run("test request")

        assert result.success is False

        spans = span_exporter.get_finished_spans()

        # Check spawn phase span has error status
        spawn_spans = [s for s in spans if s.name == "hfs.phase.spawn"]
        assert len(spawn_spans) == 1
        assert spawn_spans[0].status.status_code == StatusCode.ERROR
        assert spawn_spans[0].attributes.get("hfs.phase.success") is False

    @pytest.mark.asyncio
    async def test_run_attributes_truncation(self, span_exporter, mock_config):
        """Test that long request is truncated in run span attribute."""
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        long_request = "A" * 200  # Longer than 100 char limit

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            await orchestrator.run(long_request)

        spans = span_exporter.get_finished_spans()
        run_spans = [s for s in spans if s.name == "hfs.run"]

        # Request should be truncated to first 100 chars
        request_summary = run_spans[0].attributes.get("hfs.run.request_summary")
        assert len(request_summary) == 100


class TestOrchestratorMetrics:
    """Tests for orchestrator phase metrics recording."""

    @pytest.mark.asyncio
    async def test_phase_metrics_are_recorded(self, mock_config):
        """Test that phase metrics are recorded during run().

        This is a basic test verifying the metrics recording code path
        is executed without errors. Full metrics verification would require
        a mock MeterProvider.
        """
        orchestrator = HFSOrchestrator(config_dict=mock_config, llm_client=MockLLM())

        with patch.object(orchestrator, '_spawn_triads') as mock_spawn:
            mock_spawn.side_effect = lambda: setattr(
                orchestrator, 'triads', {"test-triad": MockTriad(None, None)}
            )

            # This should not raise any errors
            result = await orchestrator.run("test request")

        assert result.success is True

        # Verify phase_timings dict is populated (backward compatibility)
        assert "input" in result.phase_timings
        assert "spawn" in result.phase_timings
        assert "deliberation" in result.phase_timings
        assert "claims" in result.phase_timings
        assert "negotiation" in result.phase_timings
        assert "freeze" in result.phase_timings
        assert "execution" in result.phase_timings
        assert "integration" in result.phase_timings
        assert "output" in result.phase_timings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
