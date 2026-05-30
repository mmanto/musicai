"""Graph Neural Network models."""

try:
    from .models import MusicGNN
    from .embeddings import GraphEmbedder
    TORCH_AVAILABLE = True
except ImportError:
    # Provide stubs when torch is not available
    MusicGNN = None
    GraphEmbedder = None
    TORCH_AVAILABLE = False

__all__ = ["MusicGNN", "GraphEmbedder", "TORCH_AVAILABLE"]
