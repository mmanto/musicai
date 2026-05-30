"""Music Transformer model with relative attention."""

import logging
from typing import Optional
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from .layers import TransformerDecoderLayer, TokenEmbedding, PositionalEncoding
from ..config import ModelConfig, get_settings

logger = logging.getLogger(__name__)


class MusicTransformer(nn.Module):
    """
    Music Transformer with relative attention.

    A decoder-only transformer model for music generation that uses
    relative positional encodings to capture musical structure.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize Music Transformer.

        Args:
            config: Model configuration. If None, uses default from settings.
        """
        super().__init__()

        if config is None:
            settings = get_settings()
            config = ModelConfig.from_settings(settings)

        self.config = config
        self.vocab_size = config.vocab_size
        self.d_model = config.d_model

        # Token embedding
        self.token_embedding = TokenEmbedding(config.vocab_size, config.d_model)

        # Optional positional encoding (relative attention handles this, but kept for flexibility)
        self.positional_encoding = PositionalEncoding(
            config.d_model,
            config.max_seq_length,
            config.dropout,
        )

        # Transformer decoder layers
        self.layers = nn.ModuleList([
            TransformerDecoderLayer(
                d_model=config.d_model,
                n_heads=config.n_heads,
                d_ff=config.d_ff,
                max_relative_position=config.max_relative_position,
                dropout=config.dropout,
            )
            for _ in range(config.n_layers)
        ])

        # Final layer norm
        self.final_norm = nn.LayerNorm(config.d_model)

        # Output projection
        self.output_projection = nn.Linear(config.d_model, config.vocab_size)

        # Tie weights between embedding and output projection
        self.output_projection.weight = self.token_embedding.embedding.weight

        self._init_weights()

        logger.info(
            f"MusicTransformer initialized: {config.n_layers} layers, "
            f"{config.d_model} dim, {config.n_heads} heads"
        )

    def _init_weights(self):
        """Initialize weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0, std=0.02)

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        return_hidden_states: bool = False,
        return_attention: bool = False,
    ) -> dict:
        """
        Forward pass.

        Args:
            x: Input token indices (batch, seq_len)
            mask: Attention mask
            return_hidden_states: Return hidden states from all layers
            return_attention: Return attention weights from all layers

        Returns:
            Dictionary with logits and optionally hidden states/attention.
        """
        # Embed tokens
        x = self.token_embedding(x)
        x = self.positional_encoding(x)

        hidden_states = [] if return_hidden_states else None
        attention_weights = [] if return_attention else None

        # Pass through transformer layers
        for layer in self.layers:
            x, attn = layer(x, mask, return_attention)

            if return_hidden_states:
                hidden_states.append(x)
            if return_attention and attn is not None:
                attention_weights.append(attn)

        # Final norm and projection
        x = self.final_norm(x)
        logits = self.output_projection(x)

        result = {"logits": logits}

        if return_hidden_states:
            result["hidden_states"] = hidden_states
        if return_attention:
            result["attention_weights"] = attention_weights

        return result

    @torch.no_grad()
    def generate(
        self,
        input_tokens: torch.Tensor,
        max_length: int = 512,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
        repetition_penalty: float = 1.0,
        eos_token_id: Optional[int] = None,
    ) -> torch.Tensor:
        """
        Generate music autoregressively.

        Args:
            input_tokens: Initial tokens (batch, seq_len)
            max_length: Maximum generation length
            temperature: Sampling temperature
            top_k: Top-k sampling (0 to disable)
            top_p: Nucleus sampling threshold
            repetition_penalty: Penalty for repeating tokens
            eos_token_id: End of sequence token ID

        Returns:
            Generated token sequence.
        """
        self.eval()

        batch_size = input_tokens.size(0)
        device = input_tokens.device

        # Start with input tokens
        generated = input_tokens.clone()

        for _ in range(max_length):
            # Get logits for last position
            outputs = self.forward(generated)
            next_token_logits = outputs["logits"][:, -1, :]

            # Apply temperature
            next_token_logits = next_token_logits / temperature

            # Apply repetition penalty
            if repetition_penalty != 1.0:
                for i in range(batch_size):
                    for token_id in set(generated[i].tolist()):
                        next_token_logits[i, token_id] /= repetition_penalty

            # Apply top-k filtering
            if top_k > 0:
                indices_to_remove = next_token_logits < torch.topk(next_token_logits, top_k)[0][..., -1, None]
                next_token_logits[indices_to_remove] = float('-inf')

            # Apply top-p (nucleus) filtering
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

                # Remove tokens with cumulative probability above threshold
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0

                indices_to_remove = sorted_indices_to_remove.scatter(
                    1, sorted_indices, sorted_indices_to_remove
                )
                next_token_logits[indices_to_remove] = float('-inf')

            # Sample
            probs = F.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)

            # Append to generated
            generated = torch.cat([generated, next_token], dim=1)

            # Check for EOS
            if eos_token_id is not None:
                if (next_token == eos_token_id).all():
                    break

            # Check max sequence length
            if generated.size(1) >= self.config.max_seq_length:
                break

        return generated

    def get_embeddings(
        self,
        tokens: torch.Tensor,
        layer: int = -1,
    ) -> torch.Tensor:
        """
        Get embeddings from a specific layer.

        Args:
            tokens: Input tokens (batch, seq_len)
            layer: Layer to extract from (-1 for last)

        Returns:
            Embeddings tensor.
        """
        outputs = self.forward(tokens, return_hidden_states=True)
        hidden_states = outputs["hidden_states"]

        if layer == -1:
            return hidden_states[-1]
        return hidden_states[layer]

    def save(self, path: Path):
        """Save model checkpoint."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "model_state_dict": self.state_dict(),
            "config": self.config.model_dump(),
        }
        torch.save(checkpoint, path)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: Path, device: str = "cpu") -> "MusicTransformer":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device)
        config = ModelConfig(**checkpoint["config"])
        model = cls(config)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        logger.info(f"Model loaded from {path}")
        return model

    @property
    def num_parameters(self) -> int:
        """Get total number of parameters."""
        return sum(p.numel() for p in self.parameters())

    @property
    def num_trainable_parameters(self) -> int:
        """Get number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
