# Phase 10: Textual Core - Research

**Researched:** 2026-01-31
**Domain:** Python Textual TUI Framework for Chat Interface
**Confidence:** HIGH

## Summary

This phase implements a rich terminal chat interface for HFS using Textual, the modern Python TUI framework. The interface requires streaming LLM responses with live markdown rendering, command history with fuzzy search, and a yellow/amber themed visual design.

Textual v7.5.0 (released 2026-01-30) provides all necessary capabilities including the v4.0.0 `Markdown.append()` streaming feature, workers for background tasks, reactive attributes for state management, and a comprehensive theming system. The framework integrates seamlessly with Rich for syntax highlighting and markdown rendering.

Key architectural decisions are constrained by Textual's thread safety model: UI updates must happen on the main thread via `call_from_thread()` or `post_message()`, and streaming content benefits from the `MarkdownStream` buffering layer that handles high-frequency token updates.

**Primary recommendation:** Use `Markdown.get_stream()` with workers for streaming responses, `RichLog` or custom `Static`-based message containers for chat history, and build a custom input widget wrapping `TextArea` to handle Enter vs Shift+Enter key bindings.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | >=7.5.0 | TUI framework | Textualize's flagship; built-in streaming markdown support since v4.0.0 |
| rich | >=14.3.1 | Rich text & markdown | Sister library to Textual; syntax highlighting via Pygments |
| prompt_toolkit | >=3.0.50 | History/readline features | Industry standard for CLI input; Ctrl+R search support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pygments | >=2.17.0 | Syntax highlighting | Code fence rendering in markdown |
| textual-dev | >=1.0.0 | Development tools | Debug console, CSS preview |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Textual Markdown widget | RichLog + manual rendering | RichLog faster but loses streaming optimization |
| prompt_toolkit history | Custom history file | Would need to reimplement Ctrl+R fuzzy search |

**Installation:**
```bash
pip install "textual>=7.5.0" "rich>=14.3.1" "prompt_toolkit>=3.0.50"
pip install "textual-dev>=1.0.0"  # Development only
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── tui/                      # New TUI package
│   ├── __init__.py
│   ├── app.py               # Main HFSApp class
│   ├── screens/
│   │   └── chat.py          # Primary chat screen
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── chat_input.py    # Custom input widget
│   │   ├── message_list.py  # Chat message container
│   │   ├── message.py       # Single message widget
│   │   ├── spinner.py       # Hex-themed spinner
│   │   └── status_bar.py    # Custom footer
│   ├── styles/
│   │   └── theme.tcss       # Textual CSS theme
│   └── theme.py             # HFS custom theme definition
├── cli/
│   └── main.py              # Modified for REPL entry point
```

### Pattern 1: Streaming Markdown with Workers
**What:** Use `@work` decorator with `Markdown.get_stream()` for token-by-token LLM streaming
**When to use:** Displaying LLM responses that arrive token-by-token
**Example:**
```python
# Source: https://textual.textualize.io/widgets/markdown/ + v4.0.0 release
from textual.app import App
from textual.widgets import Markdown, VerticalScroll
from textual import work

class ChatApp(App):
    @work
    async def stream_response(self, user_message: str) -> None:
        """Stream LLM response with optimized markdown rendering."""
        markdown_widget = self.query_one("#response", Markdown)
        container = self.query_one("#chat-container", VerticalScroll)
        container.anchor()  # Lock to bottom for auto-scroll

        stream = Markdown.get_stream(markdown_widget)
        try:
            async for token in self.llm_client.stream(user_message):
                await stream.write(token)
        finally:
            await stream.stop()
            container.release_anchor()  # Allow manual scrolling
```

### Pattern 2: Thread-Safe UI Updates from Workers
**What:** Use `call_from_thread()` or `post_message()` for UI updates from thread workers
**When to use:** When streaming API (like Anthropic) uses synchronous HTTP client
**Example:**
```python
# Source: https://textual.textualize.io/guide/workers/
from textual import work
from textual.worker import get_current_worker

@work(thread=True)
def fetch_streaming_response(self, prompt: str) -> None:
    """Thread worker for synchronous streaming API."""
    worker = get_current_worker()

    for chunk in sync_api_call(prompt):  # Blocking API
        if worker.is_cancelled:
            break
        # Thread-safe UI update
        self.call_from_thread(self.update_response, chunk)
```

### Pattern 3: Chat Message Container with Smart Scroll
**What:** Use VerticalScroll with anchor/release pattern for chat-style auto-scroll
**When to use:** Chat interfaces where new messages appear at bottom
**Example:**
```python
# Source: https://github.com/Textualize/textual/discussions/5674
from textual.containers import VerticalScroll

class ChatContainer(VerticalScroll):
    """Chat container that auto-scrolls to bottom for new messages."""

    auto_scroll: bool = True

    def on_mount(self) -> None:
        self.anchor()

    async def add_message(self, content: str, is_user: bool) -> None:
        """Add message and scroll to bottom if auto_scroll enabled."""
        message = ChatMessage(content, is_user=is_user)
        await self.mount(message)

        if self.auto_scroll and not self.is_vertical_scrollbar_grabbed:
            self.scroll_end(animate=False, immediate=True)
```

### Pattern 4: Custom Keybinding for Enter vs Shift+Enter
**What:** Override TextArea key handling to differentiate submission from newline
**When to use:** Single input that auto-grows but submits on Enter
**Example:**
```python
# Source: https://textual.textualize.io/guide/input/
from textual.widgets import TextArea
from textual.binding import Binding

class ChatInput(TextArea):
    """Multi-line input that submits on Enter, newline on Shift+Enter."""

    BINDINGS = [
        Binding("enter", "submit", "Send", show=False),
        Binding("shift+enter", "newline", "New Line", show=False),
    ]

    def action_submit(self) -> None:
        """Submit the message."""
        text = self.text.strip()
        if text:
            self.post_message(self.Submitted(self, text))
            self.clear()

    def action_newline(self) -> None:
        """Insert a newline."""
        self.insert("\n")

    class Submitted(Message):
        """Posted when user submits input."""
        def __init__(self, input_widget: "ChatInput", text: str) -> None:
            super().__init__()
            self.text = text
```

### Pattern 5: Custom Theme Registration
**What:** Define custom theme with HFS yellow/amber colors
**When to use:** App-wide theming with brand colors
**Example:**
```python
# Source: https://textual.textualize.io/guide/design/
from textual.theme import Theme

HFS_THEME = Theme(
    name="hfs",
    primary="#F59E0B",      # Yellow/amber - THEME-01
    secondary="#D97706",     # Darker amber
    accent="#FCD34D",        # Light yellow accent
    foreground="#F5F5F5",
    background="#1A1A1A",
    surface="#262626",
    panel="#333333",
    warning="#EAB308",
    error="#EF4444",
    success="#22C55E",
    dark=True,
    variables={
        # Triad type colors - THEME-02
        "$hfs-hierarchical": "#3B82F6",   # Blue
        "$hfs-dialectic": "#A855F7",      # Purple
        "$hfs-consensus": "#22C55E",      # Green
    }
)

class HFSApp(App):
    def on_mount(self) -> None:
        self.register_theme(HFS_THEME)
        self.theme = "hfs"
```

### Anti-Patterns to Avoid
- **Blocking the event loop:** Never use `time.sleep()` or blocking I/O in async methods; use workers
- **Direct UI updates from threads:** Always use `call_from_thread()` or `post_message()` from thread workers
- **Chained thread workers:** Calling a thread worker from within a thread worker causes crashes
- **Heavy widget updates during streaming:** Markdown parser can block; use `MarkdownStream` buffer

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom parser | `Markdown` widget | Full CommonMark support, syntax highlighting, streaming optimization |
| Command history | File-based history | prompt_toolkit `FileHistory` | Handles edge cases, Ctrl+R search built-in |
| Syntax highlighting | Regex coloring | Rich `Syntax` + Pygments | 500+ language support, themes |
| Scrollable container | Manual scroll tracking | `VerticalScroll` + `anchor()` | Built-in keyboard bindings, smooth scrolling |
| Loading animation | Manual frame updates | `LoadingIndicator` or animated CSS | Performance optimized, theme-aware |
| Key binding management | Manual key event handling | `BINDINGS` + actions | Priority handling, conflict resolution |

**Key insight:** Textual's widget system handles complex layout, focus management, and event bubbling. Custom widgets should compose built-in widgets rather than reimplementing base functionality.

## Common Pitfalls

### Pitfall 1: Markdown Streaming Performance
**What goes wrong:** UI freezes or lags behind token stream at high rates (100+ tokens/sec)
**Why it happens:** Markdown-it-py parser runs on each update; large documents slow down
**How to avoid:** Use `Markdown.get_stream()` which buffers updates and only parses the last block
**Warning signs:** Visible delay between token arrival and display; UI feels sluggish

### Pitfall 2: Thread Worker UI Updates
**What goes wrong:** Random exceptions, widget state corruption, or crashes
**Why it happens:** Direct widget method calls from thread workers bypass Textual's thread safety
**How to avoid:** Always use `call_from_thread()` for widget updates or `post_message()` for events
**Warning signs:** Sporadic failures, "not on main thread" errors, inconsistent widget state

### Pitfall 3: Scroll Position Race Conditions
**What goes wrong:** Chat auto-scroll jumps erratically or doesn't follow new messages
**Why it happens:** Scroll updates compete with content updates; user scroll intention unclear
**How to avoid:** Check `is_vertical_scrollbar_grabbed` before auto-scrolling; use `anchor()` pattern
**Warning signs:** Scroll position resets while user is reading; missed messages at bottom

### Pitfall 4: TextArea vs Input Widget Confusion
**What goes wrong:** Enter key inserts newline instead of submitting; single-line Input can't grow
**Why it happens:** `Input` is explicitly single-line; `TextArea` doesn't submit on Enter by default
**How to avoid:** Use `TextArea` with custom key bindings that differentiate Enter vs Shift+Enter
**Warning signs:** User confusion about how to submit; overflow issues with long input

### Pitfall 5: Async Worker Lifecycle
**What goes wrong:** Workers continue running after screen closes; resource leaks
**Why it happens:** Workers tied to DOM node lifecycle; orphaned workers not cancelled
**How to avoid:** Check `is_cancelled` in loops; use `exclusive=True` for singleton operations
**Warning signs:** Background activity after navigation; duplicate responses

### Pitfall 6: CSS Specificity Conflicts
**What goes wrong:** Styles don't apply; unexpected visual appearance
**Why it happens:** Widget `DEFAULT_CSS` vs app CSS specificity; missing selectors
**How to avoid:** Use `!important` sparingly; prefer class selectors; test with `textual colors`
**Warning signs:** Widgets ignore theme; inconsistent colors across app

## Code Examples

Verified patterns from official sources:

### Custom Themed Footer/Status Bar
```python
# Source: Textual widgets/footer + guide/design
from textual.widgets import Footer
from textual.reactive import reactive

class HFSStatusBar(Footer):
    """Custom status bar showing model, tokens, and active agents."""

    model_name: reactive[str] = reactive("claude-3-sonnet")
    token_count: reactive[int] = reactive(0)
    active_agents: reactive[list[str]] = reactive(list)

    def compose(self) -> ComposeResult:
        yield Static(id="model-info")
        yield Static(id="token-info")
        yield Static(id="agent-info")

    def watch_token_count(self, count: int) -> None:
        self.query_one("#token-info", Static).update(f"Tokens: {count:,}")

    def watch_active_agents(self, agents: list[str]) -> None:
        text = ", ".join(agents) if agents else "None"
        self.query_one("#agent-info", Static).update(f"Agents: {text}")
```

### Pulsing Dot Loading Indicator
```python
# Source: Textual guide/animation + LoadingIndicator pattern
from textual.widgets import Static
from textual.reactive import reactive

class PulsingDot(Static):
    """Pulsing dot indicator for streaming state (CONTEXT.md decision)."""

    DEFAULT_CSS = """
    PulsingDot {
        width: auto;
        height: 1;
        color: $primary;
    }
    """

    is_pulsing: reactive[bool] = reactive(False)

    def on_mount(self) -> None:
        self.set_interval(0.5, self._pulse)

    def _pulse(self) -> None:
        if self.is_pulsing:
            # Animate opacity between 0.3 and 1.0
            current = self.styles.opacity
            target = 0.3 if current > 0.6 else 1.0
            self.styles.animate("opacity", target, duration=0.4)

    def render(self) -> str:
        return "..." if self.is_pulsing else ""
```

### Entry Point with REPL Mode
```python
# Source: setuptools entry_points + Textual App pattern
# hfs/cli/main.py modification

def main() -> int:
    """Main entry point for HFS CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # ENTRY-02: Default to REPL mode when no command given
    if args.command is None:
        from hfs.tui.app import HFSApp
        app = HFSApp()
        app.run()
        return 0

    # Existing command handlers...
    return handler(args)
```

### Slash Command Handler
```python
# Source: Textual input handling patterns
SLASH_COMMANDS = {
    "/help": "show_help",
    "/clear": "clear_conversation",
    "/exit": "quit",
}

async def handle_input(self, text: str) -> None:
    """Process user input, handling slash commands (CHAT-05, 06, 07)."""
    if text.startswith("/"):
        cmd = text.split()[0].lower()
        if cmd in SLASH_COMMANDS:
            action = getattr(self, f"action_{SLASH_COMMANDS[cmd]}", None)
            if action:
                action()
                return
        self.notify(f"Unknown command: {cmd}", severity="warning")
        return

    # Regular chat message
    await self.send_message(text)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Markdown.update()` for streaming | `Markdown.append()` + `get_stream()` | Textual v4.0.0 (Jul 2025) | 10x faster streaming; no parse blocking |
| `ScrollView` for scrolling | `VerticalScroll` + `anchor()` | Textual v4.0.0 | Built-in chat-style scroll behavior |
| Manual thread synchronization | `@work` decorator | Stable since v0.31.0 | Cleaner async/thread worker pattern |
| Basic 16 colors | Theme system with 16.7M colors | Mature | Brand-consistent theming |

**Deprecated/outdated:**
- `ScrollView`: Documentation says "typically the wrong class"; use `VerticalScroll` instead
- `@work` without `thread=True` for threads: Required since v0.31.0 to prevent accidental thread workers

## Open Questions

Things that couldn't be fully resolved:

1. **Hexagonal spinner animation**
   - What we know: Textual supports CSS animations and `set_interval` for frame updates
   - What's unclear: Best approach for custom Unicode hexagon animation vs CSS-based
   - Recommendation: Start with pulsing dot (CONTEXT.md decision); hex spinner can be a Static widget with interval-based frame updates

2. **prompt_toolkit integration within Textual**
   - What we know: Both handle terminal input; potential conflicts
   - What's unclear: Whether to use prompt_toolkit for history or build custom
   - Recommendation: Textual's TextArea lacks Ctrl+R; may need custom history widget that bridges to prompt_toolkit's history, or implement fuzzy search in Textual

3. **Large paste abbreviation (Claude Code style)**
   - What we know: TextArea accepts paste; need to detect and truncate
   - What's unclear: Hook point for paste interception in Textual
   - Recommendation: Handle in `on_text_area_changed` event; if delta > threshold, abbreviate

## Sources

### Primary (HIGH confidence)
- [Textual Official Docs](https://textual.textualize.io/) - Widgets, workers, CSS, reactivity, animation
- [Textual v4.0.0 Release](https://github.com/Textualize/textual/releases/tag/v4.0.0) - Markdown streaming, anchor() changes
- [Textual v7.5.0 PyPI](https://pypi.org/project/textual/) - Current version confirmation (Jan 30, 2026)
- [Rich Documentation](https://rich.readthedocs.io/en/latest/markdown.html) - Markdown and Syntax classes
- [Will McGugan's Streaming Markdown](https://willmcgugan.github.io/streaming-markdown/) - Four optimizations for efficient streaming

### Secondary (MEDIUM confidence)
- [GitHub Discussion #5674](https://github.com/Textualize/textual/discussions/5674) - Chat UI scroll pinning pattern
- [prompt_toolkit docs](https://python-prompt-toolkit.readthedocs.io/) - FileHistory, Ctrl+R search
- [Claude Code vs Gemini CLI comparison](https://shipyard.build/blog/claude-code-vs-gemini-cli/) - UI design conventions

### Tertiary (LOW confidence)
- Medium articles on Textual chat UIs - Specific implementations may vary

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official docs, PyPI, release notes verified
- Architecture: HIGH - Official patterns from Textual docs and release notes
- Pitfalls: HIGH - Documented in official FAQ, worker guide, and GitHub discussions
- Code examples: MEDIUM - Synthesized from official docs but not all tested

**Research date:** 2026-01-31
**Valid until:** 2026-03-01 (30 days; Textual releases frequently but patterns stable)
