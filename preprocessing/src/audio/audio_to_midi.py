"""Audio to MIDI conversion using basic-pitch."""

import logging
from typing import Optional
import tempfile
from pathlib import Path

import numpy as np

from ..config import get_settings

logger = logging.getLogger(__name__)

# Check if basic-pitch is available
BASIC_PITCH_AVAILABLE = False
BASIC_PITCH_ERROR = None

try:
    from basic_pitch.inference import predict as _basic_pitch_predict
    BASIC_PITCH_AVAILABLE = True
except ImportError as e:
    BASIC_PITCH_ERROR = str(e)
    logger.warning(
        f"basic-pitch not available: {e}. "
        "Audio-to-MIDI conversion will not work. "
        "Use Python 3.11 or earlier for full functionality."
    )


class AudioToMidiConverter:
    """
    Convert audio files to MIDI using basic-pitch (Spotify).

    Basic-pitch is a neural network model that performs automatic
    music transcription (audio to MIDI).

    Note: Requires Python 3.11 or earlier due to TensorFlow compatibility.
    """

    def __init__(self):
        """Initialize the converter."""
        self._model = None
        self._available = BASIC_PITCH_AVAILABLE
        if self._available:
            logger.info("AudioToMidiConverter initialized")
        else:
            logger.warning(
                "AudioToMidiConverter initialized but basic-pitch is not available. "
                f"Error: {BASIC_PITCH_ERROR}"
            )

    @property
    def is_available(self) -> bool:
        """Check if audio-to-MIDI conversion is available."""
        return self._available

    def _load_model(self):
        """Lazy load the basic-pitch model."""
        if not self._available:
            raise RuntimeError(
                "basic-pitch is not available. "
                "This is likely due to TensorFlow version incompatibility with Python 3.12+. "
                "Please use Python 3.11 or earlier, or run in Docker with Python 3.11. "
                f"Original error: {BASIC_PITCH_ERROR}"
            )

        if self._model is None:
            self._model = _basic_pitch_predict
            logger.info("Basic-pitch model loaded")

    def convert(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        onset_threshold: float = 0.5,
        frame_threshold: float = 0.3,
        min_note_length: float = 0.058,
        min_frequency: Optional[float] = None,
        max_frequency: Optional[float] = None,
    ) -> dict:
        """
        Convert audio to MIDI.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format (wav, mp3, flac).
            onset_threshold: Threshold for note onset detection.
            frame_threshold: Threshold for frame-level note detection.
            min_note_length: Minimum note duration in seconds.
            min_frequency: Minimum frequency to detect (Hz).
            max_frequency: Maximum frequency to detect (Hz).

        Returns:
            Dictionary with MIDI data and extracted notes.
        """
        self._load_model()

        # Write to temporary file
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_data)
            temp_audio_path = Path(f.name)

        try:
            # Run prediction
            model_output, midi_data, note_events = self._model(
                temp_audio_path,
                onset_threshold=onset_threshold,
                frame_threshold=frame_threshold,
                minimum_note_length=min_note_length,
                minimum_frequency=min_frequency,
                maximum_frequency=max_frequency,
            )

            # Extract notes from note_events
            notes = []
            for start_time, end_time, pitch, velocity, _ in note_events:
                notes.append({
                    "pitch": int(pitch),
                    "start_time": float(start_time),
                    "duration": float(end_time - start_time),
                    "velocity": int(velocity * 127),
                })

            # Save MIDI to bytes
            with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
                temp_midi_path = Path(f.name)
                midi_data.write(str(temp_midi_path))
                midi_bytes = temp_midi_path.read_bytes()

            # Calculate confidence based on note density and consistency
            confidence = self._calculate_confidence(notes, model_output)

            result = {
                "midi_data": midi_bytes,
                "notes": notes,
                "confidence": confidence,
                "num_notes": len(notes),
                "duration": max(n["start_time"] + n["duration"] for n in notes) if notes else 0,
            }

            logger.info(f"Converted audio to MIDI: {len(notes)} notes, confidence={confidence:.2f}")
            return result

        finally:
            temp_audio_path.unlink(missing_ok=True)
            if 'temp_midi_path' in locals():
                temp_midi_path.unlink(missing_ok=True)

    def _calculate_confidence(self, notes: list[dict], model_output) -> float:
        """
        Calculate confidence score for the transcription.

        Args:
            notes: Extracted notes.
            model_output: Raw model output.

        Returns:
            Confidence score between 0 and 1.
        """
        if not notes:
            return 0.0

        # Factors for confidence:
        # 1. Number of notes (too few or too many is suspicious)
        # 2. Velocity variance (consistent velocities are good)
        # 3. Note duration variance (reasonable durations)

        num_notes = len(notes)

        # Ideal note density (adjust based on your use case)
        note_density_score = min(1.0, num_notes / 50) if num_notes < 50 else min(1.0, 100 / num_notes)

        # Velocity consistency
        velocities = [n["velocity"] for n in notes]
        velocity_std = np.std(velocities)
        velocity_score = max(0, 1 - velocity_std / 64)

        # Duration reasonableness
        durations = [n["duration"] for n in notes]
        avg_duration = np.mean(durations)
        duration_score = 1.0 if 0.1 < avg_duration < 2.0 else 0.5

        # Combine scores
        confidence = (note_density_score + velocity_score + duration_score) / 3

        return float(np.clip(confidence, 0, 1))

    def convert_with_options(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        options: Optional[dict] = None,
    ) -> dict:
        """
        Convert audio to MIDI with custom options from dictionary.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format.
            options: Dictionary of conversion options.

        Returns:
            Dictionary with MIDI data and notes.
        """
        options = options or {}

        return self.convert(
            audio_data=audio_data,
            audio_format=audio_format,
            onset_threshold=float(options.get("onset_threshold", 0.5)),
            frame_threshold=float(options.get("frame_threshold", 0.3)),
            min_note_length=float(options.get("min_note_length", 0.058)),
            min_frequency=float(options["min_frequency"]) if "min_frequency" in options else None,
            max_frequency=float(options["max_frequency"]) if "max_frequency" in options else None,
        )

    def get_pitch_contour(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
    ) -> dict:
        """
        Get pitch contour from audio without full MIDI conversion.

        Useful for melodic analysis.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format.

        Returns:
            Dictionary with pitch contour data.
        """
        self._load_model()

        # Write to temporary file
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_data)
            temp_path = Path(f.name)

        try:
            model_output, _, _ = self._model(temp_path)

            # model_output contains:
            # - 'note': note activations
            # - 'onset': onset activations
            # - 'contour': pitch contour

            contour = model_output.get('contour', model_output.get('note', None))

            if contour is not None:
                # Get the most prominent pitch at each time frame
                pitch_contour = np.argmax(contour, axis=1)
                pitch_confidence = np.max(contour, axis=1)

                return {
                    "pitch_contour": pitch_contour.tolist(),
                    "confidence": pitch_confidence.tolist(),
                    "num_frames": len(pitch_contour),
                }
            else:
                return {
                    "pitch_contour": [],
                    "confidence": [],
                    "num_frames": 0,
                }

        finally:
            temp_path.unlink(missing_ok=True)
