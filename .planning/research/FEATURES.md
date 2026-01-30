# Features Research: HFS CLI

**Domain:** AI/Agent CLI with rich TUI frontend
**Researched:** 2026-01-30
**Confidence:** HIGH (verified against multiple modern AI CLI implementations)

## Executive Summary

Modern AI CLIs have converged on a standard feature set. The reference implementations (Gemini CLI, Claude Code, OpenCode, Aider) reveal clear patterns for what users expect versus what differentiates. HFS's unique value proposition lies in deep multi-agent inspection (agent tree, triad deliberation, negotiation visualization) which no competitor offers because they run single-agent loops.

---

## Table Stakes

Features users expect. Missing = product feels incomplete or amateur.

### TS-1: Streaming Response Output

**What:** Display LLM responses token-by-token as they arrive, not as a single block after completion.

**Why Expected:** Every major AI CLI streams. Users will not wait for responses to complete before seeing output.

**Complexity:** MEDIUM
- Requires async streaming from LLM provider
- Ink handles React-style rendering; need to update text component on each token
- Must handle partial markdown gracefully

**Abstraction Layer:** YES - HFS event system must emit token-level events for streaming

**Reference:** Gemini CLI streams with 1M token context; Claude Code v2.0 has "improved UI rendering performance"

### TS-2: Markdown Rendering in Terminal

**What:** Render markdown with syntax highlighting, code fences, headers, lists, tables.

**Why Expected:** LLM responses are markdown. Raw markdown looks bad. Competitors render beautifully.

**Complexity:** MEDIUM
- Use `marked-terminal` or similar for Ink
- Syntax highlighting for code blocks (likely via `highlight.js` or `prism`)
- Must handle streaming markdown (partial code fences, incomplete tables)

**Abstraction Layer:** NO - Pure presentation layer concern

**Reference:** Toad has "really nice Markdown streaming" that "remains fast with large documents"; Glow renders "markdown with pizzazz"

### TS-3: Command History and Recall

**What:** Arrow-up for previous commands, Ctrl+R for fuzzy history search.

**Why Expected:** Every terminal user expects history. Claude Code has "searchable prompt history (Ctrl+R)".

**Complexity:** LOW
- Store history in local file (~/.hfs/history)
- Ink provides input components; add history navigation
- Fuzzy search via simple substring or fzf-style algorithm

**Abstraction Layer:** NO - Pure UI concern

**Reference:** Claude Code v2.0 added "history-based autocomplete"; fzf-style search is standard

### TS-4: Session Continuity (Within Run)

**What:** Conversation context persists across messages in a single session.

**Why Expected:** Users expect follow-up questions to have context. "Fix that" should know what "that" refers to.

**Complexity:** LOW
- Maintain message history in memory during session
- Pass context to LLM calls
- HFS already has this via triad deliberation context

**Abstraction Layer:** YES - Event system must track conversation turns

### TS-5: Clear/Exit Commands

**What:** `/clear` to reset conversation, `/exit` or Ctrl+C to quit cleanly.

**Why Expected:** Basic REPL hygiene. Every CLI has this.

**Complexity:** LOW
- Slash command parsing
- State reset on /clear
- Graceful shutdown on exit

**Abstraction Layer:** PARTIAL - UI handles commands, abstraction layer handles state reset

### TS-6: Progress Indication

**What:** Show that something is happening during LLM calls, tool execution, agent work.

**Why Expected:** Users need feedback during potentially long operations. Staring at a blank screen is bad UX.

**Complexity:** LOW
- Spinner or progress bar during API calls
- Status text showing current operation
- Ink has good spinner components

**Abstraction Layer:** YES - Event system must emit phase/step events for progress tracking

**Reference:** Conduit CLI has "real-time streaming to watch agent responses"; tokscale tracks "real-time" usage

### TS-7: Error Handling with Recovery

**What:** Graceful error messages, option to retry, don't crash on API failures.

**Why Expected:** API failures happen. Good CLIs handle them gracefully.

**Complexity:** MEDIUM
- Catch and display errors cleanly
- Offer retry option
- Don't dump stack traces to user

**Abstraction Layer:** YES - Error events from HFS core must be surfaced

### TS-8: Configuration via File + Environment

**What:** Config file for persistent settings, env vars for secrets (API keys).

**Why Expected:** Standard pattern. Users expect to configure tools without editing code.

**Complexity:** LOW (HFS already has YAML config)
- Support ~/.hfs/config.yaml or project-local .hfs/config.yaml
- Read API keys from env (HFS already does via Keycycle)

**Abstraction Layer:** NO - Configuration concern separate from event system

---

## Differentiators

Features that set HFS apart. Not expected, but valued. These align with HFS's unique multi-agent architecture.

### D-1: Agent Tree Visualization

**What:** Show the triad structure - which agents exist, their roles, current status.

**Why Valuable:** HFS runs 3+ agents in triads. No competitor shows agent hierarchy because they're single-agent. This is unique visibility into multi-agent orchestration.

**Complexity:** HIGH
- Parse triad structure into visual tree
- Show roles: orchestrator/worker/proposer/critic/synthesizer/peer
- Indicate which agent is currently active
- Update in real-time as execution progresses

**Abstraction Layer:** YES - Core abstraction requirement. Must expose agent tree structure via query API.

**Example Display:**
```
HFS Run [active]
  Hierarchical Triad [deliberating]
    orchestrator (GPT-4) [active]
    worker-1 (GPT-3.5) [waiting]
    worker-2 (GPT-3.5) [waiting]
  Dialectic Triad [idle]
    proposer / critic / synthesizer
  Consensus Triad [idle]
    peer-1 / peer-2 / peer-3
```

### D-2: Negotiation Visualization

**What:** Show the spec negotiation in real-time - claims, proposals, concessions, arbiter decisions.

**Why Valuable:** The "warm wax" negotiation model is HFS's core innovation. Visualizing it shows users how their multi-agent system reaches consensus. No competitor has this because they don't have multi-agent negotiation.

**Complexity:** HIGH
- Track spec sections and their status (UNCLAIMED/CONTESTED/CLAIMED/FROZEN)
- Show which triads claimed which sections
- Display temperature decay across rounds
- Highlight arbiter interventions

**Abstraction Layer:** YES - Must expose negotiation state via query/event API.

**Example Display:**
```
Spec Negotiation [Round 3 of 10, temp: 0.7]
  layout         [CLAIMED] Hierarchical
  visual         [CONTESTED] Dialectic vs Consensus
    > Dialectic: hold (confident in gradient approach)
    > Consensus: revise (simplified to 3 colors)
  accessibility  [FROZEN] Consensus
```

### D-3: Token/Cost Tracking Display

**What:** Real-time display of tokens used and cost per agent, per phase, total.

**Why Valuable:** Multi-agent runs use more tokens. Users need visibility into cost. HFS already tracks this via OpenTelemetry; surfacing it in CLI is differentiation.

**Complexity:** MEDIUM
- Query existing OpenTelemetry token metrics
- Display per-agent, per-phase, and total
- Show cost estimate (requires pricing data per model)

**Abstraction Layer:** YES - Query API must expose token usage data.

**Reference:** tokscale is literally a separate tool because CLIs don't show this well. HFS building it in is differentiation.

### D-4: Trace Timeline View

**What:** Show execution trace - phases, durations, events - as a timeline.

**Why Valuable:** HFS has 9 phases. Users want to see where time is spent. OpenTelemetry already captures this; displaying it differentiates.

**Complexity:** MEDIUM
- Query phase timing from OpenTelemetry spans
- Render as horizontal timeline or vertical list
- Highlight slow phases, errors

**Abstraction Layer:** YES - Query API must expose trace/span data.

**Example Display:**
```
Phase Timeline [total: 45.2s]
  INPUT           0.1s  [========]
  SPAWN           0.3s  [==================]
  DELIBERATION    15.2s [====================================...]
  CLAIM           0.5s  [==========================]
  NEGOTIATION     22.1s [====================================...]
  FREEZE          0.1s  [========]
  EXECUTION       5.8s  [====================================]
  INTEGRATION     0.9s  [=============================]
  OUTPUT          0.2s  [=========]
```

### D-5: Model Escalation Visibility

**What:** Show when and why models escalated (cheap -> expensive due to failures).

**Why Valuable:** HFS's adaptive escalation is a key feature. Users should see when their run escalated to expensive models and why.

**Complexity:** LOW
- Query escalation tracker events
- Display in status bar or as inline annotations
- Show before/after model and reason

**Abstraction Layer:** YES - Event system must emit escalation events.

**Example Display:**
```
[!] Escalation: execution-worker upgraded from gemma-7b to glm-4.7
    Reason: Code execution failed validation (2 attempts)
```

### D-6: Deep Inspection Mode (/inspect)

**What:** A command to pause and deeply inspect current state - full agent tree, spec status, token breakdown, trace so far.

**Why Valuable:** Power user feature. When something goes wrong or takes too long, users want to dive deep. No competitor offers multi-agent inspection.

**Complexity:** HIGH
- Aggregate data from multiple query APIs
- Render comprehensive multi-panel view
- Allow navigation (which agent, which phase, which section)

**Abstraction Layer:** YES - Requires all query APIs (agent tree, negotiation state, tokens, traces).

### D-7: Bee/Hive Visual Theme

**What:** Cohesive yellow/amber/hexagonal visual theme throughout the CLI.

**Why Valuable:** Brand differentiation. Most AI CLIs are generic blue/white or terminal-default. A distinctive theme creates identity.

**Complexity:** LOW
- Define color palette (yellow, amber, honey variants)
- Apply consistently to all components
- Hexagonal motifs where appropriate (borders, icons)

**Abstraction Layer:** NO - Pure presentation layer.

**Example Palette:**
```
Primary:   #F59E0B (Amber-500)
Secondary: #D97706 (Amber-600)
Accent:    #FBBF24 (Amber-400)
Muted:     #92400E (Amber-800)
Background: Terminal default with amber highlights
```

---

## Nice-to-Haves

Good features that can be deferred post-MVP.

### NH-1: Session Persistence Across Runs

**What:** Save and resume conversations, like Claude Code's session management.

**Why Deferrable:** PROJECT.md explicitly marks "Session persistence across runs" as OUT OF SCOPE. Users can copy/paste or re-explain context.

**Complexity:** MEDIUM (requires local storage, session naming, resume logic)

**Reference:** Claude Code has /rename and /resume commands for session management.

### NH-2: Checkpoints/Rewind

**What:** Ability to rewind to earlier state if things go wrong.

**Why Deferrable:** HFS runs are typically shorter than full coding sessions. Less critical than for Claude Code's extended autonomous work.

**Complexity:** HIGH (requires state snapshotting, diff/restore logic)

**Reference:** Claude Code's checkpoint system "automatically saves your code state before each change".

### NH-3: Vim/Emacs Keybindings Mode

**What:** Support vi or emacs editing modes in input.

**Why Deferrable:** Power user preference. Basic readline works for most.

**Complexity:** LOW (many terminal input libraries support this)

### NH-4: Plugin/Extension System

**What:** Allow users to add custom commands or integrations.

**Why Deferrable:** Adds significant complexity. Focus on core first.

**Complexity:** HIGH

### NH-5: Tab Completion for Commands

**What:** Tab-complete slash commands, file paths, etc.

**Why Deferrable:** Nice UX polish, not critical.

**Complexity:** MEDIUM

### NH-6: Export/Import Conversations

**What:** Save conversation to JSON/markdown, import previous.

**Why Deferrable:** Power user feature for sharing/archiving.

**Complexity:** LOW

### NH-7: Compact/Expand Output Modes

**What:** Toggle between verbose and compact output.

**Why Deferrable:** Nice UX polish.

**Complexity:** LOW

**Reference:** OpenCode has auto-compact feature for context window management.

---

## Anti-Features

Things to deliberately NOT build. Common mistakes in this domain.

### AF-1: Built-in Code Execution in CLI

**What:** Running generated code directly from the CLI (like a REPL).

**Why Avoid:** HFS is about multi-agent negotiation for design/spec generation. Code execution is already handled in the EXECUTION phase by agents. Adding user-triggered code execution in CLI:
- Adds security concerns
- Confuses the "design by negotiation" paradigm
- Is out of scope per PROJECT.md

**What to Do Instead:** Output generated code to files. Let users run it themselves.

### AF-2: GUI/Web Fallback

**What:** Falling back to browser-based UI when terminal features are limited.

**Why Avoid:** PROJECT.md explicitly states "CLI-only for now". Web UI is a future milestone, not a fallback.

**What to Do Instead:** Make the CLI feature-complete. Abstraction layer enables future web UI.

### AF-3: Real-time Collaboration

**What:** Multiple users working on same HFS session.

**Why Avoid:** Massive complexity. HFS runs are typically individual. Out of scope.

**What to Do Instead:** Export/share results after completion.

### AF-4: Blocking File System Watchers

**What:** Watching files and auto-rerunning on changes.

**Why Avoid:** HFS is request-based, not continuous. Watching files implies a different workflow model.

**What to Do Instead:** Explicit "run" commands. Users decide when to re-run.

### AF-5: Over-Animated UI

**What:** Excessive animations, transitions, and visual flourishes.

**Why Avoid:** Terminal users value speed and clarity. Too much animation is distracting and can slow down rendering.

**What to Do Instead:** Subtle, purposeful animations (spinner for waiting, brief highlight on changes).

### AF-6: AI-Powered Command Suggestions

**What:** Using AI to suggest what command to run next.

**Why Avoid:** The agents ARE the AI. Adding another AI layer for UI suggestions is confusing and adds latency/cost.

**What to Do Instead:** Clear command help (/help), obvious affordances.

### AF-7: Complex Nested Menus

**What:** Multi-level menu systems for features.

**Why Avoid:** Terminal UX favors flat command structures. Menus are slow.

**What to Do Instead:** Slash commands with clear naming. /help for discovery.

---

## UX Patterns

Modern CLI conventions to follow.

### UXP-1: Slash Commands for Actions

**Pattern:** `/command [args]` for all meta-actions.
**Why:** Clear distinction between user input (to agents) and commands (to CLI).
**Examples:** `/clear`, `/exit`, `/help`, `/inspect`, `/config`

### UXP-2: Chat-Style Input

**Pattern:** Single input line at bottom, messages scroll up.
**Why:** Familiar from chat interfaces. Natural for conversational AI.

### UXP-3: Status Bar

**Pattern:** Persistent status at top or bottom showing current state.
**Why:** Users need context without scrolling. Show: current phase, token count, active agent.

### UXP-4: Progressive Disclosure

**Pattern:** Show summary by default, expand on request.
**Why:** Don't overwhelm. Agent tree shows summary; /inspect shows details.

### UXP-5: Color Coding for Agents/Phases

**Pattern:** Consistent colors for each triad type, phase, or status.
**Why:** Visual parsing is faster than reading labels.
**Suggestion:**
- Hierarchical: Blue
- Dialectic: Purple
- Consensus: Green
- Errors: Red
- Active: Yellow/Amber (theme color)

### UXP-6: Keyboard-First Navigation

**Pattern:** Common shortcuts work: Ctrl+C (cancel), Ctrl+L (clear screen), arrow keys (history).
**Why:** Terminal users expect keyboard efficiency.

### UXP-7: Graceful Degradation for Minimal Terminals

**Pattern:** Basic text mode if terminal doesn't support colors/unicode.
**Why:** Some terminals (raw ssh, Windows cmd) have limited capabilities. Don't crash.

### UXP-8: Non-Blocking Long Operations

**Pattern:** Never freeze the UI during API calls. Always show progress.
**Why:** Users need feedback. Frozen UI feels broken.

### UXP-9: Interruptibility

**Pattern:** Ctrl+C should stop current operation, not exit.
**Why:** Users often realize mid-run they want to change direction.

### UXP-10: Explicit Confirmation for Destructive Actions

**Pattern:** Confirm before actions that lose data (clear history, cancel in-progress run).
**Why:** Prevent accidental loss.

---

## Abstraction Layer Requirements Summary

Based on feature analysis, the abstraction layer must provide:

| Requirement | Features Using It | Type |
|-------------|-------------------|------|
| Token events (streaming) | TS-1 | Event subscription |
| Phase/step events | TS-6, D-4 | Event subscription |
| Error events | TS-7 | Event subscription |
| Conversation state | TS-4 | Query + mutation |
| Agent tree structure | D-1, D-6 | Query API |
| Negotiation state | D-2, D-6 | Query API |
| Token usage metrics | D-3, D-6 | Query API |
| Trace/span data | D-4, D-6 | Query API |
| Escalation events | D-5 | Event subscription |

**Two patterns emerge:**
1. **Event Subscription:** Real-time updates (streaming, progress, errors, escalation)
2. **Query API:** Point-in-time state (agent tree, negotiation, tokens, traces)

The abstraction layer should support both patterns to enable all differentiating features.

---

## Sources

**Gemini CLI:**
- [Google Blog Announcement](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemini-cli-open-source-ai-agent/)
- [GitHub Repository](https://github.com/google-gemini/gemini-cli)
- [Official Documentation](https://developers.google.com/gemini-code-assist/docs/gemini-cli)

**Claude Code:**
- [CLI Reference](https://code.claude.com/docs/en/cli-reference)
- [Product Page](https://claude.com/product/claude-code)
- [Checkpointing Docs](https://code.claude.com/docs/en/checkpointing)
- [Anthropic News on Autonomous Work](https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously)

**OpenCode:**
- [GitHub Repository](https://github.com/opencode-ai/opencode)
- [Official Site](https://opencode.ai/)
- [CLI Documentation](https://opencode.ai/docs/cli/)

**Aider:**
- [Official Site](https://aider.chat/)
- [Digital Applied Comparison](https://www.digitalapplied.com/blog/claude-code-vs-aider-vs-gemini-cli-terminal-tools-comparison)

**Streaming/Markdown:**
- [Toad - Unified Terminal AI Experience](https://willmcgugan.github.io/toad-released/)
- [Efficient Streaming Markdown](https://willmcgugan.github.io/streaming-markdown/)
- [Vercel Streamdown](https://vercel.com/changelog/introducing-streamdown)
- [Glow - Terminal Markdown Renderer](https://github.com/charmbracelet/glow)

**Token Tracking:**
- [tokscale - Token Usage Tracker](https://github.com/junhoyeo/tokscale)

**Agent Observability:**
- [LangSmith for Deep Agents](https://www.blog.langchain.com/debugging-deep-agents-with-langsmith/)
- [AgentPrism](https://evilmartians.com/chronicles/debug-ai-fast-agent-prism-open-source-library-visualize-agent-traces)
- [Maxim AI Agent Tracing](https://www.getmaxim.ai/articles/agent-tracing-for-debugging-multi-agent-ai-systems/)

**Ink/TUI:**
- [Ink GitHub](https://github.com/vadimdemedes/ink)
- [Ink UI Components](https://github.com/vadimdemedes/ink-ui)
- [Building Reactive Terminal UI](https://gerred.github.io/building-an-agentic-system/ink-yoga-reactive-ui.html)

---

*Research completed: 2026-01-30*
