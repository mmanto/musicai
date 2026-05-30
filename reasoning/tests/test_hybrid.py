"""Tests for hybrid reasoning."""

import pytest
from unittest.mock import Mock, AsyncMock


class TestHybridReasoner:
    """Tests for HybridReasoner."""

    @pytest.fixture
    def hybrid_reasoner(
        self,
        mock_music21_analyzer,
        mock_rules_engine,
        mock_llm_client,
        mock_cot_engine
    ):
        """Create hybrid reasoner instance."""
        from src.hybrid.reasoner import HybridReasoner

        return HybridReasoner(
            music_analyzer=mock_music21_analyzer,
            rules_engine=mock_rules_engine,
            llm_client=mock_llm_client,
            cot_engine=mock_cot_engine
        )

    def test_reasoner_initialization(self, hybrid_reasoner):
        """Test reasoner initializes correctly."""
        assert hybrid_reasoner is not None
        assert hasattr(hybrid_reasoner, 'music_analyzer')
        assert hasattr(hybrid_reasoner, 'rules_engine')
        assert hasattr(hybrid_reasoner, 'llm_client')
        assert hasattr(hybrid_reasoner, 'cot_engine')

    @pytest.mark.asyncio
    async def test_reason_symbolic_mode(self, mock_hybrid_reasoner, sample_musicxml):
        """Test reasoning in symbolic-only mode."""
        from src.hybrid.reasoner import ReasoningMode

        result = await mock_hybrid_reasoner.reason(
            music_data=sample_musicxml,
            query="What is the key?",
            mode=ReasoningMode.SYMBOLIC_ONLY,
            format='musicxml'
        )

        assert result is not None
        assert hasattr(result, 'symbolic_analysis')
        assert hasattr(result, 'mode')

    @pytest.mark.asyncio
    async def test_reason_neural_mode(self, mock_hybrid_reasoner, sample_musicxml):
        """Test reasoning in neural-only mode."""
        from src.hybrid.reasoner import ReasoningMode

        result = await mock_hybrid_reasoner.reason(
            music_data=sample_musicxml,
            query="Why does this sound melancholic?",
            mode=ReasoningMode.NEURAL_ONLY,
            format='musicxml'
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_reason_hybrid_mode(self, mock_hybrid_reasoner, sample_musicxml):
        """Test reasoning in hybrid mode."""
        from src.hybrid.reasoner import ReasoningMode

        result = await mock_hybrid_reasoner.reason(
            music_data=sample_musicxml,
            query="Analyze this piece comprehensively",
            mode=ReasoningMode.HYBRID,
            format='musicxml'
        )

        assert result is not None
        assert hasattr(result, 'synthesis')
        assert hasattr(result, 'confidence')

    @pytest.mark.asyncio
    async def test_analyze_and_suggest(self, mock_hybrid_reasoner, sample_musicxml):
        """Test analysis with suggestions."""
        result = await mock_hybrid_reasoner.analyze_and_suggest(
            music_data=sample_musicxml,
            focus_areas=['harmony', 'melody'],
            format='musicxml'
        )

        assert result is not None
        assert hasattr(result, 'recommendations')
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_validate_theory(self, mock_hybrid_reasoner, sample_musicxml):
        """Test theory validation."""
        result = await mock_hybrid_reasoner.validate_theory(
            music_data=sample_musicxml,
            rules=['parallel_fifths', 'voice_range'],
            explain=True,
            format='musicxml'
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_compare_pieces(self, mock_hybrid_reasoner, sample_musicxml):
        """Test piece comparison."""
        result = await mock_hybrid_reasoner.compare_pieces(
            music_data1=sample_musicxml,
            music_data2=sample_musicxml,
            aspects=['harmony', 'melody'],
            format1='musicxml',
            format2='musicxml'
        )

        assert result is not None

    def test_reasoning_mode_enum(self):
        """Test ReasoningMode enum."""
        from src.hybrid.reasoner import ReasoningMode

        assert ReasoningMode.SYMBOLIC_ONLY.value == 'symbolic_only'
        assert ReasoningMode.NEURAL_ONLY.value == 'neural_only'
        assert ReasoningMode.HYBRID.value == 'hybrid'
        assert ReasoningMode.ADAPTIVE.value == 'adaptive'

    def test_reasoning_result_structure(self):
        """Test HybridReasoningResult structure."""
        from src.hybrid.reasoner import HybridReasoningResult, ReasoningMode

        result = HybridReasoningResult(
            query="Test",
            mode=ReasoningMode.HYBRID,
            symbolic_analysis={"key": "C major"},
            neural_reasoning=None,
            synthesis="Combined analysis",
            confidence=0.9,
            recommendations=["Practice more"],
            metadata={"time": 1.5}
        )

        assert result.query == "Test"
        assert result.mode == ReasoningMode.HYBRID
        assert result.confidence == 0.9
        assert len(result.recommendations) == 1


class TestReasoningModes:
    """Tests for different reasoning modes."""

    @pytest.mark.asyncio
    async def test_adaptive_mode_selection(self, mock_hybrid_reasoner, sample_musicxml):
        """Test adaptive mode automatically selects best approach."""
        from src.hybrid.reasoner import ReasoningMode

        # Query that should use symbolic
        result1 = await mock_hybrid_reasoner.reason(
            music_data=sample_musicxml,
            query="What is the time signature?",
            mode=ReasoningMode.ADAPTIVE,
            format='musicxml'
        )
        assert result1 is not None

        # Query that should use neural
        result2 = await mock_hybrid_reasoner.reason(
            music_data=sample_musicxml,
            query="What emotions does this evoke?",
            mode=ReasoningMode.ADAPTIVE,
            format='musicxml'
        )
        assert result2 is not None
