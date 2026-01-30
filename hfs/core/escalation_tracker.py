"""Escalation tracker for failure-adaptive model tier upgrades.

This module implements MODL-04 requirement - self-improving config evolution.
It tracks consecutive failures per triad:role combination and permanently
upgrades model tiers in the config file when the escalation threshold is reached.

Key behaviors:
- 3 consecutive failures triggers permanent tier upgrade
- Escalation persists to YAML config file using ruamel.yaml (preserves comments)
- No de-escalation - once upgraded, stays upgraded
- Success resets failure count (within same tier)
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

from ruamel.yaml import YAML

from hfs.core.model_tiers import ModelTiersConfig, TierName


logger = logging.getLogger(__name__)


class EscalationTracker:
    """Tracks failures and triggers permanent tier upgrades.

    This class implements failure-adaptive model escalation. When a triad:role
    combination fails consecutively beyond the threshold, it permanently upgrades
    to a higher tier in the config file.

    Attributes:
        ESCALATION_THRESHOLD: Number of consecutive failures before escalation (3)
        TIER_ORDER: Escalation path from lowest to highest capability
        config_path: Path to the YAML config file
        config: In-memory ModelTiersConfig instance
    """

    ESCALATION_THRESHOLD: int = 3  # Consecutive failures before escalation
    TIER_ORDER: list[TierName] = ["fast", "general", "reasoning"]  # Escalation path

    def __init__(self, config_path: Path, config: ModelTiersConfig) -> None:
        """Initialize the escalation tracker.

        Args:
            config_path: Path to the YAML config file for persistent updates
            config: In-memory ModelTiersConfig instance to update
        """
        self.config_path = config_path
        self.config = config
        self._failure_counts: Dict[str, int] = defaultdict(int)

    def record_failure(self, triad_id: str, role: str) -> Optional[TierName]:
        """Record a failure for a triad:role combination.

        Increments the failure count. If the threshold is reached, triggers
        escalation to the next tier and resets the failure count.

        Args:
            triad_id: The triad identifier
            role: The role within the triad (e.g., "orchestrator", "worker_a")

        Returns:
            The new tier name if escalation was triggered, None otherwise
        """
        key = f"{triad_id}:{role}"
        self._failure_counts[key] += 1
        logger.debug(
            f"Failure recorded for {key}: "
            f"{self._failure_counts[key]}/{self.ESCALATION_THRESHOLD}"
        )

        if self._failure_counts[key] >= self.ESCALATION_THRESHOLD:
            new_tier = self._escalate(key, role)
            self._failure_counts[key] = 0  # Reset after escalation
            return new_tier
        return None

    def record_success(self, triad_id: str, role: str) -> None:
        """Record a success for a triad:role combination.

        Resets the failure count to zero, as success breaks the consecutive
        failure chain.

        Args:
            triad_id: The triad identifier
            role: The role within the triad
        """
        key = f"{triad_id}:{role}"
        if self._failure_counts[key] > 0:
            logger.debug(f"Success recorded for {key}, resetting failure count")
            self._failure_counts[key] = 0

    def _escalate(self, key: str, role: str) -> Optional[TierName]:
        """Upgrade to the next tier and persist to config file.

        Args:
            key: The "triad_id:role" key
            role: The role name (for looking up default tier)

        Returns:
            The new tier name if escalation succeeded, None if already at max
        """
        # Get current tier (from escalation_state or role_defaults)
        current: TierName = self.config.escalation_state.get(
            key,
            self.config.role_defaults.get(role, "general")
        )

        try:
            current_idx = self.TIER_ORDER.index(current)
        except ValueError:
            logger.warning(
                f"Unknown tier '{current}' for {key}, treating as 'general'"
            )
            current_idx = self.TIER_ORDER.index("general")

        if current_idx >= len(self.TIER_ORDER) - 1:
            logger.warning(
                f"{key} already at highest tier ({current}), cannot escalate"
            )
            return None

        new_tier: TierName = self.TIER_ORDER[current_idx + 1]
        logger.info(f"Escalating {key}: {current} -> {new_tier}")

        # Update in-memory config
        self.config.escalation_state[key] = new_tier

        # Persist to file
        self._persist_escalation(key, new_tier)
        return new_tier

    def _persist_escalation(self, key: str, tier: TierName) -> None:
        """Update YAML config file with new escalation state.

        Uses ruamel.yaml for round-trip editing to preserve comments and
        formatting in the config file.

        Args:
            key: The "triad_id:role" key
            tier: The new tier to persist
        """
        yaml = YAML()
        yaml.preserve_quotes = True

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        # Navigate to escalation_state, creating path if needed
        if "config" not in data:
            data["config"] = {}
        if "model_tiers" not in data["config"]:
            data["config"]["model_tiers"] = {}
        if "escalation_state" not in data["config"]["model_tiers"]:
            data["config"]["model_tiers"]["escalation_state"] = {}

        data["config"]["model_tiers"]["escalation_state"][key] = tier

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        logger.debug(f"Persisted escalation state for {key} to {self.config_path}")

    def get_failure_count(self, triad_id: str, role: str) -> int:
        """Get the current failure count for a triad:role combination.

        Args:
            triad_id: The triad identifier
            role: The role within the triad

        Returns:
            The current consecutive failure count (0 if no failures)
        """
        return self._failure_counts.get(f"{triad_id}:{role}", 0)
