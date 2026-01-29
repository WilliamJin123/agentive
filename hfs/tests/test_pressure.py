"""Tests for pressure mechanics."""

import pytest
from hfs.core.pressure import (
    ResourceBudget,
    PressureConfig,
    PressureSystem,
    ValidationResult,
    CoverageReport,
)
from hfs.core.spec import Spec, Section, SectionStatus


class TestResourceBudget:
    """Tests for ResourceBudget dataclass."""

    def test_default_values(self):
        budget = ResourceBudget()
        assert budget.tokens == 0
        assert budget.time_ms == 0
        assert budget.tool_calls == 0

    def test_add_usage(self):
        budget = ResourceBudget(tokens=100, time_ms=50, tool_calls=5)
        budget.add(tokens=50, time_ms=25, tool_calls=3)
        assert budget.tokens == 150
        assert budget.time_ms == 75
        assert budget.tool_calls == 8

    def test_exceeds_limit(self):
        usage = ResourceBudget(tokens=1500, time_ms=100, tool_calls=10)
        limit = ResourceBudget(tokens=1000, time_ms=200, tool_calls=20)
        assert usage.exceeds(limit) is True

        usage2 = ResourceBudget(tokens=500, time_ms=100, tool_calls=10)
        assert usage2.exceeds(limit) is False

    def test_remaining(self):
        usage = ResourceBudget(tokens=300, time_ms=50, tool_calls=5)
        limit = ResourceBudget(tokens=1000, time_ms=100, tool_calls=10)
        remaining = usage.remaining(limit)
        assert remaining.tokens == 700
        assert remaining.time_ms == 50
        assert remaining.tool_calls == 5

    def test_remaining_clamps_to_zero(self):
        usage = ResourceBudget(tokens=1500, time_ms=150, tool_calls=15)
        limit = ResourceBudget(tokens=1000, time_ms=100, tool_calls=10)
        remaining = usage.remaining(limit)
        assert remaining.tokens == 0
        assert remaining.time_ms == 0
        assert remaining.tool_calls == 0

    def test_to_dict(self):
        budget = ResourceBudget(tokens=100, time_ms=50, tool_calls=5)
        d = budget.to_dict()
        assert d == {"tokens": 100, "time_ms": 50, "tool_calls": 5}


class TestPressureConfig:
    """Tests for PressureConfig dataclass."""

    def test_default_values(self):
        config = PressureConfig()
        assert config.initial_temperature == 1.0
        assert config.temperature_decay == 0.15
        assert config.freeze_threshold == 0.1
        assert config.max_negotiation_rounds == 10
        assert config.escalation_threshold == 2
        assert config.enforcement == "hard"

    def test_from_dict(self):
        data = {
            "initial_temperature": 0.8,
            "temperature_decay": 0.2,
            "freeze_threshold": 0.05,
            "max_negotiation_rounds": 5,
            "escalation_threshold": 3,
            "global_budget": {"tokens": 50000, "time_ms": 30000, "tool_calls": 200},
            "per_triad_max": {"tokens": 10000, "time_ms": 5000, "tool_calls": 25},
            "validation": ["must_compile", "must_render"],
            "enforcement": "soft",
        }
        config = PressureConfig.from_dict(data)
        assert config.initial_temperature == 0.8
        assert config.temperature_decay == 0.2
        assert config.freeze_threshold == 0.05
        assert config.max_negotiation_rounds == 5
        assert config.escalation_threshold == 3
        assert config.global_budget.tokens == 50000
        assert config.per_triad_max.tokens == 10000
        assert config.validation_checks == ["must_compile", "must_render"]
        assert config.enforcement == "soft"

    def test_from_dict_with_defaults(self):
        config = PressureConfig.from_dict({})
        assert config.initial_temperature == 1.0
        assert config.temperature_decay == 0.15


class TestPressureSystem:
    """Tests for PressureSystem class."""

    def test_calculate_temperature(self):
        config = PressureConfig(initial_temperature=1.0, temperature_decay=0.15)
        system = PressureSystem(config)

        assert system.calculate_temperature(0) == 1.0
        assert system.calculate_temperature(1) == pytest.approx(0.85)
        assert system.calculate_temperature(2) == pytest.approx(0.70)
        assert system.calculate_temperature(6) == pytest.approx(0.10)
        assert system.calculate_temperature(7) == pytest.approx(0.0)  # Clamped to 0
        assert system.calculate_temperature(10) == 0.0

    def test_should_freeze(self):
        config = PressureConfig(
            initial_temperature=1.0,
            temperature_decay=0.15,
            freeze_threshold=0.1,
            max_negotiation_rounds=10,
        )
        system = PressureSystem(config)

        assert system.should_freeze(0) is False
        assert system.should_freeze(5) is False
        assert system.should_freeze(6) is True  # temp = 0.1, at threshold
        assert system.should_freeze(10) is True  # max rounds reached

    def test_track_and_get_usage(self):
        system = PressureSystem()
        system.track_usage("triad_1", tokens=100, time_ms=50, tool_calls=2)
        system.track_usage("triad_1", tokens=50, time_ms=25, tool_calls=1)

        usage = system.get_triad_usage("triad_1")
        assert usage.tokens == 150
        assert usage.time_ms == 75
        assert usage.tool_calls == 3

    def test_get_usage_unknown_triad(self):
        system = PressureSystem()
        usage = system.get_triad_usage("unknown")
        assert usage.tokens == 0
        assert usage.time_ms == 0
        assert usage.tool_calls == 0

    def test_is_budget_exceeded(self):
        config = PressureConfig(
            per_triad_max=ResourceBudget(tokens=1000, time_ms=100, tool_calls=10)
        )
        system = PressureSystem(config)

        system.track_usage("triad_1", tokens=500, time_ms=50, tool_calls=5)
        assert system.is_budget_exceeded("triad_1") is False

        system.track_usage("triad_1", tokens=600, time_ms=0, tool_calls=0)
        assert system.is_budget_exceeded("triad_1") is True

    def test_get_global_usage(self):
        system = PressureSystem()
        system.track_usage("triad_1", tokens=100, time_ms=50, tool_calls=2)
        system.track_usage("triad_2", tokens=200, time_ms=100, tool_calls=3)
        system.track_usage("triad_3", tokens=150, time_ms=75, tool_calls=5)

        global_usage = system.get_global_usage()
        assert global_usage.tokens == 450
        assert global_usage.time_ms == 225
        assert global_usage.tool_calls == 10

    def test_is_global_budget_exceeded(self):
        config = PressureConfig(
            global_budget=ResourceBudget(tokens=500, time_ms=200, tool_calls=20)
        )
        system = PressureSystem(config)

        system.track_usage("triad_1", tokens=200, time_ms=50, tool_calls=5)
        assert system.is_global_budget_exceeded() is False

        system.track_usage("triad_2", tokens=400, time_ms=50, tool_calls=5)
        assert system.is_global_budget_exceeded() is True

    def test_get_remaining_budget(self):
        config = PressureConfig(
            per_triad_max=ResourceBudget(tokens=1000, time_ms=100, tool_calls=10)
        )
        system = PressureSystem(config)
        system.track_usage("triad_1", tokens=300, time_ms=40, tool_calls=3)

        remaining = system.get_remaining_budget("triad_1")
        assert remaining.tokens == 700
        assert remaining.time_ms == 60
        assert remaining.tool_calls == 7

    def test_check_coverage_all_owned(self):
        system = PressureSystem()
        spec = Spec()
        spec.sections["layout"] = Section(status=SectionStatus.CLAIMED, owner="triad_1")
        spec.sections["visual"] = Section(status=SectionStatus.FROZEN, owner="triad_2")

        report = system.check_coverage(spec)
        assert report.total_sections == 2
        assert report.owned_sections == ["layout", "visual"]
        assert report.unclaimed_sections == []
        assert report.contested_sections == []
        assert report.coverage_complete is True

    def test_check_coverage_with_gaps(self):
        system = PressureSystem()
        spec = Spec()
        spec.sections["layout"] = Section(status=SectionStatus.CLAIMED, owner="triad_1")
        spec.sections["visual"] = Section(status=SectionStatus.UNCLAIMED)
        spec.sections["motion"] = Section(status=SectionStatus.CONTESTED, claims=["t1", "t2"])

        report = system.check_coverage(spec)
        assert report.total_sections == 3
        assert report.owned_sections == ["layout"]
        assert report.unclaimed_sections == ["visual"]
        assert report.contested_sections == ["motion"]
        assert report.coverage_complete is False

    def test_validate_quality_with_configured_checks(self):
        config = PressureConfig(validation_checks=["must_compile", "must_render"])
        system = PressureSystem(config)

        results = system.validate_quality({})
        assert len(results) == 2
        assert all(r.passed for r in results)
        assert results[0].check == "must_compile"
        assert results[1].check == "must_render"

    def test_validate_quality_with_unknown_check(self):
        config = PressureConfig(validation_checks=["unknown_check"])
        system = PressureSystem(config)

        results = system.validate_quality({})
        assert len(results) == 1
        assert results[0].passed is True
        assert "Unknown validation check" in results[0].message

    def test_register_custom_validator(self):
        system = PressureSystem()

        def custom_validator(artifact):
            return ValidationResult(
                check="custom_check",
                passed=artifact.get("valid", False),
                message="Custom validation",
            )

        system.register_validation_hook("custom_check", custom_validator)
        system.config.validation_checks = ["custom_check"]

        # Test failing validation
        results = system.validate_quality({"valid": False})
        assert results[0].passed is False

        # Test passing validation
        results = system.validate_quality({"valid": True})
        assert results[0].passed is True

    def test_reset_usage(self):
        system = PressureSystem()
        system.track_usage("triad_1", tokens=100)
        system.track_usage("triad_2", tokens=200)

        # Reset single triad
        system.reset_usage("triad_1")
        assert system.get_triad_usage("triad_1").tokens == 0
        assert system.get_triad_usage("triad_2").tokens == 200

        # Reset all
        system.reset_usage()
        assert system.get_triad_usage("triad_2").tokens == 0

    def test_get_usage_report(self):
        config = PressureConfig(
            global_budget=ResourceBudget(tokens=1000, time_ms=500, tool_calls=50),
            per_triad_max=ResourceBudget(tokens=500, time_ms=200, tool_calls=25),
        )
        system = PressureSystem(config)
        system.track_usage("triad_1", tokens=100, time_ms=50, tool_calls=5)
        system.track_usage("triad_2", tokens=200, time_ms=100, tool_calls=10)

        report = system.get_usage_report()

        assert report["global"]["used"]["tokens"] == 300
        assert report["global"]["remaining"]["tokens"] == 700
        assert report["global"]["exceeded"] is False

        assert report["per_triad"]["triad_1"]["used"]["tokens"] == 100
        assert report["per_triad"]["triad_1"]["exceeded"] is False
        assert report["per_triad"]["triad_2"]["used"]["tokens"] == 200


class TestCoverageReport:
    """Tests for CoverageReport dataclass."""

    def test_coverage_complete_when_all_owned(self):
        report = CoverageReport(
            total_sections=3,
            owned_sections=["a", "b", "c"],
            unclaimed_sections=[],
            contested_sections=[],
        )
        assert report.coverage_complete is True

    def test_coverage_incomplete_with_unclaimed(self):
        report = CoverageReport(
            total_sections=3,
            owned_sections=["a", "b"],
            unclaimed_sections=["c"],
            contested_sections=[],
        )
        assert report.coverage_complete is False

    def test_coverage_incomplete_with_contested(self):
        report = CoverageReport(
            total_sections=3,
            owned_sections=["a", "b"],
            unclaimed_sections=[],
            contested_sections=["c"],
        )
        assert report.coverage_complete is False
