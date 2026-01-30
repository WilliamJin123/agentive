# Stack Research: HFS CLI

**Researched:** 2026-01-30
**Mode:** Focused Stack Analysis
**Confidence:** HIGH (verified with official docs and production references)

## Executive Summary

**Recommendation: Textual + Rich (pure Python)**

The PROJECT.md mentions "Ink-based CLI" but this reflects an initial assumption that should be revised. Ink (React for CLI) would require:
1. Node.js runtime alongside Python
2. IPC/subprocess communication between JS frontend and Python HFS core
3. Separate event serialization layer for streaming
4. Two tech stacks to maintain

**Textual is the superior choice** because:
1. Native Python - direct integration with HFS core, Agno, OpenTelemetry
2. Proven for agentic CLIs - [Toad](https://github.com/batrachianai/toad) by Will McGugan (creator of Rich/Textual) is a terminal UI for Claude Code, Gemini CLI, and other agents
3. Rich foundation - streaming markdown, syntax highlighting, progress bars out of the box
4. Async-first - workers API designed for background tasks with UI updates
5. Single stack - no subprocess marshaling, no IPC, no dual-language maintenance

---

## Recommended Stack

### Core TUI Framework

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Textual** | 3.x (latest) | Terminal UI framework | Native Python, async-first, CSS-like styling, proven for agentic CLIs (Toad). Full widget library with reactive attributes and message passing. |
| **Rich** | 14.x | Terminal rendering primitives | Foundation for Textual. Markdown rendering, syntax highlighting, progress bars, Live display for streaming. Already production-stable. |

**Why Textual over Ink:**

| Criterion | Textual | Ink |
|-----------|---------|-----|
| Language match | Python (same as HFS) | JavaScript (requires bridging) |
| Integration complexity | Direct imports | Subprocess + IPC |
| Event streaming | Native async/await + workers | Node child_process + JSON-RPC |
| Maintenance burden | Single stack | Dual stack (Python + Node) |
| Production references | Toad (agentic coding UI) | Claude Code, Gemini CLI |
| OpenTelemetry access | Direct span/trace access | Would need serialization |

**Confidence:** HIGH - Textual documentation verified, Toad demonstrates production viability for exact use case.

### Event/State Layer

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Pydantic** | 2.x (existing) | Event models, state serialization | Already in stack. JSON-ready models for inspection data. |
| **asyncio** | stdlib | Async coordination | Textual is asyncio-native. Workers use async tasks or threads. |

**Event Architecture Pattern:**

HFS core emits events (Python objects) -> Event bus (simple pub/sub) -> Textual widgets subscribe

No serialization needed since everything is Python. Events are Pydantic models for:
- Schema validation
- Easy JSON export for debugging/logging
- Type hints for IDE support

**Confidence:** HIGH - Standard Python patterns, no new dependencies.

### Streaming Integration

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Textual Workers** | (bundled) | Background task execution | `@work` decorator and `run_worker()` for non-blocking LLM calls. Supports both async and threaded workers. |
| **Rich Live** | (bundled) | Real-time display updates | `Live` context manager for auto-updating content. Used by Textual internally. |
| **Reactive Attributes** | (bundled) | UI state binding | `reactive()` descriptor triggers `watch_*` methods and automatic refresh on change. |

**Streaming Pattern for LLM Responses:**

```python
class ChatResponse(Widget):
    content = reactive("")

    def watch_content(self, new_content: str) -> None:
        # Called automatically when content changes
        self.refresh()  # Re-render widget

    @work(thread=False)  # Async worker
    async def stream_response(self, prompt: str) -> None:
        async for chunk in llm.stream(prompt):
            self.content += chunk  # Triggers watch_content
```

**Confidence:** HIGH - Pattern documented in [Textual Workers guide](https://textual.textualize.io/guide/workers/).

### OpenTelemetry Integration

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **opentelemetry-api** | 1.x (existing) | Tracing API | Already in stack. Direct span access from Textual widgets. |
| **opentelemetry-sdk** | 1.x (existing) | Tracing implementation | BatchSpanProcessor already configured. |

**Trace Visualization Pattern:**

Since Textual is Python, CLI can directly query the tracer provider:

```python
from hfs.observability import get_tracer
from opentelemetry import trace

# Access current span context directly - no serialization needed
current_span = trace.get_current_span()
span_context = current_span.get_span_context()
```

For trace timeline display, implement a custom SpanProcessor that emits to an event bus:

```python
class UISpanProcessor(SpanProcessor):
    def on_end(self, span: ReadableSpan) -> None:
        event_bus.emit(SpanCompleted(
            name=span.name,
            duration_ms=span.end_time - span.start_time,
            attributes=dict(span.attributes)
        ))
```

**Confidence:** HIGH - OpenTelemetry SDK is designed for this extensibility.

### CLI Commands/Entry Points

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **argparse** | stdlib (existing) | Command parsing | Already in use. Keep for `hfs run`, `hfs validate-config`. |
| **Textual App** | (bundled) | Interactive REPL | New entry point: `hfs chat` launches Textual App with REPL. |

**Entry Point Strategy:**

```
hfs                    # Show help (existing argparse)
hfs run [options]      # One-shot pipeline (existing, keep)
hfs validate-config    # Config validation (existing, keep)
hfs chat               # NEW: Launch Textual REPL
hfs inspect [run-id]   # NEW: Inspect past run (Textual tree view)
```

Non-interactive commands stay argparse. Interactive commands launch Textual.

**Confidence:** HIGH - Clean separation, no migration needed for existing commands.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **textual-dev** | latest | Development tools | Dev console for debugging widgets. Install with `pip install textual-dev`. |
| **rich-pixels** | latest | Image rendering | Only if hexagonal graphics needed. Probably not for v1.1. |
| **tree-sitter-languages** | latest | Syntax highlighting | If showing code in trace inspection. Rich has basic highlighting built-in. |

---

## Alternatives Considered

### Ink (React for CLI) - NOT RECOMMENDED

| Aspect | Assessment |
|--------|------------|
| **Pros** | Claude Code and Gemini CLI use it. Familiar React patterns. |
| **Cons** | Requires Node.js runtime. IPC complexity for Python backend. Two stacks to maintain. Would need event serialization layer. |
| **Verdict** | Wrong tool for Python-centric project. Makes sense when backend is also JS. |

**Sources:**
- [Ink GitHub](https://github.com/vadimdemedes/ink) - React for CLIs
- [Ink-Python IPC tutorial](https://starbeamrainbowlabs.com/blog/article.php?article=posts/549-js-python-ipc.html) - Shows the complexity

### Blessed/Neo-Blessed (Node.js) - NOT RECOMMENDED

| Aspect | Assessment |
|--------|------------|
| **Pros** | More low-level terminal control. |
| **Cons** | Same Node.js bridging problem as Ink. Less maintained. |
| **Verdict** | Superseded by Ink for JS terminal apps. |

### Urwid (Python) - NOT RECOMMENDED

| Aspect | Assessment |
|--------|------------|
| **Pros** | Mature, battle-tested Python TUI. |
| **Cons** | Old architecture (curses-based). No async-first design. Complex API. Styling is painful compared to Textual CSS. |
| **Verdict** | Superseded by Textual for modern Python TUIs. |

### Click/Typer Extensions - NOT RECOMMENDED

| Aspect | Assessment |
|--------|------------|
| **Pros** | Could add Rich progress bars to existing CLI. |
| **Cons** | Not a full TUI. No widget system. Can't build interactive REPL. |
| **Verdict** | Good for simple CLIs, but HFS needs real interactivity. |

### Prompt Toolkit - PARTIAL FIT

| Aspect | Assessment |
|--------|------------|
| **Pros** | Excellent for REPL input. Auto-complete, syntax highlighting, history. Used by IPython. |
| **Cons** | Not a full TUI framework. Would need to combine with Rich/Textual anyway. |
| **Verdict** | Could complement Textual for input, but Textual's `Input` widget may be sufficient. |

### Gradio/Streamlit/Chainlit - NOT RECOMMENDED

| Aspect | Assessment |
|--------|------------|
| **Pros** | Fast prototyping for AI chat UIs. |
| **Cons** | Web-based, not terminal. Different paradigm. |
| **Verdict** | Wrong category. These are web UIs, not terminal UIs. |

---

## Integration Points

### 1. HFS Core -> Event Layer

**Current:** HFS orchestrator runs 9-phase pipeline with asyncio.

**Integration:**
```python
# hfs/events/bus.py (new)
class EventBus:
    def __init__(self):
        self._subscribers: dict[type, list[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def emit(self, event: BaseModel) -> None:
        for handler in self._subscribers.get(type(event), []):
            handler(event)

# hfs/core/orchestrator.py (modification)
class HFSOrchestrator:
    def __init__(self, ..., event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()

    async def run(self, request: str) -> HFSResult:
        self.event_bus.emit(RunStarted(run_id=self.run_id, request=request))
        # ... existing pipeline ...
        self.event_bus.emit(PhaseCompleted(phase="deliberation", ...))
```

### 2. Event Layer -> Textual Widgets

**Pattern:** Textual widgets subscribe to event bus on mount.

```python
# hfs/cli/widgets/agent_tree.py
class AgentTreeView(Widget):
    def on_mount(self) -> None:
        self.app.event_bus.subscribe(AgentSpawned, self.on_agent_spawned)
        self.app.event_bus.subscribe(AgentCompleted, self.on_agent_completed)

    def on_agent_spawned(self, event: AgentSpawned) -> None:
        self.query_one(Tree).root.add_leaf(event.agent_id)
        self.refresh()
```

### 3. OpenTelemetry -> UI

**Pattern:** Custom SpanProcessor bridges to event bus.

```python
# hfs/observability/ui_processor.py
class UISpanProcessor(SpanProcessor):
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def on_start(self, span: Span, parent_context: Context) -> None:
        self.event_bus.emit(SpanStarted(
            trace_id=span.get_span_context().trace_id,
            span_id=span.get_span_context().span_id,
            name=span.name,
        ))

    def on_end(self, span: ReadableSpan) -> None:
        self.event_bus.emit(SpanEnded(
            span_id=span.get_span_context().span_id,
            duration_ns=span.end_time - span.start_time,
            status=span.status.status_code.name,
        ))
```

### 4. Agno Teams -> Streaming

**Pattern:** Agno agent responses are async generators. Textual workers consume them.

```python
# hfs/cli/widgets/chat.py
class ChatView(Widget):
    @work(thread=False)
    async def send_message(self, message: str) -> None:
        response_widget = ResponseMessage()
        self.mount(response_widget)

        async for chunk in self.app.run_pipeline_streaming(message):
            response_widget.content += chunk.text
            if chunk.tokens:
                self.app.token_counter.add(chunk.tokens)
```

---

## Not Recommended (Do Not Add)

| Technology | Why Not |
|------------|---------|
| **Node.js/npm** | Adds second runtime. Textual is pure Python. |
| **gRPC** | Overkill for in-process communication. |
| **Redis/Message Queue** | Overkill. Simple event bus is sufficient. |
| **SQLite for traces** | TiDB already exists for persistence. In-memory for live display. |
| **curses/ncurses** | Textual abstracts this away. |
| **TypeScript** | No JS needed. |

---

## Installation

### Production Dependencies

```bash
# Add to pyproject.toml [project.dependencies]
pip install textual>=3.0.0
# Rich is a dependency of Textual, installed automatically
```

### Development Dependencies

```bash
# Add to pyproject.toml [project.optional-dependencies.dev]
pip install textual-dev  # Dev console for debugging
```

### pyproject.toml Changes

```toml
[project]
dependencies = [
    # ... existing ...
    "textual>=3.0.0",
]

[project.optional-dependencies]
dev = [
    # ... existing ...
    "textual-dev",
]

[project.scripts]
hfs = "hfs.cli.main:main"
# Entry point unchanged - main.py dispatches to Textual for 'chat' command
```

---

## Version Verification

| Library | Claimed Version | Verification Source | Verified |
|---------|-----------------|---------------------|----------|
| Textual | 3.x | [Textual Docs](https://textual.textualize.io/getting_started/) | YES - "pip install textual" installs latest 3.x |
| Rich | 14.x | [PyPI](https://pypi.org/project/rich/) | YES - 14.3.1 released 2026-01-24 |
| Python | 3.11+ | PROJECT.md | YES - existing requirement |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Textual API changes | LOW | Pin major version. Textual 3.x is stable. |
| Performance with many events | LOW | Use batch updates, throttle refreshes. |
| Windows terminal compatibility | LOW | Textual tested on Windows Terminal. Classic cmd.exe limited to 16 colors. |
| Learning curve | MEDIUM | Team familiar with React (Ink was considered). Textual has good docs and patterns are similar. |

---

## Sources

**Official Documentation:**
- [Textual Official Docs](https://textual.textualize.io/) - Framework documentation
- [Textual Workers Guide](https://textual.textualize.io/guide/workers/) - Background tasks
- [Textual Events and Messages](https://textual.textualize.io/guide/events/) - Event system
- [Textual Reactivity](https://textual.textualize.io/guide/reactivity/) - Reactive attributes
- [Rich Documentation](https://rich.readthedocs.io/en/stable/) - Terminal rendering

**Production References:**
- [Toad GitHub](https://github.com/batrachianai/toad) - Will McGugan's agentic coding TUI built with Textual
- [Toad Announcement](https://willmcgugan.github.io/announcing-toad/) - Architecture details
- [OpenHands + Toad](https://openhands.dev/blog/20251218-openhands-toad-collaboration) - Production deployment

**Protocol/Integration:**
- [Agent Client Protocol (ACP)](https://zed.dev/acp) - Standardized agent communication
- [ACP GitHub](https://github.com/agentclientprotocol/agent-client-protocol) - Protocol spec

**Alternatives Evaluated:**
- [Ink GitHub](https://github.com/vadimdemedes/ink) - React for CLIs
- [Ink UI Components](https://github.com/vadimdemedes/ink-ui) - Component library
