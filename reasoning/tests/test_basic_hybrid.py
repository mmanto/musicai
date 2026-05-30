"""Basic functional tests for hybrid reasoning."""

import pytest


class TestHybridReasonerBasic:
    """Basic tests for HybridReasoner."""

    def test_reasoner_can_be_imported(self):
        """Test that HybridReasoner can be imported."""
        from src.hybrid.reasoner import HybridReasoner
        assert HybridReasoner is not None

    def test_reasoning_mode_enum(self):
        """Test ReasoningMode enum exists and has correct values."""
        from src.hybrid.reasoner import ReasoningMode

        assert hasattr(ReasoningMode, 'SYMBOLIC_ONLY')
        assert hasattr(ReasoningMode, 'NEURAL_ONLY')
        assert hasattr(ReasoningMode, 'HYBRID')
        assert hasattr(ReasoningMode, 'ADAPTIVE')

        assert ReasoningMode.SYMBOLIC_ONLY.value == 'symbolic_only'
        assert ReasoningMode.NEURAL_ONLY.value == 'neural_only'
        assert ReasoningMode.HYBRID.value == 'hybrid'
        assert ReasoningMode.ADAPTIVE.value == 'adaptive'

    def test_reasoning_result_dataclass(self):
        """Test HybridReasoningResult dataclass."""
        from src.hybrid.reasoner import HybridReasoningResult, ReasoningMode

        result = HybridReasoningResult(
            query="Test query",
            mode=ReasoningMode.SYMBOLIC_ONLY,
            symbolic_analysis={"key": "C major"},
            neural_reasoning=None,
            synthesis="Test synthesis",
            confidence=0.95,
            recommendations=["Practice scales"],
            metadata={"time": 1.5}
        )

        assert result.query == "Test query"
        assert result.mode == ReasoningMode.SYMBOLIC_ONLY
        assert result.confidence == 0.95
        assert len(result.recommendations) == 1
        assert result.metadata["time"] == 1.5


class TestNeuralComponentsBasic:
    """Basic tests for neural components."""

    def test_llm_client_can_be_imported(self):
        """Test that OllamaClient can be imported."""
        from src.neural.llm_client import OllamaClient
        assert OllamaClient is not None

    def test_llm_client_initialization(self):
        """Test LLM client initializes with config."""
        from src.neural.llm_client import OllamaClient

        client = OllamaClient()
        assert client is not None
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'model')

    def test_cot_engine_can_be_imported(self):
        """Test that ChainOfThought can be imported."""
        from src.neural.chain_of_thought import ChainOfThought
        assert ChainOfThought is not None

    def test_thought_step_dataclass(self):
        """Test ThoughtStep dataclass."""
        from src.neural.chain_of_thought import ThoughtStep

        step = ThoughtStep(
            step_number=1,
            question="What is the key?",
            reasoning="Based on the key signature...",
            answer="C major",
            confidence=0.9
        )

        assert step.step_number == 1
        assert step.question == "What is the key?"
        assert step.confidence == 0.9

    def test_cot_result_dataclass(self):
        """Test ChainOfThoughtResult dataclass."""
        from src.neural.chain_of_thought import ChainOfThoughtResult, ThoughtStep

        steps = [
            ThoughtStep(1, "Q1", "R1", "A1", 0.9),
            ThoughtStep(2, "Q2", "R2", "A2", 0.85)
        ]

        result = ChainOfThoughtResult(
            query="Analyze this piece",
            steps=steps,
            final_answer="The piece is in C major",
            total_confidence=0.875,
            reasoning_path=["key_analysis", "harmony"]
        )

        assert result.query == "Analyze this piece"
        assert len(result.steps) == 2
        assert result.total_confidence == 0.875
        assert "key_analysis" in result.reasoning_path


class TestMessagingBasic:
    """Basic tests for messaging components."""

    def test_publisher_can_be_imported(self):
        """Test that publisher can be imported."""
        from src.messaging.publisher import ReasoningPublisher
        assert ReasoningPublisher is not None

    def test_consumer_can_be_imported(self):
        """Test that consumer can be imported."""
        from src.messaging.consumer import ReasoningConsumer
        assert ReasoningConsumer is not None

    def test_publisher_initialization(self):
        """Test publisher initializes with config."""
        from src.messaging.publisher import ReasoningPublisher

        publisher = ReasoningPublisher()
        assert publisher is not None
        assert hasattr(publisher, 'settings')
        assert hasattr(publisher, 'connection')
        assert hasattr(publisher, 'channel')

    def test_consumer_initialization(self):
        """Test consumer initializes with config."""
        from src.messaging.consumer import ReasoningConsumer

        consumer = ReasoningConsumer()
        assert consumer is not None
        assert hasattr(consumer, 'settings')
        assert hasattr(consumer, 'connection')
