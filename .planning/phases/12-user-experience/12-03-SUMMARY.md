---
phase: 12
plan: 03
subsystem: tui
tags: [vim, keybinding, modal-editing, textual]

dependency_graph:
  requires: ["12-01"]
  provides: ["vim-mode-input", "modal-editing"]
  affects: ["13-*"]

tech_stack:
  added: []
  patterns: ["state-machine", "reactive-attributes", "message-passing"]

key_files:
  created:
    - hfs/tui/widgets/vim_input.py
  modified:
    - hfs/tui/widgets/__init__.py
    - hfs/tui/widgets/status_bar.py
    - hfs/tui/screens/chat.py

decisions:
  - id: vim-only-normal-insert
    choice: "NORMAL and INSERT modes only (no VISUAL)"
    reason: "Reduces complexity; VISUAL mode rarely needed for chat input"
  - id: mode-changed-message
    choice: "Post ModeChanged message for status bar updates"
    reason: "Decouples input widget from status bar via Textual message system"
  - id: vim-mode-indicator-placement
    choice: "After model label, before tokens in status bar"
    reason: "Prominent position visible at glance"

metrics:
  duration: 4m
  completed: "2026-02-01"
---

# Phase 12 Plan 03: Vim-Style Modal Input Summary

VimChatInput with NORMAL/INSERT modes, h/j/k/l navigation, status bar indicator, and config-based widget selection.

## What Was Built

### VimChatInput Widget (hfs/tui/widgets/vim_input.py)

Modal editing input that extends ChatInput:

```python
class VimMode(Enum):
    NORMAL = auto()
    INSERT = auto()

class VimChatInput(ChatInput):
    class ModeChanged(Message):
        def __init__(self, mode: VimMode) -> None:
            self.mode = mode

    def _handle_normal_mode(self, event: Key) -> None:
        # h/j/k/l movement, i/a/A/I/o mode switches, x/D editing

    def _handle_insert_mode(self, event: Key) -> None:
        # Escape returns to NORMAL (with cursor left per vim convention)
```

**NORMAL mode commands:**
- Movement: h (left), l (right), j (down), k (up), w (word right), b (word left), 0 (line start), $ (line end)
- Mode switches: i (insert), a (insert after), A (insert at end), I (insert at start), o (open line below)
- Editing: x (delete char), D (delete to end)

### Status Bar Vim Mode Indicator

Added reactive `vim_mode` attribute to HFSStatusBar:

```python
vim_mode: reactive[str] = reactive("")  # "", "NORMAL", or "INSERT"
```

CSS styling:
- NORMAL mode: Yellow background (`$warning`)
- INSERT mode: Green background (`$success`)

### ChatScreen Integration

Config-based widget selection in compose():

```python
config = self.app.get_user_config()
if config.keybinding_mode == "vim":
    yield VimChatInput(id="input")
else:
    yield ChatInput(id="input")
```

ModeChanged handler updates status bar:

```python
def on_vim_chat_input_mode_changed(self, event: VimChatInput.ModeChanged) -> None:
    status_bar = self.query_one("#status-bar", HFSStatusBar)
    status_bar.vim_mode = event.mode.name
```

## Key Files

| File | Purpose |
|------|---------|
| `hfs/tui/widgets/vim_input.py` | VimChatInput class with modal state machine |
| `hfs/tui/widgets/status_bar.py` | vim_mode reactive and indicator styling |
| `hfs/tui/screens/chat.py` | Conditional widget selection and ModeChanged handler |

## Usage

To enable vim mode, set config:
```yaml
# ~/.hfs/config.yaml
keybinding_mode: vim
```

Or via command:
```
/config set keybinding_mode vim
```

Then restart TUI. Status bar will show NORMAL/INSERT mode indicator.

## Commits

| Hash | Description |
|------|-------------|
| 2c771d3 | feat(12-03): add VimChatInput with modal editing |
| 711cc1d | feat(12-03): add vim mode indicator to status bar |
| 757e1b3 | feat(12-03): wire vim mode to ChatScreen based on config |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 12 complete. Ready for phase 13 (polish and packaging).

**Integration points for phase 13:**
- Vim mode is opt-in via config (no breaking changes)
- Status bar pattern extensible for additional indicators
- /help updated with vim mode documentation
