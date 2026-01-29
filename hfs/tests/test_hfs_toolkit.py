"""Unit tests for HFSToolkit.

These tests verify the HFSToolkit's integration with the Spec class
and proper handling of Pydantic validation errors.

Run with: pytest hfs/tests/test_hfs_toolkit.py -v
"""

import pytest
import json
from hfs.agno.tools import HFSToolkit
from hfs.core.spec import Spec


class TestRegisterClaim:
    """Tests for register_claim tool."""

    def test_register_claim_success(self):
        """Registering a claim on an existing section succeeds."""
        spec = Spec()
        spec.initialize_sections(["header", "footer"])
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.register_claim(
            section_id="header",
            proposal="Navigation with logo"
        ))

        assert result["success"] is True
        assert result["section_id"] == "header"
        assert result["status"] == "claimed"
        assert "triad-1" in result["current_claimants"]

    def test_register_claim_creates_section(self):
        """Registering a claim on non-existent section creates it."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.register_claim(
            section_id="new-section",
            proposal="Content for new section"
        ))

        assert result["success"] is True
        assert result["section_id"] == "new-section"
        assert "new-section" in spec.sections

    def test_register_claim_contested(self):
        """Second claim on same section makes it contested."""
        spec = Spec()
        spec.initialize_sections(["header"])
        spec.register_claim("other-triad", "header", "Their proposal")
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.register_claim(
            section_id="header",
            proposal="My proposal"
        ))

        assert result["success"] is True
        assert result["status"] == "contested"
        assert len(result["current_claimants"]) == 2
        assert "triad-1" in result["current_claimants"]
        assert "other-triad" in result["current_claimants"]

    def test_register_claim_validation_error_empty_section_id(self):
        """Empty section_id returns validation error with hints."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.register_claim(
            section_id="",
            proposal="Content"
        ))

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert result["retry_allowed"] is True
        assert len(result["hints"]) > 0

    def test_register_claim_validation_error_empty_proposal(self):
        """Empty proposal returns validation error with hints."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.register_claim(
            section_id="header",
            proposal=""
        ))

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert result["retry_allowed"] is True

    def test_register_claim_strips_whitespace(self):
        """Section ID whitespace is stripped."""
        spec = Spec()
        spec.initialize_sections(["header"])
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.register_claim(
            section_id="  header  ",
            proposal="Content"
        ))

        assert result["success"] is True
        assert result["section_id"] == "header"


class TestNegotiateResponse:
    """Tests for negotiate_response tool."""

    def test_concede(self):
        """Concede removes triad from claimants."""
        spec = Spec()
        spec.initialize_sections(["header"])
        spec.register_claim("triad-1", "header", "Proposal 1")
        spec.register_claim("triad-2", "header", "Proposal 2")
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.negotiate_response(
            section_id="header",
            decision="concede"
        ))

        assert result["success"] is True
        assert result["decision"] == "concede"
        assert "triad-1" not in spec.sections["header"].claims

    def test_revise_updates_proposal(self):
        """Revise updates the proposal content."""
        spec = Spec()
        spec.initialize_sections(["header"])
        spec.register_claim("triad-1", "header", "Original proposal")
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.negotiate_response(
            section_id="header",
            decision="revise",
            revised_proposal="Updated proposal"
        ))

        assert result["success"] is True
        assert result["decision"] == "revise"
        assert spec.sections["header"].proposals["triad-1"] == "Updated proposal"

    def test_revise_requires_proposal(self):
        """Revise without revised_proposal returns validation error."""
        spec = Spec()
        spec.initialize_sections(["header"])
        spec.register_claim("triad-1", "header", "Proposal")
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.negotiate_response(
            section_id="header",
            decision="revise"
        ))

        assert result["success"] is False
        assert result["retry_allowed"] is True
        assert "hints" in result

    def test_hold_keeps_position(self):
        """Hold maintains current proposal."""
        spec = Spec()
        spec.initialize_sections(["header"])
        spec.register_claim("triad-1", "header", "Original proposal")
        original_proposal = spec.sections["header"].proposals["triad-1"]
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.negotiate_response(
            section_id="header",
            decision="hold"
        ))

        assert result["success"] is True
        assert result["decision"] == "hold"
        assert spec.sections["header"].proposals["triad-1"] == original_proposal

    def test_invalid_decision_returns_error(self):
        """Invalid decision value returns validation error."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.negotiate_response(
            section_id="header",
            decision="invalid_decision"
        ))

        assert result["success"] is False
        assert result["retry_allowed"] is True

    def test_negotiate_nonexistent_section_fails(self):
        """Negotiating on non-existent section returns runtime error."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.negotiate_response(
            section_id="nonexistent",
            decision="hold"
        ))

        assert result["success"] is False
        assert result["retry_allowed"] is False


class TestGetCurrentClaims:
    """Tests for get_current_claims tool."""

    def test_returns_all_categories(self):
        """Returns sections grouped by status."""
        spec = Spec()
        spec.initialize_sections(["sec1", "sec2", "sec3"])
        spec.register_claim("triad-1", "sec1", "P1")
        spec.register_claim("triad-1", "sec2", "P2")
        spec.register_claim("triad-2", "sec2", "P2b")  # contested
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.get_current_claims())

        assert result["success"] is True
        assert "sec3" in result["unclaimed"]
        assert "sec1" in result["claimed"]
        assert "sec2" in result["contested"]
        assert "sec1" in result["your_claims"]
        assert "sec2" in result["your_claims"]

    def test_includes_temperature_and_round(self):
        """Returns spec temperature and round number."""
        spec = Spec()
        spec.initialize_sections(["sec1"])
        spec.advance_round()  # Advances round, decreases temperature
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.get_current_claims())

        assert result["success"] is True
        assert "temperature" in result
        assert "round" in result
        assert result["round"] == 1
        assert result["temperature"] < 1.0

    def test_empty_spec_returns_empty_lists(self):
        """Empty spec returns empty category lists."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.get_current_claims())

        assert result["success"] is True
        assert result["unclaimed"] == []
        assert result["claimed"] == []
        assert result["contested"] == []
        assert result["frozen"] == []
        assert result["your_claims"] == []


class TestGetNegotiationState:
    """Tests for get_negotiation_state tool."""

    def test_all_contested(self):
        """Returns all contested sections when no section_id provided."""
        spec = Spec()
        spec.initialize_sections(["sec1", "sec2"])
        spec.register_claim("triad-1", "sec1", "P1")
        spec.register_claim("triad-2", "sec1", "P2")
        spec.register_claim("triad-1", "sec2", "P3")  # claimed, not contested
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.get_negotiation_state())

        assert result["success"] is True
        assert result["total_contested"] == 1
        assert "sec1" in result["contested_sections"]
        assert "sec2" not in result["contested_sections"]

    def test_specific_section(self):
        """Returns details for specific section when section_id provided."""
        spec = Spec()
        spec.initialize_sections(["sec1"])
        spec.register_claim("triad-1", "sec1", "P1")
        spec.register_claim("triad-2", "sec1", "P2")
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.get_negotiation_state(section_id="sec1"))

        assert result["success"] is True
        assert result["section_id"] == "sec1"
        assert "claimants" in result
        assert "proposals" in result
        assert len(result["claimants"]) == 2

    def test_nonexistent_section_returns_error(self):
        """Returns error for non-existent section."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.get_negotiation_state(section_id="nonexistent"))

        assert result["success"] is False
        assert result["retry_allowed"] is False


class TestGenerateCode:
    """Tests for generate_code tool."""

    def test_requires_frozen_spec(self):
        """Returns error if spec is not frozen."""
        spec = Spec()
        spec.initialize_sections(["sec1"])
        spec.register_claim("triad-1", "sec1", "P1")
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.generate_code(section_id="sec1"))

        assert result["success"] is False
        assert "frozen" in result["message"].lower()

    def test_requires_ownership(self):
        """Returns error if triad doesn't own the section."""
        spec = Spec()
        spec.initialize_sections(["sec1"])
        spec.register_claim("other-triad", "sec1", "P1")
        spec.freeze()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.generate_code(section_id="sec1"))

        assert result["success"] is False
        assert "owner" in result["message"].lower() or "not owner" in result["message"].lower()

    def test_success_when_frozen_and_owner(self):
        """Returns success placeholder when spec frozen and triad owns section."""
        spec = Spec()
        spec.initialize_sections(["sec1"])
        spec.register_claim("triad-1", "sec1", "P1")
        spec.freeze()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.generate_code(section_id="sec1"))

        assert result["success"] is True
        assert result["section_id"] == "sec1"
        # code is placeholder (None) for now
        assert "code" in result

    def test_validation_error_empty_section_id(self):
        """Empty section_id returns validation error."""
        spec = Spec()
        spec.freeze()
        toolkit = HFSToolkit(spec=spec, triad_id="triad-1")

        result = json.loads(toolkit.generate_code(section_id=""))

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert result["retry_allowed"] is True


class TestToolkitIntegration:
    """Integration tests for HFSToolkit."""

    def test_toolkit_has_five_tools(self):
        """Toolkit registers exactly 5 tools."""
        spec = Spec()
        toolkit = HFSToolkit(spec=spec, triad_id="test")

        assert len(toolkit.functions) == 5
        expected_tools = {
            "register_claim",
            "negotiate_response",
            "generate_code",
            "get_current_claims",
            "get_negotiation_state",
        }
        assert set(toolkit.functions.keys()) == expected_tools

    def test_full_workflow(self):
        """Test complete claim -> negotiate -> freeze -> generate workflow."""
        spec = Spec()
        spec.initialize_sections(["header", "footer"])

        toolkit1 = HFSToolkit(spec=spec, triad_id="triad-1")
        toolkit2 = HFSToolkit(spec=spec, triad_id="triad-2")

        # Both triads claim header
        r1 = json.loads(toolkit1.register_claim("header", "Triad 1 header"))
        r2 = json.loads(toolkit2.register_claim("header", "Triad 2 header"))
        assert r1["success"] and r2["success"]
        assert r2["status"] == "contested"

        # Triad 1 also claims footer (uncontested)
        r3 = json.loads(toolkit1.register_claim("footer", "Triad 1 footer"))
        assert r3["status"] == "claimed"

        # Check state
        state = json.loads(toolkit1.get_current_claims())
        assert "header" in state["contested"]
        assert "footer" in state["claimed"]

        # Triad 2 concedes header
        r4 = json.loads(toolkit2.negotiate_response("header", "concede"))
        assert r4["success"]

        # Header is now claimed by triad 1
        state = json.loads(toolkit1.get_current_claims())
        assert "header" in state["claimed"]
        assert "header" in state["your_claims"]

        # Freeze spec
        spec.freeze()

        # Triad 1 can generate code for both sections
        r5 = json.loads(toolkit1.generate_code("header"))
        r6 = json.loads(toolkit1.generate_code("footer"))
        assert r5["success"] and r6["success"]

        # Triad 2 cannot generate code (doesn't own anything)
        r7 = json.loads(toolkit2.generate_code("header"))
        assert r7["success"] is False
