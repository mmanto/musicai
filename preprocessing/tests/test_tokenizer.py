"""Tests for tokenizer module."""

import pytest
import allure
import json
from pathlib import Path
from src.tokenizer import TextTokenizer, BPETokenizer

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@allure.epic("Tokenization")
@allure.feature("Text Tokenizer")
class TestTextTokenizer:
    """Tests for TextTokenizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tokenizer = TextTokenizer()

    @allure.title("Basic text tokenization")
    @allure.description("Test basic text tokenization with musical prompt")
    def test_tokenize_basic(self):
        """Test basic text tokenization."""
        text = "Create a jazz progression in C major"

        with allure.step("Tokenize musical prompt"):
            allure.attach(
                json.dumps({"input_text": text}, indent=2),
                name="Input",
                attachment_type=allure.attachment_type.JSON
            )
            result = self.tokenizer.tokenize(text)
            allure.attach(
                json.dumps({
                    "tokens": result["tokens"],
                    "num_tokens": len(result["tokens"]),
                    "features": result["features"]
                }, indent=2, default=str),
                name="Output",
                attachment_type=allure.attachment_type.JSON
            )

        assert "tokens" in result
        assert "features" in result
        assert len(result["tokens"]) > 0

    def test_extract_key_major(self):
        """Test key extraction for major keys."""
        text = "C major chord progression"
        result = self.tokenizer.tokenize(text)

        assert result["features"]["key"] == "C major"

    def test_extract_key_minor(self):
        """Test key extraction for minor keys."""
        text = "A minor scale"
        result = self.tokenizer.tokenize(text)

        assert result["features"]["key"] == "A minor"

    def test_extract_key_sharp(self):
        """Test key extraction with sharps."""
        text = "F# minor melody"
        result = self.tokenizer.tokenize(text)

        assert result["features"]["key"] == "F# minor"

    def test_extract_genre_jazz(self):
        """Test genre extraction."""
        text = "Create jazz music"
        result = self.tokenizer.tokenize(text)

        assert result["features"]["genre"] == "jazz"

    def test_extract_tempo_word(self):
        """Test tempo extraction from words."""
        text = "Fast rock beat"
        result = self.tokenizer.tokenize(text)

        tempo_range = result["features"]["tempo_range"]
        assert tempo_range is not None
        assert tempo_range[0] >= 120  # Fast tempo

    def test_extract_tempo_bpm(self):
        """Test tempo extraction from BPM value."""
        text = "120 bpm drum pattern"
        result = self.tokenizer.tokenize(text)

        tempo_range = result["features"]["tempo_range"]
        assert tempo_range is not None
        assert 110 <= tempo_range[0] <= 130

    def test_extract_chords(self):
        """Test chord extraction."""
        text = "Progression with Cmaj7, Dm7, G7"
        result = self.tokenizer.tokenize(text)

        chords = result["features"]["chord_mentions"]
        assert "Cmaj7" in chords
        assert "Dm7" in chords
        assert "G7" in chords

    def test_extract_instruments(self):
        """Test instrument extraction."""
        text = "Piano and guitar duet"
        result = self.tokenizer.tokenize(text)

        instruments = result["features"]["instruments"]
        assert "piano" in instruments
        assert "guitar" in instruments

    def test_get_musical_context(self):
        """Test musical context extraction."""
        text = "Jazz piano in Dm with tritone substitution"
        context = self.tokenizer.get_musical_context(text)

        assert context["tonality"] == "D minor"
        assert context["style"] == "jazz"
        assert "piano" in context["instrumentation"]

    def test_empty_text(self):
        """Test handling of empty text."""
        result = self.tokenizer.tokenize("")
        assert result["tokens"] == []

    def test_no_musical_features(self):
        """Test text with no musical features."""
        text = "Hello world"
        result = self.tokenizer.tokenize(text)

        assert result["features"]["key"] is None
        assert result["features"]["genre"] is None


@allure.epic("Tokenization")
@allure.feature("BPE Tokenizer")
class TestBPETokenizer:
    """Tests for BPE tokenizer (requires MidiTok)."""

    @pytest.fixture
    def tokenizer(self):
        """Create BPE tokenizer instance."""
        return BPETokenizer(vocab_size=1000)

    @pytest.fixture
    def midi_file_path(self):
        """Return path to test MIDI file."""
        return TEST_DATA_DIR / "Sombras dormidas.mid"

    @allure.title("Tokenize MIDI file")
    @allure.description("Test MIDI tokenization with BPE tokenizer")
    def test_tokenize_midi(self, tokenizer, midi_file_path):
        """Test MIDI tokenization."""
        if not midi_file_path.exists():
            pytest.skip("MIDI test file not found")

        midi_data = midi_file_path.read_bytes()

        with allure.step("Tokenize MIDI file"):
            allure.attach(
                json.dumps({
                    "file": str(midi_file_path.name),
                    "size_bytes": len(midi_data),
                    "vocab_size": tokenizer.vocab_size
                }, indent=2),
                name="Input",
                attachment_type=allure.attachment_type.JSON
            )
            result = tokenizer.tokenize_midi(midi_data)
            allure.attach(
                json.dumps({
                    "num_tokens": len(result["tokens"]),
                    "tokens_sample": result["tokens"][:20],
                    "features": result["features"]
                }, indent=2, default=str),
                name="Output",
                attachment_type=allure.attachment_type.JSON
            )

        assert "tokens" in result
        assert "features" in result
        assert "embeddings" in result
        assert len(result["tokens"]) > 0
        assert result["features"]["num_tokens"] > 0

    def test_tokenize_midi_features(self, tokenizer, midi_file_path):
        """Test that MIDI tokenization extracts features."""
        if not midi_file_path.exists():
            pytest.skip("MIDI test file not found")

        midi_data = midi_file_path.read_bytes()
        result = tokenizer.tokenize_midi(midi_data)

        assert "num_tokens" in result["features"]
        assert "num_programs" in result["features"]
        assert result["features"]["num_programs"] >= 0

    def test_tokenizer_properties(self, tokenizer):
        """Test tokenizer properties."""
        assert tokenizer.vocab_size == 1000
        assert tokenizer.max_seq_length > 0
        assert not tokenizer.is_trained  # Not trained yet

    def test_train_bpe(self, tokenizer, midi_file_path):
        """Test BPE training with single file."""
        if not midi_file_path.exists():
            pytest.skip("MIDI test file not found")

        # Train with single file (minimal training)
        tokenizer.train([midi_file_path])

        assert tokenizer.is_trained
        assert tokenizer.vocab_size_actual > 0

    def test_decode_tokens(self, tokenizer, midi_file_path):
        """Test decoding tokens back to MIDI."""
        if not midi_file_path.exists():
            pytest.skip("MIDI test file not found")

        midi_data = midi_file_path.read_bytes()
        result = tokenizer.tokenize_midi(midi_data)

        # Decode back to MIDI
        decoded_midi = tokenizer.decode(result["tokens"])

        # Should return valid MIDI bytes
        assert isinstance(decoded_midi, bytes)
        assert len(decoded_midi) > 0
        # MIDI files start with "MThd"
        assert decoded_midi[:4] == b'MThd'

    @allure.title("Tokenize from note dictionaries")
    @allure.description("Test tokenization from note dictionaries (C-E-G chord)")
    def test_tokenize_from_notes(self, tokenizer):
        """Test tokenization from note dictionaries."""
        notes = [
            {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 64},
            {"pitch": 64, "start_time": 0.5, "duration": 0.5, "velocity": 64},
            {"pitch": 67, "start_time": 1.0, "duration": 0.5, "velocity": 64},
        ]

        with allure.step("Tokenize C major chord (C4-E4-G4)"):
            allure.attach(
                json.dumps({"notes": notes}, indent=2),
                name="Input Notes",
                attachment_type=allure.attachment_type.JSON
            )
            result = tokenizer.tokenize_from_notes(notes)
            allure.attach(
                json.dumps({
                    "num_tokens": len(result["tokens"]),
                    "tokens": result["tokens"],
                    "features": result["features"]
                }, indent=2, default=str),
                name="Output Tokens",
                attachment_type=allure.attachment_type.JSON
            )

        assert "tokens" in result
        assert len(result["tokens"]) > 0
        assert result["features"]["num_notes"] == 3.0

    def test_truncation(self, midi_file_path):
        """Test that long sequences are truncated."""
        # Create tokenizer with small max length
        tokenizer = BPETokenizer(vocab_size=1000)
        tokenizer.max_seq_length = 100  # Force small max length

        if not midi_file_path.exists():
            pytest.skip("MIDI test file not found")

        midi_data = midi_file_path.read_bytes()
        result = tokenizer.tokenize_midi(midi_data)

        # Tokens should be truncated to max length
        assert len(result["tokens"]) <= 100
