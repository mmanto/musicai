"""Rules-based reasoning engine for music theory validation."""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RuleSeverity(Enum):
    """Severity levels for rule violations."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Rule:
    """Definition of a music theory rule."""
    name: str
    description: str
    category: str
    severity: RuleSeverity
    validator: Callable[[Dict[str, Any]], List[Dict[str, Any]]]
    enabled: bool = True


@dataclass
class RuleViolation:
    """A violation of a music theory rule."""
    rule_name: str
    severity: RuleSeverity
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RulesEngine:
    """Engine for applying music theory rules."""

    def __init__(self):
        """Initialize the rules engine."""
        self.rules: Dict[str, Rule] = {}
        self._register_default_rules()
        logger.info("Rules engine initialized with %d rules", len(self.rules))

    def _register_default_rules(self) -> None:
        """Register default music theory rules."""

        # Voice leading rules
        self.register_rule(Rule(
            name="parallel_fifths",
            description="Avoid parallel perfect fifths between voices",
            category="voice_leading",
            severity=RuleSeverity.HIGH,
            validator=self._check_parallel_fifths
        ))

        self.register_rule(Rule(
            name="parallel_octaves",
            description="Avoid parallel perfect octaves between voices",
            category="voice_leading",
            severity=RuleSeverity.HIGH,
            validator=self._check_parallel_octaves
        ))

        self.register_rule(Rule(
            name="voice_crossing",
            description="Voices should not cross each other",
            category="voice_leading",
            severity=RuleSeverity.MEDIUM,
            validator=self._check_voice_crossing
        ))

        self.register_rule(Rule(
            name="voice_overlap",
            description="Voices should not overlap",
            category="voice_leading",
            severity=RuleSeverity.LOW,
            validator=self._check_voice_overlap
        ))

        self.register_rule(Rule(
            name="large_leaps",
            description="Avoid large melodic leaps (more than an octave)",
            category="melody",
            severity=RuleSeverity.MEDIUM,
            validator=self._check_large_leaps
        ))

        # Harmonic rules
        self.register_rule(Rule(
            name="tritone_resolution",
            description="Tritones should resolve properly",
            category="harmony",
            severity=RuleSeverity.MEDIUM,
            validator=self._check_tritone_resolution
        ))

        self.register_rule(Rule(
            name="leading_tone_resolution",
            description="Leading tone should resolve to tonic",
            category="harmony",
            severity=RuleSeverity.MEDIUM,
            validator=self._check_leading_tone_resolution
        ))

        self.register_rule(Rule(
            name="doubling",
            description="Doubling rules for four-part harmony",
            category="harmony",
            severity=RuleSeverity.LOW,
            validator=self._check_doubling
        ))

        # Melodic rules
        self.register_rule(Rule(
            name="melodic_direction",
            description="Large leaps should be followed by stepwise motion in opposite direction",
            category="melody",
            severity=RuleSeverity.LOW,
            validator=self._check_melodic_direction
        ))

        self.register_rule(Rule(
            name="consecutive_leaps",
            description="Avoid too many consecutive leaps in same direction",
            category="melody",
            severity=RuleSeverity.MEDIUM,
            validator=self._check_consecutive_leaps
        ))

        # Range rules
        self.register_rule(Rule(
            name="voice_range",
            description="Voices should stay within their typical ranges",
            category="range",
            severity=RuleSeverity.MEDIUM,
            validator=self._check_voice_range
        ))

        # Counterpoint rules
        self.register_rule(Rule(
            name="contrary_motion",
            description="Prefer contrary or oblique motion over similar motion",
            category="counterpoint",
            severity=RuleSeverity.INFO,
            validator=self._check_motion_types
        ))

        self.register_rule(Rule(
            name="dissonance_treatment",
            description="Dissonances should be prepared and resolved",
            category="counterpoint",
            severity=RuleSeverity.HIGH,
            validator=self._check_dissonance_treatment
        ))

    def register_rule(self, rule: Rule) -> None:
        """Register a new rule."""
        self.rules[rule.name] = rule
        logger.debug(f"Registered rule: {rule.name}")

    def enable_rule(self, rule_name: str) -> None:
        """Enable a rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            logger.debug(f"Enabled rule: {rule_name}")

    def disable_rule(self, rule_name: str) -> None:
        """Disable a rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            logger.debug(f"Disabled rule: {rule_name}")

    def validate(
        self,
        analysis: Dict[str, Any],
        categories: Optional[List[str]] = None,
        min_severity: RuleSeverity = RuleSeverity.INFO
    ) -> Dict[str, Any]:
        """
        Validate analysis against registered rules.

        Args:
            analysis: Analysis data from Music21Analyzer
            categories: Filter by rule categories
            min_severity: Minimum severity level to report

        Returns:
            Validation results with violations
        """
        violations = []

        for rule in self.rules.values():
            # Skip disabled rules
            if not rule.enabled:
                continue

            # Filter by category
            if categories and rule.category not in categories:
                continue

            # Filter by severity
            if rule.severity.value < min_severity.value:
                continue

            try:
                # Apply rule validator
                rule_violations = rule.validator(analysis)

                # Convert to RuleViolation objects
                for violation in rule_violations:
                    violations.append(RuleViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=violation.get("message", rule.description),
                        location=violation.get("location"),
                        suggestion=violation.get("suggestion"),
                        metadata=violation.get("metadata")
                    ))

            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {e}")

        # Compute summary statistics
        severity_counts = {
            "critical": sum(1 for v in violations if v.severity == RuleSeverity.CRITICAL),
            "high": sum(1 for v in violations if v.severity == RuleSeverity.HIGH),
            "medium": sum(1 for v in violations if v.severity == RuleSeverity.MEDIUM),
            "low": sum(1 for v in violations if v.severity == RuleSeverity.LOW),
            "info": sum(1 for v in violations if v.severity == RuleSeverity.INFO)
        }

        # Compute quality score
        quality_score = self._compute_quality_score(severity_counts)

        return {
            "total_violations": len(violations),
            "severity_counts": severity_counts,
            "quality_score": quality_score,
            "violations": [
                {
                    "rule": v.rule_name,
                    "severity": v.severity.value,
                    "message": v.message,
                    "location": v.location,
                    "suggestion": v.suggestion,
                    "metadata": v.metadata
                }
                for v in violations
            ],
            "rules_checked": len([r for r in self.rules.values() if r.enabled])
        }

    def _compute_quality_score(self, severity_counts: Dict[str, int]) -> float:
        """
        Compute quality score based on violations.

        Returns score from 0 to 100.
        """
        # Weighted penalties for different severities
        penalties = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 2,
            "info": 0.5
        }

        total_penalty = sum(
            severity_counts.get(severity, 0) * penalty
            for severity, penalty in penalties.items()
        )

        # Start at 100 and subtract penalties
        score = max(0, 100 - total_penalty)

        return round(score, 2)

    # Rule validators
    def _check_parallel_fifths(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for parallel perfect fifths."""
        violations = []

        voice_leading = analysis.get("voice_leading", {})
        all_violations = voice_leading.get("violations", [])

        for violation in all_violations:
            if violation.get("type") == "parallel_P5":
                violations.append({
                    "message": "Parallel perfect fifths detected",
                    "location": violation.get("location"),
                    "suggestion": "Use contrary or oblique motion to avoid parallel fifths",
                    "metadata": violation
                })

        return violations

    def _check_parallel_octaves(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for parallel perfect octaves."""
        violations = []

        voice_leading = analysis.get("voice_leading", {})
        all_violations = voice_leading.get("violations", [])

        for violation in all_violations:
            if violation.get("type") == "parallel_P8":
                violations.append({
                    "message": "Parallel perfect octaves detected",
                    "location": violation.get("location"),
                    "suggestion": "Use contrary or oblique motion to avoid parallel octaves",
                    "metadata": violation
                })

        return violations

    def _check_voice_crossing(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for voice crossing."""
        violations = []

        voice_leading = analysis.get("voice_leading", {})
        all_violations = voice_leading.get("violations", [])

        for violation in all_violations:
            if violation.get("type") == "voice_crossing":
                violations.append({
                    "message": "Voice crossing detected",
                    "location": violation.get("location"),
                    "suggestion": "Keep voices in their proper ranges",
                    "metadata": violation
                })

        return violations

    def _check_voice_overlap(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for voice overlap."""
        violations = []

        # This would need more detailed analysis data
        # Placeholder implementation

        return violations

    def _check_large_leaps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for excessively large melodic leaps."""
        violations = []

        melodic = analysis.get("melodic_analysis", {})
        intervals = melodic.get("intervals", {})

        # Check for leaps larger than an octave
        if isinstance(intervals, dict) and "leaps" in intervals:
            leap_count = intervals.get("leaps", 0)
            total_intervals = intervals.get("total", 1)

            if leap_count / total_intervals > 0.3:  # More than 30% leaps
                violations.append({
                    "message": f"Excessive melodic leaps detected ({leap_count} leaps)",
                    "suggestion": "Use more stepwise motion for smoother melodies"
                })

        return violations

    def _check_tritone_resolution(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check tritone resolutions."""
        violations = []

        # Would need chord progression analysis
        # Placeholder implementation

        return violations

    def _check_leading_tone_resolution(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check leading tone resolutions."""
        violations = []

        # Would need scale degree analysis
        # Placeholder implementation

        return violations

    def _check_doubling(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check doubling in four-part harmony."""
        violations = []

        # Would need voicing analysis
        # Placeholder implementation

        return violations

    def _check_melodic_direction(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check melodic direction after leaps."""
        violations = []

        # Would need detailed melodic analysis
        # Placeholder implementation

        return violations

    def _check_consecutive_leaps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for too many consecutive leaps."""
        violations = []

        melodic = analysis.get("melodic_analysis", {})

        # This would need interval sequence analysis
        # Placeholder implementation

        return violations

    def _check_voice_range(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check voice ranges."""
        violations = []

        voice_leading = analysis.get("voice_leading", {})
        all_violations = voice_leading.get("violations", [])

        for violation in all_violations:
            if violation.get("type") == "out_of_range":
                violations.append({
                    "message": f"Voice out of typical range",
                    "location": violation.get("location"),
                    "suggestion": f"Keep {violation.get('voice', 'voice')} within comfortable range",
                    "metadata": violation
                })

        return violations

    def _check_motion_types(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check types of motion between voices."""
        violations = []

        # Would need motion analysis
        # This is informational, not a violation per se

        return violations

    def _check_dissonance_treatment(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check dissonance preparation and resolution."""
        violations = []

        # Would need detailed harmonic analysis
        # Placeholder implementation

        return violations

    def get_rule_info(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific rule."""
        rule = self.rules.get(rule_name)
        if not rule:
            return None

        return {
            "name": rule.name,
            "description": rule.description,
            "category": rule.category,
            "severity": rule.severity.value,
            "enabled": rule.enabled
        }

    def list_rules(
        self,
        category: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all registered rules.

        Args:
            category: Filter by category
            enabled_only: Only show enabled rules

        Returns:
            List of rule information
        """
        rules_list = []

        for rule in self.rules.values():
            # Apply filters
            if category and rule.category != category:
                continue
            if enabled_only and not rule.enabled:
                continue

            rules_list.append({
                "name": rule.name,
                "description": rule.description,
                "category": rule.category,
                "severity": rule.severity.value,
                "enabled": rule.enabled
            })

        return rules_list

    def get_categories(self) -> List[str]:
        """Get list of rule categories."""
        categories = set(rule.category for rule in self.rules.values())
        return sorted(list(categories))

    def export_configuration(self) -> Dict[str, Any]:
        """Export current rules configuration."""
        return {
            "rules": {
                name: {
                    "enabled": rule.enabled,
                    "severity": rule.severity.value
                }
                for name, rule in self.rules.items()
            }
        }

    def import_configuration(self, config: Dict[str, Any]) -> None:
        """Import rules configuration."""
        rules_config = config.get("rules", {})

        for rule_name, rule_config in rules_config.items():
            if rule_name in self.rules:
                self.rules[rule_name].enabled = rule_config.get("enabled", True)

                # Update severity if provided
                severity_str = rule_config.get("severity")
                if severity_str:
                    try:
                        self.rules[rule_name].severity = RuleSeverity(severity_str)
                    except ValueError:
                        logger.warning(f"Invalid severity for rule {rule_name}: {severity_str}")

        logger.info("Imported configuration for %d rules", len(rules_config))
