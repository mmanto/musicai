"""RabbitMQ consumer for reasoning service."""

import logging
import json
import asyncio
from typing import Callable, Dict, Any, Optional
import base64

import aio_pika
from aio_pika import Message, ExchangeType, IncomingMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings
from ..symbolic.music21_analyzer import Music21Analyzer
from ..symbolic.rules_engine import RulesEngine, RuleSeverity
from ..neural.llm_client import OllamaClient
from ..neural.chain_of_thought import ChainOfThought
from ..hybrid.reasoner import HybridReasoner, ReasoningMode
from .publisher import ReasoningPublisher

logger = logging.getLogger(__name__)


class ReasoningConsumer:
    """Consumer for reasoning service requests."""

    def __init__(self):
        """Initialize the consumer."""
        self.settings = get_settings()
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

        # Initialize reasoning components
        self.music_analyzer = Music21Analyzer()
        self.rules_engine = RulesEngine()
        self.llm_client = OllamaClient()
        self.cot_engine = ChainOfThought(self.llm_client)
        self.hybrid_reasoner = HybridReasoner(
            music_analyzer=self.music_analyzer,
            rules_engine=self.rules_engine,
            llm_client=self.llm_client,
            cot_engine=self.cot_engine
        )

        # Initialize publisher
        self.publisher = ReasoningPublisher()

        logger.info("Reasoning consumer initialized")

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

            # Set QoS
            await self.channel.set_qos(prefetch_count=1)

            # Connect publisher
            await self.publisher.connect()

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

            await self.publisher.disconnect()

            logger.info("Disconnected from RabbitMQ")

        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def start_consuming(self) -> None:
        """Start consuming messages."""
        try:
            if not self.channel:
                await self.connect()

            # Declare exchange
            exchange = await self.channel.declare_exchange(
                self.settings.EXCHANGE_REASONING,
                ExchangeType.TOPIC,
                durable=True
            )

            # Declare queue for validation requests
            queue_validate = await self.channel.declare_queue(
                self.settings.QUEUE_REASONING_VALIDATE,
                durable=True
            )

            # Bind queue to exchange
            await queue_validate.bind(
                exchange,
                routing_key="reasoning.validate"
            )

            # Declare queue for general reasoning requests
            queue_reasoning = await self.channel.declare_queue(
                "reasoning.requests",
                durable=True
            )

            await queue_reasoning.bind(
                exchange,
                routing_key="reasoning.request"
            )

            # Start consuming
            logger.info("Starting to consume messages...")

            await asyncio.gather(
                queue_validate.consume(self._handle_validate_message),
                queue_reasoning.consume(self._handle_reasoning_message)
            )

        except Exception as e:
            logger.error(f"Error starting consumer: {e}")
            raise

    async def _handle_validate_message(self, message: IncomingMessage) -> None:
        """
        Handle validation request message.

        Args:
            message: Incoming RabbitMQ message
        """
        async with message.process():
            try:
                # Parse message
                data = json.loads(message.body.decode())

                logger.info(f"Received validation request: {data.get('id', 'unknown')}")

                # Extract data
                music_data = base64.b64decode(data["music_data"])
                rules = data.get("rules")
                explain = data.get("explain", True)
                format = data.get("format", "musicxml")

                # Perform validation
                result = await self.hybrid_reasoner.validate_theory(
                    music_data=music_data,
                    rules=rules,
                    explain=explain,
                    format=format
                )

                # Publish result
                response = {
                    "id": data.get("id"),
                    "mode": result.mode.value,
                    "synthesis": result.synthesis,
                    "confidence": result.confidence,
                    "recommendations": result.recommendations,
                    "validation": result.symbolic_analysis.get("validation", {})
                        if result.symbolic_analysis else {}
                }

                await self.publisher.publish_validation_result(
                    validation=response,
                    correlation_id=message.correlation_id
                )

                logger.info(f"Validation completed for: {data.get('id', 'unknown')}")

            except Exception as e:
                logger.error(f"Error handling validation message: {e}")

                await self.publisher.publish_error(
                    error=str(e),
                    context={"message_id": message.message_id},
                    correlation_id=message.correlation_id
                )

    async def _handle_reasoning_message(self, message: IncomingMessage) -> None:
        """
        Handle general reasoning request message.

        Args:
            message: Incoming RabbitMQ message
        """
        async with message.process():
            try:
                # Parse message
                data = json.loads(message.body.decode())

                logger.info(f"Received reasoning request: {data.get('id', 'unknown')}")

                # Extract data
                music_data = base64.b64decode(data["music_data"])
                query = data["query"]
                mode_str = data.get("mode", "hybrid")
                format = data.get("format", "musicxml")

                # Convert mode
                mode = ReasoningMode(mode_str)

                # Perform reasoning
                result = await self.hybrid_reasoner.reason(
                    music_data=music_data,
                    query=query,
                    mode=mode,
                    format=format
                )

                # Publish result
                response = {
                    "id": data.get("id"),
                    "query": result.query,
                    "mode": result.mode.value,
                    "synthesis": result.synthesis,
                    "confidence": result.confidence,
                    "recommendations": result.recommendations
                }

                await self.publisher.publish_reasoning_result(
                    result=response,
                    correlation_id=message.correlation_id
                )

                logger.info(f"Reasoning completed for: {data.get('id', 'unknown')}")

            except Exception as e:
                logger.error(f"Error handling reasoning message: {e}")

                await self.publisher.publish_error(
                    error=str(e),
                    context={"message_id": message.message_id},
                    correlation_id=message.correlation_id
                )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


async def main():
    """Run the consumer."""
    consumer = ReasoningConsumer()

    try:
        await consumer.connect()
        await consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        await consumer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
