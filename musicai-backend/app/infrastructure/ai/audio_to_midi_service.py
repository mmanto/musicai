"""
Audio to MIDI Service - Convert audio to MIDI using basic-pitch.

This service bridges the gap between MusicGen's audio output
and music21's symbolic representation.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
import pretty_midi

logger = logging.getLogger(__name__)


class AudioToMidiService:
    """
    Service for converting audio to MIDI using Spotify's basic-pitch model.

    This is a critical component that converts MusicGen's audio output
    into a format that music21 can process.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize audio-to-MIDI service.

        Args:
            model_path: Path to basic-pitch model (uses default if None)
        """
        self.model_path = model_path or ICASSP_2022_MODEL_PATH
        logger.info("Audio-to-MIDI service initialized with basic-pitch")

    def convert_audio_to_midi(
        self,
        audio_path: str,
        onset_threshold: float = 0.5,
        frame_threshold: float = 0.3,
        minimum_note_length: float = 0.058,
        minimum_frequency: Optional[float] = None,
        maximum_frequency: Optional[float] = None,
        multiple_pitch_bends: bool = False
    ) -> bytes:
        """
        Convert audio file to MIDI.

        Args:
            audio_path: Path to audio file
            onset_threshold: Threshold for note onset detection
            frame_threshold: Threshold for frame-level note detection
            minimum_note_length: Minimum note length in seconds
            minimum_frequency: Minimum frequency to consider (Hz)
            maximum_frequency: Maximum frequency to consider (Hz)
            multiple_pitch_bends: Use multiple pitch bends per note

        Returns:
            MIDI file as bytes
        """
        try:
            logger.info(f"Converting audio to MIDI: {audio_path}")

            # Run basic-pitch inference
            model_output, midi_data, note_events = predict(
                audio_path=audio_path,
                model_or_model_path=self.model_path,
                onset_threshold=onset_threshold,
                frame_threshold=frame_threshold,
                minimum_note_length=minimum_note_length,
                minimum_frequency=minimum_frequency,
                maximum_frequency=maximum_frequency,
                multiple_pitch_bends=multiple_pitch_bends
            )

            # Convert PrettyMIDI object to bytes
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
                midi_data.write(tmp_file.name)
                tmp_path = tmp_file.name

            # Read MIDI bytes
            with open(tmp_path, 'rb') as f:
                midi_bytes = f.read()

            # Clean up temp file
            Path(tmp_path).unlink()

            logger.info(f"Converted to MIDI: {len(midi_data.instruments)} instruments, "
                       f"{len(note_events)} note events")

            return midi_bytes

        except Exception as e:
            logger.error(f"Error converting audio to MIDI: {e}")
            raise RuntimeError(f"Could not convert audio to MIDI: {e}")

    def convert_audio_array_to_midi(
        self,
        audio_array: np.ndarray,
        sample_rate: int,
        onset_threshold: float = 0.5,
        frame_threshold: float = 0.3
    ) -> bytes:
        """
        Convert audio numpy array to MIDI.

        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sampling rate
            onset_threshold: Threshold for onset detection
            frame_threshold: Threshold for frame detection

        Returns:
            MIDI file as bytes
        """
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
                import soundfile as sf
                sf.write(tmp_audio.name, audio_array, sample_rate)
                tmp_audio_path = tmp_audio.name

            # Convert to MIDI
            midi_bytes = self.convert_audio_to_midi(
                audio_path=tmp_audio_path,
                onset_threshold=onset_threshold,
                frame_threshold=frame_threshold
            )

            # Clean up
            Path(tmp_audio_path).unlink()

            return midi_bytes

        except Exception as e:
            logger.error(f"Error converting audio array to MIDI: {e}")
            raise RuntimeError(f"Could not convert audio array to MIDI: {e}")

    def analyze_midi_quality(self, midi_bytes: bytes) -> dict:
        """
        Analyze the quality of converted MIDI.

        Args:
            midi_bytes: MIDI data as bytes

        Returns:
            Dictionary with quality metrics
        """
        try:
            # Save to temp file for pretty_midi to load
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
                tmp.write(midi_bytes)
                tmp_path = tmp.name

            # Load with pretty_midi
            midi_data = pretty_midi.PrettyMIDI(tmp_path)

            # Clean up
            Path(tmp_path).unlink()

            # Calculate metrics
            total_notes = sum(len(inst.notes) for inst in midi_data.instruments)
            duration = midi_data.get_end_time()

            quality_metrics = {
                "total_notes": total_notes,
                "duration": duration,
                "notes_per_second": total_notes / duration if duration > 0 else 0,
                "num_instruments": len(midi_data.instruments),
                "tempo_changes": len(midi_data.get_tempo_changes()[0]),
            }

            logger.info(f"MIDI quality: {total_notes} notes, {duration:.2f}s")
            return quality_metrics

        except Exception as e:
            logger.error(f"Error analyzing MIDI quality: {e}")
            return {"error": str(e)}

    def get_recommended_thresholds(self, music_type: str = "general") -> dict:
        """
        Get recommended thresholds for different music types.

        Args:
            music_type: Type of music (general, monophonic, polyphonic, percussion)

        Returns:
            Dictionary with recommended parameters
        """
        thresholds = {
            "general": {
                "onset_threshold": 0.5,
                "frame_threshold": 0.3,
                "minimum_note_length": 0.058
            },
            "monophonic": {  # Better for single melodies
                "onset_threshold": 0.4,
                "frame_threshold": 0.25,
                "minimum_note_length": 0.05
            },
            "polyphonic": {  # Multiple notes at once
                "onset_threshold": 0.6,
                "frame_threshold": 0.35,
                "minimum_note_length": 0.06
            },
            "percussion": {  # Drums/rhythmic
                "onset_threshold": 0.7,
                "frame_threshold": 0.4,
                "minimum_note_length": 0.03
            }
        }

        return thresholds.get(music_type, thresholds["general"])
