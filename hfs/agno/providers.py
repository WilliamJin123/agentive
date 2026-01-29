"""
Provider wrapper initialization for HFS Agno integration.

This module provides the ProviderManager class which initializes and manages
MultiProviderWrapper instances for all configured LLM providers (Cerebras, Groq,
Gemini, OpenRouter).
"""

import atexit
import logging
import os
from typing import Any

from keycycle import (
    MultiProviderWrapper,
    NoAvailableKeyError,
    RateLimitError,
    InvalidKeyError,
)

logger = logging.getLogger(__name__)

# Provider configurations: (provider_name, default_model_id)
PROVIDER_CONFIGS: list[tuple[str, str]] = [
    ("cerebras", "llama-3.3-70b"),
    ("groq", "llama-3.3-70b-versatile"),
    ("gemini", "gemini-2.5-flash"),
    ("openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
]


class ProviderManager:
    """
    Manages all LLM provider wrappers for HFS.

    Initializes MultiProviderWrapper instances for each configured provider
    from environment variables and provides a unified interface for obtaining
    rotating Agno models.

    Attributes:
        wrappers: Dictionary mapping provider names to their MultiProviderWrapper instances

    Example:
        >>> manager = ProviderManager()
        >>> model = manager.get_model("cerebras")
        >>> # Use model with Agno Agent
    """

    def __init__(self) -> None:
        """
        Initialize the ProviderManager.

        Validates environment variables, initializes all provider wrappers,
        and registers shutdown handler for clean cleanup.
        """
        self.wrappers: dict[str, MultiProviderWrapper] = {}
        self._env_status: dict[str, dict] = self._validate_environment()
        self._init_providers()
        atexit.register(self.shutdown)

    def _validate_environment(self) -> dict[str, dict]:
        """
        Validate environment variables and return status report.

        Checks for expected NUM_{PROVIDER} environment variables and
        TIDB_DB_URL for usage persistence.

        Returns:
            Dictionary mapping provider names to their environment status
        """
        expected = {
            "cerebras": {"env_var": "NUM_CEREBRAS", "expected": 51},
            "groq": {"env_var": "NUM_GROQ", "expected": 16},
            "gemini": {"env_var": "NUM_GEMINI", "expected": 110},
            "openrouter": {"env_var": "NUM_OPENROUTER", "expected": 31},
        }

        status: dict[str, dict] = {}
        for provider, info in expected.items():
            actual = os.environ.get(info["env_var"])
            if actual is None:
                logger.warning(f"Missing {info['env_var']} environment variable")
                status[provider] = {"configured": False, "keys": 0, "expected": info["expected"]}
            else:
                try:
                    count = int(actual)
                    if count != info["expected"]:
                        logger.warning(f"{info['env_var']}={count}, expected {info['expected']}")
                    status[provider] = {"configured": True, "keys": count, "expected": info["expected"]}
                except ValueError:
                    logger.error(f"{info['env_var']} is not a valid integer: {actual}")
                    status[provider] = {"configured": False, "keys": 0, "expected": info["expected"]}

        # Check TIDB_DB_URL
        if not os.environ.get("TIDB_DB_URL"):
            logger.warning("TIDB_DB_URL not set - usage statistics will not be persisted")

        return status

    def _init_providers(self) -> None:
        """
        Initialize all provider wrappers from environment.

        Iterates through PROVIDER_CONFIGS and creates MultiProviderWrapper
        instances for each. Continues on single provider failure (doesn't crash).
        """
        for provider, default_model in PROVIDER_CONFIGS:
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

        # Log summary after initialization
        healthy = [p for p, _ in PROVIDER_CONFIGS if self.is_provider_healthy(p)]
        logger.info(f"Provider initialization complete: {len(healthy)}/{len(PROVIDER_CONFIGS)} providers healthy")

    def get_model(
        self,
        provider: str,
        model_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Get a rotating Agno model for the specified provider.

        Args:
            provider: Provider name (cerebras, groq, gemini, openrouter)
            model_id: Optional model identifier (uses provider default if not specified)
            **kwargs: Additional arguments passed to wrapper.get_model()
                - estimated_tokens: Estimated token usage (default: 1000)
                - wait: Whether to wait for available key (default: True)
                - timeout: Max wait time in seconds (default: 10.0)
                - max_retries: Max retries on rate limit (default: 5)

        Returns:
            A rotating Agno model instance

        Raises:
            ValueError: If provider is not initialized
            NoAvailableKeyError: If no keys are available within timeout
        """
        if provider not in self.wrappers:
            raise ValueError(f"Unknown or uninitialized provider: {provider}")

        wrapper = self.wrappers[provider]

        # Set defaults, allow kwargs to override
        final_kwargs = {
            "estimated_tokens": kwargs.pop("estimated_tokens", 1000),
            "wait": kwargs.pop("wait", True),
            "timeout": kwargs.pop("timeout", 10.0),
            "max_retries": kwargs.pop("max_retries", 5),
        }

        # Pass model_id if provided
        if model_id is not None:
            final_kwargs["id"] = model_id

        # Merge any remaining kwargs
        final_kwargs.update(kwargs)

        return wrapper.get_model(**final_kwargs)

    def shutdown(self) -> None:
        """
        Stop all wrappers and flush usage logs.

        Called automatically via atexit registration.
        """
        for name, wrapper in self.wrappers.items():
            try:
                wrapper.manager.stop()
                logger.info(f"Stopped {name} wrapper")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")

    @property
    def available_providers(self) -> list[str]:
        """
        List providers that were successfully initialized.

        Returns:
            List of provider names with active wrappers
        """
        return list(self.wrappers.keys())

    @property
    def environment_status(self) -> dict[str, dict]:
        """
        Return environment validation status for all providers.

        Returns:
            Dictionary mapping provider names to their status info:
                - configured: Whether env var was found and valid
                - keys: Number of keys configured
                - expected: Expected number of keys
        """
        return self._env_status

    def is_provider_healthy(self, provider: str) -> bool:
        """
        Check if a provider is fully configured and initialized.

        Args:
            provider: Provider name to check

        Returns:
            True if provider is configured and has an active wrapper
        """
        return (
            provider in self._env_status
            and self._env_status[provider]["configured"]
            and provider in self.wrappers
        )
