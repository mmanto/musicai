"""Tests for Music Transformer model."""

import pytest
import torch

from src.model import MusicTransformer
from src.model.attention import RelativeMultiHeadAttention
from src.config import ModelConfig


class TestRelativeAttention:
    """Tests for relative multi-head attention."""

    def test_attention_output_shape(self):
        """Test attention output has correct shape."""
        batch_size = 2
        seq_len = 64
        d_model = 128
        n_heads = 4

        attention = RelativeMultiHeadAttention(
            d_model=d_model,
            n_heads=n_heads,
            max_relative_position=32,
        )

        x = torch.randn(batch_size, seq_len, d_model)
        output, _ = attention(x)

        assert output.shape == (batch_size, seq_len, d_model)

    def test_attention_weights(self):
        """Test attention weights are returned."""
        attention = RelativeMultiHeadAttention(
            d_model=64,
            n_heads=4,
        )

        x = torch.randn(1, 32, 64)
        output, weights = attention(x, return_attention=True)

        assert weights is not None
        assert weights.shape[0] == 1  # batch
        assert weights.shape[1] == 4  # heads
        assert weights.shape[2] == 32  # seq_len
        assert weights.shape[3] == 32  # seq_len


class TestMusicTransformer:
    """Tests for Music Transformer model."""

    @pytest.fixture
    def small_config(self):
        """Create small config for testing."""
        return ModelConfig(
            vocab_size=1000,
            d_model=64,
            n_heads=2,
            n_layers=2,
            d_ff=128,
            max_seq_length=256,
            max_relative_position=32,
        )

    def test_forward_output_shape(self, small_config):
        """Test forward pass output shape."""
        model = MusicTransformer(small_config)

        batch_size = 2
        seq_len = 32
        x = torch.randint(0, small_config.vocab_size, (batch_size, seq_len))

        outputs = model(x)
        logits = outputs["logits"]

        assert logits.shape == (batch_size, seq_len, small_config.vocab_size)

    def test_hidden_states(self, small_config):
        """Test hidden states are returned."""
        model = MusicTransformer(small_config)

        x = torch.randint(0, small_config.vocab_size, (1, 16))
        outputs = model(x, return_hidden_states=True)

        assert "hidden_states" in outputs
        assert len(outputs["hidden_states"]) == small_config.n_layers

    def test_generate(self, small_config):
        """Test generation."""
        model = MusicTransformer(small_config)
        model.eval()

        input_tokens = torch.randint(0, small_config.vocab_size, (1, 8))
        generated = model.generate(
            input_tokens,
            max_length=16,
            temperature=1.0,
            top_k=10,
        )

        assert generated.shape[0] == 1
        assert generated.shape[1] >= 8  # At least input length

    def test_get_embeddings(self, small_config):
        """Test embedding extraction."""
        model = MusicTransformer(small_config)

        tokens = torch.randint(0, small_config.vocab_size, (1, 16))
        embeddings = model.get_embeddings(tokens, layer=-1)

        assert embeddings.shape == (1, 16, small_config.d_model)

    def test_num_parameters(self, small_config):
        """Test parameter counting."""
        model = MusicTransformer(small_config)

        assert model.num_parameters > 0
        assert model.num_trainable_parameters == model.num_parameters


class TestIntegration:
    """Integration tests."""

    @pytest.mark.skip(reason="Requires full model")
    def test_full_generation_pipeline(self):
        """Test full generation pipeline."""
        pass
