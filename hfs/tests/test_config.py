"""Tests for HFS configuration loading and validation."""

import pytest
import tempfile
import yaml
from pathlib import Path

from hfs.core.config import (
    ConfigError,
    HFSConfig,
    TriadConfigModel,
    PressureConfigModel,
    ArbiterConfigModel,
    OutputConfigModel,
    load_config,
    load_config_dict,
)


class TestTriadConfigModel:
    """Tests for triad configuration validation."""

    def test_valid_triad(self):
        """Test that valid triad config is accepted."""
        config = TriadConfigModel(
            id="test-triad",
            preset="hierarchical",
            scope={"primary": ["layout"], "reach": ["visual"]},
            budget={"tokens": 10000, "tool_calls": 20, "time_ms": 15000},
            objectives=["code_quality"],
        )
        assert config.id == "test-triad"
        assert config.preset == "hierarchical"
        assert config.scope.primary == ["layout"]

    def test_invalid_preset(self):
        """Test that invalid preset is rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TriadConfigModel(
                id="test",
                preset="invalid_preset",
            )

    def test_empty_id_rejected(self):
        """Test that empty triad ID is rejected."""
        with pytest.raises(Exception):
            TriadConfigModel(
                id="",
                preset="hierarchical",
            )

    def test_default_budget(self):
        """Test that default budget values are applied."""
        config = TriadConfigModel(
            id="test",
            preset="dialectic",
        )
        assert config.budget.tokens == 20000
        assert config.budget.tool_calls == 50
        assert config.budget.time_ms == 30000


class TestPressureConfigModel:
    """Tests for pressure configuration validation."""

    def test_valid_pressure_config(self):
        """Test that valid pressure config is accepted."""
        config = PressureConfigModel(
            initial_temperature=0.8,
            temperature_decay=0.1,
            max_negotiation_rounds=5,
        )
        assert config.initial_temperature == 0.8
        assert config.temperature_decay == 0.1

    def test_temperature_bounds(self):
        """Test that temperature values are bounded."""
        with pytest.raises(Exception):
            PressureConfigModel(initial_temperature=1.5)

        with pytest.raises(Exception):
            PressureConfigModel(initial_temperature=-0.1)

    def test_default_values(self):
        """Test that default pressure values are sensible."""
        config = PressureConfigModel()
        assert config.initial_temperature == 1.0
        assert config.temperature_decay == 0.15
        assert config.freeze_threshold == 0.1
        assert config.max_negotiation_rounds == 10
        assert config.escalation_threshold == 2


class TestOutputConfigModel:
    """Tests for output configuration validation."""

    def test_valid_output_config(self):
        """Test that valid output config is accepted."""
        config = OutputConfigModel(
            format="vue",
            style_system="css-modules",
        )
        assert config.format == "vue"
        assert config.style_system == "css-modules"

    def test_invalid_format(self):
        """Test that invalid format is rejected."""
        with pytest.raises(Exception):
            OutputConfigModel(format="angular")  # Not supported

    def test_invalid_style_system(self):
        """Test that invalid style system is rejected."""
        with pytest.raises(Exception):
            OutputConfigModel(style_system="sass")  # Not supported


class TestHFSConfig:
    """Tests for main HFS configuration."""

    def test_valid_minimal_config(self):
        """Test that valid minimal config is accepted."""
        config = HFSConfig(
            triads=[
                {
                    "id": "design",
                    "preset": "dialectic",
                    "objectives": ["aesthetics"],
                }
            ],
            sections=["layout", "visual"],
        )
        assert len(config.triads) == 1
        assert config.triads[0].id == "design"

    def test_duplicate_triad_ids_rejected(self):
        """Test that duplicate triad IDs are rejected."""
        with pytest.raises(Exception):
            HFSConfig(
                triads=[
                    {"id": "triad1", "preset": "hierarchical"},
                    {"id": "triad1", "preset": "dialectic"},  # Duplicate
                ],
                sections=["layout"],
            )

    def test_empty_triads_rejected(self):
        """Test that empty triads list is rejected."""
        with pytest.raises(Exception):
            HFSConfig(triads=[], sections=["layout"])

    def test_empty_sections_rejected(self):
        """Test that empty sections list is rejected."""
        with pytest.raises(Exception):
            HFSConfig(
                triads=[{"id": "test", "preset": "hierarchical"}],
                sections=[],
            )


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_minimal_yaml(self, tmp_path):
        """Test loading minimal YAML configuration."""
        config_data = {
            "config": {
                "triads": [
                    {
                        "id": "test",
                        "preset": "hierarchical",
                        "scope": {"primary": ["layout"], "reach": []},
                        "budget": {"tokens": 10000, "tool_calls": 20, "time_ms": 15000},
                        "objectives": ["quality"],
                    }
                ],
                "sections": ["layout", "visual"],
                "output": {"format": "react", "style_system": "tailwind"},
            }
        }

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.triads[0].id == "test"
        assert config.output.format == "react"

    def test_load_without_config_wrapper(self, tmp_path):
        """Test loading YAML without 'config' wrapper key."""
        config_data = {
            "triads": [
                {
                    "id": "test",
                    "preset": "dialectic",
                }
            ],
            "sections": ["layout"],
        }

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.triads[0].preset == "dialectic"

    def test_file_not_found(self):
        """Test that missing file raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            load_config("/nonexistent/path/config.yaml")
        assert "not found" in str(exc_info.value)

    def test_invalid_yaml(self, tmp_path):
        """Test that invalid YAML raises ConfigError."""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [[[")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "YAML" in str(exc_info.value)

    def test_empty_file(self, tmp_path):
        """Test that empty file raises ConfigError."""
        config_file = tmp_path / "empty.yaml"
        config_file.touch()

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "empty" in str(exc_info.value).lower()


class TestLoadConfigDict:
    """Tests for load_config_dict function."""

    def test_load_from_dict(self):
        """Test loading config from dictionary."""
        data = {
            "triads": [{"id": "test", "preset": "consensus"}],
            "sections": ["layout"],
        }

        config = load_config_dict(data)
        assert config.triads[0].id == "test"
        assert config.triads[0].preset == "consensus"

    def test_load_with_config_wrapper(self):
        """Test loading config from dict with 'config' wrapper."""
        data = {
            "config": {
                "triads": [{"id": "test", "preset": "hierarchical"}],
                "sections": ["layout"],
            }
        }

        config = load_config_dict(data)
        assert config.triads[0].preset == "hierarchical"

    def test_validation_error(self):
        """Test that invalid data raises ConfigError."""
        with pytest.raises(ConfigError):
            load_config_dict({"triads": [], "sections": []})


class TestExampleConfigs:
    """Tests for example configuration files."""

    def test_load_default_config(self):
        """Test loading default.yaml."""
        config = load_config(Path(__file__).parent.parent / "config" / "default.yaml")
        assert config.pressure.initial_temperature == 1.0
        assert config.output.format == "react"

    def test_load_minimal_example(self):
        """Test loading minimal.yaml example."""
        config = load_config(
            Path(__file__).parent.parent / "config" / "examples" / "minimal.yaml"
        )
        assert len(config.triads) == 2
        triad_ids = [t.id for t in config.triads]
        assert "design" in triad_ids
        assert "engineering" in triad_ids

    def test_load_standard_example(self):
        """Test loading standard.yaml example."""
        config = load_config(
            Path(__file__).parent.parent / "config" / "examples" / "standard.yaml"
        )
        assert len(config.triads) == 6
        triad_ids = [t.id for t in config.triads]
        assert "layout" in triad_ids
        assert "visual" in triad_ids
        assert "accessibility" in triad_ids

    def test_standard_has_hierarchical_sections(self):
        """Test that standard config has hierarchical sections."""
        config = load_config(
            Path(__file__).parent.parent / "config" / "examples" / "standard.yaml"
        )
        # Check for hierarchical section names
        assert "layout/grid" in config.sections
        assert "visual/colors" in config.sections
        assert "accessibility/keyboard" in config.sections
