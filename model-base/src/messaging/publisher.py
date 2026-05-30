"""RabbitMQ message publisher for model-base."""

import json
import logging
import time
from typing import Optional

import pika
from pika.exceptions import AMQPConnectionError

from ..config import get_settings

logger = logging.getLogger(__name__)


class MessagePublisher:
    """Publisher for sending messages to other modules."""

    EXCHANGE_NAME = "musicai.model"

    # Routing keys
    ROUTE_REASONING = "reasoning.generated"
    ROUTE_RLHF = "rlhf.output"

    def __init__(self, rabbitmq_url: Optional[str] = None):
        settings = get_settings()
        self.rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        self._connection = None
        self._channel = None

    def connect(self, retries: int = 5, delay: float = 2.0):
        for attempt in range(retries):
            try:
                params = pika.URLParameters(self.rabbitmq_url)
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()

                self._channel.exchange_declare(
                    exchange=self.EXCHANGE_NAME,
                    exchange_type="topic",
                    durable=True,
                )

                logger.info(f"Connected to RabbitMQ")
                return

            except AMQPConnectionError as e:
                logger.warning(f"Connection attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise

    def disconnect(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()

    def _ensure_connected(self):
        if self._connection is None or self._connection.is_closed:
            self.connect()

    def publish(self, routing_key: str, message: dict, correlation_id: Optional[str] = None):
        self._ensure_connected()

        body = json.dumps(message, default=str).encode('utf-8')

        properties = pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            correlation_id=correlation_id,
            timestamp=int(time.time()),
            headers={"source": "model-base"},
        )

        self._channel.basic_publish(
            exchange=self.EXCHANGE_NAME,
            routing_key=routing_key,
            body=body,
            properties=properties,
        )

    def publish_generation_to_reasoning(
        self,
        request_id: str,
        generated_tokens: list[int],
        attention_weights: Optional[list[float]] = None,
    ):
        """Send generated output to reasoning module for validation."""
        message = {
            "event_type": "GENERATION_COMPLETE",
            "request_id": request_id,
            "payload": {
                "tokens": generated_tokens,
                "attention_weights": attention_weights or [],
            },
            "timestamp": time.time(),
            "source_module": "model-base",
            "target_module": "reasoning",
        }

        self.publish(self.ROUTE_REASONING, message, correlation_id=request_id)
        logger.info(f"Sent generation to reasoning (request_id={request_id})")

    def publish_output_to_rlhf(
        self,
        request_id: str,
        generated_tokens: list[int],
        context: dict,
    ):
        """Send output to RLHF module for evaluation."""
        message = {
            "event_type": "OUTPUT_FOR_EVALUATION",
            "request_id": request_id,
            "payload": {
                "tokens": generated_tokens,
                "context": context,
            },
            "timestamp": time.time(),
            "source_module": "model-base",
            "target_module": "rlhf",
        }

        self.publish(self.ROUTE_RLHF, message, correlation_id=request_id)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
