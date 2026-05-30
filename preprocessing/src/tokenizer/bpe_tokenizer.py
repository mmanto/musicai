"""BPE Tokenizer for symbolic music using MidiTok."""

import logging
from pathlib import Path
from typing import Optional
import tempfile

from miditok import REMI, TokenizerConfig
from symusic import Score
import numpy as np

from ..config import get_settings

logger = logging.getLogger(__name__)


class BPETokenizer:
    """
    BPE Tokenizer for MIDI/symbolic music.

    Uses MidiTok's REMI tokenization with BPE compression for
    efficient sequence representation.
    """

    def __init__(self, vocab_size: Optional[int] = None):
        """
        Initialize the BPE tokenizer.

        Args:
            vocab_size: Size of BPE vocabulary. Defaults to config value.
        """
        settings = get_settings()
        self.vocab_size = vocab_size or settings.BPE_VOCAB_SIZE
        self.max_seq_length = settings.MAX_SEQ_LENGTH

        # Configure tokenizer
        config = TokenizerConfig(
            num_velocities=32,
            use_chords=True,
            use_rests=True,
            use_tempos=True,
            use_time_signatures=True,
            use_programs=True,
            nb_tempos=32,
            tempo_range=(40, 250),
        )

        self.tokenizer = REMI(config)
        self._is_trained = False
        logger.info(f"BPE Tokenizer initialized with vocab_size={self.vocab_size}")

    def train(self, midi_files: list[Path]) -> None:
        """
        Train BPE tokenizer on a corpus of MIDI files.

        Args:
            midi_files: List of paths to MIDI files for training.
        """
        if not midi_files:
            raise ValueError("No MIDI files provided for training")

        logger.info(f"Training BPE tokenizer on {len(midi_files)} files")

        # Learn BPE
        self.tokenizer.train(
            vocab_size=self.vocab_size,
            files_paths=midi_files,
        )

        self._is_trained = True
        logger.info(f"BPE training complete. Vocabulary size: {len(self.tokenizer)}")

    def tokenize_midi(self, midi_data: bytes) -> dict:
        """
        Tokenize MIDI data into BPE tokens.

        Args:
            midi_data: Raw MIDI file bytes.

        Returns:
            Dictionary with tokens, embeddings placeholder, and features.
        """
        # Write to temporary file (MidiTok requires file path)
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            f.write(midi_data)
            temp_path = Path(f.name)

        try:
            # Tokenize
            tokens = self.tokenizer(temp_path)

            # Get token IDs
            if hasattr(tokens, 'ids'):
                token_ids = tokens.ids
            else:
                # Handle different MidiTok versions
                token_ids = [t.ids for t in tokens] if isinstance(tokens, list) else tokens
                if isinstance(token_ids, list) and len(token_ids) > 0:
                    if isinstance(token_ids[0], list):
                        token_ids = token_ids[0]

            # Truncate if necessary
            if len(token_ids) > self.max_seq_length:
                logger.warning(
                    f"Sequence length {len(token_ids)} exceeds max {self.max_seq_length}, truncating"
                )
                token_ids = token_ids[:self.max_seq_length]

            # Extract basic features from MIDI using symusic
            score = Score(temp_path)
            programs = [track.program for track in score.tracks]

            result = {
                "tokens": list(token_ids) if not isinstance(token_ids, list) else token_ids,
                "embeddings": [],  # Initial embeddings (to be computed by model)
                "embedding_dim": 0,
                "features": {
                    "num_tokens": float(len(token_ids)),
                    "num_programs": float(len(programs)),
                },
            }

            logger.debug(f"Tokenized MIDI: {len(token_ids)} tokens")
            return result

        finally:
            # Cleanup temp file
            temp_path.unlink(missing_ok=True)

    def tokenize_from_notes(self, notes: list[dict]) -> dict:
        """
        Tokenize from a list of note dictionaries.

        Args:
            notes: List of note dicts with pitch, start_time, duration, velocity.

        Returns:
            Dictionary with tokens and features.
        """
        from symusic import Score, Track, Note as SyNote

        # Create Score from notes (symusic API: first arg is tpq)
        score = Score(480)
        track = Track(program=0, is_drum=False, name="Track 0")

        for note in notes:
            # Convert time to ticks (assuming tempo=120)
            start_ticks = int(note["start_time"] * 480 * 2)
            duration_ticks = int(note["duration"] * 480 * 2)

            track.notes.append(SyNote(
                time=start_ticks,
                duration=duration_ticks,
                pitch=note["pitch"],
                velocity=note.get("velocity", 64),
            ))

        score.tracks.append(track)

        # Tokenize
        tokens = self.tokenizer(score)

        if hasattr(tokens, 'ids'):
            token_ids = tokens.ids
        else:
            token_ids = tokens[0].ids if isinstance(tokens, list) else tokens

        return {
            "tokens": list(token_ids),
            "embeddings": [],
            "embedding_dim": 0,
            "features": {
                "num_tokens": float(len(token_ids)),
                "num_notes": float(len(notes)),
            },
        }

    def decode(self, tokens: list[int]) -> bytes:
        """
        Decode tokens back to MIDI.

        Args:
            tokens: List of token IDs.

        Returns:
            MIDI file bytes.
        """
        # Decode to MIDI
        midi = self.tokenizer.decode(tokens)

        # Write to bytes
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            temp_path = Path(f.name)

        try:
            midi.dump_midi(temp_path)
            return temp_path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)

    def save(self, path: Path) -> None:
        """Save tokenizer to disk."""
        self.tokenizer.save(path)
        logger.info(f"Tokenizer saved to {path}")

    def load(self, path: Path) -> None:
        """Load tokenizer from disk."""
        self.tokenizer = REMI.from_pretrained(path)
        self._is_trained = True
        logger.info(f"Tokenizer loaded from {path}")

    @property
    def vocab_size_actual(self) -> int:
        """Get actual vocabulary size."""
        return len(self.tokenizer)

    @property
    def is_trained(self) -> bool:
        """Check if tokenizer has been trained with BPE."""
        return self._is_trained
