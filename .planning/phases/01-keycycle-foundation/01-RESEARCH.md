# Phase 1: Keycycle Foundation - Research

**Researched:** 2026-01-29
**Domain:** API Key Rotation, Multi-Provider LLM Integration, Database Persistence
**Confidence:** HIGH

## Summary

This phase establishes the foundation for HFS to use real LLM APIs via Keycycle, an already-installed library that provides automatic key rotation and rate limiting management. The research focused on understanding the installed Keycycle library's API, its Agno model integration, TiDB usage persistence, and configuration patterns for the four required providers (Cerebras, Groq, Gemini, OpenRouter).

Keycycle provides two main wrapper classes: `MultiProviderWrapper` (single provider, Agno-focused) and `MultiClientWrapper` (multi-provider, generic client support). For this phase, `MultiProviderWrapper.from_env()` is the recommended approach since it directly returns rotating Agno models via `get_model()`, which is exactly what HFS needs.

The TiDB persistence is already built into Keycycle via `UsageDatabase` class that uses SQLAlchemy. The database connection is established automatically when `TIDB_DB_URL` environment variable is set. Rate limits for all four providers are pre-configured in YAML files within the keycycle package.

**Primary recommendation:** Use `MultiProviderWrapper.from_env()` for each provider, call `wrapper.get_model()` to get rotating Agno models, and ensure `TIDB_DB_URL` is set for automatic usage persistence.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| keycycle | installed | API key rotation, rate limiting, Agno model creation | Already in project, purpose-built for this |
| agno | installed | Multi-agent framework, model abstraction | Project's LLM execution backend |
| sqlalchemy | installed | Database ORM for TiDB persistence | Keycycle's internal dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pymysql | installed | MySQL driver for TiDB | Required by SQLAlchemy for TiDB connections |
| python-dotenv | installed | Environment variable loading | Loading API keys from .env file |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MultiProviderWrapper | MultiClientWrapper | MultiClientWrapper supports multiple providers in one instance but doesn't have native Agno model support |
| Per-provider wrapper | Single multi-provider wrapper | Per-provider is simpler for HFS since each model tier may use different providers |

**Installation:**
All dependencies already installed. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
hfs/
├── agno/                    # Agno integration layer (new)
│   ├── __init__.py
│   ├── providers.py         # Provider wrapper initialization
│   └── models.py            # Model factory and tier management
```

### Pattern 1: Provider Wrapper Factory
**What:** Create a factory function that initializes MultiProviderWrapper instances for each provider from environment variables
**When to use:** At HFS startup, before any triad operations
**Example:**
```python
# Source: Keycycle library (legacy_multi_provider_wrapper.py)
from keycycle import MultiProviderWrapper

def create_provider_wrappers() -> dict[str, MultiProviderWrapper]:
    """Initialize all provider wrappers from environment variables."""
    providers = {}

    # Cerebras (51 keys) - PER_MODEL strategy
    providers["cerebras"] = MultiProviderWrapper.from_env(
        provider="cerebras",
        default_model_id="llama-3.3-70b",
        # db_url automatically loaded from TIDB_DB_URL
    )

    # Groq (16 keys) - PER_MODEL strategy
    providers["groq"] = MultiProviderWrapper.from_env(
        provider="groq",
        default_model_id="llama-3.3-70b-versatile",
    )

    # Gemini (110 keys) - PER_MODEL strategy
    providers["gemini"] = MultiProviderWrapper.from_env(
        provider="gemini",
        default_model_id="gemini-2.5-flash",
    )

    # OpenRouter (31 keys) - GLOBAL strategy
    providers["openrouter"] = MultiProviderWrapper.from_env(
        provider="openrouter",
        default_model_id="meta-llama/llama-3.3-70b-instruct:free",
    )

    return providers
```

### Pattern 2: Rotating Model Acquisition
**What:** Get a rotating Agno model from the wrapper that handles key rotation automatically on 429 errors
**When to use:** When creating agents or running model invocations
**Example:**
```python
# Source: Keycycle library (legacy_multi_provider_wrapper.py)
# Get a rotating model - automatically rotates keys on rate limits
model = wrapper.get_model(
    estimated_tokens=1000,  # Help rate limiting estimates
    wait=True,              # Wait if no keys available
    timeout=10.0,           # Max wait time
    max_retries=5,          # Retry on 429 errors
)

# Use with Agno Agent
from agno.agent import Agent

agent = Agent(
    model=model,
    instructions="You are a helpful assistant.",
)
response = agent.run("Complete this task...")
```

### Pattern 3: Environment Variable Configuration
**What:** API keys must follow the numbered pattern for Keycycle to load them
**When to use:** Always - this is how Keycycle discovers keys
**Example:**
```bash
# .env file pattern (Source: Keycycle docs/KEYCYCLE.md)

# Provider: cerebras (51 keys)
NUM_CEREBRAS=51
CEREBRAS_API_KEY_1=csk-...
CEREBRAS_API_KEY_2=csk-...
# ... through CEREBRAS_API_KEY_51

# Provider: groq (16 keys)
NUM_GROQ=16
GROQ_API_KEY_1=gsk-...
GROQ_API_KEY_2=gsk-...
# ... through GROQ_API_KEY_16

# Provider: gemini (110 keys)
NUM_GEMINI=110
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...
# ... through GEMINI_API_KEY_110

# Provider: openrouter (31 keys)
NUM_OPENROUTER=31
OPENROUTER_API_KEY_1=sk-or-...
OPENROUTER_API_KEY_2=sk-or-...
# ... through OPENROUTER_API_KEY_31

# TiDB for usage persistence
TIDB_DB_URL=mysql+pymysql://user:pass@gateway.tidbcloud.com:4000/dbname?ssl_ca=/path/to/ca.pem
```

### Anti-Patterns to Avoid
- **Creating new wrapper instances per request:** Wrappers maintain state (usage tracking, hydration from DB). Create once at startup, reuse.
- **Ignoring NoAvailableKeyError:** When all keys are rate-limited, the system should back off or escalate, not crash.
- **Hardcoding model IDs:** Use configuration files for model selection to enable tier-based escalation later.
- **Not calling wrapper.stop():** The wrapper has background threads that should be stopped on shutdown.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key rotation | Custom rotation logic | Keycycle's RotatingKeyManager | Thread-safe, handles 429 detection, cooldown periods |
| Rate limit tracking | Request counters | Keycycle's UsageBucket | Tracks rpm/rph/rpd with sliding windows |
| Model creation with rotation | Custom Agno model wrapper | MultiProviderWrapper.get_model() | Creates proper mixin with RotatingCredentialsMixin |
| Usage persistence | Custom DB logging | Keycycle's UsageDatabase + AsyncUsageLogger | Async, batched, auto-hydration |
| Provider strategies | Per-provider limit logic | PROVIDER_STRATEGIES dict in keycycle | Pre-configured PER_MODEL vs GLOBAL strategies |

**Key insight:** Keycycle already implements sophisticated rate limiting with per-key, per-model tracking, exponential backoff, temporary vs hard rate limit differentiation, and TiDB persistence. Any custom solution would be less complete.

## Common Pitfalls

### Pitfall 1: TiDB Serverless Connection Timeouts
**What goes wrong:** TiDB Serverless clusters shut down after 5 minutes of no connections, causing "Lost connection" errors
**Why it happens:** Pooled connections become stale when the serverless cluster hibernates
**How to avoid:** Keycycle already sets `pool_recycle=300` in UsageDatabase. Ensure TIDB_DB_URL is using `mysql+pymysql://` driver which supports this.
**Warning signs:** Sporadic "OperationalError: Lost connection to MySQL server" in logs

### Pitfall 2: Missing Environment Variables
**What goes wrong:** Keycycle silently uses fewer keys than expected if NUM_PROVIDER doesn't match actual key count
**Why it happens:** The `load_api_keys()` function reads exactly NUM_PROVIDER keys
**How to avoid:** Validate environment at startup. Check that NUM_CEREBRAS=51, NUM_GROQ=16, NUM_GEMINI=110, NUM_OPENROUTER=31 match actual keys.
**Warning signs:** `Initialized N keys for provider X` log message shows wrong count

### Pitfall 3: OpenRouter GLOBAL vs PER_MODEL Strategy
**What goes wrong:** OpenRouter has shared rate limits across all models, but code assumes per-model limits
**Why it happens:** OpenRouter free tier has global limits, not per-model
**How to avoid:** Keycycle already handles this - OpenRouter uses RateLimitStrategy.GLOBAL automatically
**Warning signs:** Rate limits hit much faster than expected on OpenRouter

### Pitfall 4: Not Handling NoAvailableKeyError
**What goes wrong:** HFS pipeline crashes when all keys for a provider are rate-limited
**Why it happens:** Heavy usage exhausts all keys simultaneously
**How to avoid:** Catch NoAvailableKeyError and implement fallback (wait, use different provider, or fail gracefully)
**Warning signs:** Unhandled exception stack traces with NoAvailableKeyError

### Pitfall 5: Forgetting to Stop Wrapper on Shutdown
**What goes wrong:** Background threads keep running, usage logs not flushed to TiDB
**Why it happens:** Wrapper.stop() not called during application shutdown
**How to avoid:** Register wrapper.stop() with atexit or call explicitly in cleanup
**Warning signs:** Usage data missing from TiDB for recent requests

## Code Examples

Verified patterns from Keycycle source code:

### Complete Provider Setup
```python
# Source: keycycle/legacy_multi_provider_wrapper.py
from keycycle import MultiProviderWrapper, NoAvailableKeyError, RateLimitError
import atexit
import logging

logger = logging.getLogger(__name__)

class ProviderManager:
    """Manages all LLM provider wrappers for HFS."""

    def __init__(self):
        self.wrappers: dict[str, MultiProviderWrapper] = {}
        self._init_providers()
        atexit.register(self.shutdown)

    def _init_providers(self):
        """Initialize all provider wrappers from environment."""
        provider_configs = [
            ("cerebras", "llama-3.3-70b"),
            ("groq", "llama-3.3-70b-versatile"),
            ("gemini", "gemini-2.5-flash"),
            ("openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
        ]

        for provider, default_model in provider_configs:
            try:
                wrapper = MultiProviderWrapper.from_env(
                    provider=provider,
                    default_model_id=default_model,
                    # TIDB_DB_URL loaded automatically from env
                )
                self.wrappers[provider] = wrapper
                logger.info(f"Initialized {provider} with {len(wrapper.manager.keys)} keys")
            except Exception as e:
                logger.error(f"Failed to initialize {provider}: {e}")

    def get_model(self, provider: str, model_id: str = None, **kwargs):
        """Get a rotating Agno model for the specified provider."""
        if provider not in self.wrappers:
            raise ValueError(f"Unknown provider: {provider}")

        wrapper = self.wrappers[provider]
        return wrapper.get_model(
            estimated_tokens=kwargs.get("estimated_tokens", 1000),
            wait=kwargs.get("wait", True),
            timeout=kwargs.get("timeout", 10.0),
            max_retries=kwargs.get("max_retries", 5),
            id=model_id or wrapper.default_model_id,
        )

    def shutdown(self):
        """Stop all wrappers and flush usage logs."""
        for name, wrapper in self.wrappers.items():
            try:
                wrapper.manager.stop()
                logger.info(f"Stopped {name} wrapper")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
```

### Using Models with Agno Agents
```python
# Source: docs/AGNO.md + keycycle integration
from agno.agent import Agent

# Get rotating model from provider manager
provider_manager = ProviderManager()
model = provider_manager.get_model("cerebras", model_id="llama-3.3-70b")

# Create agent with rotating model
agent = Agent(
    model=model,
    instructions="You are a specialized worker agent for code generation.",
    add_history_to_context=True,
    markdown=True,
)

# Run agent - key rotation handled automatically
try:
    response = agent.run("Generate a Python function that...")
except NoAvailableKeyError:
    # Fallback: try different provider
    fallback_model = provider_manager.get_model("groq")
    agent.model = fallback_model
    response = agent.run("Generate a Python function that...")
```

### Error Handling Pattern
```python
# Source: keycycle/core/exceptions.py
from keycycle import (
    KeycycleError,
    NoAvailableKeyError,
    KeyNotFoundError,
    RateLimitError,
    InvalidKeyError,
    ConfigurationError,
)

def safe_model_call(provider_manager, provider: str, operation):
    """Execute operation with fallback handling."""
    try:
        model = provider_manager.get_model(provider)
        return operation(model)
    except NoAvailableKeyError as e:
        # All keys exhausted - try fallback provider
        logger.warning(f"All keys exhausted for {e.provider}/{e.model_id}")
        logger.info(f"Keys: {e.total_keys}, Cooling down: {e.cooling_down}")
        raise
    except RateLimitError as e:
        # Rate limit after all retries
        logger.error(f"Rate limit exceeded after {e.attempts} attempts")
        raise
    except InvalidKeyError as e:
        # Key is invalid (401/403)
        logger.error(f"Invalid key detected: ...{e.key_suffix}")
        raise
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual key rotation | Automatic rotation via Keycycle | Pre-existing | No manual 429 handling needed |
| Single API key | Multiple keys with load balancing | Pre-existing | Higher throughput, reliability |
| In-memory usage tracking | TiDB persistence with hydration | Pre-existing | Usage survives restarts |
| Synchronous logging | AsyncUsageLogger with batching | Pre-existing | No blocking on DB writes |

**Deprecated/outdated:**
- Direct Agno model instantiation: Use Keycycle wrapper for automatic rotation
- Manual rate limit tracking: Keycycle handles this automatically
- Single-provider setup: Multi-provider gives fallback options

## Open Questions

Things that couldn't be fully resolved:

1. **TiDB SSL Certificate Path**
   - What we know: TiDB Serverless requires SSL, cert path is OS-dependent
   - What's unclear: Where the .env file currently specifies the cert path
   - Recommendation: Check existing TIDB_DB_URL in .env, ensure ssl_ca parameter is set

2. **Provider Fallback Strategy**
   - What we know: Each provider has different key counts and rate limits
   - What's unclear: Should HFS automatically try a different provider when one is exhausted?
   - Recommendation: Implement simple fallback for Phase 1, sophisticated escalation in Phase 4

3. **Model ID Validation**
   - What we know: Keycycle has YAML configs with supported models
   - What's unclear: How to validate requested model IDs against supported models
   - Recommendation: Use model IDs from keycycle's YAML configs, add validation helper

## Sources

### Primary (HIGH confidence)
- Keycycle source code: `.venv/Lib/site-packages/keycycle/` - Direct examination of installed library
- `docs/KEYCYCLE.md` - Project's integration guide
- `docs/AGNO.md` - Project's Agno integration patterns

### Secondary (MEDIUM confidence)
- [TiDB SQLAlchemy Connection Guide](https://docs.pingcap.com/tidb/dev/dev-guide-sample-application-python-sqlalchemy/) - Connection pooling recommendations
- Keycycle YAML configs: `config/models/*.yaml` - Pre-configured rate limits

### Tertiary (LOW confidence)
- None - all findings verified against source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - examined installed source code directly
- Architecture: HIGH - patterns derived from actual library implementation
- Pitfalls: HIGH - documented based on code analysis and TiDB official docs

**Research date:** 2026-01-29
**Valid until:** 60 days (stable library, already installed)
