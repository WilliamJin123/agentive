# Project Research Summary: HFS CLI v1.1

**Project:** HFS CLI - Rich terminal interface for multi-agent execution
**Domain:** AI/Agent CLI with TUI frontend
**Researched:** 2026-01-30
**Confidence:** HIGH

## Executive Summary

HFS requires a rich terminal UI for interactive multi-agent execution, featuring real-time streaming of LLM outputs, agent tree visualization, and spec negotiation monitoring. Research reveals that **Textual (Python) is the superior choice over Ink (JavaScript)** for this project. While the initial PROJECT.md mentioned "Ink-based CLI," using Textual eliminates the entire Python-JS IPC complexity layer, provides native integration with HFS's existing OpenTelemetry instrumentation, and leverages proven patterns from Toad (Will McGugan's agentic coding TUI).

The recommended architecture follows an **event sourcing lite pattern**: HFS emits typed Pydantic events via an async event bus, a state manager computes snapshots from events and existing OpenTelemetry spans, and a query interface provides inspection data. This three-layer abstraction (events/state/queries) supports both the CLI and future web UI without duplicating HFS internals.

Critical risks center on **terminal rendering performance** (streaming can cause severe flickering), **state synchronization complexity** (events must correlate with OpenTelemetry spans), and **backpressure handling** (LLMs produce tokens faster than terminals can render). These are preventable through differential rendering, frame rate limiting, and explicit buffer management. The unique differentiator is HFS's multi-agent architecture: no competitor offers agent tree visualization, triad negotiation display, or per-agent token tracking because they run single-agent loops.

## Key Findings

### Recommended Stack

**Core Decision: Textual + Rich (pure Python)**

The stack research uncovers a critical pivot: Ink would require Node.js runtime alongside Python, IPC/subprocess communication, event serialization, and dual-stack maintenance. Textual eliminates all of this complexity while providing:

- **Native Python integration**: Direct imports of HFS core, Agno, OpenTelemetry - no IPC layer
- **Proven for agentic CLIs**: Toad (by Rich/Textual creator) demonstrates production viability for terminal UIs with Claude Code, Gemini CLI integration
- **Async-first design**: Workers API for background tasks with UI updates, matches HFS's asyncio architecture
- **Rich foundation**: Streaming markdown, syntax highlighting, progress bars out of the box

**Core technologies:**
- **Textual 3.x**: Terminal UI framework with CSS-like styling, reactive attributes, message passing, full widget library
- **Rich 14.x**: Terminal rendering primitives (foundation for Textual), markdown rendering, syntax highlighting
- **asyncio (stdlib)**: Async coordination, Textual is asyncio-native
- **Pydantic 2.x (existing)**: Event models and state serialization, already in stack

**Supporting:**
- **textual-dev**: Development console for debugging widgets
- **argparse (existing)**: Keep for non-interactive commands (`hfs run`, `hfs validate-config`)

**Integration points:**
- HFS core emits events (Python objects) → Event bus (simple pub/sub) → Textual widgets subscribe
- No serialization needed since everything is Python
- Direct OpenTelemetry span access via custom SpanProcessor
- Streaming via Textual workers with reactive attributes

### Expected Features

Research analyzed Gemini CLI, Claude Code, OpenCode, and Aider to identify table stakes vs differentiators.

**Must have (table stakes):**
- **Streaming response output**: Token-by-token LLM display (every AI CLI streams)
- **Markdown rendering**: Syntax highlighting, code fences, headers (LLM responses are markdown)
- **Command history**: Arrow-up for previous commands, Ctrl+R for search (terminal user expectation)
- **Session continuity**: Conversation context persists within run (follow-up questions must work)
- **Progress indication**: Spinners/status during LLM calls (users need feedback)
- **Error handling**: Graceful error messages with retry option (API failures happen)
- **Configuration via file + env**: Config file for settings, env vars for API keys (standard pattern)

**Should have (competitive differentiators - aligned with HFS's multi-agent architecture):**
- **Agent tree visualization**: Show triad structure (orchestrator/worker/proposer/critic) with real-time status updates — unique because competitors are single-agent
- **Negotiation visualization**: Display spec negotiation ("warm wax" model) with section status, temperature decay, arbiter interventions — HFS's core innovation
- **Token/cost tracking**: Real-time per-agent, per-phase, per-provider token usage and cost estimates — critical for multi-agent cost visibility
- **Trace timeline view**: Show 9-phase execution timeline with durations from OpenTelemetry spans
- **Model escalation visibility**: Display when/why models upgraded from cheap to expensive
- **Deep inspection mode** (`/inspect`): Pause and inspect agent tree, spec status, token breakdown — power user feature
- **Bee/hive visual theme**: Yellow/amber/hexagonal brand identity (most AI CLIs are generic blue/white)

**Defer (v2+):**
- Session persistence across runs (out of scope per PROJECT.md)
- Checkpoints/rewind (less critical than for extended autonomous work)
- Vim/emacs keybindings (nice but not essential)
- Plugin/extension system (adds complexity)

**Anti-features (deliberately avoid):**
- Built-in code execution in CLI (HFS handles in EXECUTION phase)
- GUI/web fallback (PROJECT.md: CLI-only for v1)
- Real-time collaboration (massive complexity)
- Over-animated UI (terminal users value speed)

### Architecture Approach

The abstraction layer follows **event sourcing lite**: events emitted during execution, state computed from events + OpenTelemetry data, and queryable via clean API. All concerns share Pydantic model hierarchy for JSON serialization.

**Three-layer design:**

1. **Event System**: Async event bus with typed Pydantic events
   - `EventBus`: In-process pub/sub with asyncio support
   - `EventStream`: Async generator for streaming to UI
   - Event categories: Lifecycle, Agent, Negotiation, Usage
   - Correlation with OpenTelemetry: Each event carries `trace_id` and `span_id`

2. **State Management**: Computed views, not persisted state
   - `StateManager`: Computes snapshots from events + orchestrator internals
   - Snapshots: `RunSnapshot`, `TriadSnapshot`, `AgentSnapshot`, `TokenUsage`
   - Sources: Event history, OpenTelemetry spans, orchestrator instance state

3. **Query Interface**: UI-agnostic, JSON-ready responses
   - `HFSQueryInterface`: Granular queries for specific data
   - Methods: `get_agent_tree()`, `get_trace_timeline()`, `get_usage_breakdown()`, `get_spec_status()`
   - All responses are Pydantic models with `model_dump()` for serialization

**OpenTelemetry integration strategy:**
- **Do not duplicate** what OTel already captures
- Extract data from existing 4-level span hierarchy (Run > Phase > Triad > Agent)
- Custom `EventEmittingSpanProcessor` bridges spans to event bus
- Events correlate with spans via trace/span IDs

**Major components:**
1. **Event Bus** (`hfs/abstraction/events/`) — Pub/sub with typed events, async generator streaming
2. **State Manager** (`hfs/abstraction/state/`) — Snapshot computation from events, usage accumulators
3. **Query Interface** (`hfs/abstraction/queries/`) — Clean API returning Pydantic models
4. **OpenTelemetry Bridge** (`hfs/abstraction/otel.py`) — Custom SpanProcessor for event emission
5. **Textual Widgets** (`hfs/cli/widgets/`) — UI components subscribing to events

### Critical Pitfalls

From PITFALLS.md, the top threats to success:

1. **Terminal rendering flickering during streaming**
   - **What goes wrong**: Each token triggers full re-render. Claude Code experienced 4,000-6,700 scroll events/sec in tmux causing severe jitter.
   - **Prevention**: Differential rendering (only update changed lines), frame rate limiting (Textual's config), batch token updates, test in tmux/screen early.
   - **Impact**: Unusable UI if not addressed. This is a showstopper.

2. **State synchronization complexity between events and HFS internals**
   - **What goes wrong**: Event-driven state diverges from actual HFS state. Race conditions, out-of-order events, missed events cause incorrect UI display.
   - **Prevention**: Design for eventual consistency, include sequence numbers in events, periodic full state snapshots (not just deltas), explicit reconciliation.
   - **Impact**: UI shows incorrect agent status, token counts don't match reality, debugging nightmare.

3. **Backpressure handling for token streams**
   - **What goes wrong**: LLM produces tokens faster than terminal renders. Without backpressure, tokens queue unbounded, memory grows, eventual crash.
   - **Prevention**: Explicit backpressure (pause stream when buffer exceeds threshold), drop intermediate frames if behind, set buffer limits, monitor queue depths.
   - **Impact**: Memory leak during long streaming, delayed token display in bursts, crash on long outputs.

4. **Alternate screen buffer cleanup failures**
   - **What goes wrong**: App crash or Ctrl+C leaves terminal corrupted (raw mode on, alternate screen not cleared, cursor hidden). User must manually `reset`.
   - **Prevention**: Register signal handlers (SIGINT, SIGTERM), call `app.exit()` in all exit paths, test crash scenarios explicitly.
   - **Impact**: Poor user experience, lost terminal history, broken terminal requires manual reset.

5. **Over-engineering the abstraction layer**
   - **What goes wrong**: Building elaborate event/query abstraction harder to use than underlying HFS code. "We might need this" thinking for imaginary future UIs.
   - **Prevention**: Start with simplest abstraction that works for CLI, build from concrete use cases not speculation, YAGNI principle.
   - **Impact**: Slower development, more maintenance burden, bugs in abstraction itself, harder debugging.

**Other significant pitfalls:**
- **Token-by-token rendering performance**: 50-100+ tokens/sec overwhelms terminal. Batch updates (every 50ms or 16 tokens).
- **Terminal size responsiveness**: Test at 80x24, use flexbox layout, handle resize events.
- **Color theme detection**: Query OSC 11, support CLITHEME env var, provide `--theme` flag fallback.
- **Multi-stream coordination**: Multiple agents streaming simultaneously create interleaved output. Separate panels or serialize output.

## Implications for Roadmap

Based on combined research findings, a 5-phase approach is recommended with clear rationale from architecture dependencies and pitfall mitigation.

### Phase 1: Event Foundation (Weeks 1-2)
**Rationale**: Everything depends on the event system. Must be solid before UI or state layer.
**Delivers**: Event models, event bus, async event streaming
**Key files**: `hfs/abstraction/events/` with models, bus, stream
**Avoids**: Over-engineering (start simple, no external dependencies like Redis)
**Research flag**: NO RESEARCH NEEDED - standard asyncio pub/sub patterns

### Phase 2: State Layer (Weeks 2-3)
**Rationale**: State manager depends on events. Query interface depends on state. Critical path.
**Delivers**: Snapshot models, state manager, usage accumulators
**Key files**: `hfs/abstraction/state/` with manager and models
**Implements**: Computed views pattern (state from events + OTel, not persisted)
**Avoids**: State synchronization pitfalls by designing for eventual consistency from start
**Research flag**: NO RESEARCH NEEDED - documented pattern, existing OTel instrumentation

### Phase 3: Query Interface & OTel Bridge (Weeks 3-4)
**Rationale**: Can parallelize. Query interface needs state layer. OTel bridge only needs events.
**Delivers**: Query API with Pydantic responses, custom SpanProcessor for event emission
**Key files**: `hfs/abstraction/queries/`, `hfs/abstraction/otel.py`
**Addresses**: Agent tree visualization (D-1), trace timeline (D-4), token tracking (D-3) feature requirements
**Avoids**: Leaky abstractions by defining clean interface first, then mapping HFS internals
**Research flag**: NO RESEARCH NEEDED - OTel SpanProcessor API is documented

### Phase 4: Textual UI Components (Weeks 4-6)
**Rationale**: Requires event system, state layer, and query interface. This is where differentiators come alive.
**Delivers**: Chat view with streaming, agent tree widget, negotiation display, status bar, trace timeline
**Addresses**: All table stakes (TS-1 through TS-8) and differentiators (D-1 through D-7)
**Avoids**:
  - Terminal flickering: Implement differential rendering, frame rate limiting from day 1
  - Token rendering performance: Batch updates (50ms or 16 tokens)
  - Multi-stream chaos: Separate panels for each agent with clear visual separation
**Uses**: Textual's reactive attributes for streaming, workers API for background LLM calls
**Research flag**: MODERATE RESEARCH - May need specific Textual widget patterns for complex layouts

### Phase 5: Orchestrator Integration & Polish (Weeks 6-7)
**Rationale**: Wire everything together. Add event emission to HFS orchestrator, expose query interface, integration testing.
**Delivers**: Modified `hfs/core/orchestrator.py`, new CLI entry points (`hfs chat`, `hfs inspect`), terminal cleanup, signal handling
**Addresses**: Error handling (TS-7), progress indication (TS-6), session continuity (TS-4)
**Avoids**:
  - Alternate screen cleanup failures: Signal handlers and explicit cleanup from start
  - Process lifecycle issues: Proper shutdown on Ctrl+C, error paths, crashes
**Integration tests**: Full pipeline with streaming, multi-agent triads, long outputs, crash recovery
**Research flag**: NO RESEARCH NEEDED - Integration patterns

### Phase Ordering Rationale

- **Dependencies**: Events → State → Queries → UI → Integration forms a clear dependency chain with only Phase 3 parallelizable
- **Risk mitigation**: Phase 1-3 builds solid foundation before UI complexity, allowing early detection of abstraction issues
- **Differentiators early**: Phase 4 implements all unique HFS features (agent tree, negotiation viz) that no competitor offers
- **Pitfall prevention**: Each phase addresses specific pitfalls from PITFALLS.md at the point where they naturally arise

### Build Order from Architecture Research

The architecture research provides explicit dependency graph:

```
Event Models (Pydantic)
    ↓
EventBus / StateManager / QueryModels (parallel)
    ↓
QueryInterface (unified)
    ↓
OTel Processor / Orchestrator Integration / CLI Consumer (parallel)
```

This maps to phases as:
- Phase 1 = Event Models + EventBus
- Phase 2 = StateManager
- Phase 3 = QueryInterface + OTel Processor (parallel)
- Phase 4 = CLI Consumer (Textual widgets)
- Phase 5 = Orchestrator Integration + testing

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 4 (Textual UI Components)**: MODERATE - Complex layouts for multi-agent display, negotiation visualization patterns may need custom widget research. Textual docs are good but specific composition patterns for "agent tree + chat + timeline" may require experimentation.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Event Foundation)**: Standard asyncio pub/sub, well-documented
- **Phase 2 (State Layer)**: Computed views from events, established pattern
- **Phase 3 (Query Interface & OTel)**: Pydantic serialization + OTel SpanProcessor API documented
- **Phase 5 (Integration)**: Standard integration testing and error handling

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (Textual) | HIGH | Verified with official docs, Toad demonstrates production viability for exact use case |
| Features | HIGH | Analyzed multiple modern AI CLIs (Gemini, Claude Code, OpenCode, Aider), clear patterns |
| Architecture | HIGH | Based on existing HFS codebase analysis + established Python patterns, no new dependencies |
| Pitfalls | HIGH | Verified via Claude Code issues, community reports, multiple sources agree on solutions |

**Overall confidence:** HIGH

The research converges on clear recommendations with verification from production systems. The Textual pivot is strongly supported by eliminating IPC complexity while Toad proves the pattern works for agentic UIs.

### Gaps to Address

1. **Textual layout complexity for multi-panel agent view**
   - **Gap**: While Textual is proven for TUIs, the specific layout pattern for "agent tree + chat + negotiation viz + timeline" simultaneously may need experimentation
   - **Handle**: Allocate time in Phase 4 for layout prototyping. Consider starting with simpler 2-panel view (chat + tree) before adding negotiation/timeline panels
   - **Confidence**: MEDIUM for complex layouts, HIGH for individual widgets

2. **Performance characteristics under high token volume**
   - **Gap**: Research identifies batching strategies but actual frame rate limits and buffer sizes for HFS's multi-agent output need tuning
   - **Handle**: Add performance testing early in Phase 4 with synthetic high-volume streams. Benchmark against Claude Code's stated 4000-6700 events/sec threshold
   - **Confidence**: HIGH on approach, MEDIUM on specific parameters

3. **Windows terminal compatibility**
   - **Gap**: Research notes Windows Terminal supports Textual but classic cmd.exe has limitations (16 colors). PROJECT.md doesn't specify Windows as primary target
   - **Handle**: Test on Windows Terminal (modern) but document cmd.exe as unsupported/limited
   - **Confidence**: LOW on cmd.exe, HIGH on Windows Terminal

4. **Theme detection reliability**
   - **Gap**: OSC 11 query for background color isn't universally supported. CLITHEME env var is emerging standard but not widespread
   - **Handle**: Implement detection with explicit `--theme` flag as reliable fallback. Default to dark theme (safer - won't have invisible text)
   - **Confidence**: MEDIUM - detection is best-effort, flag is reliable

## Technology Decision: Textual over Ink

This is the most significant finding from research. The rationale:

**Why Textual wins:**
- **Single language**: Python throughout, no IPC layer
- **Native integration**: Direct imports of HFS, Agno, OpenTelemetry
- **Proven for agentic CLIs**: Toad (by Rich/Textual creator Will McGugan) demonstrates production viability
- **Async-first**: Matches HFS's asyncio architecture
- **Maintenance**: One stack, one language, one debugging environment

**What Ink would have cost:**
- Python-JS IPC: Subprocess management, JSON serialization, potential deadlocks
- Dual stack: Node.js + Python maintenance burden
- Event serialization: OpenTelemetry spans need JSON marshaling
- Debugging complexity: Printf debugging breaks JSON-over-stdio protocol
- Platform-specific IPC: Windows vs Unix differences

**Trade-off accepted:**
- Team may have React familiarity making Ink appealing
- But Textual's CSS-like styling and component model is learnable
- IPC complexity would consume weeks that could go to features

**Production validation:**
- Toad uses Textual for Claude Code and Gemini CLI integration
- OpenHands deployed Toad in production
- Proves Textual can handle agentic AI workloads in terminals

## Sources

### Primary (HIGH confidence)
- [Textual Official Documentation](https://textual.textualize.io/) — Framework API, workers guide, reactivity
- [Toad GitHub](https://github.com/batrachianai/toad) — Production agentic coding TUI with Textual
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/) — SpanProcessor API, instrumentation patterns
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) — Feature benchmarking, flickering issues (#9935)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli) — Streaming performance, modern CLI patterns
- [Pydantic Serialization Docs](https://docs.pydantic.dev/latest/concepts/serialization/) — Event model patterns

### Secondary (MEDIUM confidence)
- [Building an Event Bus in Python with asyncio](https://www.joeltok.com/posts/2021-03-building-an-event-bus-in-python/) — Pub/sub patterns
- [LLM Streaming Latency Optimization](https://latitude-blog.ghost.io/blog/latency-optimization-in-llm-streaming-key-techniques/) — Batching strategies
- [Redis Streams for LLM Output](https://redis.io/learn/howtos/solutions/streams/streaming-llm-output) — Backpressure patterns
- [Event-Driven Architecture Pitfalls](https://medium.com/insiderengineering/common-pitfalls-in-event-driven-architectures-de84ad8f7f25) — State sync challenges
- [When NOT to Write an Abstraction Layer](https://codeopinion.com/when-not-to-write-an-abstraction-layer/) — YAGNI principles

### Tertiary (LOW confidence - for awareness)
- [TUI Library Comparison](https://blog.logrocket.com/7-tui-libraries-interactive-terminal-apps/) — Alternatives evaluated
- [CLI Theme Standard Proposal](https://wiki.tau.garden/cli-theme/) — CLITHEME env var
- [Python Subprocess Deadlock Warning](https://docs.python.org/3/library/subprocess.html) — IPC risks (if we had chosen Ink)

---
*Research completed: 2026-01-30*
*Ready for roadmap: yes*
