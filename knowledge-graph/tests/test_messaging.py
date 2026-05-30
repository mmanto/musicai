"""Tests for RabbitMQ messaging."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch

from src.messaging.publisher import KnowledgePublisher
from src.messaging.consumer import KnowledgeConsumer


class TestKnowledgePublisher:
    """Test RabbitMQ publisher."""

    @patch('src.messaging.publisher.pika.BlockingConnection')
    def test_connect_success(self, mock_connection):
        """Test successful RabbitMQ connection."""
        # Setup
        mock_conn_instance = MagicMock()
        mock_channel = MagicMock()
        mock_connection.return_value = mock_conn_instance
        mock_conn_instance.channel.return_value = mock_channel

        publisher = KnowledgePublisher()

        # Execute
        publisher.connect()

        # Assert
        assert publisher.connection is not None
        assert publisher.channel is not None
        mock_channel.exchange_declare.assert_called_once()

    @patch('src.messaging.publisher.pika.BlockingConnection')
    def test_connect_failure(self, mock_connection):
        """Test connection failure handling."""
        # Setup
        mock_connection.side_effect = Exception("Connection failed")
        publisher = KnowledgePublisher()

        # Execute & Assert
        with pytest.raises(Exception):
            publisher.connect()

    def test_close_connection(self, mock_rabbitmq_publisher):
        """Test closing connection."""
        # Execute
        mock_rabbitmq_publisher.close()

        # Assert
        mock_rabbitmq_publisher.connection.close.assert_called_once()

    def test_publish_knowledge_response(self, mock_rabbitmq_publisher, sample_concept_data):
        """Test publishing knowledge response."""
        request_id = "test-123"

        # Execute
        mock_rabbitmq_publisher.publish_knowledge_response(
            request_id=request_id,
            concepts=sample_concept_data["concepts"]
        )

        # Assert
        mock_rabbitmq_publisher.channel.basic_publish.assert_called_once()
        call_args = mock_rabbitmq_publisher.channel.basic_publish.call_args

        # Verify routing key
        assert "knowledge" in call_args[1]["routing_key"].lower()

        # Verify message structure
        message = json.loads(call_args[1]["body"])
        assert message["request_id"] == request_id
        assert message["event_type"] == "KNOWLEDGE_RESPONSE"
        assert "payload" in message
        assert "concepts" in message["payload"]

    def test_publish_enriched_features(self, mock_rabbitmq_publisher, sample_features, sample_concept_data):
        """Test publishing enriched features."""
        request_id = "test-456"
        context = {"harmonic_function": "Tonic", "genre": "Classical"}

        # Execute
        mock_rabbitmq_publisher.publish_enriched_features(
            request_id=request_id,
            features=sample_features,
            context=context
        )

        # Assert
        mock_rabbitmq_publisher.channel.basic_publish.assert_called_once()
        call_args = mock_rabbitmq_publisher.channel.basic_publish.call_args

        message = json.loads(call_args[1]["body"])
        assert message["event_type"] == "FEATURES_ENRICHED"
        assert message["payload"]["features"] == sample_features
        assert message["payload"]["context"] == context


class TestKnowledgeConsumer:
    """Test RabbitMQ consumer."""

    @patch('src.messaging.consumer.pika.BlockingConnection')
    def test_connect_success(self, mock_connection, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher):
        """Test successful consumer connection."""
        # Setup
        mock_conn_instance = MagicMock()
        mock_channel = MagicMock()
        mock_connection.return_value = mock_conn_instance
        mock_conn_instance.channel.return_value = mock_channel

        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Execute
        consumer.connect()

        # Assert
        assert consumer.connection is not None
        assert consumer.channel is not None
        mock_channel.queue_declare.assert_called_once()
        mock_channel.queue_bind.assert_called_once()

    def test_process_feature_request(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher, sample_rabbitmq_message):
        """Test processing feature enrichment request."""
        # Setup
        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Mock channel and method
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "test-tag"

        # Execute
        message_body = json.dumps(sample_rabbitmq_message).encode()
        consumer.process_feature_request(mock_channel, mock_method, None, message_body)

        # Assert
        mock_channel.basic_ack.assert_called_once_with(delivery_tag="test-tag")
        mock_rabbitmq_publisher.publish_knowledge_response.assert_called_once()

    def test_process_feature_request_error(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher):
        """Test error handling in message processing."""
        # Setup
        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "test-tag"

        # Invalid message
        invalid_message = b"invalid json"

        # Execute
        consumer.process_feature_request(mock_channel, mock_method, None, invalid_message)

        # Assert - should nack the message
        mock_channel.basic_nack.assert_called_once()

    def test_enrich_with_knowledge(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher, sample_features):
        """Test feature enrichment with knowledge."""
        # Setup
        mock_neo4j_client.search_by_concept.return_value = [
            {"name": "C Major", "tonic": "C"}
        ]
        mock_ontology.query_related_concepts.return_value = [
            {"name": "Major", "pattern": [2, 2, 1, 2, 2, 2, 1]}
        ]

        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Execute
        concepts = consumer._enrich_with_knowledge(sample_features)

        # Assert
        assert isinstance(concepts, dict)
        # Should have looked up key, scale, and chords
        if "key" in sample_features:
            mock_neo4j_client.search_by_concept.assert_called()

    @patch('src.messaging.consumer.pika.BlockingConnection')
    def test_start_consuming(self, mock_connection, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher):
        """Test starting message consumption."""
        # Setup
        mock_conn_instance = MagicMock()
        mock_channel = MagicMock()
        mock_connection.return_value = mock_conn_instance
        mock_conn_instance.channel.return_value = mock_channel

        # Simulate KeyboardInterrupt to stop consuming
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()

        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Execute
        try:
            consumer.start_consuming()
        except KeyboardInterrupt:
            pass

        # Assert
        mock_channel.basic_qos.assert_called_once()
        mock_channel.basic_consume.assert_called_once()
        mock_channel.start_consuming.assert_called_once()
        mock_channel.stop_consuming.assert_called_once()


class TestMessagingIntegration:
    """Test publisher-consumer integration."""

    def test_message_format_compatibility(self, mock_rabbitmq_publisher, sample_concept_data):
        """Test that published messages can be consumed."""
        request_id = "test-integration"

        # Publish
        mock_rabbitmq_publisher.publish_knowledge_response(
            request_id=request_id,
            concepts=sample_concept_data["concepts"]
        )

        # Get published message
        call_args = mock_rabbitmq_publisher.channel.basic_publish.call_args
        message_body = call_args[1]["body"]

        # Verify it can be parsed
        message = json.loads(message_body)

        assert message["request_id"] == request_id
        assert "timestamp" in message
        assert "source_module" in message
        assert message["source_module"] == "knowledge-graph"
        assert "payload" in message

    def test_round_trip_message(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher, sample_rabbitmq_message):
        """Test receiving and responding to a message."""
        # Setup consumer
        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Process incoming message
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "test-tag"

        message_body = json.dumps(sample_rabbitmq_message).encode()
        consumer.process_feature_request(mock_channel, mock_method, None, message_body)

        # Verify response was published
        mock_rabbitmq_publisher.publish_knowledge_response.assert_called_once()

        # Verify message was acknowledged
        mock_channel.basic_ack.assert_called_once()
