"""
OpenTelemetry metrics setup for HFS.

Provides MeterProvider configuration with LLM-appropriate histogram buckets.
The latency buckets (100ms to 60s) are tuned for LLM API calls which can
take significant time, especially for reasoning models.

Metric Naming Convention:
    - hfs.phase.duration: Phase timing histogram
    - hfs.triad.duration: Triad timing histogram
    - hfs.agent.duration: Agent timing histogram
    - hfs.phase.success.count: Successful phase counter
    - hfs.phase.failure.count: Failed phase counter
    - hfs.tokens.total: Total token counter

All durations use seconds (OTel convention). Counters use curly-brace
annotations for dimensionless counts per UCUM ({execution}, {token}).
"""

import os
from typing import Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Meter
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation
from opentelemetry.sdk.resources import Resource, SERVICE_NAME


# LLM-appropriate latency buckets (in seconds)
# Covers quick responses (100ms) to long reasoning tasks (60s)
LLM_LATENCY_BUCKETS = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)


# Module-level provider reference for shutdown handling
_meter_provider: Optional[MeterProvider] = None


def setup_metrics(service_name: str = "hfs") -> MeterProvider:
    """Initialize OpenTelemetry metrics with LLM-appropriate histogram buckets.

    Creates a MeterProvider with:
    - Resource identifying the service
    - PeriodicExportingMetricReader with ConsoleMetricExporter (always)
    - PeriodicExportingMetricReader with OTLPMetricExporter (if endpoint set)
    - View for hfs.*.duration instruments with LLM latency buckets

    Args:
        service_name: Service name for resource identification. Defaults to "hfs".

    Returns:
        The configured MeterProvider, also set as global provider.

    Example:
        >>> provider = setup_metrics()
        >>> meter = get_meter("hfs.my_module")
        >>> histogram = meter.create_histogram("hfs.my.duration", unit="s")
        >>> histogram.record(1.5, {"phase": "deliberation"})
    """
    global _meter_provider

    resource = Resource.create({SERVICE_NAME: service_name})

    # Console exporter for development (10s interval)
    console_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=10000,  # 10s for dev visibility
    )
    readers = [console_reader]

    # OTLP exporter if configured (60s interval for production)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics"),
            export_interval_millis=60000,  # 60s for production
        )
        readers.append(otlp_reader)

    # Custom views for LLM latency histograms
    # Note: OTel Python SDK requires exact instrument name matching for views
    # We create separate views for each duration metric
    views = [
        View(
            instrument_name="hfs.phase.duration",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=LLM_LATENCY_BUCKETS
            ),
        ),
        View(
            instrument_name="hfs.triad.duration",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=LLM_LATENCY_BUCKETS
            ),
        ),
        View(
            instrument_name="hfs.agent.duration",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=LLM_LATENCY_BUCKETS
            ),
        ),
    ]

    provider = MeterProvider(
        resource=resource,
        metric_readers=readers,
        views=views,
    )

    # Set as global meter provider
    metrics.set_meter_provider(provider)

    # Store reference for shutdown
    _meter_provider = provider

    return provider


def get_meter(name: str = "hfs.metrics", version: str = "0.1.0") -> Meter:
    """Get a meter instance from the global provider.

    Args:
        name: Meter name, typically the module name. Defaults to "hfs.metrics".
        version: Meter version. Defaults to "0.1.0".

    Returns:
        Meter instance for creating instruments.

    Example:
        >>> meter = get_meter("hfs.core.orchestrator")
        >>> phase_duration = meter.create_histogram(
        ...     name="hfs.phase.duration",
        ...     description="Duration of HFS pipeline phases",
        ...     unit="s"
        ... )
        >>> phase_duration.record(2.5, {"hfs.phase.name": "deliberation"})
    """
    return metrics.get_meter(name, version)


# Pre-defined instrument factories for common metrics
# These are created lazily when first accessed to avoid requiring
# setup_metrics() to be called before import


def create_phase_duration_histogram(meter: Meter):
    """Create histogram for phase duration tracking."""
    return meter.create_histogram(
        name="hfs.phase.duration",
        description="Duration of HFS pipeline phases",
        unit="s",
    )


def create_triad_duration_histogram(meter: Meter):
    """Create histogram for triad duration tracking."""
    return meter.create_histogram(
        name="hfs.triad.duration",
        description="Duration of HFS triad executions",
        unit="s",
    )


def create_agent_duration_histogram(meter: Meter):
    """Create histogram for agent duration tracking."""
    return meter.create_histogram(
        name="hfs.agent.duration",
        description="Duration of HFS agent executions",
        unit="s",
    )


def create_phase_success_counter(meter: Meter):
    """Create counter for successful phase completions."""
    return meter.create_counter(
        name="hfs.phase.success.count",
        description="Count of successful phase completions",
        unit="{execution}",
    )


def create_phase_failure_counter(meter: Meter):
    """Create counter for failed phase executions."""
    return meter.create_counter(
        name="hfs.phase.failure.count",
        description="Count of failed phase executions",
        unit="{execution}",
    )


def create_tokens_counter(meter: Meter):
    """Create counter for total token usage."""
    return meter.create_counter(
        name="hfs.tokens.total",
        description="Total tokens used across all LLM calls",
        unit="{token}",
    )


__all__ = [
    "LLM_LATENCY_BUCKETS",
    "setup_metrics",
    "get_meter",
    "_meter_provider",
    # Instrument factories
    "create_phase_duration_histogram",
    "create_triad_duration_histogram",
    "create_agent_duration_histogram",
    "create_phase_success_counter",
    "create_phase_failure_counter",
    "create_tokens_counter",
]
