"""
HFS Observability Module.

Provides OpenTelemetry-based tracing and metrics infrastructure for the HFS
multi-agent system. This module establishes the core observability plumbing
that orchestrator and agents use to report telemetry.

Architecture:
    - 4-level span hierarchy: Run -> Phase -> Triad -> Agent
    - Custom histogram buckets tuned for LLM latencies (100ms to 60s)
    - Dual output: Console (always) + OTLP (when configured)
    - Graceful shutdown with atexit registration

Usage:
    from hfs.observability import setup_tracing, setup_metrics, get_tracer, get_meter

    # Initialize at application startup
    setup_tracing(service_name="hfs")
    setup_metrics(service_name="hfs")

    # Get instrumentation handles
    tracer = get_tracer("hfs.my_module")
    meter = get_meter("hfs.my_module")

    # Create spans
    with tracer.start_as_current_span("hfs.my_operation") as span:
        span.set_attribute("my.attribute", "value")
        # ... do work

Configuration:
    Environment variables:
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (optional)

    When set, telemetry is exported to both console and OTLP endpoint.
    When unset, only console export is active (development mode).
"""

import atexit
from typing import Optional

from hfs.observability.tracing import (
    setup_tracing,
    get_tracer,
    truncate_prompt,
    _tracer_provider,
)
from hfs.observability.metrics import (
    setup_metrics,
    get_meter,
    LLM_LATENCY_BUCKETS,
    _meter_provider,
)
from hfs.observability.config import ObservabilityConfig, get_config


def shutdown_telemetry() -> None:
    """Flush and shutdown telemetry providers.

    Ensures all pending telemetry is exported before application exit.
    Should be called during graceful shutdown or registered with atexit.
    """
    from hfs.observability.tracing import _tracer_provider
    from hfs.observability.metrics import _meter_provider

    if _tracer_provider is not None:
        _tracer_provider.force_flush(timeout_millis=5000)
        _tracer_provider.shutdown()

    if _meter_provider is not None:
        _meter_provider.force_flush(timeout_millis=5000)
        _meter_provider.shutdown()


# Register shutdown handler for graceful cleanup
atexit.register(shutdown_telemetry)


__all__ = [
    # Tracing
    "setup_tracing",
    "get_tracer",
    "truncate_prompt",
    # Metrics
    "setup_metrics",
    "get_meter",
    "LLM_LATENCY_BUCKETS",
    # Configuration
    "ObservabilityConfig",
    "get_config",
    # Shutdown
    "shutdown_telemetry",
]
