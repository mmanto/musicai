"""Basic tests for reward model components."""

import pytest
import torch


class TestRewardModel:
    """Tests for RewardModel."""

    def test_reward_model_import(self):
        """Test RewardModel can be imported."""
        from src.reward.reward_model import RewardModel
        assert RewardModel is not None

    def test_reward_type_enum(self):
        """Test RewardType enum."""
        from src.reward.reward_model import RewardType

        assert RewardType.PAIRWISE.value == "pairwise"
        assert RewardType.POINTWISE.value == "pointwise"
        assert RewardType.RANKING.value == "ranking"

    def test_reward_model_initialization(self):
        """Test reward model initializes."""
        from src.reward.reward_model import RewardModel, RewardType

        model = RewardModel(reward_type=RewardType.PAIRWISE)
        assert model is not None
        assert model.reward_type == RewardType.PAIRWISE

    def test_reward_model_forward(self):
        """Test forward pass."""
        from src.reward.reward_model import RewardModel

        model = RewardModel()
        embeddings = torch.randn(2, 768)

        with torch.no_grad():
            output = model.forward(embeddings)

        assert "score" in output
        assert output["score"].shape[0] == 2

    def test_evaluate_pointwise(self):
        """Test pointwise evaluation."""
        from src.reward.reward_model import RewardModel

        model = RewardModel()
        embedding = torch.randn(1, 768)

        result = model.evaluate_pointwise(embedding)

        assert result.score is not None
        assert 0 <= result.confidence <= 1
        assert isinstance(result.breakdown, dict)

    def test_evaluate_pairwise(self):
        """Test pairwise comparison."""
        from src.reward.reward_model import RewardModel

        model = RewardModel()
        emb_a = torch.randn(1, 768)
        emb_b = torch.randn(1, 768)

        with torch.no_grad():
            preference = model.evaluate_pairwise(emb_a, emb_b)

        assert isinstance(preference.item(), float)

    def test_evaluate_ranking(self):
        """Test ranking evaluation."""
        from src.reward.reward_model import RewardModel

        model = RewardModel()
        embeddings = [torch.randn(1, 768) for _ in range(3)]

        rankings = model.evaluate_ranking(embeddings)

        assert len(rankings) == 3
        assert set(rankings) == {0, 1, 2}


class TestFeedbackCollector:
    """Tests for FeedbackCollector."""

    def test_feedback_collector_import(self):
        """Test FeedbackCollector can be imported."""
        from src.reward.feedback_collector import FeedbackCollector
        assert FeedbackCollector is not None

    def test_feedback_collector_initialization(self):
        """Test collector initializes."""
        from src.reward.feedback_collector import FeedbackCollector

        collector = FeedbackCollector()
        assert collector is not None
        assert len(collector.feedbacks) == 0

    def test_add_preference_feedback(self):
        """Test adding preference feedback."""
        from src.reward.feedback_collector import FeedbackCollector

        collector = FeedbackCollector()

        feedback = collector.add_preference(
            feedback_id="fb_1",
            music_id="music_1",
            user_id="user_1",
            preferred_id="output_a",
            rejected_id="output_b",
        )

        assert feedback.feedback_id == "fb_1"
        assert len(collector.feedbacks) == 1

    def test_add_rating_feedback(self):
        """Test adding rating feedback."""
        from src.reward.feedback_collector import FeedbackCollector

        collector = FeedbackCollector()

        feedback = collector.add_rating(
            feedback_id="fb_2",
            music_id="music_1",
            user_id="user_1",
            rating=4.5,
            max_rating=5.0,
        )

        assert feedback.rating == 4.5
        assert len(collector.feedbacks) == 1

    def test_get_feedback_statistics(self):
        """Test getting feedback statistics."""
        from src.reward.feedback_collector import FeedbackCollector

        collector = FeedbackCollector()

        collector.add_preference("fb_1", "m_1", "u_1", "a", "b")
        collector.add_rating("fb_2", "m_2", "u_2", 4.0)

        stats = collector.get_statistics()

        assert stats["total"] == 2
        assert stats["unique_users"] == 2
        assert stats["unique_music"] == 2

    def test_get_preference_pairs(self):
        """Test getting preference pairs."""
        from src.reward.feedback_collector import FeedbackCollector

        collector = FeedbackCollector()

        collector.add_preference("fb_1", "m_1", "u_1", "a", "b", confidence=0.9)
        collector.add_preference("fb_2", "m_2", "u_2", "c", "d", confidence=0.8)

        pairs = collector.get_preference_pairs()

        assert len(pairs) == 2
        assert pairs[0] == ("a", "b", 0.9)
        assert pairs[1] == ("c", "d", 0.8)


class TestConfiguration:
    """Tests for configuration."""

    def test_settings_import(self):
        """Test settings can be imported."""
        from src.config import Settings, get_settings
        assert Settings is not None
        assert get_settings is not None

    def test_settings_defaults(self):
        """Test settings have correct defaults."""
        from src.config import get_settings

        settings = get_settings()

        assert settings.SERVICE_NAME == "rlhf"
        assert settings.REST_PORT == 8005
        assert settings.GRPC_PORT == 50055
        assert settings.TRAINING_ALGORITHM in ["ppo", "dpo", "grpo"]
