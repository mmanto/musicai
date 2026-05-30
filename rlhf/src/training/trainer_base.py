"""Base trainer class for RLHF algorithms."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path

import torch

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration."""

    learning_rate: float = 1e-5
    batch_size: int = 8
    gradient_accumulation_steps: int = 4
    max_steps: int = 10000
    save_steps: int = 500
    eval_steps: int = 100
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    logging_steps: int = 10


class TrainerBase(ABC):
    """
    Base class for RLHF trainers.

    Implements common functionality for PPO, DPO, and other algorithms.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        reward_model: torch.nn.Module,
        config: Optional[TrainingConfig] = None,
    ):
        """
        Initialize trainer.

        Args:
            model: Policy model to train
            reward_model: Reward model for scoring
            config: Training configuration
        """
        self.settings = get_settings()
        self.model = model
        self.reward_model = reward_model
        self.config = config or TrainingConfig()

        self.global_step = 0
        self.optimizer = self._create_optimizer()
        self.scheduler = self._create_scheduler()

        logger.info(f"{self.__class__.__name__} initialized")

    def _create_optimizer(self) -> torch.optim.Optimizer:
        """Create optimizer."""
        return torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
        )

    def _create_scheduler(self) -> Optional[torch.optim.lr_scheduler._LRScheduler]:
        """Create learning rate scheduler."""
        if self.config.warmup_steps > 0:
            from torch.optim.lr_scheduler import LinearLR

            return LinearLR(
                self.optimizer,
                start_factor=0.1,
                total_iters=self.config.warmup_steps,
            )
        return None

    @abstractmethod
    def train_step(self, batch: Dict[str, Any]) -> Dict[str, float]:
        """
        Perform single training step.

        Args:
            batch: Training batch

        Returns:
            Dictionary of metrics
        """
        pass

    def train(
        self,
        train_dataloader: Any,
        eval_dataloader: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Main training loop.

        Args:
            train_dataloader: Training data
            eval_dataloader: Validation data

        Returns:
            Training statistics
        """
        logger.info("Starting training...")

        self.model.train()
        total_loss = 0.0
        num_batches = 0

        for step, batch in enumerate(train_dataloader):
            if step >= self.config.max_steps:
                break

            # Training step
            metrics = self.train_step(batch)
            total_loss += metrics.get("loss", 0.0)
            num_batches += 1

            self.global_step += 1

            # Logging
            if self.global_step % self.config.logging_steps == 0:
                avg_loss = total_loss / num_batches
                logger.info(
                    f"Step {self.global_step}/{self.config.max_steps}: "
                    f"loss={avg_loss:.4f}, lr={self.optimizer.param_groups[0]['lr']:.2e}"
                )
                total_loss = 0.0
                num_batches = 0

            # Evaluation
            if eval_dataloader and self.global_step % self.config.eval_steps == 0:
                eval_metrics = self.evaluate(eval_dataloader)
                logger.info(f"Eval metrics: {eval_metrics}")

            # Save checkpoint
            if self.global_step % self.config.save_steps == 0:
                self.save_checkpoint(f"checkpoint-{self.global_step}")

            # Update scheduler
            if self.scheduler:
                self.scheduler.step()

        logger.info("Training completed")

        return {
            "global_step": self.global_step,
            "final_loss": total_loss / max(num_batches, 1),
        }

    def evaluate(self, eval_dataloader: Any) -> Dict[str, float]:
        """
        Evaluate model.

        Args:
            eval_dataloader: Evaluation data

        Returns:
            Evaluation metrics
        """
        self.model.eval()

        total_loss = 0.0
        num_batches = 0

        with torch.no_grad():
            for batch in eval_dataloader:
                metrics = self.eval_step(batch)
                total_loss += metrics.get("loss", 0.0)
                num_batches += 1

        self.model.train()

        return {
            "eval_loss": total_loss / max(num_batches, 1),
        }

    def eval_step(self, batch: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluation step (default: same as train_step without gradients).

        Args:
            batch: Evaluation batch

        Returns:
            Metrics
        """
        return self.train_step(batch)

    def save_checkpoint(self, checkpoint_name: str):
        """
        Save model checkpoint.

        Args:
            checkpoint_name: Name of checkpoint
        """
        checkpoint_dir = Path(self.settings.CHECKPOINT_DIR) / checkpoint_name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "global_step": self.global_step,
            "config": self.config,
        }, checkpoint_dir / "trainer.pt")

        logger.info(f"Checkpoint saved: {checkpoint_dir}")

    def load_checkpoint(self, checkpoint_path: str):
        """
        Load model checkpoint.

        Args:
            checkpoint_path: Path to checkpoint
        """
        checkpoint = torch.load(checkpoint_path)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.global_step = checkpoint["global_step"]

        logger.info(f"Checkpoint loaded from: {checkpoint_path}")
