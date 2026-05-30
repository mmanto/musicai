"""Pytest configuration and fixtures for reasoning tests."""

import pytest
import os
import base64
from typing import Generator
from unittest.mock import Mock, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Set test environment
os.environ["SERVICE_NAME"] = "reasoning"
os.environ["REST_PORT"] = "8004"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.1:8b"
os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["RABBITMQ_PORT"] = "5672"


@pytest.fixture
def sample_musicxml():
    """Sample MusicXML data for testing."""
    musicxml = """<?xml version="1.0" encoding="UTF-8"?>
    <score-partwise version="3.1">
      <part-list>
        <score-part id="P1">
          <part-name>Piano</part-name>
        </score-part>
      </part-list>
      <part id="P1">
        <measure number="1">
          <attributes>
            <divisions>1</divisions>
            <key><fifths>0</fifths></key>
            <time><beats>4</beats><beat-type>4</beat-type></time>
            <clef><sign>G</sign><line>2</line></clef>
          </attributes>
          <note>
            <pitch><step>C</step><octave>4</octave></pitch>
            <duration>4</duration>
            <type>whole</type>
          </note>
        </measure>
      </part>
    </score-partwise>
    """
    return musicxml.encode('utf-8')


@pytest.fixture
def sample_musicxml_base64(sample_musicxml):
    """Base64-encoded sample MusicXML."""
    return base64.b64encode(sample_musicxml).decode('utf-8')


@pytest.fixture
def mock_music21_analyzer():
    """Mock Music21Analyzer for testing."""
    mock_analyzer = Mock()
    mock_analyzer.analyze_score = Mock(return_value={
        "key": "C major",
        "time_signature": "4/4",
        "tempo": 120,
        "harmony": {
            "chords": ["C", "G", "Am", "F"],
            "key_confidence": 0.95
        },
        "melody": {
            "range": "C4-C5",
            "contour": "ascending"
        }
    })
    return mock_analyzer


@pytest.fixture
def mock_rules_engine():
    """Mock RulesEngine for testing."""
    mock_engine = Mock()
    mock_engine.validate = Mock(return_value={
        "passed": True,
        "violations": [],
        "warnings": []
    })
    mock_engine.list_rules = Mock(return_value=[
        {"name": "parallel_fifths", "category": "voice_leading", "enabled": True}
    ])
    mock_engine.get_categories = Mock(return_value=["voice_leading", "harmony", "melody"])
    return mock_engine


@pytest.fixture
def mock_llm_client():
    """Mock OllamaClient for testing."""
    mock_client = AsyncMock()

    # Mock response class
    class MockLLMResponse:
        def __init__(self, content="Mocked LLM response", model="llama3.1:8b"):
            self.content = content
            self.model = model

    mock_client.generate = AsyncMock(return_value=MockLLMResponse())
    mock_client.check_health = AsyncMock(return_value=True)
    mock_client.explain_concept = AsyncMock(return_value=MockLLMResponse(
        "A cadence is a harmonic progression that creates a sense of resolution."
    ))
    return mock_client


@pytest.fixture
def mock_cot_engine(mock_llm_client):
    """Mock Chain-of-Thought engine for testing."""
    from src.neural.chain_of_thought import ThoughtStep, ChainOfThoughtResult

    mock_engine = AsyncMock()

    # Create sample result
    steps = [
        ThoughtStep(
            step_number=1,
            question="What is the key?",
            reasoning="Looking at the key signature...",
            answer="C major",
            confidence=0.95
        )
    ]

    result = ChainOfThoughtResult(
        query="Analyze this piece",
        steps=steps,
        final_answer="The piece is in C major with simple harmony",
        total_confidence=0.95,
        reasoning_path=["key_analysis", "harmonic_analysis"]
    )

    mock_engine.reason = AsyncMock(return_value=result)
    mock_engine.iterative_refinement = AsyncMock(return_value=result)

    return mock_engine


@pytest.fixture
def mock_hybrid_reasoner():
    """Mock HybridReasoner for testing."""
    from src.hybrid.reasoner import HybridReasoningResult, ReasoningMode

    mock_reasoner = AsyncMock()

    result = HybridReasoningResult(
        query="Test query",
        mode=ReasoningMode.HYBRID,
        symbolic_analysis={"key": "C major"},
        neural_reasoning=None,
        synthesis="Combined analysis result",
        confidence=0.9,
        recommendations=["Practice more", "Work on voice leading"],
        metadata={"processing_time": 1.5}
    )

    mock_reasoner.reason = AsyncMock(return_value=result)
    mock_reasoner.analyze_and_suggest = AsyncMock(return_value=result)
    mock_reasoner.validate_theory = AsyncMock(return_value=result)
    mock_reasoner.compare_pieces = AsyncMock(return_value=result)

    return mock_reasoner


@pytest.fixture
def app_client():
    """FastAPI test client."""
    from src.main import create_app

    app = create_app()

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_rabbitmq_connection():
    """Mock RabbitMQ connection."""
    mock_conn = AsyncMock()
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()

    mock_conn.channel = AsyncMock(return_value=mock_channel)
    mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
    mock_channel.declare_exchange = AsyncMock()

    return mock_conn
