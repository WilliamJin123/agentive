# Phase 2: Agno Tools - Research

**Researched:** 2026-01-29
**Domain:** Agno Tool Decorators, Pydantic Validation, HFS Operations
**Confidence:** HIGH

## Summary

This phase implements HFS operations as Agno tools that agents can invoke during negotiation and execution. The research focused on Agno's `@tool` decorator patterns, the `Toolkit` class for organizing related tools, Pydantic validation integration, and how to design tools for LLM comprehension.

Agno v2.4.6 (installed) provides a mature `@tool` decorator that automatically generates JSON schemas from Python type hints and docstrings. The decorator supports async functions, Pydantic validation via `validate_call`, and context injection (agent, team, run_context). Tools return strings (typically JSON) that the agent processes.

The CONTEXT.md decisions constrain the implementation: strict Pydantic validation for inputs, Pydantic models for outputs, automatic retry on ValidationError (3 attempts), shared state injection via Team/Agent context, and LLM-optimized docstrings. State query tools (`get_current_claims`, `get_negotiation_state`) are required for agent awareness.

**Primary recommendation:** Create an `HFSToolkit` class extending `agno.tools.Toolkit` that encapsulates all HFS tools with shared state access. Use Pydantic BaseModel for input/output schemas, leverage the `@tool` decorator for registration, and design docstrings explicitly for LLM comprehension.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agno | 2.4.6 | Tool decorator, Toolkit base class | Already installed, framework's native tooling |
| pydantic | 2.x | Input/output validation, BaseModel schemas | Agno's internal validation engine |
| docstring_parser | installed | Docstring parsing for schema generation | Agno dependency, used for parameter descriptions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing | stdlib | Type hints for schema generation | Always - Agno derives JSON schema from type hints |
| enum | stdlib | Enumerated types (NegotiationResponse) | When defining constrained string values |
| dataclasses | stdlib | Lightweight data containers | For internal state, not tool I/O (use Pydantic) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Toolkit class | Standalone @tool functions | Toolkit provides shared state, organization, better DX |
| Pydantic models | dataclasses + manual validation | Pydantic integrates with Agno's validate_call |
| JSON string returns | Pydantic model returns | Agno tools expect string returns, serialize Pydantic to JSON |

**Installation:**
All dependencies already installed. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── agno/                    # Existing from Phase 1
│   ├── __init__.py          # Add HFSToolkit export
│   ├── providers.py         # From Phase 1
│   ├── models.py            # From Phase 1
│   └── tools/               # NEW: Tool implementations
│       ├── __init__.py      # Export HFSToolkit
│       ├── toolkit.py       # HFSToolkit class
│       ├── schemas.py       # Pydantic input/output models
│       └── errors.py        # Custom exceptions
```

### Pattern 1: Pydantic Input/Output Schemas
**What:** Define explicit Pydantic models for tool inputs and outputs
**When to use:** All HFS tools - provides validation, serialization, clear contracts
**Example:**
```python
# Source: Pydantic documentation + Agno patterns
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List
from enum import Enum

class NegotiationDecision(str, Enum):
    """Valid responses in a negotiation round."""
    CONCEDE = "concede"
    REVISE = "revise"
    HOLD = "hold"

class RegisterClaimInput(BaseModel):
    """Input schema for register_claim tool.

    Use this tool to claim ownership of a section in the spec.
    You must provide a section_id (string) and your proposal content.
    """
    section_id: str = Field(
        ...,
        description="The unique identifier of the section to claim. Must be a non-empty string.",
        min_length=1,
        max_length=128,
    )
    proposal: str = Field(
        ...,
        description="Your proposed content for this section. Be specific and complete.",
        min_length=1,
    )

    @field_validator('section_id')
    @classmethod
    def validate_section_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("section_id cannot be empty or whitespace only")
        return v.strip()

class RegisterClaimOutput(BaseModel):
    """Output from register_claim tool."""
    success: bool
    section_id: str
    status: str  # "claimed", "contested", "rejected"
    current_claimants: List[str]
    message: str
```

### Pattern 2: Toolkit Class with Shared State
**What:** Extend `agno.tools.Toolkit` to share HFS state across tools
**When to use:** When tools need access to shared Spec state
**Example:**
```python
# Source: Agno toolkit.py + calculator.py examples
from agno.tools import Toolkit
from typing import Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hfs.core.spec import Spec

class HFSToolkit(Toolkit):
    """HFS operation tools with shared spec state access.

    This toolkit provides tools for HFS agents to:
    - Register claims on spec sections
    - Respond to negotiations
    - Generate code for owned sections
    - Query current state

    The spec is injected at runtime via the agent's context.
    """

    def __init__(
        self,
        spec: Optional["Spec"] = None,
        triad_id: Optional[str] = None,
        **kwargs,
    ):
        self.spec = spec
        self.triad_id = triad_id

        tools: List[Callable] = [
            self.register_claim,
            self.negotiate_response,
            self.generate_code,
            self.get_current_claims,
            self.get_negotiation_state,
        ]

        super().__init__(name="hfs_tools", tools=tools, **kwargs)
```

### Pattern 3: LLM-Optimized Docstrings
**What:** Docstrings designed for LLM comprehension, not just human developers
**When to use:** All tool methods - the LLM uses docstrings to understand when/how to call
**Example:**
```python
# Source: Agno docs + best practices
def register_claim(self, section_id: str, proposal: str) -> str:
    """Register your claim on a section of the spec.

    WHEN TO USE: Call this during the deliberation phase when you want to
    claim ownership of a section. You can claim sections in your scope_primary
    (guaranteed) or scope_reach (competitive).

    IMPORTANT CONSTRAINTS:
    - section_id must be a valid section name from the spec
    - proposal must contain complete content for the section
    - You cannot claim frozen sections
    - If another agent already claimed this section, it becomes "contested"

    EXAMPLE:
    >>> register_claim(section_id="header", proposal="Navigation bar with logo...")

    Args:
        section_id: The section to claim. Must match a section name in the spec.
        proposal: Your complete proposed content for this section.

    Returns:
        JSON with success status, section status, and current claimants.
        On validation error, returns error message with correction hints.
    """
```

### Pattern 4: Error Handling with Retry Hints
**What:** Return structured errors that help the LLM self-correct
**When to use:** Validation failures that the LLM can fix
**Example:**
```python
# Source: CONTEXT.md decisions
from pydantic import ValidationError
import json

def _handle_validation_error(self, error: ValidationError) -> str:
    """Convert ValidationError to LLM-friendly error message with hints."""
    errors = error.errors()
    hints = []
    for err in errors:
        field = ".".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        hints.append(f"- {field}: {msg}")

    return json.dumps({
        "success": False,
        "error": "validation_error",
        "message": "Invalid input. Please fix and retry.",
        "hints": hints,
        "retry_allowed": True,
    })
```

### Anti-Patterns to Avoid
- **Vague docstrings:** Docstrings like "Registers a claim" don't help LLMs understand when to use the tool
- **Implicit state:** Tools that require state not injected via Toolkit class are hard to test
- **Silent failures:** Returning empty/null instead of explicit error messages confuses LLMs
- **Complex nested inputs:** Deeply nested Pydantic models are harder for LLMs to construct correctly
- **Returning raw exceptions:** Always catch and format exceptions into structured JSON responses

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema from types | Manual schema dict | Agno's `from_callable()` | Handles edge cases, Optional, Union, defaults |
| Docstring parsing | Regex parsing | `docstring_parser` library | Already Agno dependency, handles all formats |
| Input validation | Manual if/raise | Pydantic `@field_validator` | Automatic, consistent, serializable errors |
| Enum validation | String comparison | Pydantic with `Literal` or `Enum` | Type-safe, auto-documented in schema |
| Tool registration | Manual Function() | `@tool` decorator or Toolkit | Handles async detection, wrapping, schema |

**Key insight:** Agno's tool infrastructure does significant work transforming Python functions into agent-callable tools. Leverage this rather than reimplementing validation, schema generation, or error handling.

## Common Pitfalls

### Pitfall 1: Forgetting to Return Strings
**What goes wrong:** Tools return Pydantic models or dicts directly, causing agent errors
**Why it happens:** Python habit of returning typed objects
**How to avoid:** Always serialize output to JSON string: `return output_model.model_dump_json()`
**Warning signs:** Agent receives `<ModelName object at ...>` or dict repr instead of content

### Pitfall 2: Docstrings Without Constraints
**What goes wrong:** LLM calls tool with invalid arguments, repeated validation failures
**Why it happens:** Docstring describes what tool does but not input constraints
**How to avoid:** Include explicit constraints section in docstring: "IMPORTANT CONSTRAINTS: ..."
**Warning signs:** Same validation error repeating across retries

### Pitfall 3: Missing Error Context for Retries
**What goes wrong:** LLM receives "validation failed" but doesn't know how to fix
**Why it happens:** Generic error messages without field-specific hints
**How to avoid:** Return structured error with `hints` array and `retry_allowed` flag
**Warning signs:** LLM retries with identical (wrong) arguments

### Pitfall 4: State Access Without Injection
**What goes wrong:** Tools try to access global/module-level state, breaks in tests
**Why it happens:** Easier to reach for globals than wire dependency injection
**How to avoid:** Pass state via Toolkit `__init__` or via Agno's `run_context` parameter
**Warning signs:** Tests require complex mocking of module globals

### Pitfall 5: Blocking Async in Sync Tools
**What goes wrong:** Async Spec operations called from sync tool methods
**Why it happens:** Mixing sync/async without considering execution context
**How to avoid:** Either make all tools async (recommended for HFS) or ensure Spec operations are sync-compatible
**Warning signs:** "RuntimeWarning: coroutine was never awaited"

### Pitfall 6: Over-Validating for LLMs
**What goes wrong:** Validation too strict, LLM can't produce valid input
**Why it happens:** Applying human-developer validation standards to LLM inputs
**How to avoid:** Validate structure/types strictly, content constraints loosely. Allow empty strings with warnings rather than rejecting
**Warning signs:** High retry rate, LLM "stuck" on validation loop

## Code Examples

Verified patterns from Agno source code and official documentation:

### Complete Tool with Pydantic I/O
```python
# Source: Agno decorator.py + function.py patterns
from agno.tools.decorator import tool
from pydantic import BaseModel, Field
from typing import Optional, List
import json

class NegotiateInput(BaseModel):
    """Input for negotiate_response tool."""
    section_id: str = Field(..., description="Section being negotiated")
    decision: str = Field(
        ...,
        description="Your decision: 'concede', 'revise', or 'hold'",
        pattern="^(concede|revise|hold)$"
    )
    revised_proposal: Optional[str] = Field(
        None,
        description="Required if decision is 'revise'. Your updated proposal."
    )

class NegotiateOutput(BaseModel):
    """Output from negotiate_response tool."""
    success: bool
    section_id: str
    decision: str
    round_number: int
    participants: List[str]
    message: str

@tool(
    name="negotiate_response",
    description="Respond to a negotiation round for a contested section",
)
def negotiate_response(
    section_id: str,
    decision: str,
    revised_proposal: Optional[str] = None,
    agent=None,  # Injected by Agno
) -> str:
    """Submit your negotiation response for a contested section.

    WHEN TO USE: Call this when you're in a negotiation round and need to
    respond to other agents' proposals for a section you've claimed.

    DECISIONS:
    - "concede": Withdraw your claim. Use when another proposal is clearly better.
    - "revise": Update your proposal. Provide revised_proposal with improvements.
    - "hold": Maintain your current position. Use when your proposal is strongest.

    IMPORTANT CONSTRAINTS:
    - decision must be exactly one of: "concede", "revise", "hold"
    - If decision is "revise", you MUST provide revised_proposal
    - If decision is "concede" or "hold", revised_proposal is ignored

    Args:
        section_id: The contested section's identifier
        decision: Your response - "concede", "revise", or "hold"
        revised_proposal: New proposal content (required for "revise")

    Returns:
        JSON with decision status, round number, and participants
    """
    try:
        input_model = NegotiateInput(
            section_id=section_id,
            decision=decision,
            revised_proposal=revised_proposal,
        )
    except ValidationError as e:
        return _format_validation_error(e)

    # ... tool implementation ...

    output = NegotiateOutput(
        success=True,
        section_id=section_id,
        decision=decision,
        round_number=1,  # from spec state
        participants=["triad_1", "triad_2"],  # from spec state
        message=f"Response recorded: {decision}"
    )
    return output.model_dump_json()
```

### Toolkit Class with State Injection
```python
# Source: Agno toolkit.py patterns
from agno.tools import Toolkit
from agno.tools.decorator import tool
from typing import Callable, List, Optional, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from hfs.core.spec import Spec

class HFSToolkit(Toolkit):
    """HFS negotiation and execution tools.

    Provides tools for agents to interact with the HFS spec during
    deliberation, negotiation, and execution phases.

    State is injected via __init__ and accessed by all tools.
    """

    def __init__(
        self,
        spec: "Spec",
        triad_id: str,
        **kwargs,
    ):
        """Initialize HFS toolkit with shared state.

        Args:
            spec: The shared Spec instance (warm wax)
            triad_id: Identifier of the triad using these tools
            **kwargs: Additional args passed to Toolkit base
        """
        self._spec = spec
        self._triad_id = triad_id

        tools: List[Callable] = [
            self.register_claim,
            self.negotiate_response,
            self.generate_code,
            self.get_current_claims,
            self.get_negotiation_state,
        ]

        super().__init__(name="hfs_tools", tools=tools, **kwargs)

    def register_claim(self, section_id: str, proposal: str) -> str:
        """Register your claim on a spec section.

        WHEN TO USE: During deliberation when you want to claim a section.

        CONSTRAINTS:
        - section_id must exist in the spec
        - Cannot claim frozen sections
        - Your claim may result in "contested" status if others claimed it

        Args:
            section_id: Section to claim
            proposal: Your proposed content

        Returns:
            JSON with claim status and current claimants
        """
        if not section_id or not section_id.strip():
            return json.dumps({
                "success": False,
                "error": "section_id cannot be empty",
                "hint": "Provide a valid section name from the spec"
            })

        try:
            self._spec.register_claim(self._triad_id, section_id.strip(), proposal)
            section = self._spec.sections.get(section_id)
            return json.dumps({
                "success": True,
                "section_id": section_id,
                "status": section.status.value if section else "unknown",
                "current_claimants": list(section.claims) if section else [],
                "message": f"Claim registered for {section_id}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "retry_allowed": False
            })

    def get_current_claims(self) -> str:
        """Get all current claims in the spec.

        WHEN TO USE: To understand the current state before claiming or negotiating.

        Returns:
            JSON with sections grouped by status (unclaimed, claimed, contested, frozen)
        """
        return json.dumps({
            "success": True,
            "unclaimed": self._spec.get_unclaimed_sections(),
            "claimed": self._spec.get_claimed_sections(),
            "contested": self._spec.get_contested_sections(),
            "frozen": self._spec.get_frozen_sections(),
            "your_claims": [
                name for name, section in self._spec.sections.items()
                if self._triad_id in section.claims
            ],
            "temperature": self._spec.temperature,
            "round": self._spec.round,
        })

    def get_negotiation_state(self, section_id: Optional[str] = None) -> str:
        """Get negotiation state for a section or all contested sections.

        WHEN TO USE: Before responding in a negotiation round to see other proposals.

        Args:
            section_id: Optional specific section. If None, returns all contested.

        Returns:
            JSON with proposals, claimants, and history for requested sections
        """
        if section_id:
            section = self._spec.sections.get(section_id)
            if not section:
                return json.dumps({
                    "success": False,
                    "error": f"Section {section_id} not found"
                })
            return json.dumps({
                "success": True,
                "section_id": section_id,
                "status": section.status.value,
                "claimants": list(section.claims),
                "proposals": {k: str(v)[:500] for k, v in section.proposals.items()},
                "owner": section.owner,
            })

        # Return all contested
        contested = {}
        for name in self._spec.get_contested_sections():
            section = self._spec.sections[name]
            contested[name] = {
                "claimants": list(section.claims),
                "proposals": {k: str(v)[:200] for k, v in section.proposals.items()},
            }

        return json.dumps({
            "success": True,
            "contested_sections": contested,
            "total_contested": len(contested),
        })
```

### Async Tool Pattern
```python
# Source: Agno decorator.py async handling
from agno.tools.decorator import tool

@tool(
    name="generate_code",
    description="Generate code for an owned section",
)
async def generate_code(
    section_id: str,
    agent=None,  # Injected by Agno
) -> str:
    """Generate implementation code for a section you own.

    WHEN TO USE: During execution phase after spec is frozen.
    Only call for sections where you are the owner.

    CONSTRAINTS:
    - Spec must be frozen (temperature = 0)
    - You must be the owner of the section
    - Code must match the proposal you made

    Args:
        section_id: The section to generate code for

    Returns:
        JSON with generated code or error
    """
    # Async implementation...
    pass
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual Function() creation | @tool decorator | Agno 2.x | Less boilerplate, auto schema generation |
| String type hints only | Pydantic models for I/O | Pydantic v2 | Better validation, serialization |
| Single tools list | Toolkit.functions + async_functions | Agno 2.4+ | Proper sync/async separation |
| Manual docstring parsing | docstring_parser integration | Agno 2.x | Automatic parameter description extraction |

**Deprecated/outdated:**
- `agno.tools.Function` direct instantiation: Use `@tool` decorator or Toolkit.register()
- Returning dicts from tools: Always return JSON strings
- Global state access: Use Toolkit __init__ or run_context injection

## Open Questions

Things that couldn't be fully resolved:

1. **Negotiation Tool Design: One vs Three**
   - What we know: CONTEXT.md marks this as Claude's discretion
   - Options: Single `negotiate_response(decision, ...)` or separate `concede()`, `revise()`, `hold()`
   - Recommendation: Single tool with decision parameter - cleaner, matches natural language ("respond with concede/revise/hold")

2. **Module Organization: Single vs Split**
   - What we know: CONTEXT.md marks as Claude's discretion
   - Options: `tools.py` single file or `tools/` directory with separate modules
   - Recommendation: Start with `tools/` directory (toolkit.py, schemas.py, errors.py) for clean separation

3. **Output Wrapper Consistency**
   - What we know: CONTEXT.md marks as Claude's discretion
   - Options: Consistent wrapper for all outputs or tool-specific structures
   - Recommendation: Consistent base with `success`, `error`, `message` fields; tool-specific `data` field

4. **Claim Conflict Retry Behavior**
   - What we know: ValidationError triggers retry, RuntimeError fails immediately
   - What's unclear: Should "section already contested" be retryable?
   - Recommendation: Yes, with hint "consider different section or check get_current_claims()"

## Sources

### Primary (HIGH confidence)
- Agno source code (installed v2.4.6): `.venv/Lib/site-packages/agno/tools/`
  - decorator.py: @tool implementation and parameters
  - function.py: Function class, Pydantic integration
  - toolkit.py: Toolkit base class patterns
  - calculator.py: Example toolkit implementation
- HFS codebase: `hfs/core/spec.py`, `hfs/core/negotiation.py`
- CONTEXT.md: User decisions for this phase

### Secondary (MEDIUM confidence)
- [Agno Documentation - Python Functions as Tools](https://docs.agno.com/basics/tools/creating-tools/python-functions)
- [Agno Documentation - @tool Decorator Reference](https://docs.agno.com/reference/tools/decorator)
- [Pydantic Documentation - Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Agno GitHub Repository](https://github.com/agno-agi/agno)

### Tertiary (LOW confidence)
- Web search results on Agno patterns (verified against source code)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - examined installed Agno source code directly
- Architecture: HIGH - patterns derived from Agno toolkit.py and calculator.py
- Pitfalls: HIGH - based on Agno function.py error handling + CONTEXT.md decisions
- Code examples: HIGH - verified against actual Agno implementation

**Research date:** 2026-01-29
**Valid until:** 60 days (Agno 2.4.6 stable, already installed)
