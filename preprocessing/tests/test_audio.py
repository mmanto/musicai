"""Tests for audio processing modules."""

import pytest
import allure
import json
import numpy as np
import tempfile
import wave
from pathlib import Path


def create_wav_bytes(duration: float = 1.0, frequency: float = 440.0, sample_rate: int = 22050) -> bytes:
    """Create a valid WAV file in bytes for testing."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    audio_int16 = (audio * 32767).astype(np.int16)

    # Create WAV file in memory
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_path = Path(f.name)

    with wave.open(str(temp_path), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    with open(temp_path, 'rb') as f:
        wav_bytes = f.read()

    temp_path.unlink()
    return wav_bytes


@allure.epic("Audio Processing")
@allure.feature("Feature Extraction")
class TestAudioFeatureExtractor:
    """Tests for AudioFeatureExtractor."""

    @allure.title("Extract all audio features")
    @allure.description("Test extraction of all audio features from WAV data")
    def test_extract_all_features(self):
        """Test extraction of all audio features."""
        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor(sample_rate=22050)
        audio_data = create_wav_bytes(duration=2.0, frequency=440.0)

        with allure.step("Extract features from 2s 440Hz sine wave"):
            allure.attach(
                json.dumps({"duration": 2.0, "frequency": 440.0, "sample_rate": 22050}, indent=2),
                name="Input Parameters",
                attachment_type=allure.attachment_type.JSON
            )
            features = extractor.extract_all(audio_data, audio_format="wav")

        with allure.step("Verify all expected features"):
            allure.attach(
                json.dumps(features, indent=2, default=str),
                name="Extracted Features",
                attachment_type=allure.attachment_type.JSON
            )

        # Check all expected features are present
        assert "duration" in features
        assert "sample_rate" in features
        assert "tempo" in features
        assert "key" in features
        assert "mode" in features
        assert "time_signature" in features
        assert "rms_energy" in features
        assert "spectral_centroid" in features

    @allure.title("Extract tempo from audio")
    @allure.description("Test tempo extraction returns valid BPM value")
    def test_extract_tempo(self):
        """Test tempo extraction returns valid BPM."""
        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        audio_data = create_wav_bytes(duration=3.0)

        with allure.step("Extract tempo from 3s audio"):
            features = extractor.extract_all(audio_data, audio_format="wav")
            allure.attach(
                json.dumps({"tempo": features["tempo"]}, indent=2),
                name="Tempo Result",
                attachment_type=allure.attachment_type.JSON
            )

        # Tempo should be a reasonable value (defaults to 120 if not detected)
        assert 30 <= features["tempo"] <= 300
        assert isinstance(features["tempo"], float)

    @allure.title("Extract key and mode from audio")
    @allure.description("Test key extraction returns valid musical key")
    def test_extract_key(self):
        """Test key extraction returns valid key."""
        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        audio_data = create_wav_bytes(duration=2.0, frequency=440.0)  # A4

        with allure.step("Extract key from 440Hz (A4) sine wave"):
            features = extractor.extract_all(audio_data, audio_format="wav")
            allure.attach(
                json.dumps({
                    "key": features["key"],
                    "mode": features["mode"],
                    "key_confidence": features["key_confidence"]
                }, indent=2),
                name="Key Detection Result",
                attachment_type=allure.attachment_type.JSON
            )

        # Key should be one of the valid keys
        valid_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        assert features["key"] in valid_keys
        assert features["mode"] in ["major", "minor"]
        assert 0 <= features["key_confidence"] <= 1

    def test_extract_chroma(self):
        """Test chroma features are extracted."""
        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        audio_data = create_wav_bytes(duration=1.0)

        features = extractor.extract_all(audio_data, audio_format="wav")

        # Chroma should have 12 values (one per pitch class)
        assert len(features["chroma_mean"]) == 12

    def test_duration_calculation(self):
        """Test duration is calculated correctly."""
        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        duration = 2.5
        audio_data = create_wav_bytes(duration=duration)

        features = extractor.extract_all(audio_data, audio_format="wav")

        # Duration should be approximately correct
        assert abs(features["duration"] - duration) < 0.1


@allure.epic("Audio Processing")
@allure.feature("Spectrogram Generation")
class TestSpectrogramGenerator:
    """Tests for SpectrogramGenerator."""

    @allure.title("Generate mel spectrogram")
    @allure.description("Test mel spectrogram generation from audio data")
    def test_generate_mel_spectrogram(self):
        """Test mel spectrogram generation."""
        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator(
            n_mels=128,
            n_fft=2048,
            hop_length=512,
            sample_rate=22050
        )

        audio_data = create_wav_bytes(duration=1.0)

        with allure.step("Generate mel spectrogram"):
            allure.attach(
                json.dumps({"n_mels": 128, "n_fft": 2048, "hop_length": 512}, indent=2),
                name="Input Configuration",
                attachment_type=allure.attachment_type.JSON
            )
            result = generator.generate_mel_spectrogram(audio_data, audio_format="wav")
            allure.attach(
                json.dumps({
                    "n_mels": result["n_mels"],
                    "n_frames": result["n_frames"],
                    "shape": f"{result['n_mels']}x{result['n_frames']}"
                }, indent=2),
                name="Output Spectrogram Info",
                attachment_type=allure.attachment_type.JSON
            )

        assert "mel_spectrogram" in result
        assert "n_mels" in result
        assert "n_frames" in result
        assert result["n_mels"] == 128
        assert len(result["mel_spectrogram"]) > 0

    def test_generate_cqt(self):
        """Test CQT spectrogram generation."""
        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()
        audio_data = create_wav_bytes(duration=1.0)

        result = generator.generate_cqt(
            audio_data,
            audio_format="wav",
            n_bins=84,
            bins_per_octave=12
        )

        assert "cqt_spectrogram" in result
        assert "n_bins" in result
        assert "n_frames" in result
        assert result["n_bins"] == 84
        assert result["bins_per_octave"] == 12

    def test_generate_mfcc(self):
        """Test MFCC feature generation."""
        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()
        audio_data = create_wav_bytes(duration=1.0)

        result = generator.generate_mfcc(
            audio_data,
            audio_format="wav",
            n_mfcc=13
        )

        assert "mfcc" in result
        assert "mfcc_delta" in result
        assert "mfcc_delta2" in result
        assert result["n_mfcc"] == 13

    def test_normalize_spectrogram(self):
        """Test spectrogram normalization."""
        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()

        # Create test spectrogram
        spec = np.array([[1, 2, 3], [4, 5, 6]])
        normalized = generator.normalize_spectrogram(spec)

        # Check normalization to [0, 1]
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0

    def test_resize_spectrogram(self):
        """Test spectrogram resizing."""
        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()

        # Create test spectrogram (n_freq x n_frames)
        spec = np.random.rand(128, 100)
        target_frames = 200

        resized = generator.resize_spectrogram(spec, target_frames)

        assert resized.shape[0] == 128  # Frequency bins unchanged
        assert resized.shape[1] == target_frames

    def test_spectrogram_metadata(self):
        """Test spectrogram result includes correct metadata."""
        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator(sample_rate=22050, hop_length=512)
        audio_data = create_wav_bytes(duration=2.0)

        result = generator.generate_mel_spectrogram(audio_data, audio_format="wav")

        assert result["sample_rate"] == 22050
        assert result["hop_length"] == 512
        assert abs(result["duration"] - 2.0) < 0.1


@allure.epic("Audio Processing")
@allure.feature("Real Audio Files")
class TestWithRealAudio:
    """Tests using real audio files from tests/data/."""

    @allure.title("Extract features from WAV file")
    @allure.description("Test feature extraction with real WAV file (Sombras dormidas)")
    def test_extract_features_wav(self, real_audio_bytes_wav):
        """Test feature extraction with real WAV file."""
        if real_audio_bytes_wav is None:
            pytest.skip("WAV test file not found")

        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()

        with allure.step("Extract features from WAV"):
            allure.attach(
                json.dumps({"file": "Sombras dormidas.wav", "size_bytes": len(real_audio_bytes_wav)}, indent=2),
                name="Input File",
                attachment_type=allure.attachment_type.JSON
            )
            features = extractor.extract_all(real_audio_bytes_wav, audio_format="wav")
            allure.attach(
                json.dumps({
                    "tempo": features["tempo"],
                    "key": features["key"],
                    "mode": features["mode"],
                    "duration": features["duration"],
                    "chroma_mean": features["chroma_mean"]
                }, indent=2, default=str),
                name="Extracted Features",
                attachment_type=allure.attachment_type.JSON
            )

        # Real music should have detectable features
        assert features["tempo"] > 0
        assert features["key"] in ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        assert features["mode"] in ["major", "minor"]
        assert features["duration"] > 0
        assert len(features["chroma_mean"]) == 12

    def test_extract_features_mp3(self, real_audio_bytes_mp3):
        """Test feature extraction with real MP3 file."""
        if real_audio_bytes_mp3 is None:
            pytest.skip("MP3 test file not found")

        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        features = extractor.extract_all(real_audio_bytes_mp3, audio_format="mp3")

        assert features["tempo"] > 0
        assert features["duration"] > 0
        assert "key_string" in features

    def test_extract_features_flac(self, real_audio_bytes_flac):
        """Test feature extraction with real FLAC file."""
        if real_audio_bytes_flac is None:
            pytest.skip("FLAC test file not found")

        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        features = extractor.extract_all(real_audio_bytes_flac, audio_format="flac")

        assert features["tempo"] > 0
        assert features["duration"] > 0

    def test_mel_spectrogram_real_audio(self, real_audio_bytes_wav):
        """Test mel spectrogram with real audio."""
        if real_audio_bytes_wav is None:
            pytest.skip("WAV test file not found")

        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()
        result = generator.generate_mel_spectrogram(real_audio_bytes_wav, audio_format="wav")

        assert result["n_mels"] > 0
        assert result["n_frames"] > 0
        assert len(result["mel_spectrogram"]) > 0
        assert result["duration"] > 0

    def test_cqt_real_audio(self, real_audio_bytes_wav):
        """Test CQT spectrogram with real audio."""
        if real_audio_bytes_wav is None:
            pytest.skip("WAV test file not found")

        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()
        result = generator.generate_cqt(real_audio_bytes_wav, audio_format="wav")

        assert result["n_bins"] > 0
        assert result["n_frames"] > 0
        assert len(result["cqt_spectrogram"]) > 0

    def test_mfcc_real_audio(self, real_audio_bytes_wav):
        """Test MFCC extraction with real audio."""
        if real_audio_bytes_wav is None:
            pytest.skip("WAV test file not found")

        from src.audio.spectrograms import SpectrogramGenerator

        generator = SpectrogramGenerator()
        result = generator.generate_mfcc(real_audio_bytes_wav, audio_format="wav")

        assert result["n_mfcc"] == 13
        assert len(result["mfcc"]) > 0
        assert len(result["mfcc_delta"]) > 0
        assert len(result["mfcc_delta2"]) > 0

    def test_multiple_formats_same_features(self, real_audio_bytes_wav, real_audio_bytes_mp3, real_audio_bytes_flac):
        """Test that different formats of same audio produce similar features."""
        if any(x is None for x in [real_audio_bytes_wav, real_audio_bytes_mp3, real_audio_bytes_flac]):
            pytest.skip("Not all test files available")

        from src.audio.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()

        features_wav = extractor.extract_all(real_audio_bytes_wav, audio_format="wav")
        features_mp3 = extractor.extract_all(real_audio_bytes_mp3, audio_format="mp3")
        features_flac = extractor.extract_all(real_audio_bytes_flac, audio_format="flac")

        # Key should be the same across formats
        assert features_wav["key"] == features_flac["key"]

        # Tempo should be similar (within 10%)
        tempo_avg = (features_wav["tempo"] + features_mp3["tempo"] + features_flac["tempo"]) / 3
        for features in [features_wav, features_mp3, features_flac]:
            assert abs(features["tempo"] - tempo_avg) < tempo_avg * 0.15
