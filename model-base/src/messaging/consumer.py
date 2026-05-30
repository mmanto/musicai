"""RabbitMQ message consumer for model-base."""

import json
import logging
import time
from typing import Callable, Optional

import pika
from pika.exceptions import AMQPConnectionError

from ..config import get_settings

logger = logging.getLogger(__name__)


class MessageConsumer:
    """Consumer for receiving requests from preprocessing module."""

    QUEUE_TOKENS = "model.tokens"

    def __init__(self, rabbitmq_url: Optional[str] = None):
        settings = get_settings()
        self.rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        self.prefetch_count = settings.RABBITMQ_PREFETCH_COUNT
        self._connection = None
        self._channel = None
        self._handlers = {}

    def connect(self, retries: int = 5, delay: float = 2.0):
        for attempt in range(retries):
            try:
                params = pika.URLParameters(self.rabbitmq_url)
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()

                self._channel.basic_qos(prefetch_count=self.prefetch_count)

                self._channel.queue_declare(queue=self.QUEUE_TOKENS, durable=True)

                logger.info(f"Consumer connected to RabbitMQ")
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

    def register_handler(self, event_type: str, handler: Callable):
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for: {event_type}")

    def _process_message(self, channel, method, properties, body):
        try:
            message = json.loads(body.decode('utf-8'))
            event_type = message.get("event_type", "UNKNOWN")

            handler = self._handlers.get(event_type)
            if handler:
                handler(message, properties)
                channel.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.warning(f"No handler for: {event_type}")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self):
        if self._connection is None or self._connection.is_closed:
            self.connect()

        self._channel.basic_consume(
            queue=self.QUEUE_TOKENS,
            on_message_callback=self._process_message,
            auto_ack=False,
        )

        logger.info("Consumer waiting for messages...")

        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._channel.stop_consuming()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def handle_tokenization_complete(message: dict, properties):
    """Handle tokenization complete from preprocessing."""
    from ..inference import MusicGenerator
    from .publisher import MessagePublisher

    logger.info(f"Processing tokens: {message.get('request_id')}")

    payload = message.get("payload", {})
    tokens = payload.get("tokens", [])
    features = payload.get("features", {})

    if not tokens:
        logger.error("No tokens in message")
        return

    # Generate continuation
    generator = MusicGenerator()
    result = generator.generate(
        input_tokens=tokens,
        max_length=512,
        temperature=1.0,
    )

    # Send to reasoning
    with MessagePublisher() as publisher:
        publisher.publish_generation_to_reasoning(
            request_id=message.get("request_id", "unknown"),
            generated_tokens=result["generated_tokens"],
        )
