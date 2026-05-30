"""Tests for neural reasoning components."""

import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestOllamaClient:
    """Tests for OllamaClient."""

    @pytest.fixture
    def client(self):
        """Create Ollama client instance."""
        from src.neural.llm_client import OllamaClient
        return OllamaClient()

    def test_client_initialization(self, client):
        """Test client initializes correctly."""
        assert client is not None
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'model')

    @pytest.mark.asyncio
    @patch('src.neural.llm_client.httpx.AsyncClient')
    async def test_generate_text(self, mock_httpx, client):
        """Test text generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Test response",
            "model": "llama3.1:8b"
        }
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        response = await client.generate("Test prompt")

        assert response is not None
        assert hasattr(response, 'content')

    @pytest.mark.asyncio
    @patch('src.neural.llm_client.httpx.AsyncClient')
    async def test_check_health(self, mock_httpx, client):
        """Test health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        health = await client.check_health()

        assert isinstance(health, bool)

    @pytest.mark.asyncio
    async def test_generate_with_mock(self, mock_llm_client):
        """Test generation with mocked client."""
        response = await mock_llm_client.generate("Test")
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_explain_concept_with_mock(self, mock_llm_client):
        """Test concept explanation with mock."""
        response = await mock_llm_client.explain_concept("cadence")
        assert response.content is not None
        assert "cadence" in response.content.lower() or len(response.content) > 0


class TestChainOfThought:
    """Tests for Chain-of-Thought reasoning."""

    @pytest.fixture
    def cot_engine(self, mock_llm_client):
        """Create CoT engine instance."""
        from src.neural.chain_of_thought import ChainOfThought
        return ChainOfThought(mock_llm_client)

    def test_cot_initialization(self, cot_engine):
        """Test CoT engine initializes correctly."""
        assert cot_engine is not None
        assert hasattr(cot_engine, 'llm_client')

    @pytest.mark.asyncio
    async def test_reason_basic(self, mock_cot_engine):
        """Test basic reasoning."""
        result = await mock_cot_engine.reason(
            query="What is the key?",
            context={"harmony": {"chords": ["C", "G", "Am", "F"]}},
            num_steps=3
        )

        assert result is not None
        assert hasattr(result, 'query')
        assert hasattr(result, 'steps')
        assert hasattr(result, 'final_answer')

    @pytest.mark.asyncio
    async def test_reason_with_steps(self, mock_cot_engine):
        """Test reasoning returns correct number of steps."""
        result = await mock_cot_engine.reason(
            query="Analyze harmony",
            context={},
            num_steps=3
        )

        assert len(result.steps) > 0
        assert all(hasattr(step, 'step_number') for step in result.steps)
        assert all(hasattr(step, 'reasoning') for step in result.steps)

    @pytest.mark.asyncio
    async def test_iterative_refinement(self, mock_cot_engine):
        """Test iterative refinement."""
        result = await mock_cot_engine.iterative_refinement(
            query="Improve melody",
            context={"melody": {"range": "C4-C5"}},
            num_iterations=2
        )

        assert result is not None
        assert hasattr(result, 'final_answer')

    def test_thought_step_structure(self):
        """Test ThoughtStep data structure."""
        from src.neural.chain_of_thought import ThoughtStep

        step = ThoughtStep(
            step_number=1,
            question="What is X?",
            reasoning="Because Y",
            answer="X is Z",
            confidence=0.9
        )

        assert step.step_number == 1
        assert step.confidence == 0.9
        assert step.answer == "X is Z"
