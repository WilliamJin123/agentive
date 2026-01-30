# Agno + Keycycle Integration

## What This Is

A real LLM-powered multi-agent negotiation system built on HFS (Hierarchical Feature Synthesis). Triads are implemented as Agno Teams with automatic key rotation across 4 providers, role-based model selection, and failure-adaptive escalation. Full OpenTelemetry observability provides visibility into all 9 HFS pipeline phases.

## Core Value

Real LLM-powered multi-agent negotiation with automatic key rotation and failure-adaptive model escalation.

## Requirements

### Validated

- ✓ HFS 9-phase pipeline — existing
- ✓ Triad presets (Hierarchical, Dialectic, Consensus) — existing
- ✓ Spec negotiation mechanics — existing
- ✓ Configuration system (YAML + Pydantic) — existing
- ✓ CLI interface — existing
- ✓ Agno-backed real LLM calls via Keycycle — v1
- ✓ Triads implemented as Agno Teams with 3 agent members — v1
- ✓ Multi-provider support: Cerebras (51), Groq (16), Gemini (110), OpenRouter (31) — v1
- ✓ Role-based model tiers in YAML (orchestrator, worker, arbiter) — v1
- ✓ Phase-based model selection — v1
- ✓ Code execution uses high-quality models (GLM-4.7, OSS-120b) — v1
- ✓ Adaptive model escalation when execution fails — v1
- ✓ OpenTelemetry tracing for agent runs and tool executions — v1
- ✓ Token usage tracked per agent, phase, and run — v1
- ✓ Phase timing metrics for HFS pipeline — v1
- ✓ MockLLMClient removed (require real API keys) — v1

### Active

**Current Milestone: v1.1 HFS CLI (Ink)**

**Goal:** Build a rich Ink-based CLI frontend with full observability abstraction layer, preparing for future web UI.

**Target features:**
- Event/state layer — HFS emits events, state layer captures them
- Query interface — Clean API for agent tree, traces, token usage
- Serializable models — All inspection data as JSON-ready models
- Ink-based CLI in `hfs/cli/` consuming the abstraction layer
- Chat-style REPL with streaming responses
- Bee/hive/hexagonal visual theme (yellow accent)
- Live agent streaming via event subscription
- Deep inspection: agent tree, trace timeline, token breakdown
- Global `hfs` command entry point
- Replaces existing typer-based CLI

### Out of Scope

- Learning mode (agents improving over time) — complexity, defer to future
- Human-in-the-loop approval for tool execution — not needed for v1
- Session persistence across runs — each run is independent
- Mobile/web UI — CLI-only for now
- Provider fallback when one exhausted — v2 candidate
- Trace data to TiDB — v2 candidate

## Context

**Shipped v1 with:**
- 22,676 lines of Python
- 7 phases, 20 plans, 108 commits
- 240+ tests passing
- 4 providers configured (208 total API keys)

**Tech Stack:**
- Python 3.11+
- Agno (multi-agent framework)
- Keycycle (API key rotation)
- OpenTelemetry (observability)
- TiDB (usage persistence)
- Pydantic (configuration)

**Architecture:**
- `hfs/agno/providers.py` — ProviderManager singleton for model access
- `hfs/agno/tools/` — HFSToolkit and SharedStateToolkit
- `hfs/agno/teams/` — AgnoTriad base + 3 subclasses
- `hfs/core/model_selector.py` — Role/phase model resolution
- `hfs/core/escalation_tracker.py` — Failure-adaptive tier upgrades
- `hfs/observability/` — OpenTelemetry tracing and metrics

## Constraints

- **Providers**: Must use Keycycle's numbered env var format
- **Code Quality**: Code execution phase always uses GLM-4.7 or OSS-120b (Cerebras)
- **Architecture**: Triads must be Agno Teams (not standalone agents)
- **Persistence**: Usage stats go to TiDB (TIDB_DB_URL)
- **No Mocks**: Require real API keys to run

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agno Teams for triads | Built-in coordination, history management | ✓ Good |
| Role-based + pressure-linked model tiers | Start cheap, escalate on failure | ✓ Good |
| Cerebras for code models | GLM-4.7/OSS-120b quality, 51 keys available | ✓ Good |
| TiDB for usage persistence | Already have TIDB_DB_URL, production-grade | ✓ Good |
| Remove MockLLMClient | Clean slate, force real integration | ✓ Good |
| Singleton ProviderManager | Avoids re-initializing wrappers on each call | ✓ Good |
| Single negotiate_response tool | Cleaner for LLMs than three separate tools | ✓ Good |
| PhaseSummary requires phase and produced_by | Enforce structured summaries per CONTEXT.md | ✓ Good |
| Orchestrator-directed delegation | delegate_to_all_members=False for explicit control | ✓ Good |
| Consensus uses delegate_to_all_members=True | Parallel dispatch for simultaneous peer work | ✓ Good |
| Atomic writes via temp file + rename | Prevents partial writes on crash | ✓ Good |
| Lazy initialization for tracer/meter | Avoid import-time side effects | ✓ Good |
| BatchSpanProcessor for both console and OTLP | SimpleSpanProcessor blocks calling thread | ✓ Good |
| Integration tests skip by default | Require --run-integration flag for API tests | ✓ Good |

---
*Last updated: 2026-01-30 after v1.1 milestone start*
