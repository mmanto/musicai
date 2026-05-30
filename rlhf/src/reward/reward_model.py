"""Reward Model implementation for assessing music quality."""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig

from ..config import get_settings

logger = logging.getLogger(__name__)


class RewardType(str, Enum):
    """Types of reward models."""

    PAIRWISE = "pairwise"  # Compare two outputs
    POINTWISE = "pointwise"  # Score single output
    RANKING = "ranking"  # Rank multiple outputs


@dataclass
class RewardScore:
    """Reward score result."""

    score: float
    confidence: float
    breakdown: Dict[str, float]
    metadata: Dict[str, Any]


class RewardModel(nn.Module):
    """
    Reward Model for evaluating music quality.

    Supports multiple reward types:
    - Pairwise: Compares two musical outputs
    - Pointwise: Scores a single output
    - Ranking: Ranks multiple outputs
    """

    def __init__(
        self,
        model_name_or_path: Optional[str] = None,
        reward_type: RewardType = RewardType.PAIRWISE,
        num_aspects: int = 5,
    ):
        """
        Initialize reward model.

        Args:
            model_name_or_path: Path to pretrained model or model name
            reward_type: Type of reward model
            num_aspects: Number of quality aspects to evaluate
        """
        super().__init__()

        self.settings = get_settings()
        self.reward_type = reward_type
        self.num_aspects = num_aspects

        # Initialize base model
        if model_name_or_path:
            config = AutoConfig.from_pretrained(model_name_or_path)
            self.base_model = AutoModel.from_pretrained(model_name_or_path)
            hidden_size = config.hidden_size
        else:
            # Use simple model for testing
            hidden_size = 768
            self.base_model = nn.Sequential(
                nn.Linear(512, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.1),
            )

        # Reward heads
        self.aspect_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, 256),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(256, 1),
            )
            for _ in range(num_aspects)
        ])

        # Overall reward head
        self.overall_head = nn.Sequential(
            nn.Linear(hidden_size + num_aspects, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 1),
        )

        # Quality aspect names
        self.aspect_names = [
            "harmony",
            "melody",
            "rhythm",
            "structure",
            "originality",
        ][:num_aspects]

        logger.info(
            f"Reward model initialized with type={reward_type}, "
            f"aspects={num_aspects}"
        )

    def forward(
        self,
        embeddings: torch.Tensor,
        return_aspects: bool = True
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass through reward model.

        Args:
            embeddings: Input embeddings [batch_size, hidden_size]
            return_aspects: Whether to return individual aspect scores

        Returns:
            Dictionary containing overall score and optional aspect scores
        """
        batch_size = embeddings.shape[0]

        # Get aspect scores
        aspect_scores = []
        for head in self.aspect_heads:
            score = head(embeddings)  # [batch_size, 1]
            aspect_scores.append(score)

        aspect_scores = torch.cat(aspect_scores, dim=1)  # [batch_size, num_aspects]

        # Combine for overall score
        combined = torch.cat([embeddings, aspect_scores], dim=1)
        overall_score = self.overall_head(combined)  # [batch_size, 1]

        result = {
            "score": overall_score.squeeze(-1),  # [batch_size]
        }

        if return_aspects:
            result["aspect_scores"] = aspect_scores

        return result

    def evaluate_pairwise(
        self,
        embedding_a: torch.Tensor,
        embedding_b: torch.Tensor
    ) -> torch.Tensor:
        """
        Compare two music outputs.

        Args:
            embedding_a: First output embedding
            embedding_b: Second output embedding

        Returns:
            Preference logits (positive = prefer A, negative = prefer B)
        """
        scores_a = self.forward(embedding_a, return_aspects=False)
        scores_b = self.forward(embedding_b, return_aspects=False)

        # Return difference (preference for A over B)
        return scores_a["score"] - scores_b["score"]

    def evaluate_pointwise(
        self,
        embedding: torch.Tensor
    ) -> RewardScore:
        """
        Score a single music output.

        Args:
            embedding: Output embedding

        Returns:
            Reward score with breakdown
        """
        with torch.no_grad():
            outputs = self.forward(embedding, return_aspects=True)

            score = outputs["score"].item()
            aspect_scores = outputs["aspect_scores"].squeeze(0).tolist()

            breakdown = {
                name: score
                for name, score in zip(self.aspect_names, aspect_scores)
            }

            # Simple confidence based on score variance
            confidence = 1.0 - torch.std(outputs["aspect_scores"]).item()

            return RewardScore(
                score=score,
                confidence=confidence,
                breakdown=breakdown,
                metadata={"reward_type": "pointwise"}
            )

    def evaluate_ranking(
        self,
        embeddings: List[torch.Tensor]
    ) -> List[int]:
        """
        Rank multiple music outputs.

        Args:
            embeddings: List of output embeddings

        Returns:
            Indices sorted by quality (best first)
        """
        with torch.no_grad():
            scores = []
            for emb in embeddings:
                output = self.forward(emb, return_aspects=False)
                scores.append(output["score"].item())

            # Return indices sorted by score (descending)
            return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    @torch.no_grad()
    def batch_evaluate(
        self,
        embeddings: torch.Tensor,
        return_details: bool = False
    ) -> List[RewardScore]:
        """
        Evaluate a batch of music outputs.

        Args:
            embeddings: Batch of embeddings [batch_size, hidden_size]
            return_details: Whether to return detailed breakdown

        Returns:
            List of reward scores
        """
        outputs = self.forward(embeddings, return_aspects=return_details)

        scores = outputs["score"].tolist()
        results = []

        for i, score in enumerate(scores):
            if return_details:
                aspect_scores = outputs["aspect_scores"][i].tolist()
                breakdown = {
                    name: ascore
                    for name, ascore in zip(self.aspect_names, aspect_scores)
                }
            else:
                breakdown = {}

            results.append(
                RewardScore(
                    score=score,
                    confidence=0.8,  # Placeholder
                    breakdown=breakdown,
                    metadata={"batch_index": i}
                )
            )

        return results

    def save_pretrained(self, save_directory: str):
        """Save model to directory."""
        torch.save(self.state_dict(), f"{save_directory}/reward_model.pt")
        logger.info(f"Reward model saved to {save_directory}")

    @classmethod
    def load_pretrained(cls, load_directory: str, **kwargs):
        """Load model from directory."""
        model = cls(**kwargs)
        model.load_state_dict(
            torch.load(f"{load_directory}/reward_model.pt")
        )
        logger.info(f"Reward model loaded from {load_directory}")
        return model
