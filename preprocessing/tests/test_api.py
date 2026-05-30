"""Tests for REST API endpoints."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.main import app

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_wav_path():
    """Return path to sample WAV file."""
    return TEST_DATA_DIR / "Sombras dormidas.wav"


@pytest.fixture
def sample_mp3_path():
    """Return path to sample MP3 file."""
    return TEST_DATA_DIR / "Sombras dormidas.mp3"


@pytest.fixture
def sample_midi_path():
    """Return path to sample MIDI file."""
    return TEST_DATA_DIR / "Sombras dormidas.mid"


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "preprocessing"
        assert "version" in data


class TestTokenizeEndpoints:
    """Tests for tokenization endpoints."""

    def test_tokenize_text(self, client):
        """Test text tokenization endpoint."""
        response = client.post(
            "/api/v1/tokenize/text",
            data={"text": "Create jazz in C major at 120 bpm"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "tokens" in data
        assert "features" in data
        assert "musical_context" in data

    def test_tokenize_text_empty(self, client):
        """Test text tokenization with empty text."""
        response = client.post(
            "/api/v1/tokenize/text",
            data={"text": ""}
        )

        assert response.status_code == 200

    def test_tokenize_midi(self, client, sample_midi_path):
        """Test MIDI tokenization endpoint."""
        if not sample_midi_path.exists():
            pytest.skip("MIDI test file not found")

        with open(sample_midi_path, "rb") as f:
            response = client.post(
                "/api/v1/tokenize/midi",
                files={"file": ("test.mid", f, "audio/midi")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "tokens" in data
        assert "num_tokens" in data
        assert "features" in data
        assert data["num_tokens"] > 0

    def test_tokenize_audio(self, client, sample_wav_path):
        """Test audio tokenization endpoint."""
        from src.audio.audio_to_midi import BASIC_PITCH_AVAILABLE

        if not BASIC_PITCH_AVAILABLE:
            pytest.skip("basic-pitch not available (requires Python 3.11 or earlier)")

        if not sample_wav_path.exists():
            pytest.skip("WAV test file not found")

        with open(sample_wav_path, "rb") as f:
            response = client.post(
                "/api/v1/tokenize/audio",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"onset_threshold": 0.5, "frame_threshold": 0.3}
            )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "tokens" in data


class TestFeaturesEndpoints:
    """Tests for feature extraction endpoints."""

    def test_extract_features(self, client, sample_wav_path):
        """Test feature extraction endpoint."""
        if not sample_wav_path.exists():
            pytest.skip("WAV test file not found")

        with open(sample_wav_path, "rb") as f:
            response = client.post(
                "/api/v1/features/extract",
                files={"file": ("test.wav", f, "audio/wav")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "tempo" in data
        assert "key" in data
        assert "time_signature" in data
        assert "duration" in data
        assert data["duration"] > 0

    def test_extract_features_mp3(self, client, sample_mp3_path):
        """Test feature extraction with MP3 file."""
        if not sample_mp3_path.exists():
            pytest.skip("MP3 test file not found")

        with open(sample_mp3_path, "rb") as f:
            response = client.post(
                "/api/v1/features/extract",
                files={"file": ("test.mp3", f, "audio/mpeg")}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["duration"] > 0

    def test_generate_spectrogram_mel(self, client, sample_wav_path):
        """Test mel spectrogram generation."""
        if not sample_wav_path.exists():
            pytest.skip("WAV test file not found")

        with open(sample_wav_path, "rb") as f:
            response = client.post(
                "/api/v1/features/spectrogram",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"spectrogram_type": "mel", "use_gpu": False}
            )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "mel_spectrogram" in data
        assert "n_mels" in data
        assert "n_frames" in data

    def test_generate_spectrogram_cqt(self, client, sample_wav_path):
        """Test CQT spectrogram generation."""
        if not sample_wav_path.exists():
            pytest.skip("WAV test file not found")

        with open(sample_wav_path, "rb") as f:
            response = client.post(
                "/api/v1/features/spectrogram",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"spectrogram_type": "cqt"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "cqt_spectrogram" in data

    def test_generate_spectrogram_mfcc(self, client, sample_wav_path):
        """Test MFCC spectrogram generation."""
        if not sample_wav_path.exists():
            pytest.skip("WAV test file not found")

        with open(sample_wav_path, "rb") as f:
            response = client.post(
                "/api/v1/features/spectrogram",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"spectrogram_type": "mfcc"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "mfcc" in data
        assert "n_mfcc" in data


class TestConversionEndpoints:
    """Tests for conversion endpoints."""

    def test_audio_to_midi(self, client, sample_wav_path):
        """Test audio to MIDI conversion."""
        from src.audio.audio_to_midi import BASIC_PITCH_AVAILABLE

        if not BASIC_PITCH_AVAILABLE:
            pytest.skip("basic-pitch not available (requires Python 3.11 or earlier)")

        if not sample_wav_path.exists():
            pytest.skip("WAV test file not found")

        with open(sample_wav_path, "rb") as f:
            response = client.post(
                "/api/v1/convert/audio-to-midi",
                files={"file": ("test.wav", f, "audio/wav")},
                data={
                    "onset_threshold": 0.5,
                    "frame_threshold": 0.3,
                    "min_note_length": 0.058
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "num_notes" in data
        assert "notes" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_file_format(self, client):
        """Test handling of invalid file format."""
        # Create a fake file with wrong extension
        response = client.post(
            "/api/v1/tokenize/midi",
            files={"file": ("test.txt", b"not a midi file", "text/plain")}
        )

        assert response.status_code == 400

    def test_missing_file(self, client):
        """Test handling of missing file."""
        response = client.post("/api/v1/tokenize/midi")

        assert response.status_code == 422  # Validation error
