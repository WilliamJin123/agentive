# Coding Conventions

**Analysis Date:** 2026-01-29

## Naming Patterns

**Files:**
- Snake case for module files: `spec.py`, `orchestrator.py`, `triad.py`
- Package directories use descriptive names matching functionality: `core`, `presets`, `integration`, `tests`
- Test files: `test_<module>.py` (e.g., `test_spec.py`, `test_triad.py`)

**Functions:**
- Snake case for all functions: `register_claim()`, `advance_round()`, `freeze()`, `_initialize_agents()`
- Private/internal methods prefixed with single underscore: `_record_history()`, `_initialize_agents()`, `_spec_to_dict()`
- Async functions use `async def`: `async def deliberate()`, `async def negotiate()`, `async def execute()`

**Variables:**
- Snake case for variables and parameters: `temperature`, `section_name`, `triad_id`, `claimants`
- Boolean variables prefixed with verb forms: `is_frozen()`, `has_content`, `success`
- Constants use UPPER_SNAKE_CASE where applicable (though rarely used in this codebase)
- Type hints on all parameters and return values: `def register_claim(self, triad_id: str, section_name: str, proposal: Any) -> None:`

**Types and Classes:**
- PascalCase for all class names: `Spec`, `Section`, `Triad`, `TriadConfig`, `TriadOutput`, `HierarchicalTriad`
- Enum class names in PascalCase: `SectionStatus`, `TriadPreset`, `NegotiationResponse`
- Dataclasses use `@dataclass` decorator: `@dataclass class Section`, `@dataclass class TriadConfig`

## Code Style

**Formatting:**
- No explicit formatter configured (no .prettierrc, .flake8, or setup.cfg)
- Apparent style: consistent with PEP 8
- Line length: Not enforced, observed lines up to ~100 characters
- Indentation: 4 spaces (Python standard)

**Linting:**
- No explicit linting configured (no .eslintrc or flake8 config file)
- Imports organized at module top following Python conventions
- Type hints used throughout the codebase

## Import Organization

**Order:**
1. Standard library imports: `import asyncio`, `import json`, `import logging`, `from pathlib import Path`
2. Third-party imports: `import yaml`, `from pydantic import BaseModel`, `from anthropic import ...`
3. Local/relative imports: `from .triad import Triad`, `from ..core.config import HFSConfig`

**Path Aliases:**
- No explicit path aliases configured (no pyproject.toml with [tool.pytest] paths)
- Imports use relative paths within package structure: `from ..core.spec import Spec`
- When accessing within same package: `from .config import load_config`

**Example from `hfs/tests/test_spec.py`:**
```python
import pytest
from hfs.core.spec import SectionStatus, Section, Spec
```

**Example from `hfs/core/orchestrator.py`:**
```python
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .arbiter import Arbiter, ArbiterConfig
from .config import HFSConfig, load_config, load_config_dict
from .emergent import EmergentObserver, EmergentReport
from .negotiation import NegotiationEngine, NegotiationResult
from .spec import Spec
from .triad import Triad, TriadConfig, TriadPreset, TriadOutput
from ..presets.triad_factory import create_triad
from ..integration.merger import CodeMerger, MergedArtifact
from ..integration.validator import Validator, ValidationResult
```

## Error Handling

**Patterns:**
- Raise specific exceptions with descriptive messages: `raise ValueError("'assign' decision requires 'winner' field")`
- Use custom exception classes for domain-specific errors: `ConfigError` defined in `hfs/core/config.py`
- Exception chaining with `from e`: `raise ValueError(f"Failed to call LLM: {e}") from e`

**Common patterns:**
```python
# Check preconditions, raise early
if section_name not in self.sections:
    return False

# Detailed error messages with context
if section.status == SectionStatus.FROZEN:
    section._record_history(
        self.round, "claim_rejected", triad_id,
        reason="section_frozen"
    )
    return

# Try-except for recoverable operations
try:
    # Operation
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in arbiter response: {e}") from e
```

**When to raise:**
- Configuration validation failures: `ConfigError`, `ValueError`
- Invalid state transitions: `ValueError` with clear message
- Missing required fields: `ValueError` with field name

**When to return False/None:**
- Optional operations that can fail gracefully: `concede()`, `update_proposal()`
- Query methods that may not find data: `get_section_owner()` returns `Optional[str]`

## Logging

**Framework:** `logging` (Python standard library)

**Patterns:**
```python
import logging
logger = logging.getLogger(__name__)

# At module level
logger = logging.getLogger(__name__)

# In functions/methods
logger.exception("Pipeline execution failed")
```

**When to log:**
- Pipeline phase completion/failure
- Configuration loading
- Unhandled exceptions (use `logger.exception()`)
- Debug information for tracing (rarely used in core logic)

**Setup:**
```python
# In CLI entry point (hfs/cli/main.py)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Comments

**When to Comment:**
- Module docstrings are comprehensive and explain purpose, key concepts, and design rationale
- Class docstrings explain the class's role and attributes
- Complex algorithms or non-obvious behavior
- Business logic decisions (e.g., why temperature controls malleability)

**Example module docstring from `hfs/core/spec.py`:**
```python
"""Spec management for HFS - the shared mutable state (warm wax).

The Spec is the shared document that all triads read from and write to.
It serves as the "warm wax" that allows boundaries to deform during
negotiation before freezing into final assignments.

Key concepts:
- Temperature: 1.0 = fully malleable, 0.0 = frozen
- Section statuses flow: unclaimed -> contested -> claimed -> frozen
- Claims are registered during deliberation phase
- Concession happens during negotiation
- Freeze happens when negotiation ends.
"""
```

## JSDoc/TSDoc

**Not used** - this is a Python project. Uses Python docstrings following Google style:

```python
def register_claim(self, triad_id: str, section_name: str, proposal: Any) -> None:
    """Register a triad's claim on a section.

    Creates the section if it doesn't exist. Adds the triad to claimants
    and stores their proposal. Updates section status based on number
    of claimants.

    Args:
        triad_id: ID of the triad making the claim
        section_name: Name of the section being claimed
        proposal: The triad's proposed content for this section
    """
```

## Function Design

**Size:**
- Typically 20-50 lines (except orchestration/coordination functions which may be longer)
- Complex methods broken into helpers: `_spec_to_dict()`, `_negotiation_log_to_dict()`
- Dataclass methods using field defaults and helper methods for validation

**Parameters:**
- Always include type hints
- Keep to 3-4 parameters; use dataclasses for config with many fields
- Use `Optional` for nullable parameters: `Optional[str] = None`

**Return Values:**
- Always include return type hints
- Return `None` explicitly for side-effect functions
- Return `Optional[T]` when operation may not produce result
- Return bool for validation/check operations: `return False` when precondition fails
- Return dataclass instances for structured outputs: `return TriadOutput(...)`

**Example from `hfs/core/spec.py`:**
```python
def concede(self, triad_id: str, section_name: str) -> bool:
    """Triad withdraws claim from a section.

    Returns:
        True if concession was successful, False if section doesn't
        exist or triad wasn't a claimant
    """
    if section_name not in self.sections:
        return False

    section = self.sections[section_name]

    if section.status == SectionStatus.FROZEN:
        section._record_history(
            self.round, "concede_rejected", triad_id,
            reason="section_frozen"
        )
        return False

    if triad_id not in section.claims:
        return False

    # ... perform operation ...
    return True
```

## Module Design

**Exports:**
- Modules export key classes and functions for public API
- Main entry point `hfs/__init__.py` uses explicit `__all__` list: `__all__ = ["HFSOrchestrator", "HFSResult", ...]`
- Core components re-exported from submodules for convenience

**Barrel Files:**
- `hfs/__init__.py` acts as main barrel file, importing from submodules
- `hfs/core/__init__.py` imports from submodules and re-exports
- Example `hfs/__init__.py`:
```python
from .core.orchestrator import HFSOrchestrator, HFSResult, run_hfs
from .core import (
    Spec, SectionStatus, Section,
    Triad, TriadConfig, TriadPreset, TriadOutput,
    # ... etc
)
__all__ = [
    "__version__",
    "HFSOrchestrator",
    "HFSResult",
    "run_hfs",
    # ... etc
]
```

**File structure for modules:**
- Dataclasses and Enums defined at top of module
- Abstract base classes defined next
- Implementations follow
- Utility functions at end
- Example `hfs/core/triad.py`:
  - Lines 16-30: Enum definitions (`TriadPreset`)
  - Lines 33-56: Dataclass definitions (`TriadConfig`, `TriadOutput`)
  - Lines 73-74: Type aliases (`NegotiationResponse`)
  - Lines 77-171: Abstract base class (`Triad`)

---

*Convention analysis: 2026-01-29*
