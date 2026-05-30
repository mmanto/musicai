"""RabbitMQ message publisher for async communication with other modules."""

import json
import logging
import time
from typing import Any, Optional

import pika
from pika.exceptions import AMQPConnectionError

from ..config import get_settings

logger = logging.getLogger(__name__)


class MessagePublisher:
    """
    Publisher for sending messages to other modules via RabbitMQ.

    Handles connection management, message serialization, and routing.
    """

    # Exchange and queue names for inter-module communication
    EXCHANGE_NAME = "musicai.preprocessing"

    # Routing keys for different destinations
    ROUTE_MODEL_BASE = "model.tokens"
    ROUTE_KNOWLEDGE_GRAPH = "knowledge.features"
    ROUTE_REASONING = "reasoning.analysis"
    ROUTE_RLHF = "rlhf.feedback"

    def __init__(self, rabbitmq_url: Optional[str] = None):
        """
        Initialize the publisher.

        Args:
            rabbitmq_url: RabbitMQ connection URL.
        """
        settings = get_settings()
        self.rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        self._connection = None
        self._channel = None

    def connect(self, retries: int = 5, delay: float = 2.0):
        """
        Connect to RabbitMQ with retry logic.

        Args:
            retries: Number of connection retries.
            delay: Delay between retries in seconds.
        """
        for attempt in range(retries):
            try:
                params = pika.URLParameters(self.rabbitmq_url)
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()

                # Declare exchange
                self._channel.exchange_declare(
                    exchange=self.EXCHANGE_NAME,
                    exchange_type="topic",
                    durable=True,
                )

                logger.info(f"Connected to RabbitMQ: {self.rabbitmq_url}")
                return

            except AMQPConnectionError as e:
                logger.warning(
                    f"RabbitMQ connection attempt {attempt + 1}/{retries} failed: {e}"
                )
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise

    def disconnect(self):
        """Close the connection."""
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    def _ensure_connected(self):
        """Ensure we have an active connection."""
        if self._connection is None or self._connection.is_closed:
            self.connect()

    def publish(
        self,
        routing_key: str,
        message: dict,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ):
        """
        Publish a message to the exchange.

        Args:
            routing_key: Routing key for message destination.
            message: Message payload as dictionary.
            correlation_id: Optional correlation ID for request tracking.
            reply_to: Optional queue for replies.
        """
        self._ensure_connected()

        # Serialize message
        body = json.dumps(message, default=str).encode('utf-8')

        # Message properties
        properties = pika.BasicProperties(
            delivery_mode=2,  # Persistent
            content_type="application/json",
            correlation_id=correlation_id,
            reply_to=reply_to,
            timestamp=int(time.time()),
            headers={
                "source": "preprocessing",
                "version": "0.1.0",
            },
        )

        self._channel.basic_publish(
            exchange=self.EXCHANGE_NAME,
            routing_key=routing_key,
            body=body,
            properties=properties,
        )

        logger.debug(f"Published message to {routing_key}: {len(body)} bytes")

    def publish_tokens_to_model(
        self,
        request_id: str,
        tokens: list[int],
        features: dict,
        embeddings: Optional[list[float]] = None,
    ):
        """
        Send tokenized data to the Model Base module.

        Args:
            request_id: Request tracking ID.
            tokens: BPE token IDs.
            features: Extracted features.
            embeddings: Optional initial embeddings.
        """
        message = {
            "event_type": "TOKENIZATION_COMPLETE",
            "request_id": request_id,
            "payload": {
                "tokens": tokens,
                "features": features,
                "embeddings": embeddings or [],
            },
            "timestamp": time.time(),
            "source_module": "preprocessing",
            "target_module": "model-base",
        }

        self.publish(
            routing_key=self.ROUTE_MODEL_BASE,
            message=message,
            correlation_id=request_id,
        )

        logger.info(f"Sent {len(tokens)} tokens to model-base (request_id={request_id})")

    def publish_features_to_knowledge_graph(
        self,
        request_id: str,
        features: dict,
    ):
        """
        Send extracted features to the Knowledge Graph module.

        Args:
            request_id: Request tracking ID.
            features: Musical features (key, tempo, chords, etc.).
        """
        message = {
            "event_type": "FEATURES_EXTRACTED",
            "request_id": request_id,
            "payload": {
                "tonality": features.get("key_string"),
                "tempo": features.get("tempo"),
                "time_signature": features.get("time_signature"),
                "chords": features.get("chord_progression", []),
                "mode": features.get("mode"),
            },
            "timestamp": time.time(),
            "source_module": "preprocessing",
            "target_module": "knowledge-graph",
        }

        self.publish(
            routing_key=self.ROUTE_KNOWLEDGE_GRAPH,
            message=message,
            correlation_id=request_id,
        )

        logger.info(f"Sent features to knowledge-graph (request_id={request_id})")

    def publish_analysis_to_reasoning(
        self,
        request_id: str,
        tokens: list[int],
        features: dict,
        context: Optional[dict] = None,
    ):
        """
        Send analysis results to the Reasoning module.

        Args:
            request_id: Request tracking ID.
            tokens: BPE tokens.
            features: Musical features.
            context: Optional additional context.
        """
        message = {
            "event_type": "ANALYSIS_COMPLETE",
            "request_id": request_id,
            "payload": {
                "tokens": tokens,
                "features": features,
                "context": context or {},
            },
            "timestamp": time.time(),
            "source_module": "preprocessing",
            "target_module": "reasoning",
        }

        self.publish(
            routing_key=self.ROUTE_REASONING,
            message=message,
            correlation_id=request_id,
        )

        logger.info(f"Sent analysis to reasoning (request_id={request_id})")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
