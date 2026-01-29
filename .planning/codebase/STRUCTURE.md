# Codebase Structure

**Analysis Date:** 2026-01-29

## Directory Layout

```
agentive/
├── hfs/                          # Hexagonal Frontend System package root
│   ├── __init__.py               # Main exports: HFSOrchestrator, run_hfs, Triad, all presets
│   ├── cli/                      # Command-line interface
│   │   ├── __init__.py
│   │   └── main.py               # CLI commands: run, validate-config, list-presets
│   ├── core/                     # Core pipeline and abstractions
│   │   ├── __init__.py           # Exports core classes
│   │   ├── orchestrator.py       # HFSOrchestrator (9-phase pipeline coordinator)
│   │   ├── config.py             # Configuration loading and validation (Pydantic models)
│   │   ├── spec.py               # Spec (shared mutable state, warm wax model)
│   │   ├── triad.py              # Triad ABC, TriadPreset enum, TriadConfig, TriadOutput
│   │   ├── negotiation.py        # NegotiationEngine (manages contested section resolution)
│   │   ├── arbiter.py            # Arbiter (LLM-mediated conflict resolution)
│   │   ├── emergent.py           # EmergentObserver (quality metrics and patterns)
│   │   └── pressure.py           # Pressure mechanics (temperature decay, escalation logic)
│   ├── integration/              # Artifact merging and validation
│   │   ├── __init__.py           # Exports CodeMerger, Validator, Renderer
│   │   ├── merger.py             # CodeMerger (combines artifacts from triads)
│   │   ├── validator.py          # Validator (syntax, render, a11y, perf checks)
│   │   └── renderer.py           # Renderer (format conversion, optional)
│   ├── presets/                  # Triad preset implementations
│   │   ├── __init__.py           # Exports preset classes and factory functions
│   │   ├── hierarchical.py       # HierarchicalTriad (orchestrator + 2 workers)
│   │   ├── dialectic.py          # DialecticTriad (proposer + critic + synthesizer)
│   │   ├── consensus.py          # ConsensusTriad (3 equal peers)
│   │   └── triad_factory.py      # create_triad(), preset registry, info functions
│   ├── config/                   # Configuration files
│   │   ├── default.yaml          # Default config with sensible defaults
│   │   └── examples/             # Example configs for different scenarios
│   │       ├── minimal.yaml
│   │       └── standard.yaml
│   ├── prompts/                  # System prompts for agents
│   │   ├── system/               # System-level prompts for orchestrator, arbiter, etc.
│   │   └── domain/               # Domain-specific prompts (layout, visual, interaction)
│   ├── triads/                   # (Currently empty; may hold custom triad implementations)
│   ├── tests/                    # Test suite
│   │   ├── __init__.py
│   │   ├── test_spec.py
│   │   ├── test_triad.py
│   │   ├── test_negotiation.py
│   │   ├── test_config.py
│   │   ├── test_integration.py
│   │   ├── test_pressure.py
│   │   └── conftest.py           # Pytest fixtures and shared test utilities
│   └── __init__.py               # Package root; re-exports public API
├── docs/                         # Documentation
│   ├── AGNO.md                   # Architecture overview
│   └── KEYCYCLE.md               # Key concepts and glossary
├── .planning/                    # Planning and analysis output
│   └── codebase/                 # Generated codebase documentation
├── .claude/                      # Claude context files
├── .env                          # Environment variables (API keys, etc.)
├── .gitignore                    # Git ignore rules
└── .venv/                        # Python virtual environment
```

## Directory Purposes

**hfs/**
- Purpose: Root package containing the entire Hexagonal Frontend System
- Contains: All core logic, CLI, presets, tests, configurations
- Key files: `__init__.py` (public API), `cli/main.py` (entry point)

**hfs/cli/**
- Purpose: Command-line interface for HFS
- Contains: Argument parsing, command handlers (run, validate-config, list-presets)
- Key files: `main.py` (all CLI logic in single file)
- Entry: User runs `hfs run --config ...` or `hfs validate-config ...`

**hfs/core/**
- Purpose: Core pipeline abstractions and orchestration
- Contains: Orchestrator (9-phase coordinator), Spec (shared state), negotiation logic, arbiter, emergent observation
- Key files:
  - `orchestrator.py`: HFSOrchestrator class (main entry point)
  - `spec.py`: Spec dataclass (warm wax model)
  - `triad.py`: Triad ABC (base class for all triads)
  - `negotiation.py`: NegotiationEngine (contested section resolution)
  - `arbiter.py`: Arbiter (deadlock breaking)
- Pattern: All files follow pattern of dataclasses + business logic

**hfs/integration/**
- Purpose: Phase 8 (Integration) logic: merge and validate artifacts
- Contains: CodeMerger (combines all triad outputs), Validator (quality checks), Renderer (format conversion)
- Key files:
  - `merger.py`: Merges artifacts; handles import resolution, style deduplication
  - `validator.py`: Runs syntax, render, accessibility, performance checks

**hfs/presets/**
- Purpose: Concrete Triad implementations (the three preset patterns)
- Contains: HierarchicalTriad, DialecticTriad, ConsensusTriad (all inherit from Triad ABC)
- Key files:
  - `hierarchical.py`: Orchestrator + 2 workers pattern
  - `dialectic.py`: Thesis-antithesis-synthesis pattern
  - `consensus.py`: 3 equal peers voting pattern
  - `triad_factory.py`: Factory functions and preset registry
- Pattern: Each preset initializes 3 agents with role-specific system prompts

**hfs/config/**
- Purpose: Configuration files and schema
- Contains: YAML files defining default and example configs
- Key files:
  - `default.yaml`: Defaults (overridable in project config)
  - `examples/minimal.yaml`: Simple config with 1-2 triads
  - `examples/standard.yaml`: Full example with 3+ triads

**hfs/prompts/**
- Purpose: System prompts for agents and arbiter
- Contains: Organization by function (system/ for orchestrator/arbiter, domain/ for triad roles)
- Pattern: May contain prompt templates with placeholders

**hfs/tests/**
- Purpose: Full test suite
- Contains: Unit and integration tests for each core module
- Key files:
  - `test_spec.py`: Tests Spec state machine (register_claim, freeze, etc.)
  - `test_triad.py`: Tests Triad presets and factory
  - `test_negotiation.py`: Tests negotiation rounds and escalation
  - `test_config.py`: Tests config loading and validation
  - `test_integration.py`: Tests CodeMerger and Validator
- Pattern: Each module has corresponding test file; fixtures in conftest.py

## Key File Locations

**Entry Points:**
- `hfs/cli/main.py`: CLI entry point; `main()` function dispatches to command handlers
- `hfs/core/orchestrator.py`: Programmatic entry point; HFSOrchestrator.run() and run_hfs()
- `hfs/__init__.py`: Public API; re-exports all public classes and functions

**Configuration:**
- `hfs/core/config.py`: Configuration validation (Pydantic models)
- `hfs/config/default.yaml`: Default settings
- `.env`: Environment variables (API keys, model choices)

**Core Logic:**
- `hfs/core/spec.py`: Spec state machine (temperature, sections, ownership)
- `hfs/core/negotiation.py`: NegotiationEngine (round management, escalation)
- `hfs/core/arbiter.py`: Arbiter LLM client and decision logic
- `hfs/core/emergent.py`: EmergentObserver (metrics, pattern detection)

**Triad Implementations:**
- `hfs/core/triad.py`: Abstract base class
- `hfs/presets/hierarchical.py`: HierarchicalTriad (orchestrator pattern)
- `hfs/presets/dialectic.py`: DialecticTriad (creative pattern)
- `hfs/presets/consensus.py`: ConsensusTriad (voting pattern)

**Integration:**
- `hfs/integration/merger.py`: CodeMerger (combines artifacts)
- `hfs/integration/validator.py`: Validator (quality checks)
- `hfs/integration/renderer.py`: Renderer (optional format conversion)

**Testing:**
- `hfs/tests/conftest.py`: Pytest fixtures (MockLLMClient, test configs)
- `hfs/tests/test_*.py`: Test modules (one per core module)

## Naming Conventions

**Files:**
- Module names: `snake_case` (e.g., `orchestrator.py`, `hierarchical.py`)
- Class files: Match class name in snake_case (e.g., `spec.py` contains Spec, `triad.py` contains Triad)
- Test files: `test_<module>.py` (e.g., `test_spec.py`, `test_negotiation.py`)
- Config files: `<name>.yaml` (e.g., `default.yaml`, `minimal.yaml`)

**Directories:**
- Package dirs: `snake_case`, plural where multiple items (e.g., `presets/`, `triads/`, `prompts/`)
- Grouping: By function/layer (core, integration, presets) not by feature

**Classes:**
- Concrete classes: `PascalCase` (e.g., HFSOrchestrator, TriadConfig, Spec)
- Enums: `PascalCase` (e.g., TriadPreset, SectionStatus, IssueSeverity)
- Abstract base classes: `PascalCase` with suffix (e.g., Triad for Triad ABC)

**Functions:**
- Module functions: `snake_case` (e.g., `load_config()`, `create_triad()`)
- Methods: `snake_case` (e.g., `register_claim()`, `deliberate()`)
- Private methods: `_leading_underscore_snake_case` (e.g., `_initialize_agents()`)

**Constants:**
- Global constants: `UPPER_SNAKE_CASE` (e.g., `ARBITER_SYSTEM_PROMPT`)

**Variables:**
- Snake_case throughout (e.g., `user_request`, `triad_id`, `section_name`)

## Where to Add New Code

**New Triad Preset (e.g., "cooperative"):**
- Implementation file: `hfs/presets/cooperative.py`
- Contains: CooperativeTriad class inheriting from Triad
- Register: Add entry to TRIAD_REGISTRY in `hfs/presets/triad_factory.py`
- Tests: Add `test_cooperative()` to `hfs/tests/test_triad.py` or new file `test_cooperative.py`
- System prompts: Add to `hfs/prompts/domain/cooperative/`

**New Phase (e.g., "validation" between current integration and output):**
- Method: Add phase method to HFSOrchestrator in `hfs/core/orchestrator.py`
- Timestamp: Add entry to phase_timings dict
- Class: Create supporting class in `hfs/core/` if complex logic
- Tests: Add phase test to `hfs/tests/test_orchestrator.py` (new file if needed)

**New Validation Check (e.g., "typescript_strict"):**
- Checker: Add method to Validator class in `hfs/integration/validator.py`
- Issue: Create ValidationIssue with appropriate category and severity
- Config: Add check name to `config.pressure.validation` list in YAML
- Tests: Add test method to `hfs/tests/test_integration.py`

**New Emergent Metric (e.g., "accessibility_score"):**
- Metric: Add field to EmergentMetrics in `hfs/core/emergent.py`
- Observer: Implement metric calculation in EmergentObserver.observe()
- Report: Include metric in EmergentReport.to_dict()
- Tests: Add test case to `hfs/tests/test_emergent.py` (new file if needed)

**New Pressure Mechanic (e.g., "escalation_bonus"):**
- Config field: Add to PressureConfigModel in `hfs/core/config.py`
- Logic: Implement in NegotiationEngine or Spec in `hfs/core/negotiation.py` or `hfs/core/spec.py`
- Tests: Add test to `hfs/tests/test_pressure.py`

**Utility Functions/Helpers:**
- Shared utilities: `hfs/core/utils.py` (create if needed) for cross-module helpers
- Preset-specific: `hfs/presets/<preset>_utils.py` for preset-only utilities
- Prompt helpers: `hfs/prompts/utils.py` for prompt template rendering

**Type Definitions:**
- Core types: Define in `hfs/core/triad.py` or respective module
- Shared types: Consider `hfs/core/types.py` if multiple modules need them

**Tests for New Code:**
- Location: `hfs/tests/test_<feature>.py`
- Pattern: Use fixtures from `hfs/tests/conftest.py` (MockLLMClient, test configs)
- Coverage: Aim for >80% line coverage for core logic

## Special Directories

**hfs/prompts/**
- Purpose: Centralized system prompts for agents
- Generated: No (manually maintained)
- Committed: Yes
- Pattern: Templates with {placeholders} for runtime insertion

**hfs/config/examples/**
- Purpose: Reference configs for different scenarios
- Generated: No
- Committed: Yes
- Usage: Users copy and modify for their projects

**hfs/tests/**
- Purpose: Full test suite (unit + integration)
- Generated: No (tests written by developers)
- Committed: Yes
- Run: `pytest hfs/tests/` from project root

**.env**
- Purpose: Environment secrets (API keys, model choices)
- Generated: No (created manually per environment)
- Committed: No (in .gitignore)
- Required vars: Depends on LLM client implementation

**hfs/triads/**
- Purpose: (Placeholder for future custom triad implementations)
- Generated: No
- Committed: Yes (currently empty)
- Usage: Users may place custom triads here or in separate package

**hfs/core/__init__.py**
- Purpose: Re-export public API from core modules
- Contains: from .spec import Spec; from .triad import Triad; etc.
- Pattern: Simplifies imports for downstream code

---

*Structure analysis: 2026-01-29*
