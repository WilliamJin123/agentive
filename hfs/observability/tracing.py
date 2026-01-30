"""
OpenTelemetry tracing setup for HFS.

Provides TracerProvider configuration with console and optional OTLP export.
Uses BatchSpanProcessor for non-blocking span export (never SimpleSpanProcessor
which blocks the calling thread).

Span Naming Convention:
    - hfs.run: Top-level pipeline execution
    - hfs.phase.{name}: Phase execution (deliberation, negotiation, execution)
    - hfs.triad.{id}: Triad execution
    - hfs.agent.{role}: Individual agent execution

Attributes are used for variable data (run_id, model name, tokens) to keep
span names low-cardinality.
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Tracer


# Module-level provider reference for shutdown handling
_tracer_provider: Optional[TracerProvider] = None


def setup_tracing(service_name: str = "hfs") -> TracerProvider:
    """Initialize OpenTelemetry tracing with console and optional OTLP export.

    Creates a TracerProvider with:
    - Resource identifying the service
    - BatchSpanProcessor with ConsoleSpanExporter (always, for dev visibility)
    - BatchSpanProcessor with OTLPSpanExporter (if OTEL_EXPORTER_OTLP_ENDPOINT set)

    Args:
        service_name: Service name for resource identification. Defaults to "hfs".

    Returns:
        The configured TracerProvider, also set as global provider.

    Example:
        >>> provider = setup_tracing()
        >>> tracer = get_tracer("hfs.my_module")
        >>> with tracer.start_as_current_span("hfs.my_operation") as span:
        ...     span.set_attribute("key", "value")
    """
    global _tracer_provider

    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "0.1.0",
    })

    provider = TracerProvider(resource=resource)

    # Always add console exporter for development visibility
    # Use BatchSpanProcessor (not SimpleSpanProcessor) to avoid blocking
    console_processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(console_processor)

    # Add OTLP exporter if endpoint configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(otlp_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Store reference for shutdown
    _tracer_provider = provider

    return provider


def get_tracer(name: str = "hfs.observability", version: str = "0.1.0") -> Tracer:
    """Get a tracer instance from the global provider.

    Args:
        name: Tracer name, typically the module name. Defaults to "hfs.observability".
        version: Tracer version. Defaults to "0.1.0".

    Returns:
        Tracer instance for creating spans.

    Example:
        >>> tracer = get_tracer("hfs.core.orchestrator")
        >>> with tracer.start_as_current_span("hfs.run") as span:
        ...     span.set_attribute("hfs.run.id", run_id)
    """
    return trace.get_tracer(name, version)


def truncate_prompt(prompt: str, max_length: int = 200) -> str:
    """Truncate prompt for span attribute, preserving meaning.

    Replaces newlines with spaces and truncates to max_length with ellipsis
    if needed. This keeps span attributes readable while avoiding memory
    bloat from large prompt strings.

    Args:
        prompt: The prompt text to truncate.
        max_length: Maximum length including ellipsis. Defaults to 200.

    Returns:
        Truncated prompt string.

    Example:
        >>> truncate_prompt("hello\\nworld", 10)
        'hello w...'
        >>> truncate_prompt("short", 200)
        'short'
    """
    # Replace newlines with spaces for single-line attribute
    clean = " ".join(prompt.split())
    if len(clean) <= max_length:
        return clean
    return clean[:max_length - 3] + "..."


__all__ = [
    "setup_tracing",
    "get_tracer",
    "truncate_prompt",
    "_tracer_provider",
]
