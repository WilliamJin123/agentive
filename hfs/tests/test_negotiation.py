"""Tests for the NegotiationEngine module."""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from hfs.core.spec import Spec, Section, SectionStatus
from hfs.core.triad import Triad, TriadConfig, TriadPreset, TriadOutput
from hfs.core.arbiter import Arbiter, ArbiterDecision, ArbiterConfig
from hfs.core.negotiation import (
    NegotiationEngine,
    NegotiationResult,
    NegotiationRoundResult,
)


class MockTriad(Triad):
    """Mock triad for testing negotiation."""

    def __init__(self, triad_id: str, negotiate_response: str = "hold"):
        config = TriadConfig(
            id=triad_id,
            preset=TriadPreset.HIERARCHICAL,
            scope_primary=["test"],
            scope_reach=[],
            budget_tokens=1000,
            budget_tool_calls=10,
            budget_time_ms=1000,
            objectives=["test"],
        )
        self.config = config
        self.llm = None
        self.agents = {}
        self._negotiate_response = negotiate_response
        self.pending_revised_proposal: Dict[str, Any] = {}

    def _initialize_agents(self) -> Dict[str, Any]:
        return {}

    async def deliberate(self, user_request: str, spec_state: Dict[str, Any]) -> TriadOutput:
        return TriadOutput(position="test", claims=[], proposals={})

    async def negotiate(self, section: str, other_proposals: Dict[str, Any]) -> str:
        return self._negotiate_response

    async def execute(self, frozen_spec: Dict[str, Any]) -> Dict[str, str]:
        return {}

    def set_negotiate_response(self, response: str):
        """Set the response for negotiate calls."""
        self._negotiate_response = response


class MockArbiter:
    """Mock arbiter for testing escalation."""

    def __init__(self, decision_type: str = "assign", winner: str = "triad_1"):
        self.decision_type = decision_type
        self.winner = winner
        self.division = {}
        self.merged_proposal = None
        self.resolve_called = False
        self.resolve_args = None

    async def resolve(
        self,
        section_name: str,
        claimants: list,
        proposals: dict,
        triads: dict,
        spec_state: Spec,
    ) -> ArbiterDecision:
        self.resolve_called = True
        self.resolve_args = {
            "section_name": section_name,
            "claimants": claimants,
            "proposals": proposals,
        }

        if self.decision_type == "assign":
            return ArbiterDecision(
                type="assign",
                winner=self.winner,
                rationale="Test decision",
            )
        elif self.decision_type == "split":
            return ArbiterDecision(
                type="split",
                division=self.division,
                rationale="Test split decision",
            )
        elif self.decision_type == "merge":
            return ArbiterDecision(
                type="merge",
                merged_proposal=self.merged_proposal,
                assigned_to=self.winner,
                rationale="Test merge decision",
            )
        else:
            raise ValueError(f"Unknown decision type: {self.decision_type}")


class TestNegotiationRoundResult:
    """Tests for NegotiationRoundResult dataclass."""

    def test_default_values(self):
        """Verify default initialization."""
        result = NegotiationRoundResult(section_name="test")
        assert result.section_name == "test"
        assert result.responses == {}
        assert result.resolved is False
        assert result.escalated is False
        assert result.winner is None


class TestNegotiationResult:
    """Tests for NegotiationResult dataclass."""

    def test_default_values(self):
        """Verify default initialization."""
        result = NegotiationResult()
        assert result.total_rounds == 0
        assert result.sections_resolved == []
        assert result.sections_escalated == []
        assert result.final_temperature == 0.0
        assert result.round_history == []


class TestNegotiationEngineInit:
    """Tests for NegotiationEngine initialization."""

    def test_initialization_with_defaults(self):
        """Verify default configuration values."""
        spec = Spec()
        triads = {}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})

        assert engine.temperature_decay == 0.15
        assert engine.max_rounds == 10
        assert engine.escalation_threshold == 2
        assert engine.stuck_counters == {}

    def test_initialization_with_custom_config(self):
        """Verify custom configuration values are used."""
        spec = Spec()
        triads = {}
        arbiter = MockArbiter()
        config = {
            "temperature_decay": 0.2,
            "max_negotiation_rounds": 5,
            "escalation_threshold": 3,
        }

        engine = NegotiationEngine(triads, spec, arbiter, config)

        assert engine.temperature_decay == 0.2
        assert engine.max_rounds == 5
        assert engine.escalation_threshold == 3


class TestNegotiationEngineRun:
    """Tests for NegotiationEngine.run() method."""

    @pytest.mark.asyncio
    async def test_run_no_contested_sections(self):
        """Verify run completes immediately when no contested sections."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        triads = {"triad_1": MockTriad("triad_1")}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        result_spec = await engine.run()

        assert result_spec.is_frozen()
        assert result_spec.round == 0  # No rounds needed

    @pytest.mark.asyncio
    async def test_run_with_concession(self):
        """Verify run resolves contested section through concession."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        result_spec = await engine.run()

        assert result_spec.is_frozen()
        assert result_spec.sections["layout"].owner == "triad_1"
        assert "layout" in engine.get_result().sections_resolved

    @pytest.mark.asyncio
    async def test_run_max_rounds_reached(self):
        """Verify run stops at max rounds."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        # Both triads always hold - will never resolve naturally
        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}

        # Arbiter will assign to triad_1 when escalated
        arbiter = MockArbiter(decision_type="assign", winner="triad_1")

        config = {"max_negotiation_rounds": 3, "escalation_threshold": 2}
        engine = NegotiationEngine(triads, spec, arbiter, config)
        result_spec = await engine.run()

        assert result_spec.is_frozen()
        # Should have escalated within max rounds
        assert arbiter.resolve_called

    @pytest.mark.asyncio
    async def test_run_temperature_decay(self):
        """Verify temperature decays each round."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter(decision_type="assign", winner="triad_1")

        config = {"temperature_decay": 0.3, "escalation_threshold": 10}
        engine = NegotiationEngine(triads, spec, arbiter, config)
        result_spec = await engine.run()

        # Should have decayed
        assert result_spec.temperature == 0.0


class TestNegotiationEngineEscalation:
    """Tests for escalation to arbiter."""

    @pytest.mark.asyncio
    async def test_escalation_after_threshold(self):
        """Verify escalation happens after stuck threshold."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter(decision_type="assign", winner="triad_1")

        config = {"escalation_threshold": 2}
        engine = NegotiationEngine(triads, spec, arbiter, config)
        await engine.run()

        assert arbiter.resolve_called
        assert arbiter.resolve_args["section_name"] == "layout"
        assert "layout" in engine.get_result().sections_escalated

    @pytest.mark.asyncio
    async def test_arbiter_assign_decision(self):
        """Verify arbiter assign decision is applied correctly."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter(decision_type="assign", winner="triad_2")

        config = {"escalation_threshold": 1}
        engine = NegotiationEngine(triads, spec, arbiter, config)
        result_spec = await engine.run()

        assert result_spec.sections["layout"].owner == "triad_2"

    @pytest.mark.asyncio
    async def test_arbiter_split_decision(self):
        """Verify arbiter split decision creates sub-sections."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"spacing": "8px"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}

        arbiter = MockArbiter(decision_type="split")
        arbiter.division = {
            "layout/grid": "triad_1",
            "layout/spacing": "triad_2",
        }

        config = {"escalation_threshold": 1}
        engine = NegotiationEngine(triads, spec, arbiter, config)
        result_spec = await engine.run()

        # Original section should be removed
        assert "layout" not in result_spec.sections
        # Sub-sections should exist
        assert "layout/grid" in result_spec.sections
        assert "layout/spacing" in result_spec.sections
        assert result_spec.sections["layout/grid"].owner == "triad_1"
        assert result_spec.sections["layout/spacing"].owner == "triad_2"

    @pytest.mark.asyncio
    async def test_arbiter_merge_decision(self):
        """Verify arbiter merge decision combines proposals."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"spacing": "8px"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}

        arbiter = MockArbiter(decision_type="merge", winner="triad_1")
        arbiter.merged_proposal = {"grid": "12-col", "spacing": "8px"}

        config = {"escalation_threshold": 1}
        engine = NegotiationEngine(triads, spec, arbiter, config)
        result_spec = await engine.run()

        assert result_spec.sections["layout"].owner == "triad_1"
        assert result_spec.sections["layout"].proposals["triad_1"] == {
            "grid": "12-col",
            "spacing": "8px",
        }


class TestNegotiationEngineResponses:
    """Tests for handling different negotiation responses."""

    @pytest.mark.asyncio
    async def test_concede_removes_claimant(self):
        """Verify CONCEDE response removes triad from claimants."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="concede")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        await engine.run()

        assert "triad_1" not in spec.sections["layout"].claims
        assert spec.sections["layout"].owner == "triad_2"

    @pytest.mark.asyncio
    async def test_revise_with_pending_proposal(self):
        """Verify REVISE response updates proposal when available."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="revise")
        triad_1.pending_revised_proposal = {"layout": {"grid": "8-col"}}
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        await engine.run()

        assert spec.sections["layout"].proposals["triad_1"] == {"grid": "8-col"}

    @pytest.mark.asyncio
    async def test_hold_maintains_position(self):
        """Verify HOLD response doesn't change anything."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        await engine.run()

        # triad_1's proposal should be unchanged
        assert spec.sections["layout"].proposals["triad_1"] == {"grid": "12-col"}


class TestNegotiationEngineMultipleSections:
    """Tests for handling multiple contested sections."""

    @pytest.mark.asyncio
    async def test_multiple_contested_sections(self):
        """Verify multiple sections are negotiated independently."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})
        spec.register_claim("triad_1", "visual", {"theme": "dark"})
        spec.register_claim("triad_3", "visual", {"theme": "light"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triad_3 = MockTriad("triad_3", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2, "triad_3": triad_3}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        result_spec = await engine.run()

        assert result_spec.sections["layout"].owner == "triad_1"
        assert result_spec.sections["visual"].owner == "triad_1"


class TestNegotiationEngineEdgeCases:
    """Tests for edge cases in negotiation."""

    @pytest.mark.asyncio
    async def test_all_claimants_concede(self):
        """Verify handling when all claimants concede."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="concede")
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        result_spec = await engine.run()

        assert result_spec.sections["layout"].owner is None
        assert result_spec.sections["layout"].status == SectionStatus.UNCLAIMED

    @pytest.mark.asyncio
    async def test_invalid_response_treated_as_hold(self):
        """Verify invalid responses are treated as HOLD."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="invalid_response")
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        result_spec = await engine.run()

        # triad_1 should still be owner (invalid response = hold)
        assert result_spec.sections["layout"].owner == "triad_1"

    @pytest.mark.asyncio
    async def test_missing_triad_treated_as_hold(self):
        """Verify missing triads are treated as HOLD."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        # Only include triad_2 in the triads dict
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        result_spec = await engine.run()

        # triad_1 should be owner (missing = hold)
        assert result_spec.sections["layout"].owner == "triad_1"


class TestNegotiationEngineStatusTracking:
    """Tests for result and status tracking."""

    @pytest.mark.asyncio
    async def test_get_result(self):
        """Verify result tracking."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="concede")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter()

        engine = NegotiationEngine(triads, spec, arbiter, {})
        await engine.run()

        result = engine.get_result()
        assert result.total_rounds == 1
        assert "layout" in result.sections_resolved
        assert result.final_temperature < 1.0

    @pytest.mark.asyncio
    async def test_get_stuck_sections(self):
        """Verify stuck section tracking."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        triad_1 = MockTriad("triad_1", negotiate_response="hold")
        triad_2 = MockTriad("triad_2", negotiate_response="hold")
        triads = {"triad_1": triad_1, "triad_2": triad_2}
        arbiter = MockArbiter(decision_type="assign", winner="triad_1")

        config = {"escalation_threshold": 3, "max_negotiation_rounds": 2}
        engine = NegotiationEngine(triads, spec, arbiter, config)

        # Run one round manually
        await engine._run_round()
        spec.round += 1

        stuck = engine.get_stuck_sections()
        assert "layout" in stuck
        assert stuck["layout"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
