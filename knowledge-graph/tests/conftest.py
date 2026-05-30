"""Pytest configuration and fixtures for knowledge-graph tests."""

import pytest
import os
from typing import Generator
from unittest.mock import Mock, MagicMock

from fastapi.testclient import TestClient

# Mock torch and torch_geometric if not available
try:
    import torch
    from torch_geometric.data import Data
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Create mock classes
    class MockTensor:
        def __init__(self, *args, **kwargs):
            self.shape = kwargs.get('shape', (0,))
        def randn(self, *args, **kwargs):
            return self
        def tensor(self, *args, **kwargs):
            return self

    class torch:
        @staticmethod
        def randn(*args, **kwargs):
            obj = MockTensor()
            if len(args) >= 2:
                obj.shape = tuple(args)
            return obj

        @staticmethod
        def tensor(data, **kwargs):
            obj = MockTensor()
            if isinstance(data, list) and len(data) > 0:
                obj.shape = (len(data), len(data[0]) if isinstance(data[0], list) else 1)
            return obj

        long = int

    class Data:
        def __init__(self, x=None, edge_index=None, **kwargs):
            self.x = x
            self.edge_index = edge_index
            self.num_nodes = x.shape[0] if hasattr(x, 'shape') else 0

# Set test environment
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test_password"
os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["RABBITMQ_PORT"] = "5672"


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for testing."""
    mock_client = Mock()
    mock_client.connect = Mock()
    mock_client.close = Mock()
    mock_client.execute_query = Mock(return_value=[])
    mock_client.search_by_concept = Mock(return_value=[])
    mock_client.find_node = Mock(return_value=None)
    mock_client.create_node = Mock(return_value={"id": "test-id", "name": "test"})
    mock_client.create_relationship = Mock(return_value={"id": "rel-id"})
    return mock_client


@pytest.fixture
def mock_ontology(mock_neo4j_client):
    """Mock Music Ontology for testing."""
    from src.graph import MusicOntology

    mock_onto = Mock(spec=MusicOntology)
    mock_onto.client = mock_neo4j_client
    mock_onto.initialize = Mock()
    mock_onto.query_related_concepts = Mock(return_value=[])
    mock_onto.get_scale_chords = Mock(return_value=[])
    mock_onto.get_chord_progressions = Mock(return_value=[])
    return mock_onto


@pytest.fixture
def sample_graph_data():
    """Sample PyTorch Geometric graph data."""
    # Create a simple graph: 5 nodes, 6 edges
    x = torch.randn(5, 128)  # 5 nodes, 128 features each
    edge_index = torch.tensor([
        [0, 1, 1, 2, 2, 3],
        [1, 0, 2, 1, 3, 2]
    ], dtype=torch.long)

    return Data(x=x, edge_index=edge_index)


@pytest.fixture
def mock_gnn_model():
    """Mock GNN model for testing."""
    if not TORCH_AVAILABLE:
        # Return a simple mock when torch is not available
        mock_model = Mock()
        mock_model.eval = Mock(return_value=mock_model)
        mock_model.in_channels = 128
        mock_model.out_channels = 128
        mock_model.num_layers = 2
        return mock_model

    from src.gnn import MusicGNN

    model = MusicGNN(
        in_channels=128,
        hidden_channels=256,
        out_channels=128,
        num_layers=2,
        dropout=0.1
    )
    model.eval()
    return model


@pytest.fixture
def mock_embedder(mock_gnn_model):
    """Mock graph embedder for testing."""
    if not TORCH_AVAILABLE:
        # Return a simple mock when torch is not available
        import numpy as np

        mock_embedder = Mock()
        mock_embedder.model = mock_gnn_model
        mock_embedder.device = "cpu"
        mock_embedder.embed_graph = Mock(return_value=np.random.randn(5, 128))
        mock_embedder.embed_node = Mock(return_value=np.random.randn(128))
        mock_embedder.compute_similarity = Mock(return_value=0.85)
        mock_embedder.find_similar_nodes = Mock(return_value=[(0, 1.0), (1, 0.9), (2, 0.8)])
        mock_embedder.neo4j_to_pyg_data = Mock()
        mock_embedder.save_model = Mock()
        mock_embedder.load_model = Mock()
        mock_embedder.train_autoencoder = Mock(return_value=[0.5, 0.4, 0.3, 0.2, 0.1])
        return mock_embedder

    from src.gnn import GraphEmbedder

    embedder = GraphEmbedder(model=mock_gnn_model)
    return embedder


@pytest.fixture
def mock_rabbitmq_connection():
    """Mock RabbitMQ connection."""
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_connection.channel.return_value = mock_channel
    mock_connection.is_closed = False
    return mock_connection


@pytest.fixture
def mock_rabbitmq_publisher(mock_rabbitmq_connection):
    """Mock RabbitMQ publisher."""
    from src.messaging import KnowledgePublisher

    publisher = KnowledgePublisher()
    publisher.connection = mock_rabbitmq_connection
    publisher.channel = mock_rabbitmq_connection.channel()
    return publisher


@pytest.fixture
def app_client():
    """FastAPI test client."""
    from src.main import create_app
    from src.api.rest.routes import set_globals
    from src.graph import Neo4jClient, MusicOntology
    from src.gnn import GraphEmbedder

    # Create mock instances
    mock_client = Mock()
    mock_client.connect = Mock()
    mock_client.close = Mock()
    mock_client.search_by_concept = Mock(return_value=[
        {"n": {"name": "Major", "quality": "Major", "pattern": [2, 2, 1, 2, 2, 2, 1]}}
    ])
    mock_client.execute_query = Mock(return_value=[
        {"label": "Note"},
        {"label": "Chord"},
        {"label": "Scale"}
    ])

    mock_ontology = Mock()
    mock_ontology.query_related_concepts = Mock(return_value=[])

    mock_embedder = Mock()

    # Set globals
    set_globals(mock_client, mock_ontology, mock_embedder)

    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_concept_data():
    """Sample musical concept data."""
    return {
        "concepts": {
            "key": [{"name": "C Major", "tonic": "C", "mode": "Major"}],
            "scale": [{"name": "Major", "pattern": [2, 2, 1, 2, 2, 2, 1]}],
            "chords": [
                {"name": "C Major", "intervals": [0, 4, 7]},
                {"name": "G Major", "intervals": [0, 4, 7]}
            ]
        }
    }


@pytest.fixture
def sample_features():
    """Sample musical features from preprocessing."""
    return {
        "key": "C Major",
        "scale": "Major",
        "chords": ["C", "F", "G", "Am"],
        "tempo": 120,
        "time_signature": "4/4"
    }


@pytest.fixture
def sample_rabbitmq_message(sample_features):
    """Sample RabbitMQ message."""
    return {
        "event_type": "FEATURE_EXTRACTION_COMPLETE",
        "request_id": "test-request-123",
        "timestamp": "2025-11-20T12:00:00",
        "source_module": "preprocessing",
        "target_module": "knowledge-graph",
        "payload": {
            "features": sample_features
        }
    }
