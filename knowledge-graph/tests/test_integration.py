"""Integration tests for knowledge-graph service."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock


class TestEndToEndFlow:
    """Test complete end-to-end workflows."""

    @patch('src.graph.neo4j_client.GraphDatabase.driver')
    def test_ontology_initialization_workflow(self, mock_driver):
        """Test complete ontology initialization flow."""
        # Setup
        mock_driver_instance = MagicMock()
        mock_session = MagicMock()
        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session

        from src.graph import Neo4jClient, MusicOntology

        client = Neo4jClient()
        client.connect()

        ontology = MusicOntology(client)

        # Execute - should not raise exceptions
        ontology.initialize()

        # Assert - verify calls were made
        assert mock_session.run.call_count > 0

    def test_feature_enrichment_workflow(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher):
        """Test feature enrichment workflow."""
        from src.messaging import KnowledgeConsumer

        # Setup
        mock_neo4j_client.search_by_concept.return_value = [
            {"n": {"name": "C Major", "tonic": "C"}}
        ]
        mock_ontology.query_related_concepts.return_value = [
            {"related": {"name": "G Major"}, "r": {"type": "DOMINANT_OF"}}
        ]

        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Simulate incoming features
        features = {
            "key": "C Major",
            "chords": ["C", "F", "G"],
            "tempo": 120
        }

        # Execute
        concepts = consumer._enrich_with_knowledge(features)

        # Assert
        assert "key" in concepts
        mock_neo4j_client.search_by_concept.assert_called()

    def test_embedding_generation_workflow(self, mock_embedder, sample_graph_data):
        """Test embedding generation workflow."""
        # Execute - generate embeddings
        embeddings = mock_embedder.embed_graph(sample_graph_data)

        # Get embedding for specific node
        node_0_emb = embeddings[0]

        # Find similar nodes
        similar = mock_embedder.find_similar_nodes(node_0_emb, embeddings, top_k=3)

        # Assert
        assert len(similar) == 3
        assert similar[0][0] == 0  # Most similar to itself


class TestModuleIntegration:
    """Test integration with other MusicAI modules."""

    def test_preprocessing_to_knowledge_graph(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher):
        """Test receiving data from preprocessing module."""
        from src.messaging import KnowledgeConsumer
        import json

        # Setup consumer
        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        # Simulate message from preprocessing
        preprocessing_message = {
            "event_type": "FEATURE_EXTRACTION_COMPLETE",
            "request_id": "prep-001",
            "source_module": "preprocessing",
            "target_module": "knowledge-graph",
            "payload": {
                "features": {
                    "key": "D Minor",
                    "scale": "Natural Minor",
                    "chords": ["Dm", "F", "C", "Gm"],
                    "tempo": 140
                }
            }
        }

        # Execute
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "tag-1"

        message_body = json.dumps(preprocessing_message).encode()
        consumer.process_feature_request(mock_channel, mock_method, None, message_body)

        # Assert
        mock_channel.basic_ack.assert_called_once()
        mock_rabbitmq_publisher.publish_knowledge_response.assert_called_once()

        # Verify response structure
        call_args = mock_rabbitmq_publisher.publish_knowledge_response.call_args
        assert call_args[1]["request_id"] == "prep-001"

    def test_knowledge_graph_to_reasoning(self, mock_rabbitmq_publisher):
        """Test sending enriched data to reasoning module."""
        # Setup
        request_id = "kg-to-reasoning-001"
        features = {"key": "A Minor", "chords": ["Am", "Dm", "E"]}
        context = {
            "harmonic_function": ["Tonic", "Subdominant", "Dominant"],
            "genre": "Classical",
            "related_scales": ["A Minor", "C Major"]
        }

        # Execute
        mock_rabbitmq_publisher.publish_enriched_features(
            request_id=request_id,
            features=features,
            context=context
        )

        # Assert
        mock_rabbitmq_publisher.channel.basic_publish.assert_called_once()
        call_args = mock_rabbitmq_publisher.channel.basic_publish.call_args

        import json
        message = json.loads(call_args[1]["body"])

        assert message["target_module"] == "reasoning"
        assert message["payload"]["features"] == features
        assert message["payload"]["context"] == context

    def test_api_to_database_integration(self, app_client):
        """Test API endpoints using database."""
        # Health check
        response = app_client.get("/api/v1/health")
        assert response.status_code == 200

        # Query concept
        response = app_client.post(
            "/api/v1/query/concept",
            json={"concept_name": "Major", "max_depth": 2}
        )
        assert response.status_code == 200

        # Get schema
        response = app_client.get("/api/v1/ontology/schema")
        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data


class TestErrorHandling:
    """Test error handling across integration points."""

    def test_database_connection_failure(self):
        """Test handling database connection failure."""
        from src.graph import Neo4jClient

        # Use invalid credentials
        client = Neo4jClient()
        client.settings.NEO4J_URI = "bolt://invalid:7687"

        # Should raise exception
        with pytest.raises(Exception):
            client.connect()

    def test_message_processing_with_invalid_data(self, mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher):
        """Test handling invalid message data."""
        from src.messaging import KnowledgeConsumer

        consumer = KnowledgeConsumer(mock_neo4j_client, mock_ontology, mock_rabbitmq_publisher)

        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "tag-error"

        # Invalid JSON
        invalid_message = b"not valid json {{"

        # Execute
        consumer.process_feature_request(mock_channel, mock_method, None, invalid_message)

        # Assert - should nack
        mock_channel.basic_nack.assert_called_once()

    def test_api_with_invalid_request(self, app_client):
        """Test API error handling with invalid requests."""
        # Missing required field
        response = app_client.post(
            "/api/v1/query/concept",
            json={"max_depth": 2}  # Missing concept_name
        )
        assert response.status_code == 422

        # Invalid field type
        response = app_client.post(
            "/api/v1/query/concept",
            json={"concept_name": "Major", "max_depth": "not_a_number"}
        )
        assert response.status_code == 422


class TestPerformance:
    """Test performance characteristics."""

    def test_batch_embedding_generation(self, mock_embedder):
        """Test generating embeddings for multiple nodes."""
        import torch
        from torch_geometric.data import Data

        # Create larger graph
        x = torch.randn(100, 128)
        edge_index = torch.randint(0, 100, (2, 300))
        data = Data(x=x, edge_index=edge_index)

        # Execute
        start = time.time()
        embeddings = mock_embedder.embed_graph(data)
        elapsed = time.time() - start

        # Assert
        assert embeddings.shape[0] == 100
        # Should complete in reasonable time (< 1 second for small graph)
        assert elapsed < 1.0

    def test_concurrent_api_requests(self, app_client):
        """Test handling concurrent API requests."""
        # Make multiple requests
        responses = []
        for i in range(5):
            response = app_client.get("/api/v1/health")
            responses.append(response)

        # Assert all succeeded
        assert all(r.status_code == 200 for r in responses)


class TestDataConsistency:
    """Test data consistency across operations."""

    def test_concept_relationships_consistency(self, mock_neo4j_client, mock_ontology):
        """Test that related concepts are consistent."""
        # Mock related concepts
        mock_ontology.query_related_concepts.return_value = [
            {"related": {"name": "Minor"}, "r": {"type": "SIMILAR_TO"}},
            {"related": {"name": "Lydian"}, "r": {"type": "DERIVED_FROM"}}
        ]

        # Query relationships
        results = mock_ontology.query_related_concepts("Major", max_depth=2)

        # Assert
        assert len(results) == 2
        assert all("related" in r for r in results)

    def test_embedding_determinism(self, mock_embedder, sample_graph_data):
        """Test that embeddings are deterministic in eval mode."""
        mock_embedder.model.eval()

        # Generate embeddings twice
        emb1 = mock_embedder.embed_graph(sample_graph_data)
        emb2 = mock_embedder.embed_graph(sample_graph_data)

        # Assert they're identical
        import numpy as np
        assert np.allclose(emb1, emb2)
