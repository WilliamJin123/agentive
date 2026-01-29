"""
Model factory for HFS Agno integration.

This module provides convenience functions for obtaining rotating Agno models
from the Keycycle-managed provider pool. The main entry point is `get_model()`,
with provider-specific helpers for common use cases.
"""

import logging
from typing import Any

from keycycle import NoAvailableKeyError

from .providers import ProviderManager

logger = logging.getLogger(__name__)

# Module-level singleton for ProviderManager
_provider_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """
    Get or create the global ProviderManager instance.

    Returns a singleton ProviderManager that initializes all providers
    from environment variables on first call.

    Returns:
        The global ProviderManager instance
    """
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def get_model(provider: str, model_id: str | None = None, **kwargs: Any) -> Any:
    """
    Get a rotating Agno model for the specified provider.

    This is the main entry point for obtaining rotating Agno models from
    Keycycle. The model will automatically rotate API keys on rate limit
    errors (429) and handle key exhaustion gracefully.

    Args:
        provider: Provider name (cerebras, groq, gemini, openrouter)
        model_id: Optional model identifier (uses provider default if not specified)
        **kwargs: Additional arguments passed to the underlying wrapper
            - estimated_tokens: Estimated token usage (default: 1000)
            - wait: Whether to wait for available key (default: True)
            - timeout: Max wait time in seconds (default: 10.0)
            - max_retries: Max retries on rate limit (default: 5)

    Returns:
        A rotating Agno model instance that can be used with Agno Agents

    Raises:
        ValueError: If provider is not initialized
        NoAvailableKeyError: If no keys are available within timeout

    Example:
        >>> model = get_model("cerebras")
        >>> agent = Agent(model=model, instructions="You are helpful.")
        >>> response = agent.run("Hello!")
    """
    manager = get_provider_manager()
    return manager.get_model(provider, model_id, **kwargs)


def get_any_model(estimated_tokens: int = 1000, **kwargs: Any) -> tuple[str, Any]:
    """
    Get a model from any available provider.

    Tries providers in order until one succeeds. Useful for fallback patterns
    when you don't care which provider handles a request.

    Args:
        estimated_tokens: Estimated token usage for the request
        **kwargs: Additional arguments passed to get_model()

    Returns:
        Tuple of (provider_name, model)

    Raises:
        NoAvailableKeyError: If all providers are exhausted

    Example:
        >>> provider, model = get_any_model()
        >>> agent = Agent(model=model, instructions="You are helpful.")
        >>> response = agent.run("Hello!")
        >>> print(f"Handled by: {provider}")
    """
    manager = get_provider_manager()
    return manager.get_any_model(estimated_tokens=estimated_tokens, **kwargs)


def get_cerebras_model(model_id: str = "llama-3.3-70b", **kwargs: Any) -> Any:
    """
    Get a rotating Cerebras model.

    Args:
        model_id: Model identifier (default: llama-3.3-70b)
        **kwargs: Additional arguments passed to get_model()

    Returns:
        A rotating Cerebras Agno model
    """
    return get_model("cerebras", model_id, **kwargs)


def get_groq_model(model_id: str = "llama-3.3-70b-versatile", **kwargs: Any) -> Any:
    """
    Get a rotating Groq model.

    Args:
        model_id: Model identifier (default: llama-3.3-70b-versatile)
        **kwargs: Additional arguments passed to get_model()

    Returns:
        A rotating Groq Agno model
    """
    return get_model("groq", model_id, **kwargs)


def get_gemini_model(model_id: str = "gemini-2.5-flash", **kwargs: Any) -> Any:
    """
    Get a rotating Gemini model.

    Args:
        model_id: Model identifier (default: gemini-2.5-flash)
        **kwargs: Additional arguments passed to get_model()

    Returns:
        A rotating Gemini Agno model
    """
    return get_model("gemini", model_id, **kwargs)


def get_openrouter_model(
    model_id: str = "meta-llama/llama-3.3-70b-instruct:free", **kwargs: Any
) -> Any:
    """
    Get a rotating OpenRouter model.

    Args:
        model_id: Model identifier (default: meta-llama/llama-3.3-70b-instruct:free)
        **kwargs: Additional arguments passed to get_model()

    Returns:
        A rotating OpenRouter Agno model
    """
    return get_model("openrouter", model_id, **kwargs)


def list_available_providers() -> list[str]:
    """
    List providers that were successfully initialized.

    Returns:
        List of provider names with active wrappers
    """
    return get_provider_manager().available_providers
