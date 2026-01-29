"""Tests for HFS Agno Teams base infrastructure.

Tests the schemas and AgnoTriad base class without external API calls.
"""

import pytest
from pydantic import ValidationError

from hfs.agno.teams.schemas import (
    PhaseSummary,
    TriadSessionState,
    TriadExecutionError,
)
from hfs.agno.teams import AgnoTriad


class TestPhaseSummary:
    """Tests for PhaseSummary model."""

    def test_phase_summary_validation(self):
        """PhaseSummary requires phase and produced_by fields."""
        summary = PhaseSummary(
            phase="deliberation",
            decisions=["decided X", "decided Y"],
            open_questions=["what about Z?"],
            artifacts={"claims": "header, footer"},
            produced_by="synthesizer",
        )
        assert summary.phase == "deliberation"
        assert len(summary.decisions) == 2
        assert len(summary.open_questions) == 1
        assert summary.artifacts["claims"] == "header, footer"
        assert summary.produced_by == "synthesizer"

    def test_phase_summary_defaults(self):
        """PhaseSummary has default empty lists for optional fields."""
        summary = PhaseSummary(
            phase="negotiation",
            produced_by="orchestrator",
        )
        assert summary.decisions == []
        assert summary.open_questions == []
        assert summary.artifacts == {}

    def test_phase_summary_requires_phase(self):
        """PhaseSummary requires phase field."""
        with pytest.raises(ValidationError):
            PhaseSummary(produced_by="synthesizer")

    def test_phase_summary_requires_produced_by(self):
        """PhaseSummary requires produced_by field."""
        with pytest.raises(ValidationError):
            PhaseSummary(phase="execution")


class TestTriadSessionState:
    """Tests for TriadSessionState model."""

    def test_triad_session_state_defaults(self):
        """TriadSessionState initializes with None phases."""
        state = TriadSessionState()
        assert state.current_phase is None
        assert state.deliberation_summary is None
        assert state.negotiation_summary is None
        assert state.execution_summary is None

    def test_triad_session_state_with_summaries(self):
        """TriadSessionState can store phase summaries."""
        delib_summary = PhaseSummary(
            phase="deliberation",
            decisions=["claim header"],
            produced_by="synthesizer",
        )
        state = TriadSessionState(
            current_phase="negotiation",
            deliberation_summary=delib_summary,
        )
        assert state.current_phase == "negotiation"
        assert state.deliberation_summary is not None
        assert state.deliberation_summary.decisions == ["claim header"]

    def test_triad_session_state_get_phase_context_deliberation(self):
        """get_phase_context returns empty context for deliberation."""
        state = TriadSessionState()
        context = state.get_phase_context("deliberation")
        assert context == {"phase": "deliberation"}

    def test_triad_session_state_get_phase_context_negotiation(self):
        """get_phase_context returns deliberation context for negotiation."""
        delib_summary = PhaseSummary(
            phase="deliberation",
            decisions=["decision A"],
            open_questions=["question B"],
            artifacts={"section": "preview"},
            produced_by="synthesizer",
        )
        state = TriadSessionState(deliberation_summary=delib_summary)
        context = state.get_phase_context("negotiation")
        assert context["phase"] == "negotiation"
        assert context["prior_decisions"] == ["decision A"]
        assert context["open_questions"] == ["question B"]
        assert context["artifacts"] == {"section": "preview"}

    def test_triad_session_state_get_phase_context_execution(self):
        """get_phase_context returns negotiation + deliberation context for execution."""
        delib_summary = PhaseSummary(
            phase="deliberation",
            decisions=["delib decision"],
            produced_by="synthesizer",
        )
        nego_summary = PhaseSummary(
            phase="negotiation",
            decisions=["nego decision"],
            artifacts={"final": "content"},
            produced_by="orchestrator",
        )
        state = TriadSessionState(
            deliberation_summary=delib_summary,
            negotiation_summary=nego_summary,
        )
        context = state.get_phase_context("execution")
        assert context["phase"] == "execution"
        assert context["prior_decisions"] == ["nego decision"]
        assert context["artifacts"] == {"final": "content"}
        assert context["deliberation_decisions"] == ["delib decision"]


class TestTriadExecutionError:
    """Tests for TriadExecutionError exception."""

    def test_triad_execution_error_attributes(self):
        """TriadExecutionError captures all required context."""
        error = TriadExecutionError(
            triad_id="visual_triad",
            phase="deliberation",
            agent="proposer",
            error="LLM timeout",
            partial_state={"current_phase": "deliberation"},
        )
        assert error.triad_id == "visual_triad"
        assert error.phase == "deliberation"
        assert error.agent == "proposer"
        assert error.error == "LLM timeout"
        assert error.partial_state == {"current_phase": "deliberation"}

    def test_triad_execution_error_message_format(self):
        """Error message includes triad, phase, and agent."""
        error = TriadExecutionError(
            triad_id="layout_triad",
            phase="negotiation",
            agent="worker_a",
            error="Rate limited",
        )
        message = str(error)
        assert "layout_triad" in message
        assert "negotiation" in message
        assert "worker_a" in message
        assert "Rate limited" in message

    def test_triad_execution_error_unknown_agent(self):
        """TriadExecutionError defaults to unknown agent."""
        error = TriadExecutionError(
            triad_id="test_triad",
            phase="execution",
            error="Something failed",
        )
        assert error.agent == "unknown"
        message = str(error)
        # Message format without agent when unknown
        assert "test_triad" in message
        assert "execution" in message

    def test_triad_execution_error_is_exception(self):
        """TriadExecutionError is a proper Exception subclass."""
        error = TriadExecutionError(
            triad_id="test",
            phase="test",
        )
        assert isinstance(error, Exception)

        # Can be raised and caught
        with pytest.raises(TriadExecutionError) as exc_info:
            raise error
        assert exc_info.value.triad_id == "test"


class TestAgnoTriad:
    """Tests for AgnoTriad abstract base class."""

    def test_agno_triad_is_abstract(self):
        """Cannot instantiate AgnoTriad directly."""
        with pytest.raises(TypeError) as exc_info:
            AgnoTriad(None, None, None)
        error_msg = str(exc_info.value).lower()
        assert "abstract" in error_msg or "instantiate" in error_msg

    def test_agno_triad_abstract_methods(self):
        """AgnoTriad has the correct abstract methods defined."""
        abstract_methods = AgnoTriad.__abstractmethods__
        expected_methods = {
            "_create_agents",
            "_create_team",
            "_get_phase_summary_prompt",
            "_build_deliberation_prompt",
            "_build_negotiation_prompt",
            "_build_execution_prompt",
        }
        assert expected_methods == abstract_methods

    def test_agno_triad_has_concrete_methods(self):
        """AgnoTriad has concrete implementation methods."""
        # These should be defined (not abstract)
        assert hasattr(AgnoTriad, "_run_with_error_handling")
        assert hasattr(AgnoTriad, "_save_partial_progress")
        assert hasattr(AgnoTriad, "_load_partial_progress")
        assert hasattr(AgnoTriad, "deliberate")
        assert hasattr(AgnoTriad, "negotiate")
        assert hasattr(AgnoTriad, "execute")

        # Verify they're not abstract
        assert "_run_with_error_handling" not in AgnoTriad.__abstractmethods__
        assert "_save_partial_progress" not in AgnoTriad.__abstractmethods__
        assert "_load_partial_progress" not in AgnoTriad.__abstractmethods__
        assert "deliberate" not in AgnoTriad.__abstractmethods__
        assert "negotiate" not in AgnoTriad.__abstractmethods__
        assert "execute" not in AgnoTriad.__abstractmethods__
