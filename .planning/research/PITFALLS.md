# Pitfalls Research: HFS CLI

**Domain:** Rich CLI frontend for AI/agent systems (Ink-based terminal UI)
**Researched:** 2026-01-30
**Context:** Adding Ink-based CLI to existing Python HFS framework with streaming LLM responses, agent tree inspection, and event/state abstraction layer

## Terminal UI Pitfalls

### Critical: Terminal Rendering Flickering

**What goes wrong:** Streaming LLM output causes severe flickering and visual corruption. Claude Code's initial implementation experienced 4,000-6,700 scroll events per second when running inside terminal multiplexers, causing severe UI jitter.

**Why it happens:** Each token streamed from the LLM triggers a re-render. Without batching or differential rendering, the terminal receives far more updates than it can process smoothly. Terminal multiplexers (tmux, screen) make this worse because they add their own rendering layers.

**Consequences:**
- Unusable UI during streaming
- User fatigue and frustration
- Perceived poor quality even if underlying functionality works

**Prevention:**
- Implement differential/incremental rendering (only update changed lines)
- Batch updates and limit frame rate (Ink's `framesPerSecond` option)
- Use synchronized output (DEC mode 2026) where supported
- Test in tmux/screen, not just bare terminal

**Detection:**
- Run streaming output in tmux and observe flicker
- Count scroll events per second (should be <100)
- Test on slower terminals (not just iTerm2/Ghostty)

**Phase to address:** Early architecture phase - must design rendering strategy before building UI components

**Sources:**
- [Claude Code flickering issues](https://github.com/anthropics/claude-code/issues/9935)
- [Claude Code rendering rewrite](https://www.threads.com/@boris_cherny/post/DSZbZatiIvJ)

---

### Critical: Alternate Screen Buffer Management

**What goes wrong:** Application crashes or ctrl+C exits leave terminal in corrupted state (raw mode still on, alternate screen not cleared, cursor hidden).

**Why it happens:** Fullscreen terminal apps use the alternate screen buffer and raw mode. If cleanup doesn't run (crash, unhandled signal), the user's terminal is left broken.

**Consequences:**
- User must manually reset terminal (`reset` command)
- Lost terminal history
- Poor user experience

**Prevention:**
- Always register signal handlers (SIGINT, SIGTERM, SIGQUIT)
- Call `render().unmount()` in all exit paths
- Use `fullscreen-ink` package for proper alternate screen handling
- Test crash scenarios explicitly

**Detection:**
- Kill process with `kill -9` and check terminal state
- Test ctrl+C during streaming operations

**Phase to address:** Foundation phase - terminal lifecycle management is core infrastructure

**Sources:**
- [Ink fullscreen mode discussion](https://github.com/vadimdemedes/ink/issues/263)
- [fullscreen-ink npm package](https://www.npmjs.com/package/fullscreen-ink)
- [Terminal alternate screen buffer](https://terminalguide.namepad.de/mode/p47/)

---

### Moderate: Terminal Size and Responsiveness

**What goes wrong:** UI renders incorrectly on different terminal sizes. Content overflows, wraps unexpectedly, or renders on top of itself.

**Why it happens:** Unlike web where overflow can scroll, terminal UIs are confined to the visible window. Building a layout that assumes specific dimensions breaks on smaller terminals.

**Consequences:**
- Unreadable UI on narrow terminals
- Critical information cut off
- User confusion

**Prevention:**
- Use Ink's Yoga flexbox layout for responsive design
- Subscribe to terminal resize events (`useStdout` hook)
- Test at minimum viable size (80x24 is classic minimum)
- Provide graceful degradation for very small terminals

**Detection:**
- Resize terminal during operation
- Test in 80-column mode
- Test in split pane configurations

**Phase to address:** UI component phase - design responsive layouts from the start

**Sources:**
- [Twilio conference CLI terminal size challenges](https://www.twilio.com/en-us/blog/developers/building-conference-cli-in-react)

---

### Moderate: Color Theme Detection

**What goes wrong:** Light text on light background or dark text on dark background becomes invisible. App looks professional on dark terminals but unreadable on light ones.

**Why it happens:** Terminal color schemes vary wildly. There's no universal standard for detecting dark vs light mode. Different terminals support different detection methods.

**Consequences:**
- Invisible text in some terminals
- Accessibility failures
- User frustration ("this app doesn't work")

**Prevention:**
- Query terminal background color via OSC 11 escape sequence
- Support CLITHEME environment variable (emerging standard)
- On macOS, check `defaults read -globalDomain AppleInterfaceStyle`
- Provide explicit `--theme dark/light` flag as fallback
- Test with both dark and light terminal themes

**Detection:**
- Test in Terminal.app (light default), iTerm2 (dark default), VS Code terminal
- Check if your yellow accent color is visible on both themes

**Phase to address:** Theming phase - but architecture should anticipate theme switching

**Sources:**
- [Automatic dark mode for terminal apps](https://arslan.io/2025/06/06/automatic-dark-mode-for-terminal-apps-revisited/)
- [CLI theme standard proposal](https://wiki.tau.garden/cli-theme/)

---

### Minor: stdin and Raw Mode Conflicts

**What goes wrong:** Creating temporary readline interfaces (for autocomplete, paste detection) breaks Ink's input handling. stdin becomes unresponsive after readline.close().

**Why it happens:** Ink manages stdin in raw mode. Mixing this with Node's readline API causes state conflicts. This is especially problematic in Bun.

**Consequences:**
- Keyboard input stops working
- App appears frozen
- Hard to diagnose

**Prevention:**
- Use only Ink's `useInput` and `useStdin` hooks
- Don't mix raw readline with Ink
- If you must use readline, fully restore stdin state after
- Test thoroughly in both Node.js and Bun

**Detection:**
- Test any input mode transitions
- Test paste operations

**Phase to address:** Input handling phase - establish input patterns early

**Sources:**
- [Bun Ink readline issue](https://github.com/oven-sh/bun/issues/21189)

---

## Streaming Pitfalls

### Critical: Token-by-Token Rendering Performance

**What goes wrong:** Rendering every token as it arrives overwhelms the terminal. CPU spikes, UI becomes unresponsive, tokens appear to "stutter."

**Why it happens:** LLM streaming can produce 50-100+ tokens per second. Naive implementation re-renders the entire UI for each token.

**Consequences:**
- High CPU usage
- Laggy, stuttering display
- Poor perceived performance

**Prevention:**
- Buffer tokens and render in batches (e.g., every 50ms or 16 tokens)
- Use Ink's `framesPerSecond` to cap update frequency
- Only re-render the streaming content area, not full UI
- Use `print(..., flush=True)` pattern equivalent in JS

**Detection:**
- Monitor CPU during streaming
- Compare visual smoothness against Claude Code, Gemini CLI
- Measure time-to-first-token vs time-to-render-first-token

**Phase to address:** Streaming infrastructure phase - fundamental to agent output display

**Sources:**
- [Latency optimization in LLM streaming](https://latitude-blog.ghost.io/blog/latency-optimization-in-llm-streaming-key-techniques/)
- [Streaming events in OpenAI Agents SDK](https://medium.com/@abdulkabirlive1/streaming-events-in-openai-agents-sdk-complete-expert-guide-b79c1ccd9714)

---

### Critical: Backpressure Handling

**What goes wrong:** Slow terminal rendering causes event/token backlog. Memory grows unbounded. Eventually crashes or exhibits strange behavior as delayed events arrive in bursts.

**Why it happens:** LLM produces tokens faster than terminal can render. Without backpressure, tokens queue up indefinitely. Redis Streams calls this the "fast producer/slow consumer" problem.

**Consequences:**
- Memory leak during long streaming sessions
- Delayed token display (tokens arrive in bursts)
- Potential crash on long outputs

**Prevention:**
- Implement explicit backpressure (pause stream when buffer exceeds threshold)
- Drop intermediate frames if behind (show latest state)
- Set buffer limits in event/state layer
- Monitor queue depths

**Detection:**
- Run very long streaming outputs (10,000+ tokens)
- Artificially slow down rendering
- Monitor memory during streaming

**Phase to address:** Event/state layer phase - backpressure is an infrastructure concern

**Sources:**
- [Redis Streams for LLM output](https://redis.io/learn/howtos/solutions/streams/streaming-llm-output)

---

### Moderate: Multi-Stream Coordination

**What goes wrong:** Multiple agents streaming simultaneously create interleaved, incomprehensible output. User can't tell which agent produced which content.

**Why it happens:** HFS triads have multiple agents. If they stream in parallel without UI coordination, outputs interleave.

**Consequences:**
- Confusing display
- Lost context
- User can't follow agent reasoning

**Prevention:**
- Design UI to show multiple agent streams in separate panels
- Or serialize agent output (one at a time)
- Clear visual separation with agent labels, colors, borders
- Consider collapsible sections for verbose agents

**Detection:**
- Run triad negotiation with streaming enabled
- Verify each agent's output is distinguishable

**Phase to address:** Agent display phase - requires UI component design

---

## Abstraction Layer Pitfalls

### Critical: Over-Engineering the Event Layer

**What goes wrong:** Building an elaborate event/query abstraction that's harder to use than the underlying HFS code. Adding abstraction for imaginary future UIs that never materialize.

**Why it happens:** Anticipating web UI leads to building generic abstractions. "We might need this" thinking. Each abstraction layer adds indirection.

**Consequences:**
- Slower development velocity
- More code to maintain
- Bugs in abstraction layer itself
- Harder to debug (more layers to trace through)

**Prevention:**
- Start with the simplest abstraction that works for CLI
- Build abstraction from concrete use cases, not speculation
- Single use case doesn't justify abstraction
- Prefer stable logic for abstraction (volatile requirements = constant churn)
- "You Aren't Gonna Need It" (YAGNI)

**Detection:**
- If abstraction API is more complex than HFS API, you've over-engineered
- If you're adding generic capabilities "for later," stop

**Phase to address:** Architecture phase - establish clear boundaries early

**Sources:**
- [When NOT to write an abstraction layer](https://codeopinion.com/when-not-to-write-an-abstraction-layer/)
- [API design pitfalls](https://readme.com/resources/api-design)

---

### Critical: State Synchronization Complexity

**What goes wrong:** Event-driven state layer gets out of sync with actual HFS state. UI shows stale or incorrect data. Race conditions between events.

**Why it happens:** HFS runs in Python, events cross process boundary to JS UI. Network/IPC delays, out-of-order events, missed events all cause divergence.

**Consequences:**
- UI shows incorrect agent state
- Token counts don't match reality
- Debugging becomes nightmare (which state is wrong?)

**Prevention:**
- Design for eventual consistency, not perfect sync
- Include sequence numbers in events to detect gaps/reordering
- Periodic full state snapshots (not just deltas)
- UI shows "last updated" timestamps
- Explicit reconciliation mechanism

**Detection:**
- Compare UI state to Python state at various points
- Artificially delay events to test out-of-order handling
- Kill and restart UI mid-operation

**Phase to address:** Event/state layer phase - core design decision

**Sources:**
- [Event-driven architecture pitfalls](https://medium.com/insiderengineering/common-pitfalls-in-event-driven-architectures-de84ad8f7f25)

---

### Moderate: Leaky Abstractions

**What goes wrong:** Abstraction layer exposes internal HFS details that shouldn't leak to UI. Changes to HFS internals break CLI.

**Why it happens:** Rushed abstraction design. Taking existing data structures and wrapping them minimally.

**Consequences:**
- Tight coupling despite abstraction
- HFS refactoring breaks CLI
- Abstraction provides no value

**Prevention:**
- Design abstraction interface first (what does CLI need?)
- Map HFS internals to abstraction types (don't pass through)
- Abstraction layer owns its data models (Pydantic)
- Test that abstraction survives HFS refactoring

**Detection:**
- If CLI code references HFS internals, abstraction is leaky
- If changing HFS breaks CLI tests, coupling is too tight

**Phase to address:** Architecture phase - define clean boundaries

---

## Integration Pitfalls

### Critical: Python-JS IPC Deadlocks

**What goes wrong:** Python subprocess blocks waiting for JS to read stdout while JS blocks waiting for Python to read its input. Classic pipe buffer deadlock.

**Why it happens:** OS pipe buffers are limited (~64KB). If Python writes more than buffer capacity without JS reading, Python blocks. If JS waits for Python response, deadlock.

**Consequences:**
- App hangs indefinitely
- No error message (just frozen)
- Intermittent (depends on output size)

**Prevention:**
- Use `asyncio.create_subprocess_exec` with `communicate()` for safety
- Read stdout/stderr continuously in separate async tasks
- Set explicit buffer limits
- Don't use `process.wait()` with pipes - use `communicate()`
- Frame messages (JSON newline-delimited) and flush after each

**Detection:**
- Test with large outputs (agents can produce thousands of tokens)
- Test with rapid back-and-forth communication
- Add timeout to all IPC operations

**Phase to address:** IPC layer phase - foundational infrastructure

**Sources:**
- [Python subprocess deadlock warning](https://docs.python.org/3/library/subprocess.html)
- [Python-JS IPC approaches](https://levelup.gitconnected.com/inter-process-communication-between-node-js-and-python-2e9c4fda928d)

---

### Critical: Debugging stdin/stdout IPC

**What goes wrong:** Can't add print statements for debugging because stdout is the communication channel. Logs corrupt the protocol.

**Why it happens:** JSON-over-stdio protocols use stdout for messages. Print debugging writes to same stdout, breaking parsing.

**Consequences:**
- "Works but can't debug" frustration
- Broken protocol from stray prints
- Hard to diagnose issues

**Prevention:**
- Use stderr for debug logs (but note: JSPyBridge uses stderr for its protocol)
- Log to file instead of stdout
- Use structured logging that writes to separate channel
- Environment variable to enable debug mode

**Detection:**
- Try to add a print statement; does it break the app?

**Phase to address:** IPC layer phase - establish logging patterns early

**Sources:**
- [JS-Python IPC limitations](https://starbeamrainbowlabs.com/blog/article.php?article=posts/549-js-python-ipc.html)

---

### Moderate: Platform-Specific IPC

**What goes wrong:** IPC approach that works on macOS/Linux fails on Windows. Or vice versa.

**Why it happens:** Unix named pipes don't exist on Windows. Windows named pipes are different. Signal handling differs. Path handling differs.

**Consequences:**
- Windows users can't use CLI
- Or Linux users can't use CLI
- Platform-specific bugs

**Prevention:**
- Use cross-platform primitives (stdio, TCP sockets)
- Test on all target platforms early
- Avoid Unix-specific features (named pipes, signals beyond SIGINT/SIGTERM)

**Detection:**
- Run full test suite on Windows
- Check for platform-specific code paths

**Phase to address:** IPC layer phase - design for cross-platform from start

---

### Moderate: Process Lifecycle Management

**What goes wrong:** Parent process exits but child keeps running (zombie). Or child crashes and parent doesn't notice. Or cleanup code never runs.

**Why it happens:** Process management is hard. Signal propagation, exit codes, and cleanup require explicit handling.

**Consequences:**
- Orphan processes consuming resources
- User thinks they exited but HFS is still running
- Inconsistent state on restart

**Prevention:**
- Use process groups for reliable termination
- Implement heartbeat between processes
- Parent monitors child exit
- Explicit cleanup on all exit paths
- Test kill -9 scenarios

**Detection:**
- Exit CLI and check if Python process is still running
- Kill CLI and check for orphans
- Run `ps aux | grep hfs` after exiting

**Phase to address:** IPC layer phase - must handle from beginning

---

## Testing Pitfalls

### Moderate: Terminal UI Testing Complexity

**What goes wrong:** Can't write automated tests for terminal UI. Everything requires manual testing. Bugs slip through.

**Why it happens:** Terminal UIs are harder to test than web UIs. No equivalent of Playwright for terminals. Ink testing utilities exist but are limited.

**Consequences:**
- Low test coverage
- Regressions
- Fear of refactoring

**Prevention:**
- Use Ink's `render()` test utilities for component testing
- Separate logic from rendering (test logic in isolation)
- Use snapshot testing for UI output
- Consider BATS (Bash Automated Testing System) for CLI integration tests
- Use `expect` or `autoexpect` for interactive scenarios

**Detection:**
- Try to write a test for a UI component; if it's painful, improve testability

**Phase to address:** Testing phase - but design for testability from start

**Sources:**
- [CLI testing with BATS and expect](https://pkaramol.medium.com/end-to-end-command-line-tool-testing-with-bats-and-auto-expect-7a4ffb19336d)

---

## Technology Choice Pitfalls

### Critical: Python-JS Bridge Complexity vs Native Python TUI

**What goes wrong:** Building a Python-JS bridge adds months of work when Textual (Python-native TUI) could do the job. Or choosing Textual when Ink's React model is genuinely better for the use case.

**Why it happens:** Technology preference vs pragmatic choice. Ink is appealing (React familiarity) but adds cross-language complexity.

**Consequences:**
- Months of IPC debugging
- Two languages to maintain
- Or: Missed opportunity for better developer experience

**Prevention:**
- Honestly evaluate: Is Ink's React model worth the Python-JS bridge complexity?
- Consider Textual (Python-native, CSS styling, rich components)
- Prototype both approaches before committing
- If choosing Ink, accept and budget for IPC complexity

**Detection:**
- Spending more time on IPC than UI? Consider native Python
- Textual can't express your UI vision? Ink may be worth it

**Phase to address:** Technology selection phase - decide before building

**Sources:**
- [Textual documentation](https://textual.textualize.io/)
- [TUI library comparison](https://blog.logrocket.com/7-tui-libraries-interactive-terminal-apps/)

---

## Prevention Checklist

### Before Starting Development
- [ ] Decided on Ink vs Textual with clear rationale
- [ ] Designed IPC protocol if using Ink (JSON newline-delimited recommended)
- [ ] Planned terminal state cleanup (alternate screen, raw mode)
- [ ] Established logging strategy that doesn't corrupt IPC

### During Architecture Phase
- [ ] Event/state layer has explicit backpressure handling
- [ ] State synchronization handles out-of-order events
- [ ] Abstraction layer designed from CLI needs, not HFS internals
- [ ] Cross-platform IPC approach selected

### During UI Development
- [ ] Differential rendering for streaming content
- [ ] Frame rate limiting configured
- [ ] Terminal resize handling implemented
- [ ] Dark/light theme detection (or explicit flag)
- [ ] Multi-agent output clearly separated

### During Integration
- [ ] IPC tested with large outputs (deadlock check)
- [ ] Process lifecycle tested (kill -9 scenarios)
- [ ] Tested in tmux/screen (not just bare terminal)
- [ ] Tested on target platforms (macOS, Linux, Windows)

### Before Release
- [ ] Crash recovery leaves terminal in clean state
- [ ] Performance tested with long streaming sessions
- [ ] Test coverage for core logic (even if UI is hard to test)
- [ ] Manual testing on light and dark terminal themes

---

## Summary: Top 5 Pitfalls to Address First

| Priority | Pitfall | Impact | Phase to Address |
|----------|---------|--------|------------------|
| 1 | Terminal flickering during streaming | Unusable UI | Early architecture |
| 2 | Python-JS IPC deadlocks | App hangs | IPC layer design |
| 3 | Over-engineered abstraction layer | Slow development | Architecture phase |
| 4 | Alternate screen cleanup failures | Broken terminal | Foundation phase |
| 5 | State synchronization complexity | Incorrect UI | Event/state layer |

---

## Confidence Assessment

| Category | Confidence | Notes |
|----------|------------|-------|
| Terminal rendering pitfalls | HIGH | Verified via Claude Code issues, Gemini CLI improvements |
| Streaming performance | HIGH | Multiple sources agree on batching, frame limiting |
| Python-JS IPC | MEDIUM | Based on documentation and community reports |
| Abstraction layer | MEDIUM | General principles, not domain-specific verification |
| Textual alternative | MEDIUM | Researched but not tested for this use case |

---

## Sources

### Terminal Rendering
- [Claude Code flickering fix](https://www.threads.com/@boris_cherny/post/DSZbZatiIvJ)
- [Claude Code scroll events issue](https://github.com/anthropics/claude-code/issues/9935)
- [Ink GitHub repository](https://github.com/vadimdemedes/ink)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)

### Streaming and Performance
- [LLM streaming latency optimization](https://latitude-blog.ghost.io/blog/latency-optimization-in-llm-streaming-key-techniques/)
- [Redis Streams for LLM](https://redis.io/learn/howtos/solutions/streams/streaming-llm-output)
- [OpenAI Agents SDK streaming](https://openai.github.io/openai-agents-python/streaming/)

### Python-JS Integration
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
- [Node.js Python IPC](https://levelup.gitconnected.com/inter-process-communication-between-node-js-and-python-2e9c4fda928d)
- [JSPyBridge](https://github.com/extremeheat/JSPyBridge)

### Architecture
- [Event-driven architecture pitfalls](https://medium.com/insiderengineering/common-pitfalls-in-event-driven-architectures-de84ad8f7f25)
- [When NOT to write an abstraction layer](https://codeopinion.com/when-not-to-write-an-abstraction-layer/)

### Alternatives
- [Textual Python TUI](https://textual.textualize.io/)
- [TUI library comparison](https://blog.logrocket.com/7-tui-libraries-interactive-terminal-apps/)
