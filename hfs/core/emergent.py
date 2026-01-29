"""Emergent center observation for HFS.

The "emergent center" is the quality that no triad owns but all triads affect.
It's observed, not controlled. This module provides tools to observe and report
on emergent properties that arise from triad interactions.

Key concepts:
- Quantitative metrics: coherence_score, style_consistency, interaction_consistency
- Detected patterns: implicit_style, natural_clusters
- Issues: coverage_gaps, unresolved_tensions
- Recommendations: suggested improvements based on observed patterns

Use cases:
- Quality Assessment: Is the output coherent or just assembled?
- Architecture Learning: Do triad boundaries match problem structure?
- Iteration: Adjust configuration for future runs
- Debugging: Understand why outputs feel "off"
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict


@dataclass
class EmergentMetrics:
    """Quantitative metrics for emergent properties.

    All metrics are normalized to 0.0 - 1.0 range.

    Attributes:
        coherence_score: How well do sections fit together?
            Higher values indicate more unified output.
        style_consistency: Is there a unified visual/tonal language?
            Signals: color_palette_variance, typography_consistency, spacing_rhythm.
        interaction_consistency: Do interactions feel of-a-piece?
            Signals: animation_timing_variance, feedback_pattern_similarity.
    """
    coherence_score: float = 0.0
    style_consistency: float = 0.0
    interaction_consistency: float = 0.0

    def __post_init__(self) -> None:
        """Validate that all metrics are within valid range."""
        for field_name in ['coherence_score', 'style_consistency', 'interaction_consistency']:
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0.0 and 1.0, got {value}"
                )

    @property
    def average_score(self) -> float:
        """Compute the average of all metrics."""
        return (
            self.coherence_score +
            self.style_consistency +
            self.interaction_consistency
        ) / 3.0


@dataclass
class DetectedPatterns:
    """Qualitative observations about emergent patterns.

    Attributes:
        implicit_style: What emerged without being specified?
            Examples: "minimal", "dark-mode-first", "motion-forward", "content-dense"
        natural_clusters: Which triads ended up collaborating most?
            Format: List of triad ID groups that naturally clustered together.
            This reveals actual problem structure vs assumed structure.
        collaboration_frequency: Dict mapping (triad_a, triad_b) to interaction count.
    """
    implicit_style: List[str] = field(default_factory=list)
    natural_clusters: List[List[str]] = field(default_factory=list)
    collaboration_frequency: Dict[Tuple[str, str], int] = field(default_factory=dict)

    def get_most_collaborative_pair(self) -> Optional[Tuple[str, str]]:
        """Return the triad pair that collaborated most frequently."""
        if not self.collaboration_frequency:
            return None
        return max(
            self.collaboration_frequency.keys(),
            key=lambda k: self.collaboration_frequency[k]
        )


@dataclass
class EmergentIssues:
    """Gaps and tensions identified in the output.

    Attributes:
        coverage_gaps: Things no triad addressed.
            Examples: "error-states", "empty-states", "loading-transitions"
        unresolved_tensions: Conflicts that persisted into final output.
            Examples: "visual wants slow transitions, interaction wants snappy feedback"
        sections_without_owner: Section names that remained unclaimed.
        escalation_count: Number of times arbiter intervention was needed.
    """
    coverage_gaps: List[str] = field(default_factory=list)
    unresolved_tensions: List[str] = field(default_factory=list)
    sections_without_owner: List[str] = field(default_factory=list)
    escalation_count: int = 0

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues that need attention."""
        return (
            len(self.sections_without_owner) > 0 or
            len(self.coverage_gaps) > 0
        )

    @property
    def total_issues(self) -> int:
        """Total number of issues detected."""
        return (
            len(self.coverage_gaps) +
            len(self.unresolved_tensions) +
            len(self.sections_without_owner)
        )


@dataclass
class EmergentReport:
    """Complete emergent center observation report.

    Combines metrics, patterns, issues, and recommendations into a
    comprehensive report on the emergent properties of the system output.

    Attributes:
        metrics: Quantitative scores for coherence and consistency.
        patterns: Detected patterns including implicit style and clusters.
        issues: Coverage gaps and unresolved tensions.
        recommendations: Suggested improvements based on observations.
    """
    metrics: EmergentMetrics
    patterns: DetectedPatterns
    issues: EmergentIssues
    recommendations: List[str] = field(default_factory=list)

    @property
    def overall_health(self) -> str:
        """Compute an overall health assessment.

        Returns:
            "healthy": Good metrics, no critical issues
            "needs_attention": Some issues but metrics acceptable
            "unhealthy": Critical issues or poor metrics
        """
        if self.issues.has_critical_issues:
            return "unhealthy"

        if self.metrics.average_score < 0.5:
            return "unhealthy"

        if self.issues.total_issues > 3 or self.metrics.average_score < 0.7:
            return "needs_attention"

        return "healthy"

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format for serialization."""
        return {
            "metrics": {
                "coherence_score": self.metrics.coherence_score,
                "style_consistency": self.metrics.style_consistency,
                "interaction_consistency": self.metrics.interaction_consistency,
                "average_score": self.metrics.average_score,
            },
            "patterns": {
                "implicit_style": self.patterns.implicit_style,
                "natural_clusters": self.patterns.natural_clusters,
                "collaboration_frequency": {
                    f"{k[0]}-{k[1]}": v
                    for k, v in self.patterns.collaboration_frequency.items()
                },
            },
            "issues": {
                "coverage_gaps": self.issues.coverage_gaps,
                "unresolved_tensions": self.issues.unresolved_tensions,
                "sections_without_owner": self.issues.sections_without_owner,
                "escalation_count": self.issues.escalation_count,
            },
            "recommendations": self.recommendations,
            "overall_health": self.overall_health,
        }


class EmergentObserver:
    """Observer for emergent center properties.

    The EmergentObserver analyzes the spec, artifacts, merged output, and
    validation results to produce an EmergentReport. This report provides
    insights into:

    - How coherent the final output is
    - What patterns emerged naturally
    - What issues need attention
    - How to improve future runs

    Example usage:
        observer = EmergentObserver()
        report = observer.observe(
            spec=frozen_spec,
            artifacts=triad_artifacts,
            merged=merged_code,
            validation=validation_results
        )
        print(f"Overall health: {report.overall_health}")
    """

    def __init__(self) -> None:
        """Initialize the EmergentObserver."""
        self._escalation_keywords = ["arbiter", "escalat", "stuck", "deadlock"]
        self._style_indicators = {
            "minimal": ["simple", "clean", "minimal", "whitespace"],
            "dark-mode-first": ["dark", "bg-gray-9", "bg-slate-9", "bg-black"],
            "motion-forward": ["animation", "transition", "motion", "animate"],
            "content-dense": ["compact", "dense", "grid", "columns"],
            "colorful": ["gradient", "rainbow", "colorful", "vibrant"],
            "accessible": ["aria-", "role=", "sr-only", "focus:"],
        }

    def observe(
        self,
        spec: Any,
        artifacts: Dict[str, Any],
        merged: Any,
        validation: Any
    ) -> EmergentReport:
        """Analyze inputs and produce an emergent center report.

        Args:
            spec: The frozen spec with finalized section assignments.
            artifacts: Dictionary mapping triad IDs to their generated artifacts.
            merged: The integrated/merged output from all triads.
            validation: Results from the validation suite.

        Returns:
            EmergentReport containing metrics, patterns, issues, and recommendations.
        """
        # Compute all observation components
        metrics = self._compute_metrics(spec, artifacts, merged, validation)
        patterns = self._detect_patterns(spec, artifacts, merged)
        issues = self._identify_issues(spec, artifacts, validation)
        recommendations = self._generate_recommendations(
            metrics, patterns, issues, spec
        )

        return EmergentReport(
            metrics=metrics,
            patterns=patterns,
            issues=issues,
            recommendations=recommendations,
        )

    def _compute_metrics(
        self,
        spec: Any,
        artifacts: Dict[str, Any],
        merged: Any,
        validation: Any
    ) -> EmergentMetrics:
        """Compute quantitative metrics for the emergent center.

        This is a simplified implementation that can be enhanced with more
        sophisticated analysis techniques (embeddings, style analysis, etc.).

        Args:
            spec: The frozen spec.
            artifacts: Triad artifacts.
            merged: Merged output.
            validation: Validation results.

        Returns:
            EmergentMetrics with computed scores.
        """
        coherence = self._compute_coherence_score(spec, artifacts, merged)
        style = self._compute_style_consistency(artifacts, merged)
        interaction = self._compute_interaction_consistency(artifacts, merged)

        return EmergentMetrics(
            coherence_score=coherence,
            style_consistency=style,
            interaction_consistency=interaction,
        )

    def _compute_coherence_score(
        self,
        spec: Any,
        artifacts: Dict[str, Any],
        merged: Any
    ) -> float:
        """Compute how well sections fit together.

        Current implementation uses simple heuristics:
        - Checks coverage (all sections have owners)
        - Checks artifact completeness
        - Penalizes contested sections

        Can be enhanced with embedding similarity analysis.

        Returns:
            Float between 0.0 and 1.0.
        """
        score = 1.0

        # Check spec coverage
        if hasattr(spec, 'sections'):
            sections = spec.sections
            if sections:
                # Count sections with content
                sections_with_content = sum(
                    1 for s in sections.values()
                    if hasattr(s, 'content') and s.content is not None
                )
                coverage_ratio = sections_with_content / len(sections)
                score *= coverage_ratio

                # Penalize sections that remained contested (shouldn't happen after freeze)
                contested = sum(
                    1 for s in sections.values()
                    if hasattr(s, 'status') and str(s.status.value) == "contested"
                )
                if contested > 0:
                    score *= max(0.5, 1.0 - (contested * 0.1))

        # Check artifact coverage
        if artifacts:
            non_empty_artifacts = sum(
                1 for a in artifacts.values()
                if a and (isinstance(a, dict) and len(a) > 0 or isinstance(a, str) and len(a) > 0)
            )
            if len(artifacts) > 0:
                artifact_completeness = non_empty_artifacts / len(artifacts)
                score *= artifact_completeness

        return max(0.0, min(1.0, score))

    def _compute_style_consistency(
        self,
        artifacts: Dict[str, Any],
        merged: Any
    ) -> float:
        """Compute style consistency across artifacts.

        Current implementation checks for:
        - Presence of consistent style indicators
        - Mixed style signals (penalty)

        Can be enhanced with actual CSS/style analysis.

        Returns:
            Float between 0.0 and 1.0.
        """
        if not merged:
            return 0.5  # Neutral score if no merged content

        merged_str = str(merged).lower() if merged else ""

        if not merged_str:
            return 0.5

        # Count which style categories are present
        detected_styles: Set[str] = set()
        for style_name, indicators in self._style_indicators.items():
            for indicator in indicators:
                if indicator.lower() in merged_str:
                    detected_styles.add(style_name)
                    break

        # Consistency is higher when fewer distinct style categories are detected
        # (suggests unified approach) but penalize if nothing is detected
        if len(detected_styles) == 0:
            return 0.6  # No clear style, neutral-ish
        elif len(detected_styles) == 1:
            return 0.95  # Very consistent
        elif len(detected_styles) == 2:
            return 0.8  # Mostly consistent
        elif len(detected_styles) == 3:
            return 0.65  # Getting fragmented
        else:
            return max(0.4, 1.0 - (len(detected_styles) * 0.1))

    def _compute_interaction_consistency(
        self,
        artifacts: Dict[str, Any],
        merged: Any
    ) -> float:
        """Compute interaction pattern consistency.

        Current implementation looks for:
        - Consistent timing values
        - Consistent feedback patterns

        Can be enhanced with actual timing/pattern analysis.

        Returns:
            Float between 0.0 and 1.0.
        """
        if not merged:
            return 0.5

        merged_str = str(merged).lower() if merged else ""

        if not merged_str:
            return 0.5

        # Look for timing indicators
        timing_patterns = ["duration-", "delay-", "transition", "ease-"]
        timing_count = sum(1 for p in timing_patterns if p in merged_str)

        # Look for interaction feedback patterns
        feedback_patterns = ["hover:", "focus:", "active:", "click", "onclick"]
        feedback_count = sum(1 for p in feedback_patterns if p in merged_str)

        # Basic heuristic: having some interaction patterns is good
        # Having many diverse patterns could indicate inconsistency
        if timing_count == 0 and feedback_count == 0:
            return 0.5  # No interaction patterns detected
        elif timing_count <= 2 and feedback_count <= 3:
            return 0.85  # Reasonable amount of patterns
        elif timing_count <= 4 and feedback_count <= 6:
            return 0.75  # More patterns, still okay
        else:
            return 0.6  # Many patterns, might be inconsistent

    def _detect_patterns(
        self,
        spec: Any,
        artifacts: Dict[str, Any],
        merged: Any
    ) -> DetectedPatterns:
        """Detect emergent patterns in the output.

        Analyzes:
        - Implicit style that emerged
        - Natural clustering of triads

        Args:
            spec: The frozen spec.
            artifacts: Triad artifacts.
            merged: Merged output.

        Returns:
            DetectedPatterns with discovered patterns.
        """
        implicit_style = self._detect_implicit_style(merged)
        natural_clusters, collab_freq = self._detect_natural_clusters(spec, artifacts)

        return DetectedPatterns(
            implicit_style=implicit_style,
            natural_clusters=natural_clusters,
            collaboration_frequency=collab_freq,
        )

    def _detect_implicit_style(self, merged: Any) -> List[str]:
        """Detect implicit styles that emerged without being specified.

        Returns:
            List of detected style descriptors.
        """
        merged_str = str(merged).lower() if merged else ""
        detected: List[str] = []

        for style_name, indicators in self._style_indicators.items():
            indicator_count = sum(
                1 for ind in indicators if ind.lower() in merged_str
            )
            # Require at least 2 indicators to confirm a style
            if indicator_count >= 2:
                detected.append(style_name)

        return detected

    def _detect_natural_clusters(
        self,
        spec: Any,
        artifacts: Dict[str, Any]
    ) -> Tuple[List[List[str]], Dict[Tuple[str, str], int]]:
        """Detect which triads naturally clustered together.

        Triads cluster when they:
        - Had overlapping claims on sections
        - Were involved in negotiations together

        Returns:
            Tuple of (cluster groups, collaboration frequency dict)
        """
        collaboration_freq: Dict[Tuple[str, str], int] = defaultdict(int)

        if hasattr(spec, 'sections'):
            for section_name, section in spec.sections.items():
                # Look at section history to find triads that interacted
                if hasattr(section, 'history'):
                    triads_in_section: Set[str] = set()
                    for entry in section.history:
                        if 'by' in entry and entry['by'] != 'system':
                            triads_in_section.add(entry['by'])

                    # Triads that were in same section collaborated
                    triad_list = sorted(triads_in_section)
                    for i, t1 in enumerate(triad_list):
                        for t2 in triad_list[i + 1:]:
                            key = (t1, t2) if t1 < t2 else (t2, t1)
                            collaboration_freq[key] += 1

                # Also look at claims
                if hasattr(section, 'claims') and len(section.claims) > 1:
                    claims = sorted(section.claims)
                    for i, t1 in enumerate(claims):
                        for t2 in claims[i + 1:]:
                            key = (t1, t2) if t1 < t2 else (t2, t1)
                            collaboration_freq[key] += 1

        # Build clusters from high-frequency collaborations
        clusters = self._build_clusters_from_frequency(collaboration_freq)

        return clusters, dict(collaboration_freq)

    def _build_clusters_from_frequency(
        self,
        freq: Dict[Tuple[str, str], int]
    ) -> List[List[str]]:
        """Build clusters from collaboration frequency using simple grouping.

        Uses a simple threshold-based approach: triads that collaborated
        more than the average are considered clustered.
        """
        if not freq:
            return []

        # Find threshold (average frequency)
        avg_freq = sum(freq.values()) / len(freq) if freq else 0

        # Group triads that collaborated above threshold
        clusters: List[Set[str]] = []
        for (t1, t2), count in freq.items():
            if count > avg_freq:
                # Find existing cluster containing t1 or t2
                found_cluster = None
                for cluster in clusters:
                    if t1 in cluster or t2 in cluster:
                        found_cluster = cluster
                        break

                if found_cluster is not None:
                    found_cluster.add(t1)
                    found_cluster.add(t2)
                else:
                    clusters.append({t1, t2})

        # Merge overlapping clusters
        merged = True
        while merged:
            merged = False
            for i, c1 in enumerate(clusters):
                for j, c2 in enumerate(clusters[i + 1:], i + 1):
                    if c1 & c2:  # Overlap
                        clusters[i] = c1 | c2
                        clusters.pop(j)
                        merged = True
                        break
                if merged:
                    break

        return [sorted(c) for c in clusters if len(c) > 1]

    def _identify_issues(
        self,
        spec: Any,
        artifacts: Dict[str, Any],
        validation: Any
    ) -> EmergentIssues:
        """Identify coverage gaps and unresolved tensions.

        Args:
            spec: The frozen spec.
            artifacts: Triad artifacts.
            validation: Validation results.

        Returns:
            EmergentIssues with identified problems.
        """
        coverage_gaps: List[str] = []
        unresolved_tensions: List[str] = []
        sections_without_owner: List[str] = []
        escalation_count = 0

        # Analyze spec for coverage gaps
        if hasattr(spec, 'sections'):
            for section_name, section in spec.sections.items():
                # Check for sections without owners
                if not hasattr(section, 'owner') or section.owner is None:
                    sections_without_owner.append(section_name)

                # Check for sections without content
                if hasattr(section, 'content') and section.content is None:
                    if section_name not in sections_without_owner:
                        coverage_gaps.append(f"{section_name} (no content)")

                # Count escalations from history
                if hasattr(section, 'history'):
                    for entry in section.history:
                        action = entry.get('action', '')
                        if any(kw in action.lower() for kw in self._escalation_keywords):
                            escalation_count += 1

        # Check for common missing patterns (simple heuristic)
        common_gaps = ["error-states", "empty-states", "loading-transitions", "edge-cases"]
        if artifacts:
            all_content = str(artifacts).lower()
            for gap in common_gaps:
                gap_indicators = gap.replace("-", " ").split()
                if not any(ind in all_content for ind in gap_indicators):
                    if gap not in coverage_gaps:
                        coverage_gaps.append(gap)

        # Detect tensions from validation issues
        if validation and hasattr(validation, 'warnings'):
            for warning in getattr(validation, 'warnings', []):
                if 'conflict' in str(warning).lower() or 'tension' in str(warning).lower():
                    unresolved_tensions.append(str(warning))

        # Look for common tension patterns in artifacts
        tensions = self._detect_tensions_in_artifacts(artifacts)
        unresolved_tensions.extend(tensions)

        return EmergentIssues(
            coverage_gaps=coverage_gaps,
            unresolved_tensions=unresolved_tensions,
            sections_without_owner=sections_without_owner,
            escalation_count=escalation_count,
        )

    def _detect_tensions_in_artifacts(
        self,
        artifacts: Dict[str, Any]
    ) -> List[str]:
        """Detect potential tensions in artifact content.

        Simple heuristic-based detection of common conflicts.
        """
        tensions: List[str] = []

        if not artifacts:
            return tensions

        all_content = str(artifacts).lower()

        # Check for animation vs performance tension
        has_heavy_animation = any(
            kw in all_content
            for kw in ["animation", "animate", "keyframes"]
        )
        has_performance_focus = any(
            kw in all_content
            for kw in ["lazy", "defer", "optimize", "performance"]
        )
        if has_heavy_animation and has_performance_focus:
            tensions.append(
                "Potential tension: animation/motion vs performance optimization"
            )

        # Check for accessibility vs visual tension
        has_low_contrast = any(
            kw in all_content
            for kw in ["text-gray-4", "text-slate-4", "opacity-50", "subtle"]
        )
        has_accessibility_focus = any(
            kw in all_content
            for kw in ["aria-", "wcag", "accessible", "contrast"]
        )
        if has_low_contrast and has_accessibility_focus:
            tensions.append(
                "Potential tension: subtle visual styling vs accessibility contrast requirements"
            )

        return tensions

    def _generate_recommendations(
        self,
        metrics: EmergentMetrics,
        patterns: DetectedPatterns,
        issues: EmergentIssues,
        spec: Any
    ) -> List[str]:
        """Generate improvement recommendations based on observations.

        Args:
            metrics: Computed metrics.
            patterns: Detected patterns.
            issues: Identified issues.
            spec: The frozen spec.

        Returns:
            List of recommendation strings.
        """
        recommendations: List[str] = []

        # Recommendations based on metrics
        if metrics.coherence_score < 0.7:
            recommendations.append(
                "Low coherence score - consider reducing number of triads "
                "or increasing overlap in scope.reach to encourage more integration"
            )

        if metrics.style_consistency < 0.6:
            recommendations.append(
                "Low style consistency - consider adding a design-system triad "
                "with broad reach across visual sections"
            )

        if metrics.interaction_consistency < 0.6:
            recommendations.append(
                "Low interaction consistency - consider having motion and "
                "interaction triads share more scope overlap"
            )

        # Recommendations based on patterns
        most_collaborative = patterns.get_most_collaborative_pair()
        if most_collaborative:
            t1, t2 = most_collaborative
            freq = patterns.collaboration_frequency.get(most_collaborative, 0)
            if freq > 3:
                recommendations.append(
                    f"Triads '{t1}' and '{t2}' had {freq} interactions - "
                    "consider merging their scopes or creating a shared sub-triad"
                )

        # Recommendations based on issues
        if issues.escalation_count > 2:
            recommendations.append(
                f"High escalation count ({issues.escalation_count}) - "
                "consider adjusting triad scopes to reduce overlap, "
                "or increase negotiation rounds"
            )

        if issues.sections_without_owner:
            recommendations.append(
                f"Sections without owners: {', '.join(issues.sections_without_owner)} - "
                "ensure at least one triad has these in scope.primary or scope.reach"
            )

        if len(issues.coverage_gaps) > 2:
            recommendations.append(
                f"Multiple coverage gaps detected ({len(issues.coverage_gaps)}) - "
                "consider spawning additional triads or expanding existing scopes"
            )

        # Recommendations based on detected implicit style
        if patterns.implicit_style:
            styles = ", ".join(patterns.implicit_style)
            recommendations.append(
                f"Implicit style emerged: {styles} - "
                "consider making this explicit in future configurations "
                "via system_context for consistent results"
            )

        return recommendations
