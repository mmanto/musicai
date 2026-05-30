"""Basic integration tests for the reasoning service.

These tests verify the service is running and responding correctly.
"""

import pytest


class TestServiceHealth:
    """Test service health and availability."""

    def test_service_is_importable(self):
        """Test that main service can be imported."""
        import src.main
        assert src.main is not None

    def test_app_creation(self):
        """Test FastAPI app can be created."""
        from src.main import create_app

        app = create_app()
        assert app is not None
        assert app.title == "MusicAI Reasoning Service"

    def test_app_has_routes(self):
        """Test app has expected routes."""
        from src.main import create_app

        app = create_app()
        routes = [route.path for route in app.routes]

        assert "/" in routes
        assert "/api/v1/health" in routes
        assert "/api/v1/rules" in routes


class TestAPISchemas:
    """Test API request/response schemas."""

    def test_schemas_can_be_imported(self):
        """Test that schemas can be imported."""
        from src.api.rest import schemas
        assert schemas is not None

    def test_health_response_schema(self):
        """Test HealthResponse schema."""
        from src.api.rest.schemas import HealthResponse

        response = HealthResponse(
            status="healthy",
            service="reasoning",
            version="0.1.0",
            components={"test": True}
        )

        assert response.status == "healthy"
        assert response.service == "reasoning"

    def test_analyze_request_schema(self):
        """Test AnalyzeRequest schema."""
        from src.api.rest.schemas import AnalyzeRequest, MusicFormat

        request = AnalyzeRequest(
            music_data="YmFzZTY0ZGF0YQ==",
            format=MusicFormat.MUSICXML
        )

        assert request.music_data == "YmFzZTY0ZGF0YQ=="
        assert request.format == MusicFormat.MUSICXML

    def test_reasoning_mode_enum(self):
        """Test ReasoningModeEnum."""
        from src.api.rest.schemas import ReasoningModeEnum

        assert ReasoningModeEnum.SYMBOLIC_ONLY.value == 'symbolic_only'
        assert ReasoningModeEnum.NEURAL_ONLY.value == 'neural_only'
        assert ReasoningModeEnum.HYBRID.value == 'hybrid'
        assert ReasoningModeEnum.ADAPTIVE.value == 'adaptive'


class TestModuleStructure:
    """Test that all modules have correct structure."""

    def test_symbolic_module_structure(self):
        """Test symbolic module has expected components."""
        from src import symbolic

        assert hasattr(symbolic, 'Music21Analyzer')
        assert hasattr(symbolic, 'RulesEngine')

    def test_neural_module_structure(self):
        """Test neural module has expected components."""
        from src import neural

        assert hasattr(neural, 'OllamaClient')
        assert hasattr(neural, 'ChainOfThought')

    def test_hybrid_module_structure(self):
        """Test hybrid module has expected components."""
        from src import hybrid

        assert hasattr(hybrid, 'HybridReasoner')

    def test_api_module_structure(self):
        """Test API module has expected components."""
        from src.api import rest

        assert hasattr(rest, 'router')
        assert hasattr(rest, 'schemas')

    def test_messaging_module_structure(self):
        """Test messaging module has expected components."""
        from src.messaging import publisher, consumer

        assert hasattr(publisher, 'ReasoningPublisher')
        assert hasattr(consumer, 'ReasoningConsumer')


class TestDataModels:
    """Test data models and their validation."""

    def test_rule_model(self):
        """Test Rule dataclass."""
        from src.symbolic.rules_engine import Rule, RuleSeverity

        rule = Rule(
            name="test_rule",
            description="A test rule",
            category="test",
            severity=RuleSeverity.MEDIUM,
            enabled=True,
            validator=lambda x: True
        )

        assert rule.name == "test_rule"
        assert rule.severity == RuleSeverity.MEDIUM
        assert rule.enabled is True
        assert callable(rule.validator)

    def test_validation_result_model(self):
        """Test validation result dictionary format."""
        from src.symbolic.rules_engine import RulesEngine, RuleSeverity

        engine = RulesEngine()

        # Validate with empty analysis should return a result dict
        result = engine.validate({}, min_severity=RuleSeverity.INFO)

        assert isinstance(result, dict)
        assert 'passed' in result or 'violations' in result
