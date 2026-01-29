# Keycycle Integration Guide

Keycycle is a thread-safe API key rotation and rate limiting manager that automatically rotates between multiple API keys when rate limits are hit.

## Features

- **Automatic Key Rotation**: Rotates between multiple API keys on 429 errors
- **Rate Limiting Management**: Tracks per-model and global rate limits
- **Smart Error Handling**: Differentiates temporary rate limits (retry) from hard quota limits (rotate)
- **Multi-Provider Support**: OpenAI, Anthropic, Groq, Gemini, Cohere, and more
- **Usage Tracking**: Optional database persistence for usage statistics

## Environment Variables

Set up your API keys using numbered environment variables:

```bash
# OpenAI keys
NUM_OPENAI=2
OPENAI_API_KEY_1=sk-...
OPENAI_API_KEY_2=sk-...

# Anthropic keys
NUM_ANTHROPIC=2
ANTHROPIC_API_KEY_1=sk-ant-...
ANTHROPIC_API_KEY_2=sk-ant-...

# Optional: Database URL for usage persistence
TIDB_DB_URL=mysql://user:pass@host:3306/db
```

For providers with extra parameters (like TwelveLabs with index IDs):

```bash
NUM_TWELVELABS=2
TWELVELABS_API_KEY_1=sk-...
TWELVELABS_API_KEY_2=sk-...
TWELVELABS_INDEX_ID_1=idx_abc123
TWELVELABS_INDEX_ID_2=idx_xyz789
```

## OpenAI Client Integration

### Basic Setup

```python
from keycycle import MultiClientWrapper, ProviderEnvConfig
from openai import OpenAI, AsyncOpenAI

# Create wrapper with environment-based configuration
wrapper = MultiClientWrapper.from_env({
    "openai": ProviderEnvConfig(
        default_model="gpt-4",
    )
})

# Get a rotating OpenAI client
client = wrapper.get_rotating_client("openai", OpenAI)

# Use it like normal - keys rotate automatically on rate limits
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Async Client

```python
from openai import AsyncOpenAI

async_client = wrapper.get_rotating_client("openai", AsyncOpenAI)

response = await async_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Using MultiProviderWrapper for OpenAI Clients

`MultiProviderWrapper` provides dedicated methods for OpenAI-compatible clients:

```python
from keycycle import MultiProviderWrapper

wrapper = MultiProviderWrapper.from_env(
    provider="openai",
    default_model_id="gpt-4",
)

# Sync OpenAI client with rotation
client = wrapper.get_openai_client(
    estimated_tokens=1000,
    max_retries=5,
)

# Async OpenAI client with rotation
async_client = wrapper.get_async_openai_client(
    estimated_tokens=1000,
    max_retries=5,
)

# Generic rotating client for any provider
from anthropic import Anthropic
anthropic_wrapper = MultiProviderWrapper.from_env(
    provider="anthropic",
    default_model_id="claude-3-sonnet-20240229",
)
anthropic_client = anthropic_wrapper.get_rotating_client(Anthropic)
```

## Agno Integration

Keycycle provides `MultiProviderWrapper.get_model()` which returns a rotating Agno model with automatic key rotation.

### Creating a Rotating Agno Model

```python
from keycycle import MultiProviderWrapper

# Initialize wrapper from environment variables
wrapper = MultiProviderWrapper.from_env(
    provider="openai",
    default_model_id="gpt-4",
)

# Get a rotating Agno model - handles key rotation automatically
model = wrapper.get_model()

# With custom parameters
model = wrapper.get_model(
    estimated_tokens=1000,  # Token estimate for rate limiting
    wait=True,              # Wait for available capacity
    timeout=10.0,           # Timeout for waiting
    max_retries=5,          # Retries on rate limit errors
)
```

### Using a Specific Key

```python
# Pin to a specific key by index (0-based)
model = wrapper.get_model(key_id=0, pin_key=True)

# Pin to a specific key by suffix
model = wrapper.get_model(key_id="abc123", pin_key=True)
```

### Using the Rotating Model

```python
# Synchronous invocation
response = model.invoke("What is AI?")

# Async invocation
response = await model.ainvoke("What is AI?")

# Streaming (sync)
for chunk in model.invoke_stream("What is AI?"):
    print(chunk, end="")

# Streaming (async)
async for chunk in model.ainvoke_stream("What is AI?"):
    print(chunk, end="")
```

### With Agno Agents

```python
from agno.agent import Agent

agent = Agent(
    model=model,  # Pass the rotating model
    instructions="You are a helpful assistant.",
)

response = agent.run("Tell me about Python")
```

## Configuration Options

### ProviderEnvConfig

```python
ProviderEnvConfig(
    default_model="gpt-4",              # Default model to use
    strategy=RateLimitStrategy.PER_MODEL,  # Rate limit strategy
)
```

### Rate Limit Strategies

```python
from keycycle.config.enums import RateLimitStrategy

RateLimitStrategy.PER_MODEL  # Track limits separately per model (default)
RateLimitStrategy.GLOBAL     # Shared pool across all models (OpenRouter)
```

### Custom Rate Limits

```python
from keycycle import RateLimits

limits = RateLimits(
    requests_per_minute=10,
    requests_per_hour=100,
    requests_per_day=1000,
    tokens_per_minute=100000,
    tokens_per_hour=1000000,
    tokens_per_day=10000000,
)
```

## Usage Tracking

### Get Statistics

```python
# For MultiClientWrapper
manager = wrapper.get_manager("openai")

# For MultiProviderWrapper
manager = wrapper.manager

# Global stats across all keys
stats = manager.get_global_stats()
print(f"Total tokens: {stats.total.total_tokens}")
print(f"Requests this minute: {stats.total.rpm}")

# Stats for a specific key (by index or suffix)
key_stats = manager.get_key_stats(0)  # By index
key_stats = manager.get_key_stats("abc123")  # By key suffix

# Stats aggregated by model
model_stats = manager.get_model_stats("gpt-4")

# Granular stats: specific key + specific model
granular = manager.get_granular_stats(0, "gpt-4")
```

### Database Persistence

Enable database persistence for usage tracking:

```python
wrapper = MultiClientWrapper.from_env(
    providers={"openai": ProviderEnvConfig(default_model="gpt-4")},
    db_url="mysql://user:pass@host:3306/db",
)
```

## Error Handling

Keycycle provides specific exceptions:

```python
from keycycle import (
    KeycycleError,           # Base exception
    NoAvailableKeyError,     # No keys available
    KeyNotFoundError,        # Specific key not found
    RateLimitError,          # Rate limit exhausted after retries
    InvalidKeyError,         # Invalid API key (401/403)
    ConfigurationError,      # Configuration issues
)

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )
except NoAvailableKeyError:
    print("All keys are rate-limited, try again later")
except RateLimitError:
    print("Rate limit exhausted after all retries")
```

## Multi-Provider Setup

```python
from keycycle import MultiClientWrapper, ProviderEnvConfig
from openai import OpenAI
from anthropic import Anthropic

wrapper = MultiClientWrapper.from_env({
    "openai": ProviderEnvConfig(default_model="gpt-4"),
    "anthropic": ProviderEnvConfig(default_model="claude-3-sonnet-20240229"),
})

openai_client = wrapper.get_rotating_client("openai", OpenAI)
anthropic_client = wrapper.get_rotating_client("anthropic", Anthropic)
```

## Cleanup

Always stop the wrapper when done to clean up background threads:

```python
wrapper.stop()
```

Or use a context manager pattern in your application lifecycle.

## Pre-configured Providers

Keycycle includes pre-built rate limits for:

- **Cerebras** - PER_MODEL strategy
- **Groq** - PER_MODEL strategy
- **Gemini** - PER_MODEL strategy
- **OpenRouter** - GLOBAL strategy
- **Cohere** - PER_MODEL strategy with tier support
