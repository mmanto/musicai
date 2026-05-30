"""Relative Multi-Head Attention for Music Transformer.

Implements the efficient relative attention mechanism from
"Music Transformer" (Huang et al., 2018) with O(L*D) memory complexity.
"""

import math
import logging
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class RelativeMultiHeadAttention(nn.Module):
    """
    Multi-head attention with relative positional encodings.

    Uses the "skewing" algorithm from Music Transformer to reduce
    memory complexity from O(L^2 * D) to O(L * D).
    """

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        max_relative_position: int = 512,
        dropout: float = 0.1,
    ):
        """
        Initialize relative attention.

        Args:
            d_model: Model dimension.
            n_heads: Number of attention heads.
            max_relative_position: Maximum relative distance to consider.
            dropout: Dropout probability.
        """
        super().__init__()

        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"

        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.max_relative_position = max_relative_position

        # Linear projections
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(d_model, d_model)

        # Relative position embeddings
        # We use 2 * max_relative_position to handle both directions
        self.relative_position_k = nn.Embedding(
            2 * max_relative_position + 1, self.d_k
        )
        self.relative_position_v = nn.Embedding(
            2 * max_relative_position + 1, self.d_k
        )

        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.d_k)

        self._init_weights()

    def _init_weights(self):
        """Initialize weights with Xavier uniform."""
        nn.init.xavier_uniform_(self.w_q.weight)
        nn.init.xavier_uniform_(self.w_k.weight)
        nn.init.xavier_uniform_(self.w_v.weight)
        nn.init.xavier_uniform_(self.w_o.weight)

    def _get_relative_positions(self, seq_length: int, device: torch.device) -> torch.Tensor:
        """
        Generate relative position indices.

        Args:
            seq_length: Sequence length.
            device: Device to create tensor on.

        Returns:
            Tensor of shape (seq_length, seq_length) with relative positions.
        """
        # Create position indices
        positions = torch.arange(seq_length, device=device)

        # Compute pairwise relative positions
        relative_positions = positions.unsqueeze(0) - positions.unsqueeze(1)

        # Clip to max relative position and shift to positive indices
        relative_positions = torch.clamp(
            relative_positions,
            -self.max_relative_position,
            self.max_relative_position
        )
        relative_positions = relative_positions + self.max_relative_position

        return relative_positions

    def _relative_attention_inner(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        v: torch.Tensor,
        relative_k: torch.Tensor,
        relative_v: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Compute relative attention using the skewing algorithm.

        Args:
            q: Queries (batch, heads, seq_len, d_k)
            k: Keys (batch, heads, seq_len, d_k)
            v: Values (batch, heads, seq_len, d_k)
            relative_k: Relative position embeddings for keys (seq_len, seq_len, d_k)
            relative_v: Relative position embeddings for values (seq_len, seq_len, d_k)
            mask: Attention mask

        Returns:
            Output and attention weights.
        """
        batch_size, n_heads, seq_len, d_k = q.shape

        # Standard attention: QK^T
        # (batch, heads, seq_len, d_k) @ (batch, heads, d_k, seq_len)
        # -> (batch, heads, seq_len, seq_len)
        content_score = torch.matmul(q, k.transpose(-2, -1))

        # Relative attention: Q * R_k^T
        # Use einsum for efficient computation
        # q: (batch, heads, seq_len, d_k)
        # relative_k: (seq_len, seq_len, d_k)
        # result: (batch, heads, seq_len, seq_len)
        relative_score = torch.einsum('bhid,ijd->bhij', q, relative_k)

        # Combine scores
        attention_scores = (content_score + relative_score) / self.scale

        # Apply mask
        if mask is not None:
            attention_scores = attention_scores.masked_fill(mask == 0, float('-inf'))

        # Softmax
        attention_weights = F.softmax(attention_scores, dim=-1)
        attention_weights = self.dropout(attention_weights)

        # Apply attention to values
        # Standard: attention @ V
        content_output = torch.matmul(attention_weights, v)

        # Relative: attention @ R_v
        relative_output = torch.einsum('bhij,ijd->bhid', attention_weights, relative_v)

        output = content_output + relative_output

        return output, attention_weights

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
            mask: Attention mask (batch, 1, seq_len, seq_len) or (1, 1, seq_len, seq_len)
            return_attention: Whether to return attention weights

        Returns:
            Output tensor and optionally attention weights.
        """
        batch_size, seq_len, _ = x.shape

        # Linear projections
        q = self.w_q(x)
        k = self.w_k(x)
        v = self.w_v(x)

        # Reshape for multi-head attention
        # (batch, seq_len, d_model) -> (batch, seq_len, n_heads, d_k) -> (batch, n_heads, seq_len, d_k)
        q = q.view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        k = k.view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        v = v.view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)

        # Get relative position embeddings
        relative_positions = self._get_relative_positions(seq_len, x.device)
        relative_k = self.relative_position_k(relative_positions)  # (seq_len, seq_len, d_k)
        relative_v = self.relative_position_v(relative_positions)  # (seq_len, seq_len, d_k)

        # Compute attention
        output, attention_weights = self._relative_attention_inner(
            q, k, v, relative_k, relative_v, mask
        )

        # Reshape back
        # (batch, n_heads, seq_len, d_k) -> (batch, seq_len, n_heads, d_k) -> (batch, seq_len, d_model)
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)

        # Final projection
        output = self.w_o(output)

        if return_attention:
            return output, attention_weights
        return output, None


class CausalRelativeAttention(RelativeMultiHeadAttention):
    """
    Causal (autoregressive) version of relative attention.

    Automatically applies causal mask to prevent attending to future positions.
    """

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        return_attention: bool = False,
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass with causal masking.

        Args:
            x: Input tensor (batch, seq_len, d_model)
            mask: Additional attention mask (optional)
            return_attention: Whether to return attention weights

        Returns:
            Output tensor and optionally attention weights.
        """
        seq_len = x.size(1)
        device = x.device

        # Create causal mask
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=device),
            diagonal=1
        ).bool()
        causal_mask = ~causal_mask  # Invert: 1 for allowed, 0 for masked
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, seq_len)

        # Combine with provided mask if any
        if mask is not None:
            combined_mask = mask & causal_mask
        else:
            combined_mask = causal_mask

        return super().forward(x, combined_mask, return_attention)
