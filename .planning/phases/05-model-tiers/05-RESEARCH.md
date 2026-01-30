# Phase 5: Model Tiers - Research

**Researched:** 2026-01-29
**Domain:** LLM model selection, role-based routing, adaptive escalation
**Confidence:** HIGH

## Summary

This phase implements model selection driven by role, phase, and failure-adaptive escalation. The existing ProviderManager and keycycle infrastructure provides a solid foundation for multi-provider model access. The key work is adding a configuration layer that maps roles to tiers, tiers to provider-specific models, and tracks failures for permanent config evolution.

The research confirms that:
1. Agno supports per-agent model assignment via the `model` parameter on Agent construction
2. PyYAML/ruamel.yaml can handle round-trip config editing for persistent escalation
3. The existing config.py pattern with Pydantic models can be extended for tier configuration
4. Provider-specific model IDs vary (e.g., `gpt-oss-120b` on Cerebras vs `openai/gpt-oss-120b` on Groq)

**Primary recommendation:** Add a `model_tiers` section to HFS YAML config with role defaults, provider-specific model IDs per tier, and escalation state tracking.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x | Config validation | Already used for HFSConfig, type-safe validation |
| pyyaml | 6.0.3 | YAML parsing | Already installed, safe_load/safe_dump for config |
| ruamel.yaml | 0.19.1 | Round-trip YAML editing | Preserves comments/formatting when updating escalation state |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| keycycle | existing | Provider wrapper | Already integrated, provides get_model() |
| agno | existing | Agent model param | Pass model to Agent constructor |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ruamel.yaml | pyyaml only | pyyaml loses comments on write; ruamel preserves formatting |
| YAML config file | env vars | YAML more readable for tier mappings, env vars harder to structure |
| Permanent file update | runtime-only | File persistence survives restarts, enables learning |

**Installation:**
```bash
pip install ruamel.yaml
```

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── config/
│   ├── default.yaml       # Extended with model_tiers section
│   └── examples/
├── core/
│   ├── config.py          # Extended with ModelTiersConfig
│   └── model_selector.py  # NEW: Tier resolution and escalation logic
└── agno/
    ├── providers.py       # Extended: get_model_for_role() method
    └── teams/
        └── base.py        # Modified: Use tier-based model selection
```

### Pattern 1: Tier Configuration Schema
**What:** YAML schema for role-to-tier mapping with provider-specific models
**When to use:** All model tier configuration
**Example:**
```yaml
# Source: Project design based on CONTEXT.md decisions
model_tiers:
  # Tier definitions with provider-specific model IDs
  tiers:
    reasoning:
      description: "Highest capability for complex orchestration"
      providers:
        cerebras: "qwen-3-235b-a22b-instruct-2507"
        groq: "moonshotai/kimi-k2-instruct"
        gemini: "gemini-2.5-flash"
        openrouter: "anthropic/claude-sonnet-4"
    general:
      description: "Balanced capability for workers"
      providers:
        cerebras: "llama-3.3-70b"
        groq: "llama-3.3-70b-versatile"
        gemini: "gemini-2.5-flash-lite"
        openrouter: "meta-llama/llama-3.3-70b-instruct:free"
    fast:
      description: "Speed-optimized for code execution"
      providers:
        cerebras: "zai-glm-4.7"
        groq: "openai/gpt-oss-120b"
        gemini: "gemma-3-27b-it"
        openrouter: "meta-llama/llama-3.3-70b-instruct:free"

  # Role-to-tier defaults
  role_defaults:
    # Hierarchical triad
    orchestrator: "reasoning"
    worker_a: "general"
    worker_b: "general"
    # Dialectic triad
    proposer: "general"      # Creative generation
    critic: "general"        # Analysis
    synthesizer: "reasoning" # Complex integration
    # Consensus triad
    peer_1: "general"
    peer_2: "general"
    peer_3: "general"
    # Special case
    code_execution: "fast"   # Always uses fast tier

  # Phase overrides (optional)
  phase_overrides:
    execution:
      worker_a: "fast"
      worker_b: "fast"

  # Escalation state (updated by system)
  escalation_state:
    # Format: "triad_id:role": "current_tier"
    # Empty initially, populated on failures
```

### Pattern 2: Model Selector Class
**What:** Encapsulates tier resolution with provider fallback
**When to use:** Obtaining model for specific role
**Example:**
```python
# Source: Design based on existing ProviderManager pattern
class ModelSelector:
    """Resolves role + triad to appropriate model via tier system."""

    def __init__(
        self,
        config: ModelTiersConfig,
        provider_manager: ProviderManager,
    ):
        self.config = config
        self.provider_manager = provider_manager
        self._failure_counts: Dict[str, int] = {}  # "triad:role" -> count

    def get_model(
        self,
        triad_id: str,
        role: str,
        phase: Optional[str] = None,
    ) -> Model:
        """Get model for role, considering phase overrides and escalation."""
        # 1. Check escalation state first (highest priority)
        escalation_key = f"{triad_id}:{role}"
        if escalation_key in self.config.escalation_state:
            tier = self.config.escalation_state[escalation_key]
        # 2. Check phase override
        elif phase and phase in self.config.phase_overrides:
            tier = self.config.phase_overrides[phase].get(
                role,
                self.config.role_defaults.get(role, "general")
            )
        # 3. Use role default
        else:
            tier = self.config.role_defaults.get(role, "general")

        # 4. Resolve tier to provider-specific model ID
        return self._get_model_for_tier(tier)

    def _get_model_for_tier(self, tier: str) -> Model:
        """Try each provider until one returns a model."""
        tier_config = self.config.tiers[tier]
        for provider in self.provider_manager.available_providers:
            if provider in tier_config.providers:
                model_id = tier_config.providers[provider]
                try:
                    return self.provider_manager.get_model(provider, model_id)
                except NoAvailableKeyError:
                    continue
        raise NoAvailableKeyError(...)
```

### Pattern 3: Failure Tracking and Escalation
**What:** Track consecutive failures, trigger permanent config update
**When to use:** After tool/task execution failure
**Example:**
```python
# Source: Design based on CONTEXT.md escalation decisions
class EscalationTracker:
    """Tracks failures and triggers permanent tier upgrades."""

    ESCALATION_THRESHOLD = 3  # Consecutive failures
    TIER_ORDER = ["fast", "general", "reasoning"]  # Escalation path

    def __init__(self, config_path: Path, config: ModelTiersConfig):
        self.config_path = config_path
        self.config = config
        self._failure_counts: Dict[str, int] = defaultdict(int)

    def record_failure(self, triad_id: str, role: str) -> Optional[str]:
        """Record failure, return new tier if escalation triggered."""
        key = f"{triad_id}:{role}"
        self._failure_counts[key] += 1

        if self._failure_counts[key] >= self.ESCALATION_THRESHOLD:
            new_tier = self._escalate(key)
            self._failure_counts[key] = 0  # Reset after escalation
            return new_tier
        return None

    def record_success(self, triad_id: str, role: str) -> None:
        """Reset failure count on success (within same tier)."""
        key = f"{triad_id}:{role}"
        self._failure_counts[key] = 0

    def _escalate(self, key: str) -> Optional[str]:
        """Upgrade to next tier, persist to config file."""
        current = self.config.escalation_state.get(
            key,
            self.config.role_defaults.get(key.split(":")[-1], "general")
        )
        current_idx = self.TIER_ORDER.index(current)

        if current_idx >= len(self.TIER_ORDER) - 1:
            # Already at highest tier
            logger.warning(f"{key} at highest tier, cannot escalate")
            return None

        new_tier = self.TIER_ORDER[current_idx + 1]
        self._persist_escalation(key, new_tier)
        return new_tier

    def _persist_escalation(self, key: str, tier: str) -> None:
        """Update YAML config file with new escalation state."""
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True

        with open(self.config_path, 'r') as f:
            data = yaml.load(f)

        # Ensure escalation_state exists
        if 'model_tiers' not in data.get('config', {}):
            data['config']['model_tiers'] = {}
        if 'escalation_state' not in data['config']['model_tiers']:
            data['config']['model_tiers']['escalation_state'] = {}

        data['config']['model_tiers']['escalation_state'][key] = tier

        with open(self.config_path, 'w') as f:
            yaml.dump(data, f)
```

### Anti-Patterns to Avoid
- **Runtime-only escalation:** Loses learning across restarts; always persist to config
- **Tier de-escalation:** Creates oscillation; once upgraded, stay upgraded
- **Hardcoded model IDs:** Provider IDs differ; always use tier config mapping
- **Single provider assumption:** Provider may be unavailable; implement fallback chain

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML round-trip editing | Manual string manipulation | ruamel.yaml | Preserves comments, handles edge cases |
| Config validation | Manual type checking | Pydantic models | Type safety, clear error messages |
| Provider model lookup | Dict access | ProviderManager.get_model() | Handles key rotation, rate limiting |
| Retry with backoff | Manual loops | keycycle built-in | Already handles 429s, key rotation |

**Key insight:** The existing keycycle/ProviderManager infrastructure handles the hard parts (rate limiting, key rotation, provider abstraction). This phase adds a thin configuration layer on top.

## Common Pitfalls

### Pitfall 1: Provider Model ID Mismatch
**What goes wrong:** Same model has different IDs across providers (e.g., `gpt-oss-120b` vs `openai/gpt-oss-120b`)
**Why it happens:** No standard model naming convention across providers
**How to avoid:** Always use provider-specific model IDs in tier config; never assume IDs are portable
**Warning signs:** "Model not found" errors when switching providers

### Pitfall 2: Escalation Without Reset
**What goes wrong:** Failure count persists even after tier upgrade, causing immediate re-escalation
**Why it happens:** Forgetting to reset counter after successful escalation
**How to avoid:** Reset failure count to 0 when escalation triggers
**Warning signs:** Rapid escalation through all tiers on single bad run

### Pitfall 3: Missing Code Execution Override
**What goes wrong:** Code execution uses wrong model, not fast tier
**Why it happens:** generate_code tool doesn't check phase/role override
**How to avoid:** Explicit check in generate_code for code_execution role
**Warning signs:** Slow/expensive code generation, timeouts

### Pitfall 4: Lost Config Comments
**What goes wrong:** User comments in YAML config disappear after escalation update
**Why it happens:** Using pyyaml.safe_dump instead of ruamel.yaml
**How to avoid:** Always use ruamel.yaml for config updates
**Warning signs:** Clean YAML after update vs commented YAML before

### Pitfall 5: Circular Escalation Dependency
**What goes wrong:** Escalation triggers during escalation check, infinite loop
**Why it happens:** Config file read during write operation
**How to avoid:** Load config once at start, update in-memory + file atomically
**Warning signs:** Stack overflow, hung process during failure handling

## Code Examples

### Example 1: Pydantic Config Models
```python
# Source: Design based on existing config.py pattern
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field

TierName = Literal["reasoning", "general", "fast"]

class TierConfig(BaseModel):
    """Configuration for a single model tier."""
    description: str = Field(..., description="Human-readable tier purpose")
    providers: Dict[str, str] = Field(
        ..., description="Provider name -> model ID mapping"
    )

class ModelTiersConfig(BaseModel):
    """Model tier configuration section."""
    tiers: Dict[TierName, TierConfig] = Field(
        ..., description="Tier name -> tier config"
    )
    role_defaults: Dict[str, TierName] = Field(
        default_factory=dict,
        description="Role name -> default tier"
    )
    phase_overrides: Dict[str, Dict[str, TierName]] = Field(
        default_factory=dict,
        description="Phase name -> role overrides"
    )
    escalation_state: Dict[str, TierName] = Field(
        default_factory=dict,
        description="triad:role -> escalated tier (system-managed)"
    )
```

### Example 2: Agent Construction with Tier Model
```python
# Source: Based on existing dialectic.py pattern
def _create_agents(self) -> Dict[str, Agent]:
    """Create agents with tier-appropriate models."""
    # Get models from selector
    proposer_model = self.model_selector.get_model(
        triad_id=self.config.id,
        role="proposer",
        phase=self._session_state.current_phase,
    )
    critic_model = self.model_selector.get_model(
        triad_id=self.config.id,
        role="critic",
        phase=self._session_state.current_phase,
    )
    synthesizer_model = self.model_selector.get_model(
        triad_id=self.config.id,
        role="synthesizer",
        phase=self._session_state.current_phase,
    )

    proposer = Agent(
        name=f"proposer_{self.config.id}",
        model=proposer_model,  # Tier-selected model
        role="Creative proposal generator (thesis)",
        instructions="...",
        tools=[...],
    )
    # ... similar for critic, synthesizer
```

### Example 3: Code Execution Fast Tier Override
```python
# Source: Design based on MODL-03 requirement
def generate_code(self, section_id: str) -> str:
    """Generate code using fast tier model."""
    # Force fast tier for code execution
    code_model = self.model_selector.get_model(
        triad_id=self._triad_id,
        role="code_execution",  # Special role, always fast tier
        phase="execution",
    )

    # Use code_model for actual generation
    # ... rest of implementation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single model for all agents | Per-agent model selection | Agno 1.x (2025) | Better cost/capability tradeoff |
| Manual model ID strings | Provider-agnostic config | This phase | Cleaner multi-provider support |
| Runtime config only | Persistent config evolution | This phase | Learning across restarts |

**Deprecated/outdated:**
- Hardcoded model IDs: Use tier config instead
- Single provider assumption: Use provider fallback chain

## Open Questions

1. **Config file location**
   - What we know: Existing config in `hfs/config/default.yaml`
   - What's unclear: Should escalation state go in same file or separate?
   - Recommendation: Same file for simplicity, `escalation_state` section clearly marked as system-managed

2. **Provider preference order**
   - What we know: Current order is cerebras, groq, gemini, openrouter
   - What's unclear: Should tier config override default provider preference?
   - Recommendation: Use same order for consistency; tier config only specifies model IDs

3. **Dialectic triad tier mapping**
   - What we know: CONTEXT.md delegates to Claude's discretion
   - What's unclear: Optimal tier for proposer/critic roles
   - Recommendation: Proposer=general (creative), Critic=general (analysis), Synthesizer=reasoning (complex integration)

## Sources

### Primary (HIGH confidence)
- Existing codebase: `hfs/agno/providers.py`, `hfs/core/config.py`, `hfs/agno/teams/dialectic.py`
- keycycle YAML configs: `cerebras.yaml`, `groq.yaml`, `gemini.yaml` (verified model IDs)
- 05-CONTEXT.md: Locked decisions from discussion phase

### Secondary (MEDIUM confidence)
- [Agno Model Selection Guide](https://www.agno.com/blog/a-practical-guide-to-ai-model-selection-in-agno) - Pattern for per-agent models
- [ruamel.yaml PyPI](https://pypi.org/project/ruamel.yaml/) - Round-trip YAML editing
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) - Basic YAML handling

### Tertiary (LOW confidence)
- General circuit breaker patterns - Informed escalation design but not directly applicable

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries already in project
- Architecture: HIGH - Extends existing patterns (config.py, providers.py)
- Pitfalls: MEDIUM - Based on common patterns, may miss domain-specific issues
- Model IDs: HIGH - Verified against keycycle YAML configs

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (30 days - stable domain, models may update)
