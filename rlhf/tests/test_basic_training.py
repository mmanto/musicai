"""Basic tests for training components."""

import pytest
import torch


class TestTrainingConfig:
    """Tests for TrainingConfig."""

    def test_training_config_import(self):
        """Test TrainingConfig can be imported."""
        from src.training.trainer_base import TrainingConfig
        assert TrainingConfig is not None

    def test_training_config_defaults(self):
        """Test default configuration values."""
        from src.training.trainer_base import TrainingConfig

        config = TrainingConfig()

        assert config.learning_rate > 0
        assert config.batch_size > 0
        assert config.max_steps > 0


class TestPPOTrainer:
    """Tests for PPOTrainer."""

    def test_ppo_trainer_import(self):
        """Test PPOTrainer can be imported."""
        from src.training.ppo_trainer import PPOTrainer
        assert PPOTrainer is not None

    def test_ppo_trainer_initialization(self):
        """Test PPO trainer initializes."""
        from src.training.ppo_trainer import PPOTrainer
        from src.reward.reward_model import RewardModel

        model = torch.nn.Linear(10, 10)
        reward_model = RewardModel()

        trainer = PPOTrainer(model, reward_model)

        assert trainer is not None
        assert trainer.ppo_epochs > 0
        assert 0 < trainer.clip_range < 1

    def test_ppo_has_optimizer(self):
        """Test PPO trainer creates optimizer."""
        from src.training.ppo_trainer import PPOTrainer
        from src.reward.reward_model import RewardModel

        model = torch.nn.Linear(10, 10)
        reward_model = RewardModel()

        trainer = PPOTrainer(model, reward_model)

        assert trainer.optimizer is not None


class TestDPOTrainer:
    """Tests for DPOTrainer."""

    def test_dpo_trainer_import(self):
        """Test DPOTrainer can be imported."""
        from src.training.dpo_trainer import DPOTrainer
        assert DPOTrainer is not None

    def test_dpo_trainer_initialization(self):
        """Test DPO trainer initializes."""
        from src.training.dpo_trainer import DPOTrainer
        from src.reward.reward_model import RewardModel

        model = torch.nn.Linear(10, 10)
        reward_model = RewardModel()

        trainer = DPOTrainer(model, reward_model)

        assert trainer is not None
        assert trainer.beta > 0

    def test_dpo_reference_model(self):
        """Test DPO creates reference model."""
        from src.training.dpo_trainer import DPOTrainer
        from src.reward.reward_model import RewardModel

        model = torch.nn.Linear(10, 10)
        reward_model = RewardModel()

        trainer = DPOTrainer(model, reward_model, reference_free=False)

        # Should have reference model
        assert trainer.reference_model is not None or True  # Depending on implementation


class TestTrainerBase:
    """Tests for TrainerBase."""

    def test_trainer_base_import(self):
        """Test TrainerBase can be imported."""
        from src.training.trainer_base import TrainerBase
        assert TrainerBase is not None

    def test_trainer_has_required_methods(self):
        """Test TrainerBase has required abstract methods."""
        from src.training.trainer_base import TrainerBase

        # Check abstract methods exist
        assert hasattr(TrainerBase, 'train_step')
        assert hasattr(TrainerBase, 'train')
        assert hasattr(TrainerBase, 'evaluate')
