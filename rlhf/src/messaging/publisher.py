"""RabbitMQ publisher for RLHF service."""

import logging
import json
from typing import Dict, Any, Optional

import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


class RLHFPublisher:
    """Publisher for RLHF service events."""

    def __init__(self):
        """Initialize the publisher."""
        self.settings = get_settings()
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None

        logger.info("RLHF publisher initialized")

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

            self.exchange = await self.channel.declare_exchange(
                self.settings.EXCHANGE_RLHF,
                ExchangeType.TOPIC,
                durable=True
            )

            logger.info("RLHF publisher connected to RabbitMQ")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def publish_training_update(
        self,
        job_id: str,
        status: str,
        metrics: Dict[str, Any],
        routing_key: str = "rlhf.training.update"
    ) -> None:
        """Publish training update event."""
        message = {
            "event_type": "TRAINING_UPDATE",
            "job_id": job_id,
            "status": status,
            "metrics": metrics,
        }

        await self._publish(message, routing_key)

    async def publish_feedback_received(
        self,
        feedback_id: str,
        feedback_type: str,
        routing_key: str = "rlhf.feedback.received"
    ) -> None:
        """Publish feedback received event."""
        message = {
            "event_type": "FEEDBACK_RECEIVED",
            "feedback_id": feedback_id,
            "feedback_type": feedback_type,
        }

        await self._publish(message, routing_key)

    async def _publish(
        self,
        message: Dict[str, Any],
        routing_key: str
    ) -> None:
        """Publish message to exchange."""
        if not self.exchange:
            await self.connect()

        body = json.dumps(message).encode()

        await self.exchange.publish(
            Message(
                body=body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json"
            ),
            routing_key=routing_key
        )

        logger.debug(f"Published message to {routing_key}")

    async def close(self) -> None:
        """Close connection."""
        if self.connection:
            await self.connection.close()
            logger.info("RLHF publisher connection closed")
