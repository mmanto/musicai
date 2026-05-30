"""RabbitMQ message consumer for receiving requests from other modules."""

import json
import logging
import time
from typing import Callable, Optional

import pika
from pika.exceptions import AMQPConnectionError

from ..config import get_settings

logger = logging.getLogger(__name__)


class MessageConsumer:
    """
    Consumer for receiving messages from other modules via RabbitMQ.

    Handles incoming requests for preprocessing tasks.
    """

    # Queue names for incoming requests
    QUEUE_TASKS = "preprocessing.tasks"
    QUEUE_REANALYZE = "preprocessing.reanalyze"

    def __init__(self, rabbitmq_url: Optional[str] = None):
        """
        Initialize the consumer.

        Args:
            rabbitmq_url: RabbitMQ connection URL.
        """
        settings = get_settings()
        self.rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        self.prefetch_count = settings.RABBITMQ_PREFETCH_COUNT
        self._connection = None
        self._channel = None
        self._handlers = {}

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

                # Set QoS
                self._channel.basic_qos(prefetch_count=self.prefetch_count)

                # Declare queues
                self._channel.queue_declare(
                    queue=self.QUEUE_TASKS,
                    durable=True,
                )
                self._channel.queue_declare(
                    queue=self.QUEUE_REANALYZE,
                    durable=True,
                )

                logger.info(f"Consumer connected to RabbitMQ: {self.rabbitmq_url}")
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
            logger.info("Consumer disconnected from RabbitMQ")

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.

        Args:
            event_type: Event type to handle.
            handler: Handler function that takes (message, properties).
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    def _process_message(self, channel, method, properties, body):
        """
        Process an incoming message.

        Args:
            channel: RabbitMQ channel.
            method: Delivery method.
            properties: Message properties.
            body: Message body.
        """
        try:
            message = json.loads(body.decode('utf-8'))
            event_type = message.get("event_type", "UNKNOWN")

            logger.debug(f"Received message: {event_type}")

            # Find handler
            handler = self._handlers.get(event_type)
            if handler:
                handler(message, properties)
                channel.basic_ack(delivery_tag=method.delivery_tag)
                logger.debug(f"Successfully processed: {event_type}")
            else:
                logger.warning(f"No handler for event type: {event_type}")
                # Reject but don't requeue
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Requeue on error
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self, queue: str = None):
        """
        Start consuming messages from queues.

        Args:
            queue: Specific queue to consume from. If None, consumes from all.
        """
        if self._connection is None or self._connection.is_closed:
            self.connect()

        queues = [queue] if queue else [self.QUEUE_TASKS, self.QUEUE_REANALYZE]

        for q in queues:
            self._channel.basic_consume(
                queue=q,
                on_message_callback=self._process_message,
                auto_ack=False,
            )
            logger.info(f"Started consuming from queue: {q}")

        logger.info("Consumer waiting for messages...")

        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._channel.stop_consuming()
            logger.info("Consumer stopped")

    def consume_one(self, queue: str, timeout: float = 5.0) -> Optional[dict]:
        """
        Consume a single message with timeout.

        Useful for testing or one-off operations.

        Args:
            queue: Queue to consume from.
            timeout: Timeout in seconds.

        Returns:
            Message dictionary or None if timeout.
        """
        if self._connection is None or self._connection.is_closed:
            self.connect()

        method, properties, body = self._channel.basic_get(queue=queue)

        if method:
            message = json.loads(body.decode('utf-8'))
            self._channel.basic_ack(delivery_tag=method.delivery_tag)
            return message

        return None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Handler examples for preprocessing tasks
def handle_tokenize_request(message: dict, properties):
    """
    Handle incoming tokenization request.

    Args:
        message: Message with audio/midi data to tokenize.
        properties: Message properties with reply_to, correlation_id.
    """
    from ..tokenizer import BPETokenizer
    from ..audio import AudioToMidiConverter
    from .publisher import MessagePublisher

    logger.info(f"Processing tokenize request: {message.get('request_id')}")

    payload = message.get("payload", {})
    audio_data = payload.get("audio_data")
    midi_data = payload.get("midi_data")

    tokenizer = BPETokenizer()

    if midi_data:
        # Tokenize MIDI directly
        result = tokenizer.tokenize_midi(bytes(midi_data))
    elif audio_data:
        # Convert to MIDI first
        converter = AudioToMidiConverter()
        midi_result = converter.convert(bytes(audio_data))
        result = tokenizer.tokenize_midi(midi_result["midi_data"])
    else:
        logger.error("No audio or midi data in request")
        return

    # Send results to model-base
    with MessagePublisher() as publisher:
        publisher.publish_tokens_to_model(
            request_id=message.get("request_id", "unknown"),
            tokens=result["tokens"],
            features=result["features"],
        )


def handle_reanalyze_request(message: dict, properties):
    """
    Handle re-analysis request from Reasoning module.

    Args:
        message: Message with section to re-analyze.
        properties: Message properties.
    """
    from ..tokenizer import BPETokenizer
    from ..audio import AudioFeatureExtractor
    from .publisher import MessagePublisher

    logger.info(f"Processing reanalyze request: {message.get('request_id')}")

    payload = message.get("payload", {})
    audio_data = payload.get("audio_data")
    focus_features = payload.get("focus_features", [])

    # Extract features with focus
    extractor = AudioFeatureExtractor()
    features = extractor.extract_all(bytes(audio_data))

    # Add focus indicators
    features["focus_features"] = focus_features

    # Send back to reasoning
    with MessagePublisher() as publisher:
        publisher.publish_analysis_to_reasoning(
            request_id=message.get("request_id", "unknown"),
            tokens=[],  # Re-analysis may not need re-tokenization
            features=features,
        )
