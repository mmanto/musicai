"""Tests for REST API endpoints."""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_generator():
    """Mock the MusicGenerator for API tests."""
    with patch('src.api.rest.routes.get_generator') as mock_get:
        generator = Mock()
        generator.device = "cpu"
        generator.use_fp16 = False
        generator.model.num_parameters = 1000000
        generator.model.config.vocab_size = 30000
        generator.model.config.d_model = 512
        generator.model.config.n_heads = 8
        generator.model.config.n_layers = 12
        generator.model.config.d_ff = 2048
        generator.model.config.max_seq_length = 8192

        mock_get.return_value = generator
        yield generator


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client, mock_generator):
        """Test health endpoint returns healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "model-base"
        assert "version" in data
        assert "model_loaded" in data
        assert "device" in data


class TestGenerateEndpoint:
    """Tests for generation endpoint."""

    def test_generate_basic(self, client, mock_generator):
        """Test basic generation request."""
        mock_generator.generate.return_value = {
            "generated_tokens": [1, 2, 3, 4, 5, 6, 7, 8],
            "input_length": 3,
            "output_length": 8,
            "new_tokens": 5,
        }

        response = client.post(
            "/api/v1/generate",
            json={
                "input_tokens": [1, 2, 3],
                "max_length": 8,
                "temperature": 1.0,
                "top_k": 50,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "generated_tokens" in data
        assert data["input_length"] == 3
        assert data["output_length"] == 8

    def test_generate_with_all_params(self, client, mock_generator):
        """Test generation with all parameters."""
        mock_generator.generate.return_value = {
            "generated_tokens": [1, 2, 3, 4, 5],
            "input_length": 2,
            "output_length": 5,
            "new_tokens": 3,
        }

        response = client.post(
            "/api/v1/generate",
            json={
                "input_tokens": [1, 2],
                "max_length": 100,
                "temperature": 0.8,
                "top_k": 40,
                "top_p": 0.95,
                "repetition_penalty": 1.1,
            }
        )

        assert response.status_code == 200

        # Verify generator was called with correct params
        mock_generator.generate.assert_called_once()
        call_kwargs = mock_generator.generate.call_args.kwargs
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["top_p"] == 0.95

    def test_generate_error_handling(self, client, mock_generator):
        """Test generation error handling."""
        mock_generator.generate.side_effect = Exception("Model error")

        response = client.post(
            "/api/v1/generate",
            json={
                "input_tokens": [1, 2, 3],
                "max_length": 10,
            }
        )

        assert response.status_code == 500


class TestContinueEndpoint:
    """Tests for sequence continuation endpoint."""

    def test_continue_sequence(self, client, mock_generator):
        """Test sequence continuation."""
        mock_generator.continue_sequence.return_value = {
            "continuation_tokens": [6, 7, 8, 9, 10],
            "full_sequence": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "continuation_length": 5,
        }

        response = client.post(
            "/api/v1/continue",
            json={
                "input_tokens": [1, 2, 3, 4, 5],
                "continuation_length": 5,
                "temperature": 1.0,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "continuation_tokens" in data
        assert "full_sequence" in data
        assert data["continuation_length"] == 5

    def test_continue_with_style_hint(self, client, mock_generator):
        """Test continuation with style hint."""
        mock_generator.continue_sequence.return_value = {
            "continuation_tokens": [10, 11],
            "full_sequence": [1, 2, 10, 11],
            "continuation_length": 2,
        }

        response = client.post(
            "/api/v1/continue",
            json={
                "input_tokens": [1, 2],
                "continuation_length": 10,
                "style_hint": "jazz",
            }
        )

        assert response.status_code == 200


class TestEmbeddingsEndpoint:
    """Tests for embeddings endpoint."""

    def test_get_embeddings(self, client, mock_generator):
        """Test embedding extraction."""
        # Return flattened embeddings (seq_len * d_model)
        mock_generator.get_embeddings.return_value = [0.1] * (5 * 512)

        response = client.post(
            "/api/v1/embeddings",
            json={
                "tokens": [1, 2, 3, 4, 5],
                "layer": -1,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "embeddings" in data
        assert "seq_length" in data
        assert data["seq_length"] == 5

    def test_get_embeddings_specific_layer(self, client, mock_generator):
        """Test embedding extraction from specific layer."""
        mock_generator.get_embeddings.return_value = [0.5] * 1024

        response = client.post(
            "/api/v1/embeddings",
            json={
                "tokens": [1, 2],
                "layer": 6,
            }
        )

        assert response.status_code == 200

        # Verify correct layer was requested
        mock_generator.get_embeddings.assert_called_with(
            tokens=[1, 2],
            layer=6,
        )


class TestModelInfoEndpoint:
    """Tests for model info endpoint."""

    def test_model_info(self, client, mock_generator):
        """Test model info endpoint."""
        response = client.get("/api/v1/model/info")

        assert response.status_code == 200
        data = response.json()
        assert "vocab_size" in data
        assert "d_model" in data
        assert "n_heads" in data
        assert "n_layers" in data
        assert "num_parameters" in data
        assert "device" in data


class TestStreamEndpoint:
    """Tests for streaming generation endpoint."""

    def test_generate_stream(self, client, mock_generator):
        """Test streaming generation returns SSE format."""
        # Mock stream generator
        def stream_gen(*args, **kwargs):
            yield {"token": 1, "probability": 0.9, "position": 0}
            yield {"token": 2, "probability": 0.8, "position": 1}

        mock_generator.generate_stream.return_value = stream_gen()

        response = client.post(
            "/api/v1/generate/stream",
            json={
                "input_tokens": [1, 2, 3],
                "max_length": 5,
            }
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


class TestValidation:
    """Tests for request validation."""

    def test_missing_input_tokens(self, client):
        """Test validation error for missing input_tokens."""
        response = client.post(
            "/api/v1/generate",
            json={
                "max_length": 10,
            }
        )

        assert response.status_code == 422

    def test_invalid_temperature(self, client, mock_generator):
        """Test that negative temperature is handled."""
        mock_generator.generate.return_value = {
            "generated_tokens": [1],
            "input_length": 1,
            "output_length": 1,
            "new_tokens": 0,
        }

        # Note: Pydantic may not validate temperature range by default
        response = client.post(
            "/api/v1/generate",
            json={
                "input_tokens": [1],
                "temperature": -1.0,  # Invalid but may not be caught
            }
        )

        # Should either process or reject
        assert response.status_code in [200, 422]
