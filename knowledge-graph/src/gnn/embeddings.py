"""Graph embedding utilities."""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from torch_geometric.data import Data
from torch_geometric.utils import to_undirected, negative_sampling

from .models import MusicGNN, GraphAutoEncoder
from ..config import get_settings

logger = logging.getLogger(__name__)


class GraphEmbedder:
    """Utility for generating and managing graph embeddings."""

    def __init__(
        self,
        model: Optional[MusicGNN] = None,
        device: str = "cpu"
    ):
        """
        Initialize GraphEmbedder.

        Args:
            model: Pre-trained MusicGNN model (optional)
            device: Device to run on ('cpu' or 'cuda')
        """
        self.settings = get_settings()
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        if model is None:
            # Create default model
            self.model = MusicGNN(
                in_channels=128,  # Default input features
                hidden_channels=self.settings.GNN_HIDDEN_DIM,
                out_channels=self.settings.GNN_EMBEDDING_DIM,
                num_layers=self.settings.GNN_NUM_LAYERS,
                dropout=self.settings.GNN_DROPOUT
            ).to(self.device)
        else:
            self.model = model.to(self.device)

        self.model.eval()
        logger.info(f"GraphEmbedder initialized on {self.device}")

    def load_model(self, path: str) -> None:
        """Load pre-trained model weights."""
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            logger.info(f"Loaded model from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def save_model(self, path: str, epoch: int = 0, loss: float = 0.0) -> None:
        """Save model weights and metadata."""
        try:
            torch.save({
                'epoch': epoch,
                'model_state_dict': self.model.state_dict(),
                'loss': loss,
            }, path)
            logger.info(f"Saved model to {path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            raise

    def neo4j_to_pyg_data(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Data:
        """
        Convert Neo4j graph data to PyTorch Geometric format.

        Args:
            nodes: List of node dictionaries with 'id' and features
            edges: List of edge dictionaries with 'source' and 'target'

        Returns:
            PyTorch Geometric Data object
        """
        # Create node ID mapping
        node_id_map = {node['id']: idx for idx, node in enumerate(nodes)}

        # Extract node features
        # For now, use simple one-hot encoding based on node type
        # In practice, you'd use richer features
        num_nodes = len(nodes)
        x = torch.zeros((num_nodes, 128))  # 128-dim features

        for idx, node in enumerate(nodes):
            # Simple encoding: could be enhanced with node properties
            x[idx] = torch.randn(128)  # Placeholder: use actual features

        # Build edge index
        edge_list = []
        for edge in edges:
            src_idx = node_id_map.get(edge['source'])
            tgt_idx = node_id_map.get(edge['target'])
            if src_idx is not None and tgt_idx is not None:
                edge_list.append([src_idx, tgt_idx])

        if not edge_list:
            # No edges, create empty edge_index
            edge_index = torch.empty((2, 0), dtype=torch.long)
        else:
            edge_index = torch.tensor(edge_list, dtype=torch.long).t()
            # Make undirected
            edge_index = to_undirected(edge_index)

        return Data(x=x, edge_index=edge_index)

    @torch.no_grad()
    def embed_graph(
        self,
        data: Data
    ) -> np.ndarray:
        """
        Generate embeddings for graph nodes.

        Args:
            data: PyTorch Geometric Data object

        Returns:
            Node embeddings as numpy array [num_nodes, embedding_dim]
        """
        self.model.eval()

        data = data.to(self.device)
        embeddings = self.model(data.x, data.edge_index)

        return embeddings.cpu().numpy()

    @torch.no_grad()
    def embed_node(
        self,
        node_idx: int,
        data: Data
    ) -> np.ndarray:
        """
        Get embedding for a specific node.

        Args:
            node_idx: Index of the node
            data: Graph data

        Returns:
            Node embedding [embedding_dim]
        """
        embeddings = self.embed_graph(data)
        return embeddings[node_idx]

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """
        Compute similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding
            metric: Similarity metric ('cosine', 'euclidean', 'dot')

        Returns:
            Similarity score
        """
        if metric == "cosine":
            dot = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            return float(dot / (norm1 * norm2 + 1e-10))
        elif metric == "euclidean":
            return float(-np.linalg.norm(embedding1 - embedding2))
        elif metric == "dot":
            return float(np.dot(embedding1, embedding2))
        else:
            raise ValueError(f"Unknown metric: {metric}")

    def find_similar_nodes(
        self,
        query_embedding: np.ndarray,
        all_embeddings: np.ndarray,
        top_k: int = 10,
        metric: str = "cosine"
    ) -> List[Tuple[int, float]]:
        """
        Find most similar nodes to a query embedding.

        Args:
            query_embedding: Query embedding
            all_embeddings: All node embeddings [num_nodes, embedding_dim]
            top_k: Number of results to return
            metric: Similarity metric

        Returns:
            List of (node_idx, similarity_score) tuples
        """
        similarities = []

        for idx, emb in enumerate(all_embeddings):
            sim = self.compute_similarity(query_embedding, emb, metric)
            similarities.append((idx, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def train_autoencoder(
        self,
        data: Data,
        num_epochs: int = 100,
        learning_rate: float = 0.01,
        neg_sampling_ratio: float = 1.0
    ) -> List[float]:
        """
        Train graph autoencoder for unsupervised learning.

        Args:
            data: Training graph data
            num_epochs: Number of training epochs
            learning_rate: Learning rate
            neg_sampling_ratio: Ratio of negative samples to positive edges

        Returns:
            List of loss values per epoch
        """
        autoencoder = GraphAutoEncoder(self.model).to(self.device)
        optimizer = torch.optim.Adam(autoencoder.parameters(), lr=learning_rate)

        data = data.to(self.device)
        losses = []

        logger.info("Starting autoencoder training...")

        for epoch in range(num_epochs):
            autoencoder.train()
            optimizer.zero_grad()

            # Forward pass
            z, _ = autoencoder(data.x, data.edge_index)

            # Sample negative edges
            neg_edge_index = negative_sampling(
                edge_index=data.edge_index,
                num_nodes=data.num_nodes,
                num_neg_samples=int(data.edge_index.size(1) * neg_sampling_ratio)
            )

            # Compute loss
            loss = autoencoder.loss(z, data.edge_index, neg_edge_index)

            # Backward pass
            loss.backward()
            optimizer.step()

            losses.append(loss.item())

            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch + 1}/{num_epochs}, Loss: {loss.item():.4f}")

        logger.info("Training completed")

        # Update the embedder's model
        self.model = autoencoder.encoder
        self.model.eval()

        return losses
