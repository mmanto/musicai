"""Tests for REST API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_root(self, app_client):
        """Test root endpoint."""
        response = app_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["status"] == "running"

    @patch('src.api.rest.routes.music_analyzer')
    @patch('src.api.rest.routes.llm_client')
    def test_health_check_all_components(self, mock_llm, mock_analyzer, app_client):
        """Test health check with all components."""
        # Mock components
        mock_analyzer.__bool__ = lambda self: True
        mock_llm.check_health = AsyncMock(return_value=True)

        response = app_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data


class TestAnalysisEndpoints:
    """Tests for analysis endpoints."""

    @patch('src.api.rest.routes.music_analyzer')
    @patch('src.api.rest.routes.rules_engine')
    def test_analyze_music(
        self,
        mock_rules,
        mock_analyzer,
        app_client,
        sample_musicxml_base64
    ):
        """Test music analysis endpoint."""
        # Mock responses
        mock_analyzer.analyze_score.return_value = {
            "key": "C major",
            "harmony": {"chords": ["C", "G", "Am", "F"]}
        }
        mock_rules.validate.return_value = {
            "passed": True,
            "violations": []
        }

        response = app_client.post(
            "/api/v1/analyze",
            json={
                "music_data": sample_musicxml_base64,
                "format": "musicxml"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "key" in data or "harmony" in data

    @patch('src.api.rest.routes.hybrid_reasoner')
    def test_reason_about_music(
        self,
        mock_reasoner,
        app_client,
        sample_musicxml_base64
    ):
        """Test reasoning endpoint."""
        from src.hybrid.reasoner import HybridReasoningResult, ReasoningMode

        # Mock result
        mock_result = HybridReasoningResult(
            query="Test query",
            mode=ReasoningMode.HYBRID,
            symbolic_analysis={"key": "C major"},
            neural_reasoning=None,
            synthesis="Analysis result",
            confidence=0.9,
            recommendations=[],
            metadata={}
        )
        mock_reasoner.reason = AsyncMock(return_value=mock_result)

        response = app_client.post(
            "/api/v1/reason",
            json={
                "music_data": sample_musicxml_base64,
                "query": "What is the key?",
                "mode": "hybrid",
                "format": "musicxml"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "synthesis" in data

    @patch('src.api.rest.routes.hybrid_reasoner')
    def test_suggest_improvements(
        self,
        mock_reasoner,
        app_client,
        sample_musicxml_base64
    ):
        """Test improvement suggestions endpoint."""
        from src.hybrid.reasoner import HybridReasoningResult, ReasoningMode

        mock_result = HybridReasoningResult(
            query="Suggest improvements",
            mode=ReasoningMode.HYBRID,
            symbolic_analysis={},
            neural_reasoning=None,
            synthesis="Suggestions",
            confidence=0.85,
            recommendations=["Improve voice leading", "Add more variety"],
            metadata={}
        )
        mock_reasoner.analyze_and_suggest = AsyncMock(return_value=mock_result)

        response = app_client.post(
            "/api/v1/suggest-improvements",
            json={
                "music_data": sample_musicxml_base64,
                "focus_areas": ["harmony", "melody"],
                "format": "musicxml"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    @patch('src.api.rest.routes.hybrid_reasoner')
    def test_validate_theory(
        self,
        mock_reasoner,
        app_client,
        sample_musicxml_base64
    ):
        """Test theory validation endpoint."""
        from src.hybrid.reasoner import HybridReasoningResult, ReasoningMode

        mock_result = HybridReasoningResult(
            query="Validate theory",
            mode=ReasoningMode.SYMBOLIC_ONLY,
            symbolic_analysis={"violations": []},
            neural_reasoning=None,
            synthesis="No violations found",
            confidence=1.0,
            recommendations=[],
            metadata={}
        )
        mock_reasoner.validate_theory = AsyncMock(return_value=mock_result)

        response = app_client.post(
            "/api/v1/validate-theory",
            json={
                "music_data": sample_musicxml_base64,
                "rules": ["parallel_fifths", "voice_range"],
                "explain": True,
                "format": "musicxml"
            }
        )

        assert response.status_code == 200

    @patch('src.api.rest.routes.llm_client')
    def test_explain_concept(self, mock_llm, app_client):
        """Test concept explanation endpoint."""
        class MockResponse:
            content = "A cadence is a harmonic progression..."
            model = "llama3.1:8b"

        mock_llm.explain_concept = AsyncMock(return_value=MockResponse())
        mock_llm.__bool__ = lambda self: True

        response = app_client.post(
            "/api/v1/explain-concept",
            json={
                "concept": "cadence",
                "level": "intermediate"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data

    @patch('src.api.rest.routes.cot_engine')
    def test_chain_of_thought(self, mock_cot, app_client):
        """Test chain-of-thought endpoint."""
        from src.neural.chain_of_thought import ChainOfThoughtResult, ThoughtStep

        mock_result = ChainOfThoughtResult(
            query="Test",
            steps=[
                ThoughtStep(1, "Q1", "R1", "A1", 0.9)
            ],
            final_answer="Final",
            total_confidence=0.9,
            reasoning_path=["step1"]
        )
        mock_cot.reason = AsyncMock(return_value=mock_result)
        mock_cot.__bool__ = lambda self: True

        response = app_client.post(
            "/api/v1/chain-of-thought",
            json={
                "query": "Analyze this",
                "context": {},
                "num_steps": 3,
                "iterative": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "steps" in data


class TestRulesEndpoints:
    """Tests for rules management endpoints."""

    @patch('src.api.rest.routes.rules_engine')
    def test_list_rules(self, mock_engine, app_client):
        """Test listing rules."""
        mock_engine.list_rules.return_value = [
            {"name": "parallel_fifths", "category": "voice_leading", "enabled": True}
        ]

        response = app_client.get("/api/v1/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    @patch('src.api.rest.routes.rules_engine')
    def test_list_rules_by_category(self, mock_engine, app_client):
        """Test listing rules by category."""
        mock_engine.list_rules.return_value = [
            {"name": "parallel_fifths", "category": "voice_leading", "enabled": True}
        ]

        response = app_client.get("/api/v1/rules?category=voice_leading")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "voice_leading"

    @patch('src.api.rest.routes.rules_engine')
    def test_list_categories(self, mock_engine, app_client):
        """Test listing rule categories."""
        mock_engine.get_categories.return_value = ["voice_leading", "harmony"]

        response = app_client.get("/api/v1/rules/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    @patch('src.api.rest.routes.rules_engine')
    def test_enable_rule(self, mock_engine, app_client):
        """Test enabling a rule."""
        mock_engine.enable_rule.return_value = None

        response = app_client.post("/api/v1/rules/parallel_fifths/enable")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enabled"

    @patch('src.api.rest.routes.rules_engine')
    def test_disable_rule(self, mock_engine, app_client):
        """Test disabling a rule."""
        mock_engine.disable_rule.return_value = None

        response = app_client.post("/api/v1/rules/parallel_fifths/disable")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"


class TestErrorHandling:
    """Tests for API error handling."""

    @patch('src.api.rest.routes.music_analyzer')
    def test_analyze_with_invalid_data(self, mock_analyzer, app_client):
        """Test analysis with invalid data."""
        mock_analyzer.analyze_score.side_effect = Exception("Invalid data")

        response = app_client.post(
            "/api/v1/analyze",
            json={
                "music_data": "invalid_base64!!!",
                "format": "musicxml"
            }
        )

        assert response.status_code == 500

    def test_explain_concept_without_llm(self, app_client):
        """Test concept explanation when LLM is unavailable."""
        with patch('src.api.rest.routes.llm_client', None):
            response = app_client.post(
                "/api/v1/explain-concept",
                json={"concept": "cadence", "level": "basic"}
            )

            # Should handle gracefully
            assert response.status_code in [503, 500]
