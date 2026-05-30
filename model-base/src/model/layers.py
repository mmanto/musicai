"""Transformer layers for Music Transformer."""

import logging
from typing import Optional

import torch
import torch.nn as nn

from .attention import CausalRelativeAttention

logger = logging.getLogger(__name__)


class TransformerDecoderLayer(nn.Module):
    """
    Single transformer decoder layer with relative attention.

    Pre-LayerNorm architecture for better training stability.
    """

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        d_ff: int,
        max_relative_position: int = 512,
        dropout: float = 0.1,
    ):
        """
        Initialize decoder layer.

        Args:
            d_model: Model dimension.
            n_heads: Number of attention heads.
            d_ff: Feed-forward dimension.
            max_relative_position: Maximum relative position for attention.
            dropout: Dropout probability.
        """
        super().__init__()

        # Self-attention with relative positions
        self.self_attention = CausalRelativeAttention(
            d_model=d_model,
            n_heads=n_heads,
            max_relative_position=max_relative_position,
            dropout=dropout,
        )

        # Feed-forward network
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

        # Layer normalization (pre-norm)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)

        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        return_attention: bool = False,
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass.

        Args:
            x: Input tensor (batch, seq_len, d_model)
            mask: Attention mask
            return_attention: Whether to return attention weights

        Returns:
            Output tensor and optionally attention weights.
        """
        # Self-attention with residual
        normed = self.norm1(x)
        attn_output, attn_weights = self.self_attention(
            normed, mask, return_attention
        )
        x = x + self.dropout(attn_output)

        # Feed-forward with residual
        normed = self.norm2(x)
        ff_output = self.feed_forward(normed)
        x = x + ff_output

        return x, attn_weights


class PositionalEncoding(nn.Module):
    """
    Sinusoidal positional encoding.

    Note: The relative attention already handles positional information,
    but we include this for compatibility with standard transformer setups.
    """

    def __init__(self, d_model: int, max_len: int = 8192, dropout: float = 0.1):
        """
        Initialize positional encoding.

        Args:
            d_model: Model dimension.
            max_len: Maximum sequence length.
            dropout: Dropout probability.
        """
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-torch.log(torch.tensor(10000.0)) / d_model)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)

        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Add positional encoding to input.

        Args:
            x: Input tensor (batch, seq_len, d_model)

        Returns:
            Tensor with positional encoding added.
        """
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class TokenEmbedding(nn.Module):
    """Token embedding with scaling."""

    def __init__(self, vocab_size: int, d_model: int):
        """
        Initialize token embedding.

        Args:
            vocab_size: Size of vocabulary.
            d_model: Model dimension.
        """
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.d_model = d_model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Embed tokens with scaling.

        Args:
            x: Token indices (batch, seq_len)

        Returns:
            Embeddings (batch, seq_len, d_model)
        """
        return self.embedding(x) * (self.d_model ** 0.5)
