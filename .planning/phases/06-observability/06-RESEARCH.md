# Phase 6: Observability - Research

**Researched:** 2026-01-30
**Domain:** OpenTelemetry Python SDK for LLM agent observability
**Confidence:** HIGH

## Summary

This phase implements full observability for HFS agent runs using OpenTelemetry Python SDK. The research covers custom span hierarchies (Run -> Phase -> Triad -> Agent), token tracking from LLM responses, timing metrics, and configurable output destinations.

OpenTelemetry Python SDK v1.39.x provides stable APIs for both tracing and metrics. The SDK offers `BatchSpanProcessor` for production use (recommended) and `SimpleSpanProcessor` for development. Console and OTLP exporters are built-in, with OTLP endpoint configurable via environment variables. For metrics, `MeterProvider` with `View` configuration enables custom histogram bucket boundaries appropriate for LLM latencies.

The GenAI semantic conventions (experimental) provide standardized attribute names for LLM operations including `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`. However, since we're building custom instrumentation per CONTEXT.md decisions, we'll use HFS-specific naming following OTel naming conventions.

**Primary recommendation:** Use `opentelemetry-api` and `opentelemetry-sdk` v1.39.x with custom span hierarchy `hfs.{level}.{detail}`, BatchSpanProcessor for production, and explicit histogram buckets tuned for LLM latencies.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| opentelemetry-api | 1.39.x | Tracing/metrics API | Official OTel Python API, stable |
| opentelemetry-sdk | 1.39.x | SDK implementation | Required for TracerProvider, MeterProvider |
| opentelemetry-exporter-otlp-proto-http | 1.39.x | OTLP HTTP exporter | Standard protocol for OTel backends |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| opentelemetry-exporter-otlp-proto-grpc | 1.39.x | OTLP gRPC exporter | When gRPC preferred over HTTP |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom OTel | Agno's setup_tracing | Less control, doesn't support 4-level hierarchy (LOCKED: use custom) |
| Custom OTel | OpenLLMetry | Auto-instruments LLM calls but harder to customize hierarchy (LOCKED: use custom) |

**Installation:**
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── observability/           # New module for observability
│   ├── __init__.py
│   ├── tracing.py          # TracerProvider setup, span creation helpers
│   ├── metrics.py          # MeterProvider setup, metric instruments
│   ├── exporters.py        # Exporter configuration (console, OTLP)
│   └── context.py          # Context propagation helpers
├── core/
│   └── orchestrator.py     # Instrument with tracing (modify existing)
└── agno/
    └── teams/
        └── base.py         # Instrument agent execution (modify existing)
```

### Pattern 1: Hierarchical Span Structure (LOCKED per CONTEXT.md)
**What:** 4-level span hierarchy: Run -> Phase -> Triad -> Agent
**When to use:** All HFS pipeline execution
**Example:**
```python
# Source: OTel Python docs + HFS-specific design
from opentelemetry import trace

tracer = trace.get_tracer("hfs.observability", "0.1.0")

async def run(self, user_request: str) -> HFSResult:
    with tracer.start_as_current_span("hfs.run") as run_span:
        run_span.set_attribute("hfs.run.id", run_id)
        run_span.set_attribute("hfs.run.request_summary", user_request[:100])

        # Phase span (child of run)
        with tracer.start_as_current_span("hfs.phase.deliberation") as phase_span:
            phase_span.set_attribute("hfs.phase.name", "deliberation")
            phase_span.set_attribute("hfs.phase.goal", "Triads analyze request")

            # Triad span (child of phase)
            with tracer.start_as_current_span("hfs.triad.layout") as triad_span:
                triad_span.set_attribute("hfs.triad.id", "layout")
                triad_span.set_attribute("hfs.triad.type", "hierarchical")

                # Agent span (child of triad)
                with tracer.start_as_current_span("hfs.agent.orchestrator") as agent_span:
                    agent_span.set_attribute("hfs.agent.role", "orchestrator")
                    agent_span.set_attribute("hfs.agent.model", "llama-3.3-70b")
                    agent_span.set_attribute("hfs.agent.provider", "cerebras")
                    # ... execute agent
```

### Pattern 2: Token Tracking via Span Attributes (LOCKED per CONTEXT.md)
**What:** Capture token counts from LLM response metadata
**When to use:** Every agent LLM call
**Example:**
```python
# Source: GenAI semantic conventions + HFS design
def record_llm_usage(span, response):
    """Record token usage from LLM API response."""
    if hasattr(response, 'usage') and response.usage:
        span.set_attribute("hfs.tokens.prompt", response.usage.prompt_tokens)
        span.set_attribute("hfs.tokens.completion", response.usage.completion_tokens)
        span.set_attribute("hfs.tokens.total",
            response.usage.prompt_tokens + response.usage.completion_tokens)
```

### Pattern 3: Metrics with Custom Histogram Buckets (LOCKED per CONTEXT.md)
**What:** LLM-appropriate latency buckets for timing histograms
**When to use:** Phase, triad, and agent timing
**Example:**
```python
# Source: OTel Python SDK docs
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation

# LLM-appropriate buckets: 100ms, 500ms, 1s, 2s, 5s, 10s, 30s, 60s
LLM_LATENCY_BUCKETS = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)

provider = MeterProvider(
    metric_readers=[reader],
    views=[
        View(
            instrument_name="hfs.*.duration",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=LLM_LATENCY_BUCKETS
            )
        )
    ]
)
```

### Pattern 4: Dual Output (Span Attributes + Metrics API) (LOCKED per CONTEXT.md)
**What:** Expose timing via both span attributes AND OTel metrics
**When to use:** All timing and count metrics
**Example:**
```python
# Source: OTel metrics docs
meter = metrics.get_meter("hfs.metrics", "0.1.0")

# Histograms for timing
phase_duration = meter.create_histogram(
    name="hfs.phase.duration",
    description="Duration of HFS pipeline phases",
    unit="s"
)

# Counters for success/failure
phase_success = meter.create_counter(
    name="hfs.phase.success",
    description="Count of successful phase completions",
    unit="{execution}"
)

phase_failure = meter.create_counter(
    name="hfs.phase.failure",
    description="Count of failed phase executions",
    unit="{execution}"
)

# Record both span attribute and metric
def record_phase_timing(span, phase_name: str, duration_s: float, success: bool):
    # Span attribute (for trace view)
    span.set_attribute("hfs.phase.duration_ms", duration_s * 1000)
    span.set_attribute("hfs.phase.success", success)

    # Metric (for aggregation/dashboards)
    phase_duration.record(duration_s, {"hfs.phase.name": phase_name})
    if success:
        phase_success.add(1, {"hfs.phase.name": phase_name})
    else:
        phase_failure.add(1, {"hfs.phase.name": phase_name})
```

### Anti-Patterns to Avoid
- **High-cardinality span names:** Never include run_id, user input, or unique identifiers in span NAMES (put them in attributes)
- **Synchronous span processing in production:** Use BatchSpanProcessor, not SimpleSpanProcessor
- **Missing shutdown handling:** Always call `tracer_provider.shutdown()` on application exit
- **Token tracking in span names:** Token counts vary per call; use attributes, not names
- **Blocking on telemetry:** Never let telemetry failures block LLM execution

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Span context propagation | Manual thread-local tracking | `tracer.start_as_current_span()` context manager | Handles async, exceptions, nesting automatically |
| Trace/span ID generation | Custom UUID generation | OTel SDK auto-generates | W3C Trace Context compliant, 128-bit trace ID |
| Metric aggregation | Manual timing buckets | ExplicitBucketHistogramAggregation | Handles overflow, provides min/max/sum |
| Console formatting | Custom JSON serialization | ConsoleSpanExporter | Consistent output format |
| OTLP protocol | Manual HTTP/gRPC calls | OTLPSpanExporter | Handles batching, retries, compression |
| Exception recording | Manual error string capture | span.record_exception() | Captures stack trace, exception type |

**Key insight:** OTel SDK handles the complex concurrency and lifecycle management. Custom solutions will miss edge cases like async context loss, resource cleanup, or trace context propagation across threads.

## Common Pitfalls

### Pitfall 1: Context Loss in Async Code
**What goes wrong:** Span hierarchy breaks when using asyncio without proper context propagation
**Why it happens:** Python's contextvars work with asyncio but require spans to be started within async context
**How to avoid:** Always use `start_as_current_span()` within the async function that needs tracing, not in a wrapper
**Warning signs:** Child spans appear as separate root traces instead of nested

### Pitfall 2: Missing TracerProvider Shutdown
**What goes wrong:** Spans buffered in BatchSpanProcessor are lost on application exit
**Why it happens:** BatchSpanProcessor batches spans for efficiency; unflushed batches are lost
**How to avoid:** Call `tracer_provider.shutdown()` in atexit handler or application shutdown hook
**Warning signs:** Last few spans of a run are missing from trace backend

### Pitfall 3: High-Cardinality Attributes Causing Memory Issues
**What goes wrong:** Unbounded attribute values (full prompts, responses) cause memory bloat
**Why it happens:** Span attributes are held in memory until export
**How to avoid:** Truncate strings, hash large values, or use span events for large data
**Warning signs:** Memory growth during long runs, OOM errors

### Pitfall 4: Blocking on Exporter Failures
**What goes wrong:** Application hangs when OTLP endpoint is unavailable
**Why it happens:** Default exporter timeout may be too long for production
**How to avoid:** Configure reasonable timeouts, use BatchSpanProcessor with max_queue_size
**Warning signs:** Application latency increases when telemetry backend is down

### Pitfall 5: Inconsistent Metric Units
**What goes wrong:** Dashboards show incorrect values due to unit mismatch
**Why it happens:** Mixing seconds/milliseconds without clear naming
**How to avoid:** Always use seconds for duration (OTel convention), specify unit in instrument creation
**Warning signs:** Latency percentiles show implausible values (e.g., p99 = 5000 when expecting 5s)

## Code Examples

Verified patterns from official sources:

### TracerProvider Setup with Dual Exporters
```python
# Source: OTel Python Exporters docs
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import os

def setup_tracing(service_name: str = "hfs") -> TracerProvider:
    """Initialize OpenTelemetry tracing with console and optional OTLP export."""

    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "0.1.0",
    })

    provider = TracerProvider(resource=resource)

    # Always add console exporter for development visibility
    console_processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(console_processor)

    # Add OTLP exporter if endpoint configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(otlp_processor)

    trace.set_tracer_provider(provider)
    return provider
```

### MeterProvider Setup with Custom Histogram Buckets
```python
# Source: OTel Python SDK docs + Better Stack guide
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import os

# LLM-appropriate latency buckets (in seconds)
LLM_LATENCY_BUCKETS = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)

def setup_metrics(service_name: str = "hfs") -> MeterProvider:
    """Initialize OpenTelemetry metrics with LLM-appropriate histogram buckets."""

    resource = Resource.create({SERVICE_NAME: service_name})

    # Console exporter for development
    console_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=10000  # 10s for dev
    )
    readers = [console_reader]

    # OTLP exporter if configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics"),
            export_interval_millis=60000  # 60s for production
        )
        readers.append(otlp_reader)

    # Custom view for LLM latency histograms
    duration_view = View(
        instrument_name="hfs.*.duration",
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=LLM_LATENCY_BUCKETS
        )
    )

    provider = MeterProvider(
        resource=resource,
        metric_readers=readers,
        views=[duration_view]
    )

    metrics.set_meter_provider(provider)
    return provider
```

### Exception Handling with Status
```python
# Source: OTel Python Instrumentation docs
from opentelemetry.trace import Status, StatusCode

async def execute_agent(self, prompt: str):
    with tracer.start_as_current_span("hfs.agent.execute") as span:
        span.set_attribute("hfs.agent.role", self.role)
        span.set_attribute("hfs.agent.prompt_length", len(prompt))

        try:
            response = await self.llm.complete(prompt)

            # Record success
            span.set_attribute("hfs.agent.success", True)
            if hasattr(response, 'usage'):
                span.set_attribute("hfs.tokens.prompt", response.usage.prompt_tokens)
                span.set_attribute("hfs.tokens.completion", response.usage.completion_tokens)

            return response

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("hfs.agent.success", False)
            raise
```

### Graceful Shutdown
```python
# Source: OTel Python SDK docs
import atexit

tracer_provider = setup_tracing()
meter_provider = setup_metrics()

def shutdown_telemetry():
    """Flush and shutdown telemetry providers."""
    tracer_provider.force_flush(timeout_millis=5000)
    tracer_provider.shutdown()
    meter_provider.force_flush(timeout_millis=5000)
    meter_provider.shutdown()

atexit.register(shutdown_telemetry)
```

## Claude's Discretion Recommendations

Based on research, here are recommendations for items marked as Claude's discretion in CONTEXT.md:

### 1. Span Naming Convention
**Recommendation:** Use hierarchical dotted names: `hfs.{level}.{identifier}`

| Level | Pattern | Example |
|-------|---------|---------|
| Run | `hfs.run` | `hfs.run` |
| Phase | `hfs.phase.{name}` | `hfs.phase.deliberation` |
| Triad | `hfs.triad.{id}` | `hfs.triad.layout` |
| Agent | `hfs.agent.{role}` | `hfs.agent.orchestrator` |

**Rationale:**
- Follows OTel naming conventions (dot-separated hierarchy)
- Keeps span names low-cardinality (IDs like "layout" are from config, not runtime)
- Enables filtering by level (e.g., `hfs.phase.*`)
- Verb-object pattern adapted for hierarchy (`hfs` is the system, rest describes what)

### 2. Prompt Snippet Truncation
**Recommendation:** Truncate to 200 characters with ellipsis, strip newlines

```python
def truncate_prompt(prompt: str, max_length: int = 200) -> str:
    """Truncate prompt for span attribute, preserving meaning."""
    # Replace newlines with spaces for single-line attribute
    clean = ' '.join(prompt.split())
    if len(clean) <= max_length:
        return clean
    return clean[:max_length-3] + "..."
```

**Rationale:**
- 200 chars provides enough context to identify the operation
- Stripping newlines makes logs/traces more readable
- Ellipsis indicates truncation occurred
- Balances debuggability vs. memory/export size

### 3. BatchSpanProcessor vs SimpleSpanProcessor
**Recommendation:** Use `BatchSpanProcessor` for both development and production

```python
# Development: smaller batch, shorter delay for faster feedback
dev_processor = BatchSpanProcessor(
    exporter,
    max_queue_size=512,
    max_export_batch_size=64,
    schedule_delay_millis=1000  # 1s delay
)

# Production: larger batches, longer delay for efficiency
prod_processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    max_export_batch_size=512,
    schedule_delay_millis=5000  # 5s delay
)
```

**Rationale:**
- SimpleSpanProcessor blocks the calling thread, unacceptable for LLM calls
- BatchSpanProcessor with smaller batch sizes still provides timely feedback for dev
- Consistent API means no code changes between environments
- Only difference is tuning parameters via environment or config

### 4. Meter Naming and Units
**Recommendation:** Use hierarchical names with UCUM units

| Metric | Name | Unit | Type |
|--------|------|------|------|
| Phase duration | `hfs.phase.duration` | `s` | Histogram |
| Triad duration | `hfs.triad.duration` | `s` | Histogram |
| Agent duration | `hfs.agent.duration` | `s` | Histogram |
| Phase success | `hfs.phase.success.count` | `{execution}` | Counter |
| Phase failure | `hfs.phase.failure.count` | `{execution}` | Counter |
| Tokens used | `hfs.tokens.total` | `{token}` | Counter |
| Prompt tokens | `hfs.tokens.prompt` | `{token}` | Counter |
| Completion tokens | `hfs.tokens.completion` | `{token}` | Counter |

**Rationale:**
- Durations in seconds per OTel convention
- Curly-brace annotations for dimensionless counts per UCUM
- Hierarchical names match span naming for correlation
- Separate counters for success/failure enable rate calculations

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Basic logging | Structured tracing (OTel) | 2023+ | Full context propagation, correlation |
| Custom metrics | OTel Metrics API | 2024 (stable) | Standard aggregation, export |
| Prometheus-only | OTLP as standard | 2024+ | Vendor-neutral telemetry |
| Manual timing | Span duration auto-tracking | OTel 1.x | Automatic start/end timing |

**Deprecated/outdated:**
- `opentelemetry-instrumentation-*` auto-instrumentation: Useful but doesn't give 4-level hierarchy control
- Agno's `setup_tracing`: Uses OTel internally but doesn't expose hierarchy customization

## Open Questions

Things that couldn't be fully resolved:

1. **Console Exporter Verbosity Levels**
   - What we know: Python SDK's ConsoleSpanExporter has a `formatter` parameter, not verbosity levels
   - What's unclear: How to implement minimal/standard/verbose modes per CONTEXT.md
   - Recommendation: Implement custom formatter functions that filter/format output based on config level

2. **Token Tracking from Agno**
   - What we know: Need to capture from LLM API response metadata
   - What's unclear: Exact location of usage data in Agno's response objects
   - Recommendation: Investigate Agno response structure during implementation; may need to hook into lower-level API

3. **View Name Matching with Wildcards**
   - What we know: View `instrument_name` accepts wildcards like `hfs.*.duration`
   - What's unclear: Whether Python SDK supports this exact pattern
   - Recommendation: Test during implementation; may need separate views per metric name

## Sources

### Primary (HIGH confidence)
- [OpenTelemetry Python SDK Documentation](https://opentelemetry.io/docs/languages/python/) - Tracing, metrics, exporters
- [OpenTelemetry Python Instrumentation Guide](https://opentelemetry.io/docs/languages/python/instrumentation/) - Span creation, attributes, exceptions
- [OpenTelemetry Python Exporters](https://opentelemetry.io/docs/languages/python/exporters/) - Console, OTLP setup
- [opentelemetry-api PyPI](https://pypi.org/project/opentelemetry-api/) - Version 1.39.1 confirmed
- [opentelemetry-sdk PyPI](https://pypi.org/project/opentelemetry-sdk/) - Version 1.39.1 confirmed

### Secondary (MEDIUM confidence)
- [OpenTelemetry Naming Conventions](https://opentelemetry.io/docs/specs/semconv/general/naming/) - Attribute and metric naming
- [OTel Metrics Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/general/metrics/) - Unit specifications
- [GenAI Spans Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) - LLM-specific attributes
- [Better Stack OTel Metrics Guide](https://betterstack.com/community/guides/observability/otel-metrics-python/) - MeterProvider setup
- [OTel Best Practices Blog](https://opentelemetry.io/blog/2025/how-to-name-your-spans/) - Span naming

### Tertiary (LOW confidence)
- [OpenLLMetry GitHub](https://github.com/traceloop/openllmetry) - LLM observability patterns (not used, for reference)
- [OTel LLM Observability Blog](https://opentelemetry.io/blog/2024/llm-observability/) - General LLM tracing concepts

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official OTel packages with verified versions
- Architecture: HIGH - Based on official docs and verified patterns
- Pitfalls: HIGH - Documented in official troubleshooting guides
- Discretion recommendations: MEDIUM - Based on conventions, may need validation during implementation

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - OTel Python is stable)
