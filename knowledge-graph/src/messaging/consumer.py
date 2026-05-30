"""RabbitMQ consumer for knowledge-graph service."""

import json
import logging
from typing import Callable, Dict, Any

import pika
from pika.exceptions import AMQPConnectionError

from ..config import get_settings
from ..graph import Neo4jClient, MusicOntology
from .publisher import KnowledgePublisher

logger = logging.getLogger(__name__)


class KnowledgeConsumer:
    """Consumer for processing feature requests."""

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        ontology: MusicOntology,
        publisher: KnowledgePublisher
    ):
        """
        Initialize consumer.

        Args:
            neo4j_client: Neo4j client instance
            ontology: Music ontology instance
            publisher: Publisher for responses
        """
        self.settings = get_settings()
        self.neo4j_client = neo4j_client
        self.ontology = ontology
        self.publisher = publisher
        self.connection = None
        self.channel = None

    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(
                self.settings.RABBITMQ_USER,
                self.settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=self.settings.RABBITMQ_HOST,
                port=self.settings.RABBITMQ_PORT,
                virtual_host=self.settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.settings.EXCHANGE_KNOWLEDGE,
                exchange_type='topic',
                durable=True
            )

            # Declare queue
            self.channel.queue_declare(
                queue=self.settings.QUEUE_KNOWLEDGE_FEATURES,
                durable=True
            )

            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.settings.EXCHANGE_KNOWLEDGE,
                queue=self.settings.QUEUE_KNOWLEDGE_FEATURES,
                routing_key=self.settings.QUEUE_KNOWLEDGE_FEATURES
            )

            logger.info("Consumer connected to RabbitMQ")

        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Consumer closed RabbitMQ connection")

    def process_feature_request(
        self,
        ch,
        method,
        properties,
        body: bytes
    ) -> None:
        """
        Process incoming feature enrichment request.

        Args:
            ch: Channel
            method: Method
            properties: Properties
            body: Message body
        """
        try:
            message = json.loads(body.decode())
            logger.info(f"Received message: {message.get('event_type')}")

            request_id = message.get("request_id")
            payload = message.get("payload", {})

            # Extract musical features
            features = payload.get("features", {})

            # Query relevant concepts from knowledge graph
            concepts = self._enrich_with_knowledge(features)

            # Publish response
            self.publisher.publish_knowledge_response(
                request_id=request_id,
                concepts=concepts
            )

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Processed request {request_id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reject and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _enrich_with_knowledge(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich features with knowledge graph context.

        Args:
            features: Extracted musical features

        Returns:
            Relevant concepts and relationships
        """
        concepts = {}

        # Example: If features contain key information
        if "key" in features:
            key_name = features["key"]
            key_concepts = self.neo4j_client.search_by_concept(key_name, limit=5)
            concepts["key"] = key_concepts

        # Example: If features contain scale information
        if "scale" in features:
            scale_name = features["scale"]
            scale_info = self.ontology.query_related_concepts(scale_name, max_depth=2)
            concepts["scale"] = scale_info

        # Example: If features contain chord information
        if "chords" in features:
            chord_names = features["chords"]
            chord_concepts = []
            for chord in chord_names[:5]:  # Limit to avoid overload
                chord_info = self.neo4j_client.search_by_concept(chord, limit=1)
                if chord_info:
                    chord_concepts.append(chord_info[0])
            concepts["chords"] = chord_concepts

        return concepts

    def start_consuming(self) -> None:
        """Start consuming messages from the queue."""
        if not self.channel:
            self.connect()

        # Set QoS
        self.channel.basic_qos(prefetch_count=1)

        # Set up consumer
        self.channel.basic_consume(
            queue=self.settings.QUEUE_KNOWLEDGE_FEATURES,
            on_message_callback=self.process_feature_request
        )

        logger.info("Started consuming messages")

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer")
            self.channel.stop_consuming()
            self.close()
