"""
HFS Agno Integration Layer

This module provides the integration between HFS and Keycycle for
multi-provider LLM access with automatic key rotation and rate limiting.

Exports:
    ProviderManager: Manages all LLM provider wrappers
    get_model: Main entry point for obtaining rotating Agno models
    get_provider_manager: Get or create the global ProviderManager instance
    get_cerebras_model: Get a rotating Cerebras model
    get_groq_model: Get a rotating Groq model
    get_gemini_model: Get a rotating Gemini model
    get_openrouter_model: Get a rotating OpenRouter model
    list_available_providers: List providers that were successfully initialized
"""

from .providers import ProviderManager, PROVIDER_CONFIGS
from .models import (
    get_model,
    get_provider_manager,
    get_cerebras_model,
    get_groq_model,
    get_gemini_model,
    get_openrouter_model,
    list_available_providers,
)

__all__ = [
    # Core
    "ProviderManager",
    "PROVIDER_CONFIGS",
    # Model factory
    "get_model",
    "get_provider_manager",
    # Provider-specific helpers
    "get_cerebras_model",
    "get_groq_model",
    "get_gemini_model",
    "get_openrouter_model",
    # Utilities
    "list_available_providers",
]
