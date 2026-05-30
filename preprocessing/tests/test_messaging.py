"""Tests for RabbitMQ messaging module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
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
        assert call_args.kwargs["exchange"] == "musicai.preprocessing"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish_tokens_to_model(self, mock_params, mock_connection):
        """Test publishing tokens to model-base module."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        tokens = [1, 2, 3, 4, 5]
        features = {"key": "C major", "tempo": 120}

        publisher.publish_tokens_to_model(
            request_id="req-123",
            tokens=tokens,
            features=features
        )

        # Verify publish was called
        mock_channel.basic_publish.assert_called_once()

        # Verify routing key
        call_args = mock_channel.basic_publish.call_args
        assert call_args.kwargs["routing_key"] == "model.tokens"

        # Verify message content
        body = call_args.kwargs["body"]
        message = json.loads(body.decode('utf-8'))
        assert message["event_type"] == "TOKENIZATION_COMPLETE"
        assert message["request_id"] == "req-123"
        assert message["payload"]["tokens"] == tokens
        assert message["source_module"] == "preprocessing"
        assert message["target_module"] == "model-base"

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish_features_to_knowledge_graph(self, mock_params, mock_connection):
        """Test publishing features to knowledge-graph module."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        features = {
            "key_string": "D minor",
            "tempo": 90,
            "time_signature": "3/4",
            "mode": "minor"
        }

        publisher.publish_features_to_knowledge_graph(
            request_id="req-456",
            features=features
        )

        call_args = mock_channel.basic_publish.call_args
        assert call_args.kwargs["routing_key"] == "knowledge.features"

        body = call_args.kwargs["body"]
        message = json.loads(body.decode('utf-8'))
        assert message["event_type"] == "FEATURES_EXTRACTED"
        assert message["payload"]["tonality"] == "D minor"
        assert message["payload"]["tempo"] == 90

    @patch('pika.BlockingConnection')
    @patch('pika.URLParameters')
    def test_publish_analysis_to_reasoning(self, mock_params, mock_connection):
        """Test publishing analysis to reasoning module."""
        from src.messaging.publisher import MessagePublisher

        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        mock_connection.return_value.is_closed = False

        publisher = MessagePublisher()
        publisher.connect(retries=1)

        tokens = [10, 20, 30]
        features = {"key": "G major"}
        context = {"style": "jazz"}

        publisher.publish_analysis_to_reasoning(
            request_id="req-789",
            tokens=tokens,
            features=features,
            context=context
        )

        call_args = mock_channel.basic_publish.call_args
        assert call_args.kwargs["routing_key"] == "reasoning.analysis"

        body = call_args.kwargs["body"]
        message = json.loads(body.decode('utf-8'))
        assert message["event_type"] == "ANALYSIS_COMPLETE"
        assert message["payload"]["context"] == context

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

        assert MessagePublisher.EXCHANGE_NAME == "musicai.preprocessing"
        assert MessagePublisher.ROUTE_MODEL_BASE == "model.tokens"
        assert MessagePublisher.ROUTE_KNOWLEDGE_GRAPH == "knowledge.features"
        assert MessagePublisher.ROUTE_REASONING == "reasoning.analysis"
