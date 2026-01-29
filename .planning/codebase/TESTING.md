# Testing Patterns

**Analysis Date:** 2026-01-29

## Test Framework

**Runner:**
- pytest 7.0+ (from `pyproject.toml`: `pytest>=7.0`)
- pytest-asyncio 0.21+ for async test support
- Config: `hfs/pyproject.toml` with pytest section:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Assertion Library:**
- Python's built-in `assert` statements
- No special assertion library like `nose` or `hypothesis`

**Run Commands:**
```bash
pytest hfs/tests                    # Run all tests
pytest hfs/tests -v               # Verbose output
pytest hfs/tests -k test_name     # Run specific test
pytest hfs/tests --asyncio-mode=auto  # For async tests
pytest hfs/tests -x               # Stop on first failure
```

## Test File Organization

**Location:**
- Co-located in `hfs/tests/` directory alongside source code structure
- Test files mirror module names: `test_spec.py` for `hfs/core/spec.py`

**Naming:**
- Test files: `test_<module>.py`
- Test classes: `Test<ModuleName>` or `Test<FunctionName>`
- Test methods: `test_<scenario_description>`
- Mock classes: `Mock<ComponentName>`

**Structure:**
```
hfs/tests/
├── __init__.py
├── test_spec.py          # Tests for hfs/core/spec.py
├── test_triad.py         # Tests for hfs/core/triad.py
├── test_config.py        # Tests for hfs/core/config.py
├── test_negotiation.py   # Tests for hfs/core/negotiation.py
├── test_pressure.py      # Tests for hfs/core/pressure.py
├── test_integration.py   # Tests for hfs/integration/
└── __init__.py
```

## Test Structure

**Suite Organization:**

From `hfs/tests/test_spec.py`:
```python
class TestSectionStatus:
    """Tests for SectionStatus enum."""

    def test_enum_values(self):
        """Verify all expected status values exist."""
        assert SectionStatus.UNCLAIMED.value == "unclaimed"

class TestSection:
    """Tests for Section dataclass."""

    def test_default_values(self):
        """Verify default initialization."""
        section = Section()
        assert section.status == SectionStatus.UNCLAIMED

class TestSpec:
    """Tests for Spec class - comprehensive coverage of all methods."""

    def test_default_initialization(self):
        """Verify default spec state."""
        spec = Spec()
        assert spec.temperature == 1.0
```

**Patterns:**

- **Setup:** Use pytest fixtures or test helper functions
- **Teardown:** Not needed (no stateful setup in tests)
- **Assertion:** Direct Python `assert` statements

Example helper function from `hfs/tests/test_triad.py`:
```python
def create_test_config(
    triad_id: str = "test_triad",
    preset: TriadPreset = TriadPreset.HIERARCHICAL,
    scope_primary: list = None,
    scope_reach: list = None,
    objectives: list = None,
) -> TriadConfig:
    """Helper to create TriadConfig for tests."""
    return TriadConfig(
        id=triad_id,
        preset=preset,
        scope_primary=scope_primary or ["section_a", "section_b"],
        scope_reach=scope_reach or ["section_c"],
        budget_tokens=10000,
        budget_tool_calls=50,
        budget_time_ms=30000,
        objectives=objectives or ["quality", "performance"],
        system_context="Test context",
    )
```

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**

From `hfs/tests/test_negotiation.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

class MockTriad(Triad):
    """Mock triad for testing negotiation."""

    def __init__(self, triad_id: str, negotiate_response: str = "hold"):
        config = TriadConfig(
            id=triad_id,
            preset=TriadPreset.HIERARCHICAL,
            scope_primary=["test"],
            scope_reach=[],
            budget_tokens=1000,
            budget_tool_calls=10,
            budget_time_ms=1000,
            objectives=["test"],
        )
        self.config = config
        self.llm = None
        self.agents = {}
        self._negotiate_response = negotiate_response
        self.pending_revised_proposal: Dict[str, Any] = {}

    def _initialize_agents(self) -> Dict[str, Any]:
        return {}

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        return TriadOutput(position="test", claims=[], proposals={})

    async def negotiate(self, section: str, other_proposals: Dict[str, Any]) -> str:
        return self._negotiate_response

    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        return {}

    def set_negotiate_response(self, response: str):
        """Set the response for negotiate calls."""
        self._negotiate_response = response
```

Simple mock LLM from `hfs/tests/test_triad.py`:
```python
class MockLLMClient:
    """Simple mock LLM client for testing triad initialization."""

    def __init__(self):
        self.calls = []

    async def create_message(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": "Mock response"}
```

**What to Mock:**
- Abstract base classes: Create concrete mock implementations (e.g., `MockTriad`)
- External services: LLM clients, APIs
- Complex dependencies: Only when testing specific behavior

**What NOT to Mock:**
- Core data structures: Use real `Spec`, `Section`, `TriadConfig`
- Business logic: Test the actual implementation, not mocked versions
- Built-in types and standard library: Use real instances

## Fixtures and Factories

**Test Data:**

Test data is created inline using helper functions or by instantiating dataclasses directly:

From `hfs/tests/test_spec.py`:
```python
def test_register_claim_new_section(self):
    """Verify claiming creates section and sets CLAIMED status."""
    spec = Spec()
    spec.register_claim("triad_1", "layout", {"grid": "12-col"})

    assert "layout" in spec.sections
    section = spec.sections["layout"]
    assert section.status == SectionStatus.CLAIMED
    assert section.owner == "triad_1"
```

Helper factory from `hfs/tests/test_triad.py`:
```python
def create_test_config(
    triad_id: str = "test_triad",
    preset: TriadPreset = TriadPreset.HIERARCHICAL,
    # ... parameters with defaults
) -> TriadConfig:
    """Helper to create TriadConfig for tests."""
    return TriadConfig(
        id=triad_id,
        preset=preset,
        scope_primary=scope_primary or ["section_a", "section_b"],
        # ... etc
    )
```

**Location:**
- Inline in test files as module-level functions or class methods
- No separate fixtures directory
- Each test module is self-contained

## Coverage

**Requirements:** Not enforced (no coverage target in pytest.ini or pyproject.toml)

**View Coverage:**
```bash
pytest hfs/tests --cov=hfs --cov-report=html
```

Coverage tracking is not configured by default but can be enabled with pytest-cov plugin.

## Test Types

**Unit Tests:**
- Scope: Individual functions/methods and small units
- Approach: Test one behavior at a time
- Example `test_spec.py`: Tests each method of `Spec` class individually
- No external dependencies (all mocked)

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Test full workflows without mocking internal components
- Example: `TestSpecNegotiationScenario.test_full_negotiation_flow()` in `test_spec.py`:

```python
class TestSpecNegotiationScenario:
    """Integration test: Full negotiation scenario."""

    def test_full_negotiation_flow(self):
        """Test a complete negotiation from start to freeze."""
        spec = Spec()

        # Initialize territory
        spec.initialize_sections(["layout", "visual", "motion", "interaction"])

        # Round 0: Initial claims
        spec.register_claim("layout_triad", "layout", {"grid": "12-col", "spacing": "8px"})
        spec.register_claim("visual_triad", "visual", {"theme": "modern", "colors": ["#fff", "#000"]})
        spec.register_claim("motion_triad", "motion", {"duration": "300ms"})

        # Both want interaction
        spec.register_claim("visual_triad", "interaction", {"hover": "scale"})
        spec.register_claim("motion_triad", "interaction", {"hover": "fade"})

        assert spec.get_contested_sections() == ["interaction"]

        # Round 1: Negotiation
        spec.advance_round()
        spec.concede("motion_triad", "interaction")

        assert spec.get_contested_sections() == []
        assert spec.get_section_owner("interaction") == "visual_triad"

        # Freeze
        spec.freeze()

        assert spec.is_frozen()
        assert spec.sections["layout"].content == {"grid": "12-col", "spacing": "8px"}

        # Coverage report
        report = spec.get_coverage_report()
        assert report["coverage_gaps"] == 0
        assert report["unresolved_conflicts"] == 0
```

**E2E Tests:**
- Not found in codebase
- Would test full HFS pipeline end-to-end
- Would require real LLM client (expensive)

## Common Patterns

**Async Testing:**

From `hfs/tests/test_negotiation.py`:
```python
import asyncio
from unittest.mock import AsyncMock

class MockTriad(Triad):
    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        return TriadOutput(position="test", claims=[], proposals={})

    async def negotiate(self, section: str, other_proposals: Dict[str, Any]) -> str:
        return self._negotiate_response

# Test method automatically awaits with asyncio_mode = "auto" in pytest config
# No explicit async/await needed in test code
```

**Error Testing:**

From `hfs/tests/test_triad.py`:
```python
def test_cannot_instantiate_directly(self):
    """Verify Triad ABC cannot be instantiated directly."""
    config = create_test_config()
    llm = MockLLMClient()

    with pytest.raises(TypeError) as exc_info:
        Triad(config, llm)

    # The error should mention abstract methods
    assert "abstract" in str(exc_info.value).lower()
```

From `hfs/tests/test_config.py`:
```python
def test_invalid_preset(self):
    """Test that invalid preset is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        TriadConfigModel(
            id="test",
            preset="invalid_preset",
        )
```

**Boolean/Return Value Testing:**

From `hfs/tests/test_spec.py`:
```python
def test_concede_removes_claimant(self):
    """Verify concession removes triad from claimants."""
    spec = Spec()
    spec.register_claim("triad_1", "layout", {"grid": "12-col"})
    spec.register_claim("triad_2", "layout", {"grid": "16-col"})

    result = spec.concede("triad_1", "layout")

    assert result is True  # Verify success return value
    section = spec.sections["layout"]
    assert "triad_1" not in section.claims
    assert section.owner == "triad_2"

def test_concede_nonexistent_section(self):
    """Verify conceding from nonexistent section returns False."""
    spec = Spec()
    result = spec.concede("triad_1", "nonexistent")
    assert result is False  # Verify failure return value
```

## Test Classes and Organization

**Organizational approach:**
- Group tests by feature/component using test classes
- Each class tests related functionality
- Class names follow pattern: `Test<TargetClass>` or `Test<Functionality>`

From `hfs/tests/test_triad.py`:
```python
class TestTriadPreset:
    """Tests for TriadPreset enum - values, completeness, and usage."""
    # Tests for enum behavior

class TestTriadConfig:
    """Tests for TriadConfig dataclass - all fields and optional behavior."""
    # Tests for config validation

class TestTriadFactory:
    """Tests for triad_factory - create_triad() and utilities."""
    # Tests for factory pattern

class TestTriadInitialization:
    """Tests for triad initialization behavior across all presets."""
    # Tests across multiple presets
```

## Main Entry Point

Test suite can be run directly:

From `hfs/tests/test_spec.py` (end of file):
```python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

This allows tests to be run as: `python hfs/tests/test_spec.py`

---

*Testing analysis: 2026-01-29*
