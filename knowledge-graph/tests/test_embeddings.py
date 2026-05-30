"""Tests for graph embeddings."""

import pytest
import torch
import numpy as np

from src.gnn.embeddings import GraphEmbedder
from src.gnn.models import MusicGNN


class TestGraphEmbedder:
    """Test GraphEmbedder functionality."""

    def test_embedder_initialization(self):
        """Test embedder initialization."""
        embedder = GraphEmbedder()
        assert embedder.model is not None
        assert embedder.device is not None

    def test_embedder_with_custom_model(self, mock_gnn_model):
        """Test embedder with custom model."""
        embedder = GraphEmbedder(model=mock_gnn_model)
        assert embedder.model == mock_gnn_model

    def test_embed_graph(self, mock_embedder, sample_graph_data):
        """Test graph embedding generation."""
        # Execute
        embeddings = mock_embedder.embed_graph(sample_graph_data)

        # Assert
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == 5  # 5 nodes
        assert embeddings.shape[1] == 128  # Embedding dimension

    def test_embed_node(self, mock_embedder, sample_graph_data):
        """Test single node embedding."""
        # Execute
        node_embedding = mock_embedder.embed_node(0, sample_graph_data)

        # Assert
        assert isinstance(node_embedding, np.ndarray)
        assert node_embedding.shape[0] == 128

    def test_compute_similarity_cosine(self, mock_embedder):
        """Test cosine similarity computation."""
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([0.0, 1.0, 0.0])
        emb3 = np.array([1.0, 0.0, 0.0])

        # Execute
        sim_orthogonal = mock_embedder.compute_similarity(emb1, emb2, metric="cosine")
        sim_identical = mock_embedder.compute_similarity(emb1, emb3, metric="cosine")

        # Assert
        assert abs(sim_orthogonal - 0.0) < 1e-6
        assert abs(sim_identical - 1.0) < 1e-6

    def test_compute_similarity_euclidean(self, mock_embedder):
        """Test Euclidean similarity computation."""
        emb1 = np.array([0.0, 0.0])
        emb2 = np.array([3.0, 4.0])

        # Execute
        sim = mock_embedder.compute_similarity(emb1, emb2, metric="euclidean")

        # Assert - euclidean is negative distance
        assert abs(sim - (-5.0)) < 1e-6

    def test_compute_similarity_dot(self, mock_embedder):
        """Test dot product similarity."""
        emb1 = np.array([2.0, 3.0])
        emb2 = np.array([4.0, 5.0])

        # Execute
        sim = mock_embedder.compute_similarity(emb1, emb2, metric="dot")

        # Assert
        expected = 2.0 * 4.0 + 3.0 * 5.0
        assert abs(sim - expected) < 1e-6

    def test_find_similar_nodes(self, mock_embedder):
        """Test finding similar nodes."""
        query_emb = np.array([1.0, 0.0, 0.0])
        all_embeddings = np.array([
            [1.0, 0.0, 0.0],  # Identical
            [0.9, 0.1, 0.0],  # Similar
            [0.0, 1.0, 0.0],  # Different
            [0.8, 0.2, 0.0],  # Similar
            [0.0, 0.0, 1.0],  # Different
        ])

        # Execute
        similar = mock_embedder.find_similar_nodes(query_emb, all_embeddings, top_k=3)

        # Assert
        assert len(similar) == 3
        assert similar[0][0] == 0  # Most similar is itself
        assert similar[0][1] > similar[1][1]  # Scores are descending

    def test_neo4j_to_pyg_data(self, mock_embedder):
        """Test conversion from Neo4j to PyTorch Geometric."""
        nodes = [
            {"id": "node-1", "name": "C", "type": "Note"},
            {"id": "node-2", "name": "D", "type": "Note"},
            {"id": "node-3", "name": "E", "type": "Note"},
        ]
        edges = [
            {"source": "node-1", "target": "node-2", "type": "FOLLOWS"},
            {"source": "node-2", "target": "node-3", "type": "FOLLOWS"},
        ]

        # Execute
        data = mock_embedder.neo4j_to_pyg_data(nodes, edges)

        # Assert
        assert data.x.shape[0] == 3  # 3 nodes
        assert data.edge_index.shape[1] >= 2  # At least 2 edges (might be undirected)

    def test_neo4j_to_pyg_data_empty_edges(self, mock_embedder):
        """Test conversion with no edges."""
        nodes = [
            {"id": "node-1", "name": "C"},
            {"id": "node-2", "name": "D"},
        ]
        edges = []

        # Execute
        data = mock_embedder.neo4j_to_pyg_data(nodes, edges)

        # Assert
        assert data.x.shape[0] == 2
        assert data.edge_index.shape[1] == 0  # No edges

    def test_save_and_load_model(self, mock_embedder, tmp_path):
        """Test model saving and loading."""
        # Save
        save_path = tmp_path / "test_model.pt"
        mock_embedder.save_model(str(save_path), epoch=10, loss=0.5)

        # Assert file exists
        assert save_path.exists()

        # Load
        mock_embedder.load_model(str(save_path))

        # Model should still work
        assert mock_embedder.model is not None

    def test_train_autoencoder(self, mock_embedder, sample_graph_data):
        """Test autoencoder training."""
        # Execute
        losses = mock_embedder.train_autoencoder(
            sample_graph_data,
            num_epochs=5,
            learning_rate=0.01
        )

        # Assert
        assert len(losses) == 5
        assert all(loss > 0 for loss in losses)
        # Loss should generally decrease (might not be monotonic)
        assert losses[-1] <= losses[0] * 2  # Allow some variance
