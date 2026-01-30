---
phase: "05"
plan: "01"
subsystem: "core-config"
tags: ["pydantic", "yaml", "model-tiers", "config"]
dependency_graph:
  requires: ["01-provider-manager"]
  provides: ["TierConfig", "ModelTiersConfig", "TierName", "model_tiers-yaml-section"]
  affects: ["05-02", "05-03"]
tech_stack:
  added: []
  patterns: ["pydantic-config-models", "literal-type-alias", "model-validator"]
key_files:
  created:
    - hfs/core/model_tiers.py
    - tests/__init__.py
    - tests/unit/__init__.py
    - tests/unit/test_model_tiers.py
  modified:
    - hfs/config/default.yaml
decisions:
  - key: "tier-names-as-literal"
    choice: "TierName = Literal['reasoning', 'general', 'fast']"
    rationale: "Pydantic validates tier names at parse time"
  - key: "model-validator-for-required-tiers"
    choice: "model_validator ensures all 3 tiers defined"
    rationale: "Fail fast if config missing required tiers"
  - key: "escalation-state-string-keys"
    choice: "Dict[str, TierName] for escalation_state"
    rationale: "triad_id:role keys are strings, validated tier values"
metrics:
  duration: "2 min"
  completed: "2026-01-30"
---

# Phase 05 Plan 01: Model Tiers Config Schema Summary

**One-liner:** Pydantic models for 3-tier role-based model selection with provider-specific IDs and escalation state tracking

## What Was Built

### hfs/core/model_tiers.py

Created Pydantic models for model tier configuration:

- **TierName**: `Literal["reasoning", "general", "fast"]` type alias for validated tier names
- **TierConfig**: Model for single tier with `description` and `providers` mapping
- **ModelTiersConfig**: Root config with:
  - `tiers`: Dict mapping tier name to TierConfig
  - `role_defaults`: Dict mapping role name to default tier
  - `phase_overrides`: Dict mapping phase name to role override mappings
  - `escalation_state`: Dict mapping "triad_id:role" to escalated tier (system-managed)
  - Model validator ensures all 3 required tiers are defined

### hfs/config/default.yaml (extended)

Added `model_tiers` section with:

- **3 tiers** with 4 providers each (cerebras, groq, gemini, openrouter)
- **10 role defaults** covering hierarchical, dialectic, consensus triads
- **Phase override** for execution phase (workers use fast tier)
- **Empty escalation_state** ready for system-managed tier upgrades

### tests/unit/test_model_tiers.py

15 unit tests covering:

- TierConfig validation (required fields, empty providers)
- ModelTiersConfig validation (all 3 tiers required)
- role_defaults, phase_overrides, escalation_state functionality
- YAML loading from default.yaml with structure verification

## Key Code Patterns

```python
# Type-safe tier names with Literal
TierName = Literal["reasoning", "general", "fast"]

# Model validator for cross-field validation
@model_validator(mode='after')
def validate_all_tiers_defined(self) -> 'ModelTiersConfig':
    required_tiers: set[TierName] = {"reasoning", "general", "fast"}
    defined_tiers = set(self.tiers.keys())
    missing = required_tiers - defined_tiers
    if missing:
        raise ValueError(f"Missing required tiers: {missing}")
    return self
```

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tier name validation | Literal type alias | Pydantic validates at parse time |
| Required tiers check | model_validator | Fail fast if config incomplete |
| Escalation state keys | String dict keys | "triad_id:role" pattern for flexibility |

## Commit Log

| Hash | Type | Description |
|------|------|-------------|
| e2b7c1d | feat | Add model tier Pydantic config models |
| 6827295 | feat | Add model_tiers section to default.yaml |
| 2f79ac2 | test | Add unit tests for model_tiers module |

## Next Phase Readiness

**Blockers:** None

**Ready for 05-02:** ModelSelector class implementation
- TierConfig and ModelTiersConfig available for import
- YAML configuration structure established
- All provider-specific model IDs defined

## Test Results

```
15 passed in 0.12s
```
