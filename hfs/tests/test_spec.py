"""Tests for the Spec management module."""

import pytest
from hfs.core.spec import SectionStatus, Section, Spec


class TestSectionStatus:
    """Tests for SectionStatus enum."""

    def test_enum_values(self):
        """Verify all expected status values exist."""
        assert SectionStatus.UNCLAIMED.value == "unclaimed"
        assert SectionStatus.CONTESTED.value == "contested"
        assert SectionStatus.CLAIMED.value == "claimed"
        assert SectionStatus.FROZEN.value == "frozen"


class TestSection:
    """Tests for Section dataclass."""

    def test_default_values(self):
        """Verify default initialization."""
        section = Section()
        assert section.status == SectionStatus.UNCLAIMED
        assert section.owner is None
        assert section.claims == []
        assert section.content is None
        assert section.proposals == {}
        assert section.history == []

    def test_history_recording(self):
        """Verify history entries are recorded correctly."""
        section = Section()
        section._record_history(1, "test_action", "triad_1", extra_key="extra_value")

        assert len(section.history) == 1
        entry = section.history[0]
        assert entry["round"] == 1
        assert entry["action"] == "test_action"
        assert entry["by"] == "triad_1"
        assert entry["extra_key"] == "extra_value"
        assert "timestamp" in entry


class TestSpec:
    """Tests for Spec class - comprehensive coverage of all methods."""

    def test_default_initialization(self):
        """Verify default spec state."""
        spec = Spec()
        assert spec.temperature == 1.0
        assert spec.round == 0
        assert spec.status == "initializing"
        assert spec.sections == {}

    def test_initialize_sections(self):
        """Verify sections can be pre-initialized."""
        spec = Spec()
        spec.initialize_sections(["layout", "visual", "motion"])

        assert len(spec.sections) == 3
        assert "layout" in spec.sections
        assert "visual" in spec.sections
        assert "motion" in spec.sections

        for section in spec.sections.values():
            assert section.status == SectionStatus.UNCLAIMED

    def test_register_claim_new_section(self):
        """Verify claiming creates section and sets CLAIMED status."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        assert "layout" in spec.sections
        section = spec.sections["layout"]
        assert section.status == SectionStatus.CLAIMED
        assert section.owner == "triad_1"
        assert section.claims == ["triad_1"]
        assert section.proposals["triad_1"] == {"grid": "12-col"}
        assert len(section.history) == 1

    def test_register_claim_existing_section(self):
        """Verify claiming an existing unclaimed section."""
        spec = Spec()
        spec.initialize_sections(["layout"])
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        section = spec.sections["layout"]
        assert section.status == SectionStatus.CLAIMED
        assert section.owner == "triad_1"

    def test_register_claim_creates_contested(self):
        """Verify multiple claims create CONTESTED status."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        section = spec.sections["layout"]
        assert section.status == SectionStatus.CONTESTED
        assert section.owner is None
        assert "triad_1" in section.claims
        assert "triad_2" in section.claims
        assert section.proposals["triad_1"] == {"grid": "12-col"}
        assert section.proposals["triad_2"] == {"grid": "16-col"}

    def test_register_claim_updates_proposal(self):
        """Verify re-claiming updates proposal but doesn't duplicate claimant."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_1", "layout", {"grid": "8-col"})

        section = spec.sections["layout"]
        assert section.claims == ["triad_1"]  # Not duplicated
        assert section.proposals["triad_1"] == {"grid": "8-col"}  # Updated

    def test_register_claim_frozen_section_rejected(self):
        """Verify claims on frozen sections are rejected."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.freeze()

        # Try to claim frozen section
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        section = spec.sections["layout"]
        assert "triad_2" not in section.claims
        # Check rejection was recorded
        assert any(
            h["action"] == "claim_rejected" and h["by"] == "triad_2"
            for h in section.history
        )

    def test_concede_removes_claimant(self):
        """Verify concession removes triad from claimants."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        result = spec.concede("triad_1", "layout")

        assert result is True
        section = spec.sections["layout"]
        assert "triad_1" not in section.claims
        assert "triad_1" not in section.proposals
        assert section.status == SectionStatus.CLAIMED
        assert section.owner == "triad_2"

    def test_concede_to_unclaimed(self):
        """Verify last claimant conceding makes section unclaimed."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        result = spec.concede("triad_1", "layout")

        assert result is True
        section = spec.sections["layout"]
        assert section.status == SectionStatus.UNCLAIMED
        assert section.owner is None
        assert section.claims == []

    def test_concede_nonexistent_section(self):
        """Verify conceding from nonexistent section returns False."""
        spec = Spec()
        result = spec.concede("triad_1", "nonexistent")
        assert result is False

    def test_concede_non_claimant(self):
        """Verify conceding when not a claimant returns False."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        result = spec.concede("triad_2", "layout")

        assert result is False
        section = spec.sections["layout"]
        assert "triad_1" in section.claims  # Unchanged

    def test_concede_frozen_section(self):
        """Verify conceding from frozen section returns False."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.freeze()

        result = spec.concede("triad_1", "layout")
        assert result is False

    def test_update_proposal(self):
        """Verify proposals can be updated (REVISE action)."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        result = spec.update_proposal("triad_1", "layout", {"grid": "8-col"})

        assert result is True
        section = spec.sections["layout"]
        assert section.proposals["triad_1"] == {"grid": "8-col"}
        assert any(h["action"] == "revise" for h in section.history)

    def test_update_proposal_non_claimant(self):
        """Verify non-claimant cannot update proposal."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        result = spec.update_proposal("triad_2", "layout", {"grid": "8-col"})
        assert result is False

    def test_freeze_sets_content_from_owner_proposal(self):
        """Verify freeze locks in owner's proposal as content."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "visual", {"theme": "dark"})

        spec.freeze()

        assert spec.temperature == 0.0
        assert spec.status == "frozen"

        layout = spec.sections["layout"]
        assert layout.status == SectionStatus.FROZEN
        assert layout.content == {"grid": "12-col"}

        visual = spec.sections["visual"]
        assert visual.status == SectionStatus.FROZEN
        assert visual.content == {"theme": "dark"}

    def test_freeze_handles_contested_sections(self):
        """Verify freeze handles contested sections (no winner selected)."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        spec.freeze()

        section = spec.sections["layout"]
        assert section.status == SectionStatus.FROZEN
        # No owner means no content
        assert section.content is None

    def test_freeze_handles_unclaimed_sections(self):
        """Verify freeze leaves unclaimed sections as coverage gaps."""
        spec = Spec()
        spec.initialize_sections(["layout", "visual"])
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        spec.freeze()

        layout = spec.sections["layout"]
        assert layout.status == SectionStatus.FROZEN

        visual = spec.sections["visual"]
        assert visual.status == SectionStatus.UNCLAIMED  # Coverage gap

    def test_get_contested_sections(self):
        """Verify contested sections are correctly identified."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})
        spec.register_claim("triad_1", "visual", {"theme": "dark"})

        contested = spec.get_contested_sections()

        assert "layout" in contested
        assert "visual" not in contested

    def test_get_unclaimed_sections(self):
        """Verify unclaimed sections are correctly identified."""
        spec = Spec()
        spec.initialize_sections(["layout", "visual", "motion"])
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        unclaimed = spec.get_unclaimed_sections()

        assert "visual" in unclaimed
        assert "motion" in unclaimed
        assert "layout" not in unclaimed

    def test_get_claimed_sections(self):
        """Verify claimed sections are correctly identified."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_1", "visual", {"theme": "dark"})
        spec.register_claim("triad_2", "visual", {"theme": "light"})

        claimed = spec.get_claimed_sections()

        assert "layout" in claimed
        assert "visual" not in claimed  # Contested

    def test_advance_round(self):
        """Verify round advancement and temperature decay."""
        spec = Spec()
        initial_temp = spec.temperature

        spec.advance_round(temperature_decay=0.2)

        assert spec.round == 1
        assert spec.temperature == initial_temp - 0.2
        assert spec.status == "negotiating"

    def test_advance_round_status_transitions(self):
        """Verify status transitions as temperature drops."""
        spec = Spec()

        # Advance until cooling
        for _ in range(6):
            spec.advance_round(temperature_decay=0.15)

        assert spec.status == "cooling"
        assert spec.temperature <= 0.1

    def test_advance_round_temperature_floor(self):
        """Verify temperature doesn't go below 0."""
        spec = Spec()

        for _ in range(20):
            spec.advance_round(temperature_decay=0.15)

        assert spec.temperature == 0.0

    def test_is_frozen(self):
        """Verify is_frozen check."""
        spec = Spec()
        assert spec.is_frozen() is False

        spec.freeze()
        assert spec.is_frozen() is True

    def test_get_section_owner(self):
        """Verify owner retrieval."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})

        assert spec.get_section_owner("layout") == "triad_1"
        assert spec.get_section_owner("nonexistent") is None

    def test_get_section_claimants(self):
        """Verify claimants retrieval."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        claimants = spec.get_section_claimants("layout")

        assert "triad_1" in claimants
        assert "triad_2" in claimants
        assert spec.get_section_claimants("nonexistent") == []

    def test_get_section_proposals(self):
        """Verify proposals retrieval."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})

        proposals = spec.get_section_proposals("layout")

        assert proposals["triad_1"] == {"grid": "12-col"}
        assert proposals["triad_2"] == {"grid": "16-col"}
        assert spec.get_section_proposals("nonexistent") == {}

    def test_get_coverage_report(self):
        """Verify coverage report generation."""
        spec = Spec()
        spec.initialize_sections(["layout", "visual", "motion", "state"])
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.register_claim("triad_2", "visual", {"theme": "dark"})
        spec.register_claim("triad_3", "visual", {"theme": "light"})

        report = spec.get_coverage_report()

        assert report["total_sections"] == 4
        assert "motion" in report["unclaimed"]
        assert "state" in report["unclaimed"]
        assert "visual" in report["contested"]
        assert "layout" in report["claimed"]
        assert report["ownership"]["layout"] == "triad_1"
        assert report["coverage_gaps"] == 2
        assert report["unresolved_conflicts"] == 1

    def test_get_full_history(self):
        """Verify full history compilation."""
        spec = Spec()
        spec.register_claim("triad_1", "layout", {"grid": "12-col"})
        spec.advance_round()
        spec.register_claim("triad_2", "layout", {"grid": "16-col"})
        spec.advance_round()
        spec.concede("triad_1", "layout")

        history = spec.get_full_history()

        assert len(history) >= 3
        # Should be sorted by round
        rounds = [h["round"] for h in history]
        assert rounds == sorted(rounds)


class TestSpecNegotiationScenario:
    """Integration test: Full negotiation scenario."""

    def test_full_negotiation_flow(self):
        """Test a complete negotiation from start to freeze."""
        spec = Spec()

        # Initialize territory
        spec.initialize_sections(["layout", "visual", "motion", "interaction"])

        # Round 0: Initial claims
        spec.register_claim("layout_triad", "layout", {"grid": "12-col", "spacing": "8px"})
        spec.register_claim("visual_triad", "visual", {"theme": "modern", "colors": ["#fff", "#000"]})
        spec.register_claim("motion_triad", "motion", {"duration": "300ms"})

        # Both want interaction
        spec.register_claim("visual_triad", "interaction", {"hover": "scale"})
        spec.register_claim("motion_triad", "interaction", {"hover": "fade"})

        assert spec.get_contested_sections() == ["interaction"]
        assert len(spec.get_claimed_sections()) == 3

        # Round 1: Negotiation
        spec.advance_round()

        # Motion triad concedes interaction to visual
        spec.concede("motion_triad", "interaction")

        assert spec.get_contested_sections() == []
        assert spec.get_section_owner("interaction") == "visual_triad"

        # Freeze
        spec.freeze()

        assert spec.is_frozen()
        assert spec.sections["layout"].content == {"grid": "12-col", "spacing": "8px"}
        assert spec.sections["visual"].content == {"theme": "modern", "colors": ["#fff", "#000"]}
        assert spec.sections["motion"].content == {"duration": "300ms"}
        assert spec.sections["interaction"].content == {"hover": "scale"}

        # Coverage report
        report = spec.get_coverage_report()
        assert report["coverage_gaps"] == 0
        assert report["unresolved_conflicts"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
