# Technology Stack

**Analysis Date:** 2026-01-29

## Languages

**Primary:**
- Python 3.10+ - Core HFS system implementation
- YAML - Configuration files
- React/TypeScript - Generated frontend code (output format)

## Runtime

**Environment:**
- Python 3.10+ (specified in `hfs/pyproject.toml`)

**Package Manager:**
- pip with setuptools/wheel
- Lockfile: Not detected (standard requirements-based dependency management)

## Frameworks

**Core:**
- Pydantic 2.0+ - Data validation and configuration modeling (hfs/core/config.py)
- PyYAML 6.0+ - YAML configuration parsing

**Testing:**
- pytest 7.0+ - Test framework and runner
- pytest-asyncio 0.21+ - Async test support

**Build/Dev:**
- setuptools 61.0+ - Python package building
- wheel - Distribution format

## Key Dependencies

**Critical:**
- `anthropic>=0.18.0` - Anthropic Claude API client for LLM interactions
  - Used in `hfs/cli/main.py` (MockLLMClient interface design)
  - Triads call `llm_client.messages_create()` with async support
  - Interfaces with external Claude models for agent deliberation

**Infrastructure:**
- `pydantic>=2.0` - Configuration validation and type safety
  - Defines all config models in `hfs/core/config.py`
  - PressureConfigModel, TriadConfigModel, ArbiterConfigModel, OutputConfigModel
- `pyyaml>=6.0` - Parsing YAML configuration files
  - Reads config at `hfs/config/default.yaml`
  - User config in project-specific YAML files

**Internal Core Modules:**
- All core logic in `hfs/core/` (orchestrator, triad, negotiation, spec management)
- Preset implementations in `hfs/presets/` (hierarchical, dialectic, consensus)
- Integration layer in `hfs/integration/` (code merging, validation, rendering)

## Configuration

**Environment:**
- `.env` file in root directory contains external API keys (Anthropic, Cerebras, Groq, Gemini, etc.)
  - Currently unused by HFS core system (uses configurable llm_client parameter)
  - Reserved for future multi-provider support
- Configuration through YAML files:
  - Primary: `hfs/config/default.yaml` - default settings
  - Examples: `hfs/config/examples/{minimal,standard}.yaml`

**Build:**
- `pyproject.toml` - Modern Python project configuration
  - Build system: setuptools + wheel
  - CLI entry point: `hfs = "cli.main:main"`
  - Test configuration: pytest asyncio mode auto

## Platform Requirements

**Development:**
- Python 3.10 or higher
- Virtual environment (`.venv/` present)
- Standard pip/setuptools toolchain

**Production:**
- Python 3.10+ runtime
- Anthropic API access (or compatible LLM client with `messages_create()` interface)
- No external databases, file storage, or cloud infrastructure required
- Standalone: can run locally without external dependencies beyond API client

## Project Structure

**Entry Points:**
- `hfs/cli/main.py` - CLI interface with commands: run, validate-config, list-presets
- `hfs/__init__.py` - Public API exports (HFSOrchestrator, run_hfs)
- `hfs/core/orchestrator.py` - Main orchestration engine

**Core Modules:**
- `hfs/core/` - Core HFS pipeline (6 modules)
  - `orchestrator.py` - 9-phase pipeline coordination
  - `triad.py` - Triad base classes and config
  - `negotiation.py` - Negotiation engine for conflict resolution
  - `spec.py` - Shared specification management
  - `arbiter.py` - Conflict escalation resolver
  - `pressure.py` - Temperature/negotiation pressure mechanics
  - `emergent.py` - Emergent pattern observer
  - `config.py` - Configuration loading and validation

**Integration:**
- `hfs/integration/` - Result processing
  - `merger.py` - CodeMerger for combining triad outputs
  - `validator.py` - Output validation
  - `renderer.py` - Code rendering/formatting

**Presets:**
- `hfs/presets/` - Triad implementation templates
  - `hierarchical.py` - Clear delegation pattern
  - `dialectic.py` - Thesis-antithesis-synthesis pattern
  - `consensus.py` - Equal peer voting pattern
  - `triad_factory.py` - Factory for creating triads

**Testing:**
- `hfs/tests/` - Comprehensive test suite
  - Unit tests for all core modules
  - Async test support via pytest-asyncio

---

*Stack analysis: 2026-01-29*
