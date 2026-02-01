# Phase 12: User Experience - Research

**Researched:** 2026-02-01
**Domain:** Configuration loading, output modes, keybinding modes, tab completion in Textual TUI
**Confidence:** MEDIUM-HIGH

## Summary

This phase adds user configuration and customization to HFS: YAML config loading with layered precedence (global -> project -> environment), output mode toggling between compact/verbose, vim/emacs keybinding modes for input, and tab completion for commands and file paths.

The HFS project already uses Textual (>=0.50.0) with a custom TextArea-based ChatInput widget. The existing `hfs/core/config.py` uses Pydantic for validation and PyYAML for loading. This phase extends these patterns rather than introducing new dependencies.

For keybinding modes, Textual's TextArea provides cursor movement methods suitable for building vim-style modal editing. The `textual-autocomplete` library provides proven tab completion for both static lists and file paths. Configuration loading follows the standard pattern: base config -> local override -> environment variables.

**Primary recommendation:** Extend existing Pydantic config models for user preferences, create a VimChatInput subclass with modal state machine, and integrate textual-autocomplete for tab completion.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | >=6.0 | YAML config parsing | Already in project, safe_load() is secure |
| Pydantic | >=2.0 | Config validation | Already in project, excellent for typed config |
| Textual | >=0.50.0 | TUI framework | Already in project, provides TextArea base |
| textual-autocomplete | >=3.0 | Tab completion | Official extension by Textual contributor |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path handling | Config file discovery |
| os | stdlib | Environment variables | Config override from env |
| ruamel.yaml | >=0.18.0 | YAML round-trip | Config file writing (preserves comments) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic | dynaconf | More magic, less explicit typing |
| textual-autocomplete | built-in Suggester | Suggester is inline hints only, not dropdown |
| ruamel.yaml | PyYAML + manual formatting | ruamel preserves comments for user-edited files |

**Installation:**
```bash
pip install textual-autocomplete
# Other dependencies already in project
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── config/
│   ├── __init__.py
│   ├── models.py         # UserConfig Pydantic model
│   ├── loader.py         # ConfigLoader with layered loading
│   └── schema.yaml       # Optional: default config template
├── tui/
│   ├── widgets/
│   │   ├── chat_input.py       # Update with mode support
│   │   ├── vim_input.py        # VimChatInput subclass
│   │   └── completers.py       # Command/path completion
│   ├── screens/
│   │   └── chat.py             # Add /config, /mode commands
```

### Pattern 1: Layered Configuration Loading
**What:** Load configs in precedence order, merging dictionaries shallowly
**When to use:** When multiple config sources need to override each other
**Example:**
```python
# Source: Pydantic Settings pattern + PyYAML
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field

class UserConfig(BaseModel):
    """User preferences for HFS."""
    output_mode: str = Field(default="verbose", pattern="^(compact|verbose)$")
    keybinding_mode: str = Field(default="emacs", pattern="^(vim|emacs|standard)$")
    # ... other fields

def load_user_config() -> UserConfig:
    """Load config with precedence: env > project > global > defaults."""
    config_dict = {}

    # 1. Global config (~/.hfs/config.yaml)
    global_path = Path.home() / ".hfs" / "config.yaml"
    if global_path.exists():
        with open(global_path, encoding="utf-8") as f:
            global_config = yaml.safe_load(f) or {}
            config_dict.update(global_config)

    # 2. Project config (.hfs/config.yaml)
    project_path = Path.cwd() / ".hfs" / "config.yaml"
    if project_path.exists():
        with open(project_path, encoding="utf-8") as f:
            project_config = yaml.safe_load(f) or {}
            config_dict.update(project_config)

    # 3. Environment variable overrides
    env_map = {
        "HFS_OUTPUT_MODE": "output_mode",
        "HFS_KEYBINDING_MODE": "keybinding_mode",
    }
    for env_key, config_key in env_map.items():
        if env_key in os.environ:
            config_dict[config_key] = os.environ[env_key]

    # 4. Validate with Pydantic (uses defaults for missing)
    return UserConfig(**config_dict)
```

### Pattern 2: Modal Input State Machine
**What:** Track vim mode state (NORMAL/INSERT/VISUAL) and dispatch keys accordingly
**When to use:** When implementing vim-style modal editing
**Example:**
```python
# Source: Pattern from textual-vim + Textual TextArea docs
from enum import Enum, auto
from textual.events import Key
from textual.widgets import TextArea
from textual.message import Message

class VimMode(Enum):
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()

class VimChatInput(TextArea):
    """TextArea with vim-style modal editing."""

    class ModeChanged(Message):
        """Posted when vim mode changes."""
        def __init__(self, mode: VimMode) -> None:
            super().__init__()
            self.mode = mode

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mode = VimMode.NORMAL

    @property
    def mode(self) -> VimMode:
        return self._mode

    @mode.setter
    def mode(self, value: VimMode) -> None:
        if value != self._mode:
            self._mode = value
            self.post_message(self.ModeChanged(value))

    def on_key(self, event: Key) -> None:
        if self._mode == VimMode.NORMAL:
            self._handle_normal_mode(event)
        elif self._mode == VimMode.INSERT:
            self._handle_insert_mode(event)
        elif self._mode == VimMode.VISUAL:
            self._handle_visual_mode(event)

    def _handle_normal_mode(self, event: Key) -> None:
        """Handle keys in NORMAL mode."""
        event.prevent_default()

        key = event.key
        if key == "i":
            self.mode = VimMode.INSERT
        elif key == "a":
            # Move cursor right and enter insert
            self.action_cursor_right()
            self.mode = VimMode.INSERT
        elif key == "h":
            self.action_cursor_left()
        elif key == "l":
            self.action_cursor_right()
        elif key == "j":
            self.action_cursor_down()
        elif key == "k":
            self.action_cursor_up()
        # ... etc

    def _handle_insert_mode(self, event: Key) -> None:
        """Handle keys in INSERT mode - mostly pass through."""
        if event.key == "escape":
            event.prevent_default()
            self.mode = VimMode.NORMAL
        # Let other keys pass through to TextArea default handling
```

### Pattern 3: Tab Completion with textual-autocomplete
**What:** Dropdown autocomplete for slash commands and file paths
**When to use:** When input needs contextual completions
**Example:**
```python
# Source: textual-autocomplete documentation
from textual.app import ComposeResult
from textual.widgets import Input
from textual_autocomplete import AutoComplete, DropdownItem, PathAutoComplete

class CommandCompleter(AutoComplete):
    """Completer for slash commands."""

    COMMANDS = [
        DropdownItem(main="/help", prefix="?"),
        DropdownItem(main="/clear", prefix="X"),
        DropdownItem(main="/config", prefix="C"),
        DropdownItem(main="/config set", prefix="C"),
        DropdownItem(main="/mode compact", prefix="M"),
        DropdownItem(main="/mode verbose", prefix="M"),
        DropdownItem(main="/exit", prefix="Q"),
    ]

    def get_candidates(self, state):
        text = state.text
        if text.startswith("/"):
            # Filter commands matching input
            return [
                item for item in self.COMMANDS
                if item.main.lower().startswith(text.lower())
            ]
        return []

    def get_search_string(self, state):
        # Search from beginning of input
        return state.text

# For file path completion in arguments like `/config load path/to/file`:
class ArgumentCompleter(AutoComplete):
    """Context-aware completer that switches between commands and paths."""

    def get_candidates(self, state):
        text = state.text
        # Check if we're in a file path context
        if self._is_path_context(text):
            # Delegate to PathAutoComplete pattern
            return self._get_path_candidates(text)
        elif text.startswith("/"):
            return self._get_command_candidates(text)
        return []
```

### Anti-Patterns to Avoid
- **Global mutable state for config:** Use a ConfigLoader class that can be injected, not module-level globals
- **Parsing config on every access:** Load once at startup, cache the result
- **Blocking on config save:** Write config async or in background
- **Vim mode without mode indicator:** Users MUST see current mode in status bar

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom parser | PyYAML safe_load | Security, edge cases, Unicode |
| Config validation | Manual checks | Pydantic BaseModel | Type coercion, error messages |
| Tab completion dropdown | Custom widget | textual-autocomplete | Keyboard nav, styling, caching |
| File path completion | os.listdir loop | PathAutoComplete | Caching, cross-platform, escaping |
| Config file writing | yaml.dump | ruamel.yaml | Preserves comments, formatting |

**Key insight:** Config and completion are deceptively complex domains. PyYAML handles 1000+ YAML edge cases. textual-autocomplete handles keyboard navigation, focus management, styling, and dropdown positioning. Building these from scratch wastes time and introduces bugs.

## Common Pitfalls

### Pitfall 1: Config File Not Found vs Invalid
**What goes wrong:** Treating missing file same as invalid YAML
**Why it happens:** Both raise exceptions
**How to avoid:** Check `path.exists()` first, load only if exists
**Warning signs:** Errors on first run before user creates config

### Pitfall 2: Environment Variable Type Coercion
**What goes wrong:** Boolean config from env is "false" string not False
**Why it happens:** os.environ always returns strings
**How to avoid:** Use Pydantic's env parsing or explicit conversion
**Warning signs:** `if config.debug:` is always True because "false" is truthy string

### Pitfall 3: Vim Mode Cursor Jump on Mode Change
**What goes wrong:** Cursor moves unexpectedly when entering/exiting insert mode
**Why it happens:** Not handling cursor position on mode transition
**How to avoid:** In vim, Escape moves cursor left 1 char (if not at line start)
**Warning signs:** Cursor is in wrong position after Escape

### Pitfall 4: Tab Completion Steals Focus
**What goes wrong:** Tab key navigates between widgets instead of completing
**Why it happens:** Textual's default Tab behavior is focus navigation
**How to avoid:** Override Tab binding in widget, use BINDINGS with priority=True
**Warning signs:** Focus jumps away when pressing Tab

### Pitfall 5: Config Write Race Condition
**What goes wrong:** Two /config set commands overwrite each other
**Why it happens:** Load-modify-save without locking
**How to avoid:** Use file locking or queue config writes
**Warning signs:** Settings randomly revert

## Code Examples

Verified patterns from official sources:

### Config Loading with Validation
```python
# Source: PyYAML docs + Pydantic docs
from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field, ValidationError

class UserConfig(BaseModel):
    """User configuration for HFS CLI."""

    output_mode: Literal["compact", "verbose"] = "verbose"
    keybinding_mode: Literal["standard", "vim", "emacs"] = "standard"

    # API key precedence: env > config (handled externally via Keycycle)
    # Only user preferences go here

    class Config:
        extra = "ignore"  # Warn but don't fail on unknown keys

def load_config(global_path: Path, project_path: Path | None = None) -> UserConfig:
    """Load config with layered overrides."""
    config_dict = {}

    for path in [global_path, project_path]:
        if path and path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    config_dict.update(data)
            except yaml.YAMLError as e:
                # Warn and continue with partial config
                import logging
                logging.warning(f"Invalid YAML in {path}: {e}")

    try:
        return UserConfig(**config_dict)
    except ValidationError as e:
        import logging
        logging.warning(f"Config validation errors: {e}")
        return UserConfig()  # Use defaults
```

### Config Writing with ruamel.yaml
```python
# Source: ruamel.yaml documentation
from pathlib import Path
from ruamel.yaml import YAML

def write_config(path: Path, updates: dict) -> None:
    """Update config file preserving comments and formatting."""
    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing or start fresh
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.load(f) or {}
    else:
        data = {}
        path.parent.mkdir(parents=True, exist_ok=True)

    # Update values
    data.update(updates)

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
```

### textual-autocomplete Integration
```python
# Source: https://github.com/darrenburns/textual-autocomplete
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input
from textual_autocomplete import AutoComplete, DropdownItem

def compose(self) -> ComposeResult:
    """Compose input with autocomplete overlay."""
    with Container(id="input-area"):
        input_widget = Input(id="chat-input", placeholder="Type a message...")
        yield input_widget
        yield CommandAutoComplete(input_widget)

class CommandAutoComplete(AutoComplete):
    """Autocomplete for slash commands."""

    def __init__(self, target: Input, **kwargs):
        super().__init__(target, candidates=None, **kwargs)  # candidates=None for dynamic

    def get_candidates(self, state):
        """Return matching commands."""
        text = state.text
        if not text.startswith("/"):
            return []

        commands = [
            DropdownItem("/help", prefix="?  "),
            DropdownItem("/clear", prefix="X  "),
            DropdownItem("/config", prefix="C  "),
            DropdownItem("/mode compact", prefix="M  "),
            DropdownItem("/mode verbose", prefix="M  "),
            DropdownItem("/inspect", prefix="I  "),
            DropdownItem("/exit", prefix="Q  "),
        ]

        return [c for c in commands if c.main.lower().startswith(text.lower())]
```

### Vim Mode State Machine
```python
# Source: Pattern from prompt_toolkit and textual-vim
from enum import Enum, auto
from textual.widgets.text_area import Selection

class VimMode(Enum):
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()
    VISUAL_LINE = auto()

class VimState:
    """Track vim editing state."""

    def __init__(self):
        self.mode = VimMode.NORMAL
        self.pending_operator: str | None = None  # For 'd', 'c', 'y' etc
        self.count: int = 1  # Repeat count (e.g., 3j = down 3 lines)
        self.register: str = '"'  # Current register

    def reset_pending(self):
        """Reset operator state after execution."""
        self.pending_operator = None
        self.count = 1

    def accumulate_count(self, digit: str):
        """Build repeat count from digits."""
        if self.count == 1 and digit != "0":
            self.count = int(digit)
        else:
            self.count = self.count * 10 + int(digit)

# Key mappings for NORMAL mode
NORMAL_MODE_KEYS = {
    # Movement
    "h": "cursor_left",
    "l": "cursor_right",
    "j": "cursor_down",
    "k": "cursor_up",
    "w": "cursor_word_right",
    "b": "cursor_word_left",
    "0": "cursor_line_start",
    "$": "cursor_line_end",
    "^": "cursor_line_first_non_blank",
    "g,g": "cursor_document_start",
    "G": "cursor_document_end",

    # Mode changes
    "i": "enter_insert",
    "a": "enter_insert_after",
    "A": "enter_insert_line_end",
    "I": "enter_insert_line_start",
    "o": "insert_line_below",
    "O": "insert_line_above",
    "v": "enter_visual",
    "V": "enter_visual_line",

    # Operators (wait for motion)
    "d": "operator_delete",
    "c": "operator_change",
    "y": "operator_yank",

    # Immediate actions
    "x": "delete_char",
    "X": "delete_char_before",
    "D": "delete_to_end",
    "C": "change_to_end",
    "dd": "delete_line",
    "yy": "yank_line",
    "p": "paste_after",
    "P": "paste_before",
    "u": "undo",
    "ctrl+r": "redo",
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| prompt_toolkit for TUI input | Textual TextArea | Textual 0.38+ | Better composition, CSS styling |
| configparser | Pydantic Settings | 2022+ | Type safety, validation, nested models |
| yaml.load() | yaml.safe_load() | PyYAML 5.1+ | Security: no arbitrary code execution |
| Manual tab completion | textual-autocomplete | 2023+ | Proven dropdown UX, keyboard nav |

**Deprecated/outdated:**
- `yaml.load()` without Loader: Security vulnerability, always use `safe_load()`
- `configparser`: Limited to flat key=value, no nested structures
- Manual curses keybinding: Textual provides cross-platform abstraction

## Open Questions

Things that couldn't be fully resolved:

1. **textual-autocomplete + TextArea integration**
   - What we know: textual-autocomplete works with Input widget
   - What's unclear: Does it work with TextArea (used by ChatInput)?
   - Recommendation: Test integration, may need to adapt for TextArea or use Input for completion trigger then transfer to TextArea

2. **Vim visual mode selection sync**
   - What we know: TextArea has Selection and select methods
   - What's unclear: How to sync vim visual selection with TextArea selection highlight
   - Recommendation: Use TextArea's selection property, update in visual mode handlers

3. **Config file atomic writes**
   - What we know: ruamel.yaml can write YAML
   - What's unclear: Best practice for atomic writes on Windows
   - Recommendation: Write to temp file, then os.replace() for atomic rename

## Sources

### Primary (HIGH confidence)
- Textual TextArea documentation (https://textual.textualize.io/widgets/text_area/) - keybindings, cursor methods, selection
- textual-autocomplete GitHub (https://github.com/darrenburns/textual-autocomplete) - installation, PathAutoComplete, API
- PyYAML documentation - safe_load security
- Pydantic Settings documentation (https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - config precedence

### Secondary (MEDIUM confidence)
- Textual input handling guide (https://textual.textualize.io/guide/input/) - keybinding patterns
- prompt_toolkit reference - vim/emacs mode patterns, EditingMode enum

### Tertiary (LOW confidence)
- textual-vim GitHub (https://github.com/davidbrochart/textual-vim) - minimal activity, reference only
- Community patterns for YAML config merging

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project or well-documented extensions
- Architecture: HIGH - Follows existing patterns in codebase
- Configuration loading: HIGH - Standard Python patterns with PyYAML + Pydantic
- Tab completion: MEDIUM - textual-autocomplete well-documented but TextArea integration untested
- Vim keybindings: MEDIUM - Pattern clear from prompt_toolkit, implementation complexity

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - stable libraries)
