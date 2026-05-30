"""AI services for music generation and processing."""

from .music21_service import Music21Service
from .ollama_service import OllamaService

__all__ = [
    "Music21Service",
    "OllamaService"
]
