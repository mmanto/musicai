"""PPO (Proximal Policy Optimization) Trainer."""

import logging
from typing import Dict, Any

import torch
import torch.nn.functional as F

from .trainer_base import TrainerBase, TrainingConfig
from ..config import get_settings

logger = logging.getLogger(__name__)


class PPOTrainer(TrainerBase):
    """
    Proximal Policy Optimization (PPO) trainer for music generation.

    PPO is a policy gradient method that uses a clipped surrogate objective
    to prevent large policy updates.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        reward_model: torch.nn.Module,
        config: TrainingConfig = None,
        ppo_epochs: int = 4,
        clip_range: float = 0.2,
        value_coef: float = 0.1,
        entropy_coef: float = 0.01,
    ):
        """
        Initialize PPO trainer.

        Args:
            model: Policy model
            reward_model: Reward model
            config: Training configuration
            ppo_epochs: Number of PPO optimization epochs per batch
            clip_range: PPO clipping parameter
            value_coef: Value function loss coefficient
            entropy_coef: Entropy bonus coefficient
        """
        super().__init__(model, reward_model, config)

        settings = get_settings()
        self.ppo_epochs = ppo_epochs or settings.PPO_EPOCHS
        self.clip_range = clip_range or settings.PPO_CLIP_RANGE
        self.value_coef = value_coef or settings.PPO_VALUE_COEF
        self.entropy_coef = entropy_coef or settings.PPO_ENTROPY_COEF

        logger.info(
            f"PPO trainer initialized with epochs={self.ppo_epochs}, "
            f"clip={self.clip_range}, value_coef={self.value_coef}, "
            f"entropy_coef={self.entropy_coef}"
        )

    def train_step(self, batch: Dict[str, Any]) -> Dict[str, float]:
        """
        Perform PPO training step.

        Args:
            batch: Training batch containing:
                - states: Music states/embeddings
                - actions: Generated music tokens
                - old_log_probs: Log probabilities from behavior policy
                - returns: Estimated returns
                - advantages: Advantage estimates

        Returns:
            Dictionary of training metrics
        """
        states = batch["states"]
        actions = batch["actions"]
        old_log_probs = batch["old_log_probs"]
        returns = batch["returns"]
        advantages = batch["advantages"]

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0

        # PPO epochs
        for _ in range(self.ppo_epochs):
            # Forward pass
            logits, values = self.model(states)

            # Calculate log probabilities
            log_probs = F.log_softmax(logits, dim=-1)
            action_log_probs = log_probs.gather(-1, actions.unsqueeze(-1)).squeeze(-1)

            # Ratio for PPO
            ratio = torch.exp(action_log_probs - old_log_probs)

            # Clipped surrogate objective
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - self.clip_range, 1.0 + self.clip_range) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()

            # Value function loss
            value_loss = F.mse_loss(values.squeeze(-1), returns)

            # Entropy bonus
            probs = F.softmax(logits, dim=-1)
            entropy = -(probs * log_probs).sum(dim=-1).mean()

            # Total loss
            loss = (
                policy_loss +
                self.value_coef * value_loss -
                self.entropy_coef * entropy
            )

            # Backpropagation
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config.max_grad_norm
            )
            self.optimizer.step()

            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy += entropy.item()

        # Average over PPO epochs
        num_epochs = self.ppo_epochs
        metrics = {
            "loss": (total_policy_loss + total_value_loss) / num_epochs,
            "policy_loss": total_policy_loss / num_epochs,
            "value_loss": total_value_loss / num_epochs,
            "entropy": total_entropy / num_epochs,
        }

        return metrics

    def generate_trajectory(
        self,
        initial_state: torch.Tensor,
        max_length: int = 512,
    ) -> Dict[str, torch.Tensor]:
        """
        Generate a trajectory using current policy.

        Args:
            initial_state: Starting state
            max_length: Maximum sequence length

        Returns:
            Dictionary containing trajectory data
        """
        self.model.eval()

        states = [initial_state]
        actions = []
        log_probs = []
        rewards = []

        state = initial_state

        with torch.no_grad():
            for _ in range(max_length):
                # Get action from policy
                logits, value = self.model(state)
                probs = F.softmax(logits, dim=-1)

                # Sample action
                action = torch.multinomial(probs, 1)
                log_prob = F.log_softmax(logits, dim=-1).gather(-1, action)

                # Get reward
                reward = self.reward_model(state)["score"]

                # Store
                actions.append(action)
                log_probs.append(log_prob)
                rewards.append(reward)

                # Update state (simplified - would use actual generation logic)
                state = state  # Placeholder

        self.model.train()

        return {
            "states": torch.stack(states),
            "actions": torch.cat(actions),
            "log_probs": torch.cat(log_probs),
            "rewards": torch.tensor(rewards),
        }

    def compute_advantages(
        self,
        rewards: torch.Tensor,
        values: torch.Tensor,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Compute advantages using Generalized Advantage Estimation (GAE).

        Args:
            rewards: Reward sequence
            values: Value estimates
            gamma: Discount factor
            gae_lambda: GAE lambda parameter

        Returns:
            Tuple of (advantages, returns)
        """
        advantages = []
        returns = []
        gae = 0.0
        next_value = 0.0

        # Reverse iteration
        for t in reversed(range(len(rewards))):
            delta = rewards[t] + gamma * next_value - values[t]
            gae = delta + gamma * gae_lambda * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + values[t])
            next_value = values[t]

        advantages = torch.tensor(advantages)
        returns = torch.tensor(returns)

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        return advantages, returns
