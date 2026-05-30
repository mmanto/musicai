"""Graph Neural Network models for music knowledge graph."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv, SAGEConv
from torch_geometric.data import Data
from typing import Optional, Tuple

import logging

logger = logging.getLogger(__name__)


class MusicGNN(nn.Module):
    """Graph Neural Network for learning music concept embeddings."""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 512,
        out_channels: int = 256,
        num_layers: int = 3,
        dropout: float = 0.1,
        conv_type: str = "gcn"
    ):
        """
        Initialize MusicGNN.

        Args:
            in_channels: Input feature dimension
            hidden_channels: Hidden layer dimension
            out_channels: Output embedding dimension
            num_layers: Number of GNN layers
            dropout: Dropout rate
            conv_type: Type of convolution ('gcn', 'gat', 'sage')
        """
        super().__init__()

        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.num_layers = num_layers
        self.dropout = dropout

        # Build convolution layers
        self.convs = nn.ModuleList()
        self.batch_norms = nn.ModuleList()

        # First layer
        if conv_type == "gcn":
            self.convs.append(GCNConv(in_channels, hidden_channels))
        elif conv_type == "gat":
            self.convs.append(GATConv(in_channels, hidden_channels, heads=4, concat=True))
            hidden_channels = hidden_channels * 4  # Adjust for multi-head attention
        elif conv_type == "sage":
            self.convs.append(SAGEConv(in_channels, hidden_channels))
        else:
            raise ValueError(f"Unknown conv_type: {conv_type}")

        self.batch_norms.append(nn.BatchNorm1d(hidden_channels))

        # Hidden layers
        for _ in range(num_layers - 2):
            if conv_type == "gcn":
                self.convs.append(GCNConv(hidden_channels, hidden_channels))
            elif conv_type == "gat":
                self.convs.append(GATConv(hidden_channels, hidden_channels // 4, heads=4, concat=True))
            elif conv_type == "sage":
                self.convs.append(SAGEConv(hidden_channels, hidden_channels))

            self.batch_norms.append(nn.BatchNorm1d(hidden_channels))

        # Output layer
        if conv_type == "gcn":
            self.convs.append(GCNConv(hidden_channels, out_channels))
        elif conv_type == "gat":
            self.convs.append(GATConv(hidden_channels, out_channels, heads=1, concat=False))
        elif conv_type == "sage":
            self.convs.append(SAGEConv(hidden_channels, out_channels))

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Edge indices [2, num_edges]
            edge_attr: Edge features [num_edges, edge_dim] (optional)

        Returns:
            Node embeddings [num_nodes, out_channels]
        """
        # Apply convolution layers
        for i, conv in enumerate(self.convs[:-1]):
            x = conv(x, edge_index)
            x = self.batch_norms[i](x)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)

        # Final layer (no activation)
        x = self.convs[-1](x, edge_index)

        return x

    def encode(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor
    ) -> torch.Tensor:
        """
        Encode graph to embeddings.

        Args:
            x: Node features
            edge_index: Edge indices

        Returns:
            Node embeddings
        """
        return self.forward(x, edge_index)

    @property
    def num_parameters(self) -> int:
        """Get total number of parameters."""
        return sum(p.numel() for p in self.parameters())


class GraphAutoEncoder(nn.Module):
    """Graph AutoEncoder for unsupervised learning."""

    def __init__(
        self,
        encoder: MusicGNN,
        decoder_type: str = "inner_product"
    ):
        """
        Initialize Graph AutoEncoder.

        Args:
            encoder: GNN encoder
            decoder_type: Type of decoder ('inner_product', 'mlp')
        """
        super().__init__()

        self.encoder = encoder
        self.decoder_type = decoder_type

        if decoder_type == "mlp":
            self.decoder = nn.Sequential(
                nn.Linear(encoder.out_channels * 2, encoder.hidden_channels),
                nn.ReLU(),
                nn.Dropout(encoder.dropout),
                nn.Linear(encoder.hidden_channels, 1),
                nn.Sigmoid()
            )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Node features
            edge_index: Edge indices

        Returns:
            Tuple of (node embeddings, reconstructed adjacency)
        """
        # Encode
        z = self.encoder(x, edge_index)

        # Decode (reconstruct adjacency)
        if self.decoder_type == "inner_product":
            adj_recon = torch.sigmoid(torch.mm(z, z.t()))
        else:  # mlp
            src, dst = edge_index
            edge_embeddings = torch.cat([z[src], z[dst]], dim=1)
            adj_recon = self.decoder(edge_embeddings).squeeze()

        return z, adj_recon

    def loss(
        self,
        z: torch.Tensor,
        pos_edge_index: torch.Tensor,
        neg_edge_index: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute reconstruction loss.

        Args:
            z: Node embeddings
            pos_edge_index: Positive edges
            neg_edge_index: Negative edges

        Returns:
            Loss value
        """
        # Positive edges
        pos_src, pos_dst = pos_edge_index
        pos_pred = (z[pos_src] * z[pos_dst]).sum(dim=1)
        pos_loss = -torch.log(torch.sigmoid(pos_pred) + 1e-15).mean()

        # Negative edges
        neg_src, neg_dst = neg_edge_index
        neg_pred = (z[neg_src] * z[neg_dst]).sum(dim=1)
        neg_loss = -torch.log(1 - torch.sigmoid(neg_pred) + 1e-15).mean()

        return pos_loss + neg_loss
