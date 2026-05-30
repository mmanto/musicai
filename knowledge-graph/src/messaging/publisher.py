"""RabbitMQ publisher for knowledge-graph service."""

import json
import logging
from typing import Dict, Any
from datetime import datetime

import pika
from pika.exceptions import AMQPConnectionError

from ..config import get_settings

logger = logging.getLogger(__name__)


class KnowledgePublisher:
    """Publisher for sending knowledge graph results."""

    def __init__(self):
        """Initialize publisher."""
        self.settings = get_settings()
        self.connection = None
        self.channel = None

    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(
                self.settings.RABBITMQ_USER,
                self.settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=self.settings.RABBITMQ_HOST,
                port=self.settings.RABBITMQ_PORT,
                virtual_host=self.settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.settings.EXCHANGE_KNOWLEDGE,
                exchange_type='topic',
                durable=True
            )

            logger.info("Connected to RabbitMQ")

        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Closed RabbitMQ connection")

    def publish_knowledge_response(
        self,
        request_id: str,
        concepts: Dict[str, Any],
        embeddings: Dict[str, Any] = None
    ) -> None:
        """
        Publish knowledge graph response.

        Args:
            request_id: Original request ID
            concepts: Retrieved concepts and relationships
            embeddings: Optional embeddings
        """
        if not self.channel:
            self.connect()

        message = {
            "event_type": "KNOWLEDGE_RESPONSE",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "source_module": "knowledge-graph",
            "payload": {
                "concepts": concepts,
                "embeddings": embeddings or {}
            }
        }

        try:
            self.channel.basic_publish(
                exchange=self.settings.EXCHANGE_KNOWLEDGE,
                routing_key=self.settings.QUEUE_KNOWLEDGE_RESPONSE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            logger.info(f"Published knowledge response for request {request_id}")

        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    def publish_enriched_features(
        self,
        request_id: str,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Publish features enriched with knowledge graph context.

        Args:
            request_id: Request ID
            features: Original features
            context: Added theoretical context
        """
        if not self.channel:
            self.connect()

        message = {
            "event_type": "FEATURES_ENRICHED",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "source_module": "knowledge-graph",
            "target_module": "reasoning",
            "payload": {
                "features": features,
                "context": context
            }
        }

        try:
            self.channel.basic_publish(
                exchange=self.settings.EXCHANGE_KNOWLEDGE,
                routing_key="knowledge.enriched",
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            logger.info(f"Published enriched features for request {request_id}")

        except Exception as e:
            logger.error(f"Failed to publish enriched features: {e}")
            raise
