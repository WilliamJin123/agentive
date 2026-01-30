"""
Observability configuration for HFS.

Provides a centralized configuration model for observability settings,
supporting environment variable overrides and sensible defaults.

Configuration Levels:
    - console_verbosity "minimal": Only errors and warnings
    - console_verbosity "standard": Normal operation logs (default)
    - console_verbosity "verbose": Debug-level detail including prompts

Environment Variables:
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint
    HFS_OBSERVABILITY_CONSOLE_VERBOSITY: Console output level
    HFS_OBSERVABILITY_SERVICE_NAME: Service name override
"""

import os
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ObservabilityConfig:
    """Configuration for HFS observability infrastructure.

    Attributes:
        service_name: Service identifier for telemetry. Defaults to "hfs".
        console_enabled: Whether to enable console export. Defaults to True.
        console_verbosity: Console output detail level. One of "minimal",
            "standard", or "verbose". Defaults to "standard".
        otlp_endpoint: OTLP collector endpoint. If None, reads from
            OTEL_EXPORTER_OTLP_ENDPOINT environment variable.

    Example:
        >>> config = ObservabilityConfig(
        ...     service_name="hfs-production",
        ...     console_verbosity="minimal",
        ...     otlp_endpoint="http://localhost:4318"
        ... )
    """

    service_name: str = "hfs"
    console_enabled: bool = True
    console_verbosity: Literal["minimal", "standard", "verbose"] = "standard"
    otlp_endpoint: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.console_verbosity not in ("minimal", "standard", "verbose"):
            raise ValueError(
                f"console_verbosity must be 'minimal', 'standard', or 'verbose', "
                f"got '{self.console_verbosity}'"
            )

    def get_otlp_endpoint(self) -> Optional[str]:
        """Get OTLP endpoint from config or environment.

        Returns:
            OTLP endpoint URL if configured, None otherwise.
        """
        if self.otlp_endpoint is not None:
            return self.otlp_endpoint
        return os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    def is_otlp_enabled(self) -> bool:
        """Check if OTLP export is enabled.

        Returns:
            True if an OTLP endpoint is configured.
        """
        return self.get_otlp_endpoint() is not None


def get_config() -> ObservabilityConfig:
    """Load observability configuration from environment.

    Reads configuration from environment variables with sensible defaults:
        - HFS_OBSERVABILITY_SERVICE_NAME -> service_name (default: "hfs")
        - HFS_OBSERVABILITY_CONSOLE_VERBOSITY -> console_verbosity (default: "standard")
        - OTEL_EXPORTER_OTLP_ENDPOINT -> otlp_endpoint (default: None)

    Returns:
        ObservabilityConfig with values from environment or defaults.

    Example:
        >>> import os
        >>> os.environ["HFS_OBSERVABILITY_CONSOLE_VERBOSITY"] = "verbose"
        >>> config = get_config()
        >>> config.console_verbosity
        'verbose'
    """
    service_name = os.getenv("HFS_OBSERVABILITY_SERVICE_NAME", "hfs")
    console_verbosity = os.getenv("HFS_OBSERVABILITY_CONSOLE_VERBOSITY", "standard")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    # Validate and coerce console_verbosity
    if console_verbosity not in ("minimal", "standard", "verbose"):
        console_verbosity = "standard"

    return ObservabilityConfig(
        service_name=service_name,
        console_enabled=True,  # Always enabled by default
        console_verbosity=console_verbosity,  # type: ignore
        otlp_endpoint=otlp_endpoint,
    )


__all__ = [
    "ObservabilityConfig",
    "get_config",
]
