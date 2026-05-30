"""RabbitMQ messaging components."""

from .publisher import KnowledgePublisher
from .consumer import KnowledgeConsumer

__all__ = ["KnowledgePublisher", "KnowledgeConsumer"]
