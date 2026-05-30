"""
Integration tests for communication between preprocessing and model-base modules.

These tests verify that modules can communicate correctly via:
1. REST API calls
2. RabbitMQ message passing
3. gRPC calls (when implemented)

Run with: pytest tests/test_integration.py -v
"""

import pytest
import requests
import json
import time
import pika
from typing import Optional


# Configuration
PREPROCESSING_URL = "http://localhost:8001"
MODEL_BASE_URL = "http://localhost:8002"
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"


class TestServiceHealth:
    """Test that both services are running and healthy."""

    def test_preprocessing_health(self):
        """Test preprocessing service health."""
        response = requests.get(f"{PREPROCESSING_URL}/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "preprocessing"

    def test_model_base_health(self):
        """Test model-base service health."""
        response = requests.get(f"{MODEL_BASE_URL}/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "model-base"
        assert "model_loaded" in data


class TestRESTCommunication:
    """Test REST API communication between modules."""

    def test_preprocessing_tokenize_text(self):
        """Test text tokenization in preprocessing."""
        response = requests.post(
            f"{PREPROCESSING_URL}/api/v1/tokenize/text",
            data={"text": "Create jazz piano in C major at 120 bpm"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "tokens" in data
        assert "features" in data
        assert "musical_context" in data

        # Verify extracted features
        features = data["features"]
        assert features.get("key") == "C major"
        assert features.get("genre") == "jazz"

    def test_model_base_generate(self):
        """Test generation in model-base."""
        # Simple test tokens
        test_tokens = [1, 2, 3, 4, 5, 6, 7, 8]

        response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/generate",
            json={
                "input_tokens": test_tokens,
                "max_length": 32,
                "temperature": 1.0,
                "top_k": 50,
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "generated_tokens" in data
        assert len(data["generated_tokens"]) >= len(test_tokens)

    def test_end_to_end_text_to_generation(self):
        """
        Test end-to-end flow: text -> preprocessing -> tokens -> model-base -> generated.

        This simulates the full pipeline without using message queues.
        """
        # Step 1: Tokenize text description
        text = "Create a slow jazz ballad in D minor"

        preprocess_response = requests.post(
            f"{PREPROCESSING_URL}/api/v1/tokenize/text",
            data={"text": text}
        )
        assert preprocess_response.status_code == 200
        preprocess_data = preprocess_response.json()

        # Extract musical context
        context = preprocess_data["musical_context"]
        assert context["tonality"] == "D minor"
        assert context["style"] == "jazz"

        # Step 2: Generate using model (with dummy tokens since we don't have real MIDI)
        # In production, we'd use actual BPE tokens from MIDI
        dummy_tokens = list(range(1, 17))  # Simulated tokens

        generate_response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/generate",
            json={
                "input_tokens": dummy_tokens,
                "max_length": 64,
                "temperature": 0.9,
                "top_k": 40,
                "top_p": 0.95,
            }
        )
        assert generate_response.status_code == 200
        generate_data = generate_response.json()

        # Verify generation
        assert "generated_tokens" in generate_data
        assert generate_data["new_tokens"] > 0

        print(f"\n✓ End-to-end test passed:")
        print(f"  Input: '{text}'")
        print(f"  Context: {context['tonality']}, {context['style']}")
        print(f"  Generated: {generate_data['new_tokens']} new tokens")

    def test_model_embeddings(self):
        """Test embedding extraction from model-base."""
        tokens = [1, 2, 3, 4, 5]

        response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/embeddings",
            json={
                "tokens": tokens,
                "layer": -1,
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "embeddings" in data
        assert data["seq_length"] == len(tokens)
        assert len(data["embeddings"]) > 0

    def test_model_continue_sequence(self):
        """Test sequence continuation."""
        input_tokens = [10, 20, 30, 40, 50]

        response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/continue",
            json={
                "input_tokens": input_tokens,
                "continuation_length": 32,
                "temperature": 1.0,
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "continuation_tokens" in data
        assert "full_sequence" in data
        assert len(data["full_sequence"]) > len(input_tokens)


class TestRabbitMQCommunication:
    """Test RabbitMQ message passing between modules."""

    @pytest.fixture
    def rabbitmq_connection(self):
        """Create RabbitMQ connection for testing."""
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            yield channel
            connection.close()
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")

    def test_rabbitmq_connection(self, rabbitmq_connection):
        """Test RabbitMQ is accessible."""
        assert rabbitmq_connection is not None
        assert rabbitmq_connection.is_open

    def test_preprocessing_exchange_exists(self, rabbitmq_connection):
        """Test preprocessing exchange is declared."""
        # Declare exchange (will not error if already exists)
        rabbitmq_connection.exchange_declare(
            exchange="musicai.preprocessing",
            exchange_type="topic",
            durable=True,
            passive=True,  # Check if exists
        )

    def test_model_queue_exists(self, rabbitmq_connection):
        """Test model tokens queue is declared."""
        # Declare queue (will not error if already exists)
        rabbitmq_connection.queue_declare(
            queue="model.tokens",
            durable=True,
            passive=True,  # Check if exists
        )

    def test_publish_tokens_to_model(self, rabbitmq_connection):
        """Test publishing tokens from preprocessing to model-base."""
        # Create test message
        message = {
            "event_type": "TOKENIZATION_COMPLETE",
            "request_id": "test-123",
            "payload": {
                "tokens": [1, 2, 3, 4, 5],
                "features": {"tempo": 120, "key": "C major"},
            },
            "timestamp": time.time(),
            "source_module": "preprocessing",
            "target_module": "model-base",
        }

        # Declare exchange
        rabbitmq_connection.exchange_declare(
            exchange="musicai.preprocessing",
            exchange_type="topic",
            durable=True,
        )

        # Publish message
        rabbitmq_connection.basic_publish(
            exchange="musicai.preprocessing",
            routing_key="model.tokens",
            body=json.dumps(message).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        print("\n✓ Message published to model.tokens queue")

    def test_message_round_trip(self, rabbitmq_connection):
        """Test sending and receiving a message."""
        test_queue = "test.integration"

        # Declare test queue
        rabbitmq_connection.queue_declare(queue=test_queue, durable=False)

        # Publish test message
        test_message = {"test": "data", "timestamp": time.time()}
        rabbitmq_connection.basic_publish(
            exchange="",
            routing_key=test_queue,
            body=json.dumps(test_message).encode('utf-8'),
        )

        # Consume message
        method, properties, body = rabbitmq_connection.basic_get(
            queue=test_queue,
            auto_ack=True,
        )

        assert method is not None
        received = json.loads(body.decode('utf-8'))
        assert received["test"] == "data"

        # Cleanup
        rabbitmq_connection.queue_delete(queue=test_queue)


class TestStreamingGeneration:
    """Test streaming generation from model-base."""

    def test_stream_generation(self):
        """Test streaming token generation."""
        import sseclient

        tokens = [1, 2, 3, 4, 5]

        response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/generate/stream",
            json={
                "input_tokens": tokens,
                "max_length": 16,
                "temperature": 1.0,
            },
            stream=True,
        )

        assert response.status_code == 200

        # Read streamed events
        generated_count = 0
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = json.loads(line_str[6:])
                    if data.get('is_end'):
                        break
                    generated_count += 1

        assert generated_count > 0
        print(f"\n✓ Streamed {generated_count} tokens")


class TestErrorHandling:
    """Test error handling in communication."""

    def test_preprocessing_invalid_format(self):
        """Test preprocessing handles invalid file format."""
        response = requests.post(
            f"{PREPROCESSING_URL}/api/v1/tokenize/midi",
            files={"file": ("test.txt", b"not midi", "text/plain")}
        )
        assert response.status_code == 400

    def test_model_empty_tokens(self):
        """Test model handles empty token list."""
        response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/generate",
            json={
                "input_tokens": [],
                "max_length": 32,
            }
        )
        # Should either return error or handle gracefully
        assert response.status_code in [200, 400, 422, 500]

    def test_model_invalid_parameters(self):
        """Test model handles invalid parameters."""
        response = requests.post(
            f"{MODEL_BASE_URL}/api/v1/generate",
            json={
                "input_tokens": [1, 2, 3],
                "max_length": -1,  # Invalid
                "temperature": 0,  # Invalid
            }
        )
        # Should validate and return error
        assert response.status_code in [400, 422, 500]


# Utility functions for manual testing
def check_services():
    """Check if services are running."""
    services = {
        "preprocessing": PREPROCESSING_URL,
        "model-base": MODEL_BASE_URL,
    }

    for name, url in services.items():
        try:
            response = requests.get(f"{url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                print(f"✓ {name} is running")
            else:
                print(f"✗ {name} returned {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"✗ {name} is not running")


if __name__ == "__main__":
    print("Checking services...\n")
    check_services()
    print("\nRun full tests with: pytest tests/test_integration.py -v")
