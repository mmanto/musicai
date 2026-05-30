"""RabbitMQ consumer for RLHF service."""

import logging
import json
from typing import Optional

import aio_pika
from aio_pika import ExchangeType
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


class RLHFConsumer:
    """Consumer for RLHF service events."""

    def __init__(self):
        """Initialize the consumer."""
        self.settings = get_settings()
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

        logger.info("RLHF consumer initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            url = (
                f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}"
                f"@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}"
                f"{self.settings.RABBITMQ_VHOST}"
            )

            self.connection = await aio_pika.connect_robust(url)
            self.channel = await self.connection.channel()

            logger.info("RLHF consumer connected to RabbitMQ")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def start_consuming(self) -> None:
        """Start consuming messages."""
        if not self.channel:
            await self.connect()

        # Declare queue
        queue = await self.channel.declare_queue(
            self.settings.QUEUE_RLHF_FEEDBACK,
            durable=True
        )

        # Start consuming
        await queue.consume(self.on_message)

        logger.info(f"Started consuming from queue: {self.settings.QUEUE_RLHF_FEEDBACK}")

    async def on_message(self, message: aio_pika.IncomingMessage) -> None:
        """Handle incoming message."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                await self.handle_message(body)

            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def handle_message(self, message: dict) -> None:
        """Process message content."""
        event_type = message.get("event_type")

        logger.info(f"Received message: {event_type}")

        # Handle different event types
        # In production, would dispatch to appropriate handlers

    async def close(self) -> None:
        """Close connection."""
        if self.connection:
            await self.connection.close()
            logger.info("RLHF consumer connection closed")
