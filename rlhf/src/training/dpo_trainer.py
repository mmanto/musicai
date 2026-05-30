"""DPO (Direct Preference Optimization) Trainer."""

import logging
from typing import Dict, Any, Optional

import torch
import torch.nn.functional as F

from .trainer_base import TrainerBase, TrainingConfig
from ..config import get_settings

logger = logging.getLogger(__name__)


class DPOTrainer(TrainerBase):
    """
    Direct Preference Optimization (DPO) trainer.

    DPO directly optimizes the policy using preference data without
    requiring a separate reward model during training.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        reward_model: torch.nn.Module,
        reference_model: Optional[torch.nn.Module] = None,
        config: TrainingConfig = None,
        beta: float = 0.1,
        reference_free: bool = False,
    ):
        """
        Initialize DPO trainer.

        Args:
            model: Policy model to train
            reward_model: Reward model (for evaluation)
            reference_model: Reference policy (frozen)
            config: Training configuration
            beta: DPO regularization parameter
            reference_free: Whether to use reference-free DPO
        """
        super().__init__(model, reward_model, config)

        settings = get_settings()
        self.beta = beta or settings.DPO_BETA
        self.reference_free = reference_free or settings.DPO_REFERENCE_FREE

        # Reference model (frozen copy of initial policy)
        if reference_model is None and not reference_free:
            import copy
            self.reference_model = copy.deepcopy(model)
            self.reference_model.eval()
            for param in self.reference_model.parameters():
                param.requires_grad = False
        else:
            self.reference_model = reference_model

        logger.info(
            f"DPO trainer initialized with beta={self.beta}, "
            f"reference_free={self.reference_free}"
        )

    def train_step(self, batch: Dict[str, Any]) -> Dict[str, float]:
        """
        Perform DPO training step.

        Args:
            batch: Training batch containing:
                - states: Music states
                - preferred_actions: Preferred output tokens
                - rejected_actions: Rejected output tokens
                - preferred_log_probs: Optional precomputed log probs
                - rejected_log_probs: Optional precomputed log probs

        Returns:
            Dictionary of training metrics
        """
        states = batch["states"]
        preferred_actions = batch["preferred_actions"]
        rejected_actions = batch["rejected_actions"]

        # Get log probabilities from current policy
        preferred_logits = self.model(states, preferred_actions)["logits"]
        rejected_logits = self.model(states, rejected_actions)["logits"]

        preferred_log_probs = F.log_softmax(preferred_logits, dim=-1)
        rejected_log_probs = F.log_softmax(rejected_logits, dim=-1)

        # Gather action log probs
        preferred_action_log_probs = preferred_log_probs.gather(
            -1, preferred_actions.unsqueeze(-1)
        ).squeeze(-1).sum(dim=1)

        rejected_action_log_probs = rejected_log_probs.gather(
            -1, rejected_actions.unsqueeze(-1)
        ).squeeze(-1).sum(dim=1)

        # Reference model log probs (if not reference-free)
        if not self.reference_free and self.reference_model is not None:
            with torch.no_grad():
                ref_preferred_logits = self.reference_model(states, preferred_actions)["logits"]
                ref_rejected_logits = self.reference_model(states, rejected_actions)["logits"]

                ref_preferred_log_probs = F.log_softmax(ref_preferred_logits, dim=-1)
                ref_rejected_log_probs = F.log_softmax(ref_rejected_logits, dim=-1)

                ref_preferred_action_log_probs = ref_preferred_log_probs.gather(
                    -1, preferred_actions.unsqueeze(-1)
                ).squeeze(-1).sum(dim=1)

                ref_rejected_action_log_probs = ref_rejected_log_probs.gather(
                    -1, rejected_actions.unsqueeze(-1)
                ).squeeze(-1).sum(dim=1)
        else:
            ref_preferred_action_log_probs = 0.0
            ref_rejected_action_log_probs = 0.0

        # DPO loss
        pi_logratios = preferred_action_log_probs - rejected_action_log_probs
        ref_logratios = ref_preferred_action_log_probs - ref_rejected_action_log_probs

        logits = pi_logratios - ref_logratios
        loss = -F.logsigmoid(self.beta * logits).mean()

        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            self.model.parameters(),
            self.config.max_grad_norm
        )
        self.optimizer.step()

        # Metrics
        with torch.no_grad():
            accuracy = (logits > 0).float().mean()
            chosen_rewards = self.beta * preferred_action_log_probs.mean()
            rejected_rewards = self.beta * rejected_action_log_probs.mean()
            reward_margin = chosen_rewards - rejected_rewards

        metrics = {
            "loss": loss.item(),
            "accuracy": accuracy.item(),
            "chosen_rewards": chosen_rewards.item(),
            "rejected_rewards": rejected_rewards.item(),
            "reward_margin": reward_margin.item(),
        }

        return metrics

    def generate_from_prompts(
        self,
        prompts: torch.Tensor,
        max_length: int = 512,
        temperature: float = 1.0,
    ) -> Dict[str, torch.Tensor]:
        """
        Generate music from prompts using current policy.

        Args:
            prompts: Input prompts
            max_length: Maximum generation length
            temperature: Sampling temperature

        Returns:
            Generated sequences and metadata
        """
        self.model.eval()

        with torch.no_grad():
            outputs = []
            log_probs = []

            current = prompts

            for _ in range(max_length):
                logits = self.model(current)["logits"]
                logits = logits / temperature

                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs[:, -1, :], 1)

                log_prob = F.log_softmax(logits[:, -1, :], dim=-1).gather(
                    -1, next_token
                )

                outputs.append(next_token)
                log_probs.append(log_prob)

                current = torch.cat([current, next_token], dim=1)

        self.model.train()

        return {
            "sequences": torch.cat(outputs, dim=1),
            "log_probs": torch.cat(log_probs, dim=1),
        }
