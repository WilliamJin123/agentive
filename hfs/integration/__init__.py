"""Integration module for HFS output merging and validation.

This module provides components for the integration phase of HFS:
- CodeMerger: Combines artifacts from all triads into unified codebase
- Validator: Runs validation suite (syntax, render, a11y, performance)
- TestRenderer: Renders artifacts for testing and preview

Usage:
    from hfs.integration import CodeMerger, Validator, TestRenderer
    from hfs.integration.merger import MergedArtifact
    from hfs.integration.validator import ValidationResult
    from hfs.integration.renderer import RenderResult, RenderMode
"""

from .merger import CodeMerger, MergedArtifact, FileArtifact, ArtifactType
from .validator import (
    Validator,
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
)
from .renderer import (
    TestRenderer,
    RenderResult,
    RenderError,
    RenderMode,
    RenderStatus,
    ComponentNode,
)

__all__ = [
    # Merger
    "CodeMerger",
    "MergedArtifact",
    "FileArtifact",
    "ArtifactType",
    # Validator
    "Validator",
    "ValidationResult",
    "ValidationIssue",
    "IssueSeverity",
    "IssueCategory",
    # Renderer
    "TestRenderer",
    "RenderResult",
    "RenderError",
    "RenderMode",
    "RenderStatus",
    "ComponentNode",
]
