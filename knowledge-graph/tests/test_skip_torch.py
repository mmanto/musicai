"""Marker for skipping tests that require torch."""

import pytest

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

requires_torch = pytest.mark.skipif(
    not TORCH_AVAILABLE,
    reason="torch not installed"
)
