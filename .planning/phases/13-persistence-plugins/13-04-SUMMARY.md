---
phase: 13-persistence-plugins
plan: 04
subsystem: plugins
tags: [plugins, discovery, hooks, permissions, pydantic, yaml]

# Dependency graph
requires:
  - phase: 13-01
    provides: Session persistence with SQLAlchemy
  - phase: 13-02
    provides: Checkpoint system with event hooks
provides:
  - Plugin discovery from ~/.hfs/plugins/ directory
  - PluginManifest for manifest.yaml validation
  - PermissionManager for approval persistence
  - HFSHookSpec protocol with lifecycle hooks
  - PluginManager for command and hook execution
  - /plugins command for plugin management
affects: [future-plugin-development, extension-system]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plugin discovery via directory scanning"
    - "Manifest-based capability declaration"
    - "Permission approval persistence"
    - "Protocol-based hook specification"
    - "Async-compatible hook/command execution"

key-files:
  created:
    - hfs/plugins/__init__.py
    - hfs/plugins/discovery.py
    - hfs/plugins/permissions.py
    - hfs/plugins/hooks.py
    - hfs/plugins/manager.py
  modified:
    - hfs/user_config/models.py
    - hfs/tui/app.py
    - hfs/tui/screens/chat.py

key-decisions:
  - "Plugin discovery scans ~/.hfs/plugins/ for subdirectories with manifest.yaml"
  - "Plugins require capabilities list in manifest (commands, hooks, widgets)"
  - "Permission approval persists in ~/.hfs/plugin_permissions.yaml"
  - "COMMANDS dict in plugin module registers slash commands"
  - "Lifecycle hooks are module-level functions (on_start, on_message, on_run_complete, on_exit)"
  - "Plugin hooks can return modified message or None to pass through"

patterns-established:
  - "Manifest validation via Pydantic: Plugin metadata is validated using PluginManifest model"
  - "Capability-based permissions: Plugins declare capabilities, users approve per-plugin"
  - "Hook protocol: HFSHookSpec defines available hooks, plugins implement as needed"
  - "Async-aware execution: Both sync and async handlers supported for commands and hooks"

# Metrics
duration: 4min
completed: 2026-02-02
---

# Phase 13 Plan 04: Plugin System Summary

**Plugin system with discovery from ~/.hfs/plugins/, manifest-based capability declaration, permission approval workflow, and lifecycle hooks (on_start, on_message, on_run_complete, on_exit)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-02T02:07:06Z
- **Completed:** 2026-02-02T02:11:17Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Plugin discovery from ~/.hfs/plugins/ with manifest.yaml validation
- Permission system with ~/.hfs/plugin_permissions.yaml persistence
- Lifecycle hooks protocol (on_start, on_message, on_run_complete, on_exit)
- PluginManager for command registration and hook execution
- /plugins command for listing, approving, and denying plugins
- Integration with ChatScreen for automatic pending approval display

## Task Commits

Each task was committed atomically:

1. **Task 1: Create plugin discovery and manifest system** - `ad70846` (feat)
2. **Task 2: Create hook system and PluginManager** - `967e73a` (feat)
3. **Task 3: Wire plugins to TUI with permission prompts** - `c67c80e` (feat)

## Files Created/Modified
- `hfs/plugins/__init__.py` - Package exports for all plugin components
- `hfs/plugins/discovery.py` - PluginManifest model and discover_plugins() function
- `hfs/plugins/permissions.py` - PermissionManager and PluginCapability enum
- `hfs/plugins/hooks.py` - HFSHookSpec protocol and HOOK_NAMES list
- `hfs/plugins/manager.py` - PluginManager class for lifecycle and hook execution
- `hfs/user_config/models.py` - Added disabled_plugins config field
- `hfs/tui/app.py` - Added initialize_plugins() and get_plugin_manager()
- `hfs/tui/screens/chat.py` - Added /plugins command and pending approval display

## Decisions Made
- Plugin discovery scans ~/.hfs/plugins/ for subdirectories with manifest.yaml
- Manifest requires name, version; optional description, entry_point, capabilities
- Capabilities enum includes: commands, widgets, hooks, filesystem, network
- Permissions stored as YAML with plugin_name, version, capabilities, approved flag
- Commands registered via COMMANDS dict in plugin module (e.g., COMMANDS = {"test": handler})
- Hooks are module-level functions matching HFSHookSpec protocol
- on_message hook can return modified message string or None to pass through
- Both sync and async handlers supported for commands and hooks
- Bad plugins are logged and skipped without crashing the app

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plugin system fully functional for extension development
- Phase 13 (Persistence & Plugins) complete
- All v1.1 milestones achieved

---
*Phase: 13-persistence-plugins*
*Completed: 2026-02-02*
