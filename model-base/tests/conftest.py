"""Pytest configuration and fixtures for model-base tests."""

import pytest
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def small_model_config():
    """Create a small model configuration for testing."""
    from src.config import ModelConfig

    return ModelConfig(
        vocab_size=1000,
        d_model=64,
        n_heads=2,
        n_layers=2,
        d_ff=128,
        max_seq_length=256,
        max_relative_position=32,
        dropout=0.1,
    )


@pytest.fixture(scope="function")
def sample_tokens():
    """Generate sample token sequences for testing."""
    return {
        "short": [1, 2, 3, 4, 5],
        "medium": list(range(1, 33)),
        "single": [1],
    }
