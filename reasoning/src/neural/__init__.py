"""Neural reasoning with LLMs."""

from .llm_client import OllamaClient
from .chain_of_thought import ChainOfThought

__all__ = ["OllamaClient", "ChainOfThought"]
