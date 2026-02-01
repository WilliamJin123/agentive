# Phase 12: User Experience - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Configuration system, output modes, and input keybindings for the HFS CLI. Users can customize their experience via config files, switch between compact/verbose output, and use Vim or Emacs keybinding modes. Tab completion for slash commands and file paths.

</domain>

<decisions>
## Implementation Decisions

### Configuration loading
- Local overrides global: Start with ~/.hfs/config.yaml, project .hfs/config.yaml overrides specific values
- Environment variables override config files (HFS_API_KEY beats config.yaml, good for CI/containers)
- Invalid YAML or unknown keys: warn and use defaults, continue with valid values
- No auto-create: Works without config file, user creates if they want customization

### Output modes
- Compact mode hides agent activity only (agent tree, negotiation panel), shows final responses and status bar
- Toggle via slash command: /mode compact or /mode verbose
- Mode preference persists to config file, survives restart
- Default mode is verbose for new users (HFS's value is observability)

### Keybinding modes
- Vim mode is full modal editing: normal/insert modes, h/j/k/l navigation, dd to delete line
- Status bar indicator shows NORMAL/INSERT/VISUAL mode state
- Mode set in config.yaml only, requires restart to change (no runtime switching)
- Default mode is standard/Emacs for new users (familiar Ctrl+A/E/K shortcuts)

### /config command
- /config with no arguments shows current effective values as key: value pairs
- Edit via /config set key value (e.g., /config set output_mode compact)
- Changes write to global ~/.hfs/config.yaml (user preferences to home directory)
- Invalid values rejected with explanation (e.g., "'output_mode' must be 'compact' or 'verbose'")

### Claude's Discretion
- Exact config schema and key names
- Tab completion implementation details
- Error message phrasing
- Config file formatting and comments

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-user-experience*
*Context gathered: 2026-02-01*
