"""Tests for RabbitMQ messaging module."""

import pytest
from unittest.mock import Mock, patch
import json


class TestMessagePublisher:
    """Tests for MessagePublisher."""

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_connect(self, mock_params, mock_connection):
        """Test connection to RabbitMQ."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel

        publisher = MessagePublisher(rabbitmq_url="amqp://localhost:5672/")
        publisher.connect(retries=1)

        mock_connection.assert_called_once()
        mock_channel.exchange_declare.assert_called_once()

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_disconnect(self, mock_params, mock_connection):
        """Test disconnection from RabbitMQ."""
        from src.messaging.publisher import MessagePublisher

        mock_conn_instance = Mock()
        mock_conn_instance.is_closed = False
        mock_connection.return_value = mock_conn_instance

        publisher = MessagePublisher()
        publisher.connect(retries=1)
        publisher.disconnect()

        mock_conn_instance.close.assert_called_once()

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish(self, mock_params, mock_connection):
        """Test basic message publishing."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        message = {"test": "data", "value": 123}
        publisher.publish(
            routing_key="test.route",
            message=message,
            correlation_id="test-123"
        )

        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args.kwargs["routing_key"] == "test.route"
        assert call_args.kwargs["exchange"] == "musicai.model"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish_generation_to_reasoning(self, mock_params, mock_connection):
        """Test publishing generated output to reasoning module."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        generated_tokens = [1, 2, 3, 4, 5, 6, 7, 8]
        attention_weights = [0.1, 0.2, 0.3]

        publisher.publish_generation_to_reasoning(
            request_id="req-123",
            generated_tokens=generated_tokens,
            attention_weights=attention_weights
        )

        # Verify publish was called
        mock_channel.basic_publish.assert_called_once()

        # Verify routing key
        call_args = mock_channel.basic_publish.call_args
        assert call_args.kwargs["routing_key"] == "reasoning.generated"

        # Verify message content
        body = call_args.kwargs["body"]
        message = json.loads(body.decode('utf-8'))
        assert message["event_type"] == "GENERATION_COMPLETE"
        assert message["request_id"] == "req-123"
        assert message["payload"]["tokens"] == generated_tokens
        assert message["payload"]["attention_weights"] == attention_weights
        assert message["source_module"] == "model-base"
        assert message["target_module"] == "reasoning"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish_output_to_rlhf(self, mock_params, mock_connection):
        """Test publishing output to RLHF module."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        generated_tokens = [10, 20, 30, 40]
        context = {
            "input_prompt": "jazz piano",
            "temperature": 0.8,
            "user_id": "user-456"
        }

        publisher.publish_output_to_rlhf(
            request_id="req-789",
            generated_tokens=generated_tokens,
            context=context
        )

        call_args = mock_channel.basic_publish.call_args
        assert call_args.kwargs["routing_key"] == "rlhf.output"

        body = call_args.kwargs["body"]
        message = json.loads(body.decode('utf-8'))
        assert message["event_type"] == "OUTPUT_FOR_EVALUATION"
        assert message["payload"]["tokens"] == generated_tokens
        assert message["payload"]["context"] == context
        assert message["target_module"] == "rlhf"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_context_manager(self, mock_params, mock_connection):
        """Test publisher as context manager."""
        from src.messaging.publisher import MessagePublisher

        mock_conn_instance = Mock()
        mock_conn_instance.is_closed = False
        mock_connection.return_value = mock_conn_instance

        with MessagePublisher() as publisher:
            assert publisher is not None

        mock_conn_instance.close.assert_called_once()

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_ensure_connected_reconnects(self, mock_params, mock_connection):
        """Test automatic reconnection when connection is closed."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_conn_instance = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance

        publisher = MessagePublisher()

        # First connection
        publisher.connect(retries=1)
        mock_conn_instance.is_closed = True  # Simulate closed connection

        # Should reconnect on publish
        publisher.publish("test", {"data": 1})

        # Connection should have been called twice (initial + reconnect)
        assert mock_connection.call_count >= 2

    def test_routing_keys_defined(self):
        """Test that all routing keys are properly defined."""
        from src.messaging.publisher import MessagePublisher

        assert MessagePublisher.EXCHANGE_NAME == "musicai.model"
        assert MessagePublisher.ROUTE_REASONING == "reasoning.generated"
        assert MessagePublisher.ROUTE_RLHF == "rlhf.output"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_message_persistence(self, mock_params, mock_connection):
        """Test that messages are published with persistence."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)
        publisher.publish("test.route", {"data": "test"})

        call_args = mock_channel.basic_publish.call_args
        properties = call_args.kwargs["properties"]

        # delivery_mode=2 means persistent
        assert properties.delivery_mode == 2
        assert properties.content_type == "application/json"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish_without_attention_weights(self, mock_params, mock_connection):
        """Test publishing to reasoning without attention weights."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        publisher.publish_generation_to_reasoning(
            request_id="req-no-attn",
            generated_tokens=[1, 2, 3],
            attention_weights=None  # No attention weights
        )

        call_args = mock_channel.basic_publish.call_args
        body = call_args.kwargs["body"]
        message = json.loads(body.decode('utf-8'))

        # Should use empty list as default
        assert message["payload"]["attention_weights"] == []
