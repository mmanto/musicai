"""Audio feature extraction using librosa."""

import logging
from typing import Optional
import tempfile
from pathlib import Path

import numpy as np
import librosa

from ..config import get_settings

logger = logging.getLogger(__name__)


class AudioFeatureExtractor:
    """
    Extract musical features from audio files.

    Includes tempo, key, time signature, and other musical attributes.
    """

    def __init__(self, sample_rate: Optional[int] = None):
        """
        Initialize feature extractor.

        Args:
            sample_rate: Sample rate for audio processing.
        """
        settings = get_settings()
        self.sample_rate = sample_rate or settings.SAMPLE_RATE
        logger.info(f"AudioFeatureExtractor initialized with sr={self.sample_rate}")

    def extract_all(self, audio_data: bytes, audio_format: str = "wav") -> dict:
        """
        Extract all musical features from audio.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format (wav, mp3, flac).

        Returns:
            Dictionary with all extracted features.
        """
        # Load audio
        y, sr = self._load_audio(audio_data, audio_format)

        # Extract features
        features = {
            "duration": float(len(y) / sr),
            "sample_rate": sr,
        }

        # Tempo
        tempo, beats = self._extract_tempo(y, sr)
        features["tempo"] = tempo
        features["num_beats"] = len(beats)

        # Key and mode
        key, mode, key_confidence = self._extract_key(y, sr)
        features["key"] = key
        features["mode"] = mode
        features["key_confidence"] = key_confidence
        features["key_string"] = f"{key} {mode}"

        # Time signature (estimated)
        time_sig = self._estimate_time_signature(y, sr, tempo)
        features["time_signature"] = time_sig

        # Chroma features
        chroma = self._extract_chroma(y, sr)
        features["chroma_mean"] = chroma.mean(axis=1).tolist()

        # Additional features
        features["rms_energy"] = float(np.mean(librosa.feature.rms(y=y)))
        features["spectral_centroid"] = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        features["zero_crossing_rate"] = float(np.mean(librosa.feature.zero_crossing_rate(y)))

        # Onset strength (rhythmic complexity)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        features["onset_strength_mean"] = float(np.mean(onset_env))
        features["onset_strength_std"] = float(np.std(onset_env))

        logger.debug(f"Extracted features: tempo={tempo}, key={key} {mode}")
        return features

    def _load_audio(self, audio_data: bytes, audio_format: str) -> tuple[np.ndarray, int]:
        """Load audio from bytes."""
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_data)
            temp_path = Path(f.name)

        try:
            y, sr = librosa.load(temp_path, sr=self.sample_rate, mono=True)
            return y, sr
        finally:
            temp_path.unlink(missing_ok=True)

    def _extract_tempo(self, y: np.ndarray, sr: int) -> tuple[float, np.ndarray]:
        """Extract tempo and beat frames."""
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        # Handle numpy array tempo
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 120.0
        else:
            tempo = float(tempo)

        # Default to 120 BPM if tempo detection fails
        if tempo == 0.0:
            tempo = 120.0

        return tempo, beats

    def _extract_key(self, y: np.ndarray, sr: int) -> tuple[str, str, float]:
        """
        Extract key and mode using chroma features.

        Returns:
            Tuple of (key, mode, confidence).
        """
        # Compute chroma
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)

        # Key names
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        # Major and minor profiles (Krumhansl-Kessler)
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

        # Normalize
        major_profile = major_profile / np.linalg.norm(major_profile)
        minor_profile = minor_profile / np.linalg.norm(minor_profile)
        chroma_norm = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-8)

        # Correlate with all keys
        best_corr = -1
        best_key = 'C'
        best_mode = 'major'

        for i in range(12):
            # Rotate profiles
            major_rot = np.roll(major_profile, i)
            minor_rot = np.roll(minor_profile, i)

            major_corr = np.corrcoef(chroma_norm, major_rot)[0, 1]
            minor_corr = np.corrcoef(chroma_norm, minor_rot)[0, 1]

            if major_corr > best_corr:
                best_corr = major_corr
                best_key = keys[i]
                best_mode = 'major'

            if minor_corr > best_corr:
                best_corr = minor_corr
                best_key = keys[i]
                best_mode = 'minor'

        return best_key, best_mode, float(best_corr)

    def _estimate_time_signature(self, y: np.ndarray, sr: int, tempo: float) -> str:
        """
        Estimate time signature from audio.

        This is a simplified estimation based on beat strength patterns.
        """
        # Get onset strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)

        # Get beats
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)

        if len(beat_frames) < 4:
            return "4/4"  # Default

        # Analyze beat strength patterns
        beat_strengths = onset_env[beat_frames]

        # Check for patterns
        if len(beat_strengths) >= 8:
            # Look for strong beats pattern
            # 4/4: strong every 4 beats
            # 3/4: strong every 3 beats

            # Simple heuristic based on tempo
            if tempo > 150:
                return "4/4"  # Fast tempo often 4/4
            elif 90 < tempo < 110:
                # Could be waltz (3/4) at moderate tempo
                # Check if every 3rd beat is stronger
                groups_of_3 = [beat_strengths[i:i+3] for i in range(0, len(beat_strengths)-2, 3)]
                groups_of_4 = [beat_strengths[i:i+4] for i in range(0, len(beat_strengths)-3, 4)]

                if len(groups_of_3) > 0 and len(groups_of_4) > 0:
                    variance_3 = np.mean([np.var(g) for g in groups_of_3 if len(g) == 3])
                    variance_4 = np.mean([np.var(g) for g in groups_of_4 if len(g) == 4])

                    if variance_3 < variance_4:
                        return "3/4"

        return "4/4"

    def _extract_chroma(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Extract chroma features."""
        return librosa.feature.chroma_cqt(y=y, sr=sr)

    def extract_chord_progression(self, y: np.ndarray, sr: int) -> list[str]:
        """
        Extract chord progression from audio.

        This is a simplified chord detection based on chroma features.
        """
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

        # Segment audio by beats
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

        if len(beat_frames) < 2:
            return []

        # Get chord for each beat
        chords = []
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        for i in range(len(beat_frames) - 1):
            start = beat_frames[i]
            end = beat_frames[i + 1]

            # Get average chroma for this segment
            if end <= chroma.shape[1]:
                segment_chroma = chroma[:, start:end].mean(axis=1)

                # Find root note
                root_idx = np.argmax(segment_chroma)
                root = notes[root_idx]

                # Check for major/minor
                # Major: root + major 3rd (4 semitones) + perfect 5th (7 semitones)
                # Minor: root + minor 3rd (3 semitones) + perfect 5th (7 semitones)
                major_third_idx = (root_idx + 4) % 12
                minor_third_idx = (root_idx + 3) % 12

                if segment_chroma[major_third_idx] > segment_chroma[minor_third_idx]:
                    chords.append(root)
                else:
                    chords.append(f"{root}m")

        # Remove consecutive duplicates
        result = []
        for chord in chords:
            if not result or result[-1] != chord:
                result.append(chord)

        return result
