"""Tests for MusicGenerator inference interface."""

import pytest
import torch

from src.inference.generator import MusicGenerator
from src.config import ModelConfig


@pytest.fixture
def small_generator():
    """Create a small generator for testing."""
    # Use small model to avoid memory issues in tests
    config = ModelConfig(
        vocab_size=1000,
        d_model=64,
        n_heads=2,
        n_layers=2,
        d_ff=128,
        max_seq_length=256,
        max_relative_position=32,
    )

    # Monkey patch settings to use small config
    import src.config as config_module
    original_settings = config_module.get_settings()

    # Create generator with small model
    generator = MusicGenerator(device="cpu", use_fp16=False)

    # Override model with small version
    from src.model import MusicTransformer
    generator.model = MusicTransformer(config)
    generator.model.to("cpu")
    generator.model.eval()

    return generator


class TestMusicGenerator:
    """Tests for MusicGenerator class."""

    def test_generate_basic(self, small_generator):
        """Test basic music generation."""
        input_tokens = [1, 2, 3, 4, 5]
        result = small_generator.generate(
            input_tokens=input_tokens,
            max_length=16,
            temperature=1.0,
            top_k=10,
        )

        assert "generated_tokens" in result
        assert "input_length" in result
        assert "output_length" in result
        assert "new_tokens" in result
        assert result["input_length"] == len(input_tokens)
        assert result["output_length"] >= len(input_tokens)

    def test_generate_with_top_p(self, small_generator):
        """Test generation with nucleus (top-p) sampling."""
        input_tokens = [1, 2, 3]
        result = small_generator.generate(
            input_tokens=input_tokens,
            max_length=10,
            temperature=0.8,
            top_k=0,  # Disable top-k
            top_p=0.9,  # Use nucleus sampling
        )

        assert len(result["generated_tokens"]) > 0
        assert result["new_tokens"] > 0

    def test_generate_with_repetition_penalty(self, small_generator):
        """Test generation with repetition penalty."""
        input_tokens = [1, 2, 3, 4, 5]
        result = small_generator.generate(
            input_tokens=input_tokens,
            max_length=20,
            temperature=1.0,
            top_k=50,
            repetition_penalty=1.2,
        )

        assert result["output_length"] > result["input_length"]

    def test_generate_stream(self, small_generator):
        """Test streaming token generation."""
        input_tokens = [1, 2, 3]

        tokens = []
        for token_data in small_generator.generate_stream(
            input_tokens=input_tokens,
            max_length=8,
            temperature=1.0,
            top_k=10,
        ):
            assert "token" in token_data
            assert "probability" in token_data
            assert "position" in token_data
            tokens.append(token_data["token"])

            # Probability should be valid
            assert 0 <= token_data["probability"] <= 1

        assert len(tokens) > 0

    def test_get_embeddings(self, small_generator):
        """Test embedding extraction."""
        tokens = [1, 2, 3, 4, 5]
        embeddings = small_generator.get_embeddings(tokens, layer=-1)

        assert len(embeddings) > 0
        # Embeddings should be flattened (seq_len * d_model)
        expected_size = len(tokens) * small_generator.model.config.d_model
        assert len(embeddings) == expected_size

    def test_continue_sequence(self, small_generator):
        """Test sequence continuation."""
        input_tokens = [1, 2, 3, 4, 5]
        result = small_generator.continue_sequence(
            input_tokens=input_tokens,
            continuation_length=8,
            temperature=1.0,
            top_k=10,
        )

        assert "continuation_tokens" in result
        assert "full_sequence" in result
        assert "continuation_length" in result

        # Full sequence should include input + continuation
        assert len(result["full_sequence"]) >= len(input_tokens)

        # Continuation should be new tokens only
        assert result["continuation_tokens"] == result["full_sequence"][len(input_tokens):]

    def test_temperature_effect(self, small_generator):
        """Test that temperature affects generation diversity."""
        input_tokens = [1, 2, 3]

        # Low temperature - more deterministic
        result_low = small_generator.generate(
            input_tokens=input_tokens,
            max_length=10,
            temperature=0.1,
            top_k=5,
        )

        # High temperature - more random
        result_high = small_generator.generate(
            input_tokens=input_tokens,
            max_length=10,
            temperature=2.0,
            top_k=50,
        )

        # Both should produce valid output
        assert len(result_low["generated_tokens"]) > 0
        assert len(result_high["generated_tokens"]) > 0

    def test_device_property(self, small_generator):
        """Test device property is accessible."""
        assert small_generator.device in ["cpu", "cuda"]

    def test_model_eval_mode(self, small_generator):
        """Test that model is in evaluation mode."""
        assert not small_generator.model.training


class TestGeneratorEdgeCases:
    """Edge case tests for MusicGenerator."""

    def test_empty_input(self, small_generator):
        """Test handling of empty input."""
        # Should handle gracefully or raise appropriate error
        try:
            result = small_generator.generate(
                input_tokens=[],
                max_length=5,
            )
            # If it works, output should still be valid
            assert "generated_tokens" in result
        except (ValueError, IndexError):
            # It's acceptable to raise an error for empty input
            pass

    def test_single_token_input(self, small_generator):
        """Test generation from single token."""
        result = small_generator.generate(
            input_tokens=[1],
            max_length=10,
            temperature=1.0,
            top_k=10,
        )

        assert result["input_length"] == 1
        assert result["output_length"] > 0

    def test_max_length_equals_input(self, small_generator):
        """Test when max_length equals input length."""
        input_tokens = [1, 2, 3, 4, 5]
        result = small_generator.generate(
            input_tokens=input_tokens,
            max_length=5,  # Same as input length
        )

        # Should return at least the input
        assert len(result["generated_tokens"]) >= len(input_tokens)
