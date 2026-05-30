"""Hybrid reasoner combining symbolic and neural reasoning."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..symbolic.music21_analyzer import Music21Analyzer
from ..symbolic.rules_engine import RulesEngine, RuleSeverity
from ..neural.llm_client import OllamaClient
from ..neural.chain_of_thought import ChainOfThought, ChainOfThoughtResult

logger = logging.getLogger(__name__)


class ReasoningMode(Enum):
    """Reasoning modes."""
    SYMBOLIC_ONLY = "symbolic_only"
    NEURAL_ONLY = "neural_only"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


@dataclass
class HybridReasoningResult:
    """Result from hybrid reasoning."""
    query: str
    mode: ReasoningMode
    symbolic_analysis: Optional[Dict[str, Any]] = None
    neural_reasoning: Optional[ChainOfThoughtResult] = None
    synthesis: Optional[str] = None
    confidence: float = 0.0
    recommendations: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}


class HybridReasoner:
    """
    Combines symbolic music analysis with neural reasoning.

    The hybrid reasoner:
    1. Uses music21 for precise symbolic analysis
    2. Uses rules engine for theory validation
    3. Uses LLM for interpretive reasoning
    4. Synthesizes findings from both approaches
    """

    def __init__(
        self,
        music_analyzer: Optional[Music21Analyzer] = None,
        rules_engine: Optional[RulesEngine] = None,
        llm_client: Optional[OllamaClient] = None,
        cot_engine: Optional[ChainOfThought] = None
    ):
        """
        Initialize hybrid reasoner.

        Args:
            music_analyzer: Symbolic music analyzer
            rules_engine: Rules validation engine
            llm_client: LLM client for neural reasoning
            cot_engine: Chain-of-thought engine
        """
        self.music_analyzer = music_analyzer or Music21Analyzer()
        self.rules_engine = rules_engine or RulesEngine()
        self.llm_client = llm_client
        self.cot_engine = cot_engine

        logger.info("Hybrid reasoner initialized")

    async def reason(
        self,
        music_data: bytes,
        query: str,
        mode: ReasoningMode = ReasoningMode.HYBRID,
        format: str = "musicxml"
    ) -> HybridReasoningResult:
        """
        Perform hybrid reasoning on musical data.

        Args:
            music_data: Musical content as bytes
            query: User query or reasoning task
            mode: Reasoning mode to use
            format: Music data format

        Returns:
            Hybrid reasoning result
        """
        logger.info(f"Starting hybrid reasoning in {mode.value} mode")

        # Determine actual mode if adaptive
        if mode == ReasoningMode.ADAPTIVE:
            mode = self._select_mode(query)
            logger.info(f"Adaptive mode selected: {mode.value}")

        # Perform symbolic analysis if needed
        symbolic_analysis = None
        if mode in [ReasoningMode.SYMBOLIC_ONLY, ReasoningMode.HYBRID]:
            symbolic_analysis = await self._perform_symbolic_analysis(
                music_data,
                format
            )

        # Perform neural reasoning if needed
        neural_reasoning = None
        if mode in [ReasoningMode.NEURAL_ONLY, ReasoningMode.HYBRID]:
            if not self.llm_client or not self.cot_engine:
                logger.warning("Neural reasoning requested but LLM not available")
                mode = ReasoningMode.SYMBOLIC_ONLY
            else:
                context = symbolic_analysis if symbolic_analysis else {}
                neural_reasoning = await self._perform_neural_reasoning(
                    query,
                    context
                )

        # Synthesize results
        synthesis = None
        confidence = 0.0
        recommendations = []

        if mode == ReasoningMode.HYBRID:
            synthesis, confidence, recommendations = await self._synthesize_results(
                query,
                symbolic_analysis,
                neural_reasoning
            )
        elif mode == ReasoningMode.SYMBOLIC_ONLY:
            synthesis, confidence, recommendations = self._synthesize_symbolic(
                query,
                symbolic_analysis
            )
        elif mode == ReasoningMode.NEURAL_ONLY:
            synthesis = neural_reasoning.final_answer if neural_reasoning else ""
            confidence = neural_reasoning.total_confidence if neural_reasoning else 0.0

        result = HybridReasoningResult(
            query=query,
            mode=mode,
            symbolic_analysis=symbolic_analysis,
            neural_reasoning=neural_reasoning,
            synthesis=synthesis,
            confidence=confidence,
            recommendations=recommendations,
            metadata={
                "format": format,
                "has_symbolic": symbolic_analysis is not None,
                "has_neural": neural_reasoning is not None
            }
        )

        logger.info(f"Hybrid reasoning completed with confidence {confidence:.2f}")

        return result

    def _select_mode(self, query: str) -> ReasoningMode:
        """
        Adaptively select reasoning mode based on query.

        Args:
            query: User query

        Returns:
            Selected reasoning mode
        """
        query_lower = query.lower()

        # Keywords that suggest symbolic analysis
        symbolic_keywords = [
            "key", "chord", "interval", "scale", "voice leading",
            "counterpoint", "harmony", "cadence", "modulation",
            "parallel", "tritone", "analyze", "identify"
        ]

        # Keywords that suggest neural reasoning
        neural_keywords = [
            "why", "how", "explain", "suggest", "improve", "creative",
            "interpret", "feel", "mood", "character", "style",
            "compare", "similar", "like", "different"
        ]

        symbolic_score = sum(1 for kw in symbolic_keywords if kw in query_lower)
        neural_score = sum(1 for kw in neural_keywords if kw in query_lower)

        # Decide based on scores
        if symbolic_score > neural_score * 2:
            return ReasoningMode.SYMBOLIC_ONLY
        elif neural_score > symbolic_score * 2:
            return ReasoningMode.NEURAL_ONLY
        else:
            return ReasoningMode.HYBRID

    async def _perform_symbolic_analysis(
        self,
        music_data: bytes,
        format: str
    ) -> Dict[str, Any]:
        """Perform symbolic music analysis."""
        logger.debug("Performing symbolic analysis")

        try:
            # Analyze with music21
            analysis = self.music_analyzer.analyze_score(music_data, format)

            # Validate with rules engine
            validation = self.rules_engine.validate(
                analysis,
                min_severity=RuleSeverity.INFO
            )

            # Combine results
            analysis["validation"] = validation

            return analysis

        except Exception as e:
            logger.error(f"Error in symbolic analysis: {e}")
            return {"error": str(e)}

    async def _perform_neural_reasoning(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> ChainOfThoughtResult:
        """Perform neural reasoning with Chain-of-Thought."""
        logger.debug("Performing neural reasoning")

        try:
            # Use chain-of-thought for complex reasoning
            result = await self.cot_engine.reason(query, context)

            return result

        except Exception as e:
            logger.error(f"Error in neural reasoning: {e}")
            raise

    async def _synthesize_results(
        self,
        query: str,
        symbolic_analysis: Dict[str, Any],
        neural_reasoning: ChainOfThoughtResult
    ) -> tuple[str, float, List[str]]:
        """
        Synthesize symbolic and neural results.

        Returns:
            Tuple of (synthesis, confidence, recommendations)
        """
        logger.debug("Synthesizing hybrid results")

        # Extract key symbolic findings
        symbolic_findings = self._extract_symbolic_findings(symbolic_analysis)

        # Get neural insights
        neural_insights = neural_reasoning.final_answer

        # Generate synthesis
        synthesis_parts = [
            "# Hybrid Analysis Results",
            "",
            "## Symbolic Analysis Findings",
            symbolic_findings,
            "",
            "## Neural Reasoning Insights",
            neural_insights,
            ""
        ]

        # Generate recommendations based on both
        recommendations = []

        # From validation results
        validation = symbolic_analysis.get("validation", {})
        if validation.get("total_violations", 0) > 0:
            high_severity = validation.get("severity_counts", {}).get("high", 0)
            if high_severity > 0:
                recommendations.append(
                    f"Address {high_severity} high-severity music theory violations"
                )

        # From quality score
        quality_score = validation.get("quality_score", 100)
        if quality_score < 70:
            recommendations.append(
                "Consider revising voice leading and harmonic progression"
            )

        # Add neural recommendations if available
        if "suggest" in query.lower() or "improve" in query.lower():
            recommendations.append(
                "See neural reasoning insights for creative suggestions"
            )

        synthesis = "\n".join(synthesis_parts)

        # Compute combined confidence
        symbolic_confidence = quality_score / 100.0
        neural_confidence = neural_reasoning.total_confidence
        combined_confidence = (symbolic_confidence + neural_confidence) / 2

        return synthesis, combined_confidence, recommendations

    def _synthesize_symbolic(
        self,
        query: str,
        symbolic_analysis: Dict[str, Any]
    ) -> tuple[str, float, List[str]]:
        """Synthesize symbolic-only results."""
        findings = self._extract_symbolic_findings(symbolic_analysis)

        validation = symbolic_analysis.get("validation", {})
        quality_score = validation.get("quality_score", 100)

        recommendations = []
        violations = validation.get("violations", [])[:5]  # Top 5
        for v in violations:
            if v.get("suggestion"):
                recommendations.append(v["suggestion"])

        return findings, quality_score / 100.0, recommendations

    def _extract_symbolic_findings(self, analysis: Dict[str, Any]) -> str:
        """Extract key findings from symbolic analysis."""
        findings = []

        # Metadata
        if "metadata" in analysis:
            meta = analysis["metadata"]
            findings.append(f"**Title:** {meta.get('title', 'Unknown')}")
            findings.append(f"**Key:** {meta.get('key_signature', 'Unknown')}")
            findings.append(f"**Time:** {meta.get('time_signature', 'Unknown')}")
            findings.append("")

        # Key analysis
        if "key_analysis" in analysis:
            key = analysis["key_analysis"]
            findings.append(f"**Main Key:** {key.get('main_key')} ({key.get('mode')})")
            if key.get("modulations"):
                findings.append(f"**Modulations:** {len(key['modulations'])} detected")
            findings.append("")

        # Harmonic analysis
        if "harmonic_analysis" in analysis:
            harmony = analysis["harmonic_analysis"]
            findings.append(f"**Chords:** {harmony.get('total_chords', 0)} total")
            if harmony.get("progressions"):
                progs = harmony["progressions"][:3]
                findings.append(f"**Common Progressions:** {len(progs)} found")
            findings.append("")

        # Validation results
        if "validation" in analysis:
            val = analysis["validation"]
            findings.append(f"**Quality Score:** {val.get('quality_score', 0)}/100")
            findings.append(f"**Violations:** {val.get('total_violations', 0)}")

            severity_counts = val.get("severity_counts", {})
            if any(severity_counts.values()):
                findings.append("**By Severity:**")
                for severity in ["critical", "high", "medium", "low"]:
                    count = severity_counts.get(severity, 0)
                    if count > 0:
                        findings.append(f"  - {severity.capitalize()}: {count}")

        return "\n".join(findings)

    async def analyze_and_suggest(
        self,
        music_data: bytes,
        focus_areas: Optional[List[str]] = None,
        format: str = "musicxml"
    ) -> HybridReasoningResult:
        """
        Analyze music and suggest improvements.

        Args:
            music_data: Musical content
            focus_areas: Areas to focus on (harmony, melody, etc.)
            format: Music data format

        Returns:
            Hybrid reasoning result with suggestions
        """
        # First, perform full analysis
        analysis_result = await self.reason(
            music_data=music_data,
            query="Analyze this musical piece",
            mode=ReasoningMode.SYMBOLIC_ONLY,
            format=format
        )

        # Then, use neural reasoning for suggestions
        if self.llm_client:
            suggestions = await self.llm_client.suggest_improvements(
                analysis=analysis_result.symbolic_analysis,
                focus_areas=focus_areas
            )

            analysis_result.synthesis = suggestions.content
            analysis_result.mode = ReasoningMode.HYBRID

        return analysis_result

    async def validate_theory(
        self,
        music_data: bytes,
        rules: Optional[List[str]] = None,
        explain: bool = True,
        format: str = "musicxml"
    ) -> HybridReasoningResult:
        """
        Validate music theory rules with optional explanations.

        Args:
            music_data: Musical content
            rules: Specific rules to validate
            explain: Whether to explain violations
            format: Music data format

        Returns:
            Hybrid reasoning result with validation
        """
        # Perform symbolic validation
        symbolic_analysis = await self._perform_symbolic_analysis(music_data, format)

        # If explanation requested, use neural reasoning
        neural_reasoning = None
        if explain and self.llm_client and self.cot_engine:
            # Find violations
            validation = symbolic_analysis.get("validation", {})
            violations = validation.get("violations", [])

            if violations:
                # Ask LLM to explain top violations
                top_violations = violations[:5]
                query = f"Explain these music theory violations and how to fix them: {top_violations}"

                neural_reasoning = await self._perform_neural_reasoning(
                    query,
                    symbolic_analysis
                )

        # Synthesize
        mode = ReasoningMode.HYBRID if neural_reasoning else ReasoningMode.SYMBOLIC_ONLY

        synthesis, confidence, recommendations = (
            await self._synthesize_results(
                "Validate music theory",
                symbolic_analysis,
                neural_reasoning
            )
            if neural_reasoning
            else self._synthesize_symbolic(
                "Validate music theory",
                symbolic_analysis
            )
        )

        return HybridReasoningResult(
            query="Validate music theory rules",
            mode=mode,
            symbolic_analysis=symbolic_analysis,
            neural_reasoning=neural_reasoning,
            synthesis=synthesis,
            confidence=confidence,
            recommendations=recommendations
        )

    async def compare_pieces(
        self,
        music_data1: bytes,
        music_data2: bytes,
        aspects: Optional[List[str]] = None,
        format1: str = "musicxml",
        format2: str = "musicxml"
    ) -> HybridReasoningResult:
        """
        Compare two musical pieces.

        Args:
            music_data1: First piece
            music_data2: Second piece
            aspects: Aspects to compare
            format1: Format of first piece
            format2: Format of second piece

        Returns:
            Hybrid reasoning result with comparison
        """
        # Analyze both pieces
        analysis1 = await self._perform_symbolic_analysis(music_data1, format1)
        analysis2 = await self._perform_symbolic_analysis(music_data2, format2)

        # Use neural reasoning for comparison
        if self.llm_client:
            comparison = await self.llm_client.compare_pieces(
                analysis1=analysis1,
                analysis2=analysis2,
                aspects=aspects
            )

            return HybridReasoningResult(
                query="Compare musical pieces",
                mode=ReasoningMode.HYBRID,
                symbolic_analysis={
                    "piece1": analysis1,
                    "piece2": analysis2
                },
                synthesis=comparison.content,
                confidence=0.8,
                metadata={
                    "format1": format1,
                    "format2": format2
                }
            )
        else:
            # Symbolic comparison only
            comparison = self._compare_symbolic(analysis1, analysis2)

            return HybridReasoningResult(
                query="Compare musical pieces",
                mode=ReasoningMode.SYMBOLIC_ONLY,
                symbolic_analysis={
                    "piece1": analysis1,
                    "piece2": analysis2
                },
                synthesis=comparison,
                confidence=0.7
            )

    def _compare_symbolic(
        self,
        analysis1: Dict[str, Any],
        analysis2: Dict[str, Any]
    ) -> str:
        """Compare two pieces using symbolic analysis only."""
        comparison = ["# Symbolic Comparison", ""]

        # Compare keys
        key1 = analysis1.get("key_analysis", {}).get("main_key", "Unknown")
        key2 = analysis2.get("key_analysis", {}).get("main_key", "Unknown")
        comparison.append(f"**Keys:** {key1} vs {key2}")

        # Compare chord counts
        chords1 = analysis1.get("harmonic_analysis", {}).get("total_chords", 0)
        chords2 = analysis2.get("harmonic_analysis", {}).get("total_chords", 0)
        comparison.append(f"**Harmonic Complexity:** {chords1} vs {chords2} chords")

        # Compare quality scores
        quality1 = analysis1.get("validation", {}).get("quality_score", 0)
        quality2 = analysis2.get("validation", {}).get("quality_score", 0)
        comparison.append(f"**Quality Scores:** {quality1} vs {quality2}")

        return "\n".join(comparison)

    def export_result(
        self,
        result: HybridReasoningResult,
        format: str = "markdown"
    ) -> str:
        """
        Export reasoning result.

        Args:
            result: Hybrid reasoning result
            format: Export format (markdown, json, text)

        Returns:
            Formatted export
        """
        if format == "json":
            import json
            return json.dumps({
                "query": result.query,
                "mode": result.mode.value,
                "confidence": result.confidence,
                "synthesis": result.synthesis,
                "recommendations": result.recommendations,
                "has_symbolic": result.symbolic_analysis is not None,
                "has_neural": result.neural_reasoning is not None
            }, indent=2)

        elif format == "markdown":
            md = [
                f"# Hybrid Reasoning Result",
                "",
                f"**Query:** {result.query}",
                f"**Mode:** {result.mode.value}",
                f"**Confidence:** {result.confidence:.2f}",
                "",
                "## Synthesis",
                result.synthesis or "No synthesis available",
                ""
            ]

            if result.recommendations:
                md.extend([
                    "## Recommendations",
                    ""
                ])
                for i, rec in enumerate(result.recommendations, 1):
                    md.append(f"{i}. {rec}")

            return "\n".join(md)

        else:  # text
            return result.synthesis or "No result available"
