"""Tests for GNN models."""

import pytest
import torch
import numpy as np
from torch_geometric.data import Data

from src.gnn.models import MusicGNN, GraphAutoEncoder


class TestMusicGNN:
    """Test MusicGNN model."""

    def test_model_initialization(self):
        """Test model initialization with different configurations."""
        # GCN model
        model = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=128,
            num_layers=3,
            conv_type="gcn"
        )
        assert model.in_channels == 128
        assert model.out_channels == 128
        assert model.num_layers == 3

    def test_model_forward_pass(self, sample_graph_data):
        """Test forward pass through the model."""
        model = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )

        # Execute
        output = model(sample_graph_data.x, sample_graph_data.edge_index)

        # Assert
        assert output.shape == (5, 64)  # 5 nodes, 64 output dims
        assert not torch.isnan(output).any()

    def test_model_encode(self, sample_graph_data):
        """Test encoding method."""
        model = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )

        # Execute
        embeddings = model.encode(sample_graph_data.x, sample_graph_data.edge_index)

        # Assert
        assert embeddings.shape == (5, 64)

    def test_num_parameters(self):
        """Test parameter counting."""
        model = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )

        num_params = model.num_parameters
        assert num_params > 0
        assert isinstance(num_params, int)

    def test_different_conv_types(self, sample_graph_data):
        """Test different convolution types."""
        conv_types = ["gcn", "gat", "sage"]

        for conv_type in conv_types:
            model = MusicGNN(
                in_channels=128,
                hidden_channels=256,
                out_channels=64,
                num_layers=2,
                conv_type=conv_type
            )

            output = model(sample_graph_data.x, sample_graph_data.edge_index)
            assert output.shape[0] == 5  # 5 nodes
            assert not torch.isnan(output).any()

    def test_invalid_conv_type(self):
        """Test initialization with invalid conv type."""
        with pytest.raises(ValueError):
            MusicGNN(
                in_channels=128,
                hidden_channels=256,
                out_channels=64,
                num_layers=2,
                conv_type="invalid"
            )

    def test_model_eval_mode(self, sample_graph_data):
        """Test model in evaluation mode."""
        model = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )
        model.eval()

        # Execute twice to ensure determinism in eval mode
        output1 = model(sample_graph_data.x, sample_graph_data.edge_index)
        output2 = model(sample_graph_data.x, sample_graph_data.edge_index)

        # Assert outputs are identical (no dropout)
        assert torch.allclose(output1, output2)


class TestGraphAutoEncoder:
    """Test Graph AutoEncoder."""

    def test_autoencoder_initialization(self):
        """Test autoencoder initialization."""
        encoder = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )

        autoencoder = GraphAutoEncoder(encoder, decoder_type="inner_product")
        assert autoencoder.encoder is encoder
        assert autoencoder.decoder_type == "inner_product"

    def test_autoencoder_forward_inner_product(self, sample_graph_data):
        """Test forward pass with inner product decoder."""
        encoder = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )
        autoencoder = GraphAutoEncoder(encoder, decoder_type="inner_product")

        # Execute
        z, adj_recon = autoencoder(sample_graph_data.x, sample_graph_data.edge_index)

        # Assert
        assert z.shape == (5, 64)  # Node embeddings
        assert adj_recon.shape == (5, 5)  # Reconstructed adjacency
        assert (adj_recon >= 0).all() and (adj_recon <= 1).all()  # Sigmoid output

    def test_autoencoder_forward_mlp(self, sample_graph_data):
        """Test forward pass with MLP decoder."""
        encoder = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )
        autoencoder = GraphAutoEncoder(encoder, decoder_type="mlp")

        # Execute
        z, adj_recon = autoencoder(sample_graph_data.x, sample_graph_data.edge_index)

        # Assert
        assert z.shape == (5, 64)
        assert adj_recon.shape[0] == sample_graph_data.edge_index.shape[1]

    def test_autoencoder_loss(self, sample_graph_data):
        """Test loss computation."""
        encoder = MusicGNN(
            in_channels=128,
            hidden_channels=256,
            out_channels=64,
            num_layers=2
        )
        autoencoder = GraphAutoEncoder(encoder)

        # Get embeddings
        z = encoder(sample_graph_data.x, sample_graph_data.edge_index)

        # Create negative edges
        neg_edge_index = torch.tensor([
            [0, 1, 2],
            [3, 4, 4]
        ], dtype=torch.long)

        # Execute
        loss = autoencoder.loss(z, sample_graph_data.edge_index, neg_edge_index)

        # Assert
        assert loss.item() > 0
        assert not torch.isnan(loss)
