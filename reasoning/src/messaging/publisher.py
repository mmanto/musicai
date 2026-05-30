"""RabbitMQ publisher for reasoning service."""

import logging
import json
from typing import Dict, Any, Optional

import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


class ReasoningPublisher:
    """Publisher for reasoning service events."""

    def __init__(self):
        """Initialize the publisher."""
        self.settings = get_settings()
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None

        logger.info("Reasoning publisher initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            # Build connection URL
            url = (
                f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}"
                f"@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}"
                f"{self.settings.RABBITMQ_VHOST}"
            )

            # Connect
            self.connection = await aio_pika.connect_robust(url)
            self.channel = await self.connection.channel()

            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.settings.EXCHANGE_REASONING,
                ExchangeType.TOPIC,
                durable=True
            )

            logger.info("Connected to RabbitMQ")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()

            logger.info("Disconnected from RabbitMQ")

        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def publish_reasoning_result(
        self,
        result: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Publish reasoning result.

        Args:
            result: Reasoning result data
            correlation_id: Optional correlation ID for tracking
        """
        try:
            if not self.exchange:
                await self.connect()

            # Build message
            message_body = json.dumps(result).encode()

            message = Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                correlation_id=correlation_id
            )

            # Publish to queue
            routing_key = "reasoning.generated"

            await self.exchange.publish(
                message,
                routing_key=routing_key
            )

            logger.info(f"Published reasoning result with routing key: {routing_key}")

        except Exception as e:
            logger.error(f"Error publishing reasoning result: {e}")
            raise

    async def publish_validation_result(
        self,
        validation: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Publish validation result.

        Args:
            validation: Validation result data
            correlation_id: Optional correlation ID
        """
        try:
            if not self.exchange:
                await self.connect()

            message_body = json.dumps(validation).encode()

            message = Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                correlation_id=correlation_id
            )

            routing_key = "reasoning.validated"

            await self.exchange.publish(
                message,
                routing_key=routing_key
            )

            logger.info(f"Published validation result with routing key: {routing_key}")

        except Exception as e:
            logger.error(f"Error publishing validation result: {e}")
            raise

    async def publish_analysis_complete(
        self,
        analysis_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish analysis completion event.

        Args:
            analysis_id: Analysis identifier
            status: Status (success, error, etc.)
            data: Optional analysis data
        """
        try:
            if not self.exchange:
                await self.connect()

            event = {
                "analysis_id": analysis_id,
                "status": status,
                "data": data or {},
                "service": self.settings.SERVICE_NAME
            }

            message_body = json.dumps(event).encode()

            message = Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                correlation_id=analysis_id
            )

            routing_key = f"reasoning.analysis.{status}"

            await self.exchange.publish(
                message,
                routing_key=routing_key
            )

            logger.info(f"Published analysis completion: {analysis_id} - {status}")

        except Exception as e:
            logger.error(f"Error publishing analysis completion: {e}")
            raise

    async def publish_error(
        self,
        error: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Publish error event.

        Args:
            error: Error message
            context: Optional error context
            correlation_id: Optional correlation ID
        """
        try:
            if not self.exchange:
                await self.connect()

            event = {
                "error": error,
                "context": context or {},
                "service": self.settings.SERVICE_NAME
            }

            message_body = json.dumps(event).encode()

            message = Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                correlation_id=correlation_id
            )

            routing_key = "reasoning.error"

            await self.exchange.publish(
                message,
                routing_key=routing_key
            )

            logger.info("Published error event")

        except Exception as e:
            logger.error(f"Error publishing error event: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
