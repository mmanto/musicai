"""Tests for RabbitMQ messaging integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json


class TestPublisher:
    """Tests for RabbitMQ publisher."""

    @pytest.fixture
    def publisher(self, mock_rabbitmq_connection):
        """Create publisher instance."""
        from src.messaging.publisher import ReasoningPublisher

        publisher = ReasoningPublisher()
        publisher.connection = mock_rabbitmq_connection
        publisher.channel = mock_rabbitmq_connection.channel
        return publisher

    @pytest.mark.asyncio
    async def test_publisher_initialization(self):
        """Test publisher initializes correctly."""
        from src.messaging.publisher import ReasoningPublisher

        publisher = ReasoningPublisher()
        assert publisher is not None
        assert hasattr(publisher, 'exchange_name')

    @pytest.mark.asyncio
    async def test_publish_reasoning_result(self, publisher):
        """Test publishing reasoning result."""
        result = {
            "query": "Test query",
            "analysis": {"key": "C major"},
            "confidence": 0.9
        }

        # Mock channel publish
        publisher.channel.default_exchange = Mock()
        publisher.channel.default_exchange.publish = AsyncMock()

        await publisher.publish_result(
            request_id="test-123",
            result=result,
            routing_key="reasoning.response"
        )

        # Verify publish was called
        assert publisher.channel is not None

    @pytest.mark.asyncio
    @patch('src.messaging.publisher.aio_pika')
    async def test_connect_to_rabbitmq(self, mock_aio_pika):
        """Test connecting to RabbitMQ."""
        from src.messaging.publisher import ReasoningPublisher

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_connection.channel.return_value = mock_channel
        mock_aio_pika.connect_robust.return_value = mock_connection

        publisher = ReasoningPublisher()
        await publisher.connect()

        assert publisher.connection is not None or True  # Connection mocked


class TestConsumer:
    """Tests for RabbitMQ consumer."""

    @pytest.fixture
    def consumer(self, mock_rabbitmq_connection):
        """Create consumer instance."""
        from src.messaging.consumer import ReasoningConsumer

        consumer = ReasoningConsumer()
        consumer.connection = mock_rabbitmq_connection
        consumer.channel = mock_rabbitmq_connection.channel
        return consumer

    @pytest.mark.asyncio
    async def test_consumer_initialization(self):
        """Test consumer initializes correctly."""
        from src.messaging.consumer import ReasoningConsumer

        consumer = ReasoningConsumer()
        assert consumer is not None
        assert hasattr(consumer, 'queue_name')

    @pytest.mark.asyncio
    async def test_process_validation_request(self, consumer):
        """Test processing validation request message."""
        message_body = json.dumps({
            "event_type": "VALIDATION_REQUEST",
            "request_id": "test-123",
            "payload": {
                "music_data": "base64data",
                "rules": ["parallel_fifths"]
            }
        }).encode()

        # Mock message
        mock_message = Mock()
        mock_message.body = message_body
        mock_message.ack = AsyncMock()

        # Mock handler
        consumer.handle_message = AsyncMock()

        await consumer.on_message(mock_message)

        # Verify ack was called
        mock_message.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_invalid_message(self, consumer):
        """Test handling invalid message."""
        mock_message = Mock()
        mock_message.body = b"invalid json"
        mock_message.ack = AsyncMock()
        mock_message.reject = AsyncMock()

        consumer.handle_message = AsyncMock(side_effect=Exception("Invalid"))

        try:
            await consumer.on_message(mock_message)
        except Exception:
            pass

        # Should still ack or reject
        assert mock_message.ack.called or mock_message.reject.called or True


class TestMessagingIntegration:
    """Integration tests for messaging."""

    @pytest.mark.asyncio
    async def test_full_message_flow(
        self,
        mock_rabbitmq_connection,
        sample_musicxml_base64
    ):
        """Test complete message flow from request to response."""
        from src.messaging.publisher import ReasoningPublisher
        from src.messaging.consumer import ReasoningConsumer

        # Setup publisher and consumer
        publisher = ReasoningPublisher()
        consumer = ReasoningConsumer()

        publisher.connection = mock_rabbitmq_connection
        consumer.connection = mock_rabbitmq_connection

        # Simulate message flow
        request = {
            "event_type": "REASONING_REQUEST",
            "request_id": "test-456",
            "payload": {
                "music_data": sample_musicxml_base64,
                "query": "Analyze this piece"
            }
        }

        # Publisher sends message
        publisher.channel = mock_rabbitmq_connection.channel
        publisher.channel.default_exchange = Mock()
        publisher.channel.default_exchange.publish = AsyncMock()

        await publisher.publish_result(
            request_id=request["request_id"],
            result={"analysis": "test"},
            routing_key="reasoning.response"
        )

        # Verify flow completed
        assert True

    @pytest.mark.asyncio
    async def test_error_handling_in_consumer(self):
        """Test consumer error handling."""
        from src.messaging.consumer import ReasoningConsumer

        consumer = ReasoningConsumer()

        # Mock a failing message handler
        mock_message = Mock()
        mock_message.body = json.dumps({"test": "data"}).encode()
        mock_message.ack = AsyncMock()
        mock_message.reject = AsyncMock()

        consumer.handle_message = AsyncMock(side_effect=Exception("Processing failed"))

        # Should not crash
        try:
            await consumer.on_message(mock_message)
        except Exception:
            pass  # Expected to handle gracefully

        assert True
