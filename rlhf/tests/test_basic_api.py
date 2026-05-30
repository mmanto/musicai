"""Basic tests for API components."""

import pytest


class TestAPISchemas:
    """Tests for API schemas."""

    def test_schemas_import(self):
        """Test schemas can be imported."""
        from src.api.rest import schemas
        assert schemas is not None

    def test_health_response_schema(self):
        """Test HealthResponse schema."""
        from src.api.rest.schemas import HealthResponse

        response = HealthResponse(
            status="healthy",
            service="rlhf",
            version="0.1.0",
            components={"test": True}
        )

        assert response.status == "healthy"
        assert response.service == "rlhf"

    def test_training_algorithm_enum(self):
        """Test TrainingAlgorithm enum."""
        from src.api.rest.schemas import TrainingAlgorithm

        assert TrainingAlgorithm.PPO.value == "ppo"
        assert TrainingAlgorithm.DPO.value == "dpo"
        assert TrainingAlgorithm.GRPO.value == "grpo"

    def test_feedback_type_enum(self):
        """Test FeedbackTypeEnum."""
        from src.api.rest.schemas import FeedbackTypeEnum

        assert FeedbackTypeEnum.PREFERENCE.value == "preference"
        assert FeedbackTypeEnum.RATING.value == "rating"
        assert FeedbackTypeEnum.RANKING.value == "ranking"
        assert FeedbackTypeEnum.BINARY.value == "binary"


class TestServiceHealth:
    """Tests for service health."""

    def test_main_module_import(self):
        """Test main module can be imported."""
        import src.main
        assert src.main is not None

    def test_app_creation(self):
        """Test FastAPI app can be created."""
        from src.main import create_app

        app = create_app()
        assert app is not None
        assert app.title == "MusicAI RLHF Service"

    def test_app_has_routes(self):
        """Test app has expected routes."""
        from src.main import create_app

        app = create_app()
        routes = [route.path for route in app.routes]

        assert "/" in routes
        assert "/api/v1/health" in routes


class TestModuleStructure:
    """Tests for module structure."""

    def test_reward_module_import(self):
        """Test reward module imports."""
        from src import reward

        assert hasattr(reward, 'RewardModel')
        assert hasattr(reward, 'FeedbackCollector')

    def test_training_module_import(self):
        """Test training module imports."""
        from src import training

        assert hasattr(training, 'PPOTrainer')
        assert hasattr(training, 'DPOTrainer')
        assert hasattr(training, 'TrainerBase')

    def test_messaging_module_import(self):
        """Test messaging module imports."""
        from src.messaging import publisher, consumer

        assert hasattr(publisher, 'RLHFPublisher')
        assert hasattr(consumer, 'RLHFConsumer')

    def test_api_module_import(self):
        """Test API module imports."""
        from src import api

        assert hasattr(api, 'router')
