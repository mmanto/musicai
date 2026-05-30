"""Text tokenizer for user descriptions and prompts."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class TextTokenizer:
    """
    Simple text tokenizer for musical descriptions.

    Extracts musical keywords and normalizes text for processing
    by the reasoning module.
    """

    # Musical keywords for feature extraction
    MUSICAL_KEYS = [
        "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb",
        "G", "G#", "Ab", "A", "A#", "Bb", "B"
    ]

    MUSICAL_MODES = ["major", "minor", "dorian", "phrygian", "lydian", "mixolydian", "locrian"]

    GENRES = [
        "jazz", "blues", "rock", "pop", "classical", "electronic", "hip-hop",
        "r&b", "soul", "funk", "reggae", "latin", "folk", "country", "metal"
    ]

    TEMPO_WORDS = {
        "slow": (60, 80),
        "moderate": (80, 120),
        "fast": (120, 160),
        "very fast": (160, 200),
        "largo": (40, 60),
        "adagio": (66, 76),
        "andante": (76, 108),
        "allegro": (120, 168),
        "presto": (168, 200),
    }

    def __init__(self):
        """Initialize text tokenizer."""
        logger.info("Text tokenizer initialized")

    def tokenize(self, text: str) -> dict:
        """
        Tokenize and extract features from text description.

        Args:
            text: User's musical description/prompt.

        Returns:
            Dictionary with extracted features and normalized text.
        """
        text_lower = text.lower().strip()

        features = {
            "key": self._extract_key(text),
            "mode": self._extract_mode(text_lower),
            "genre": self._extract_genre(text_lower),
            "tempo_range": self._extract_tempo(text_lower),
            "chord_mentions": self._extract_chords(text),
            "instruments": self._extract_instruments(text_lower),
        }

        # Simple word tokenization
        words = re.findall(r'\b\w+\b', text_lower)

        return {
            "tokens": words,
            "features": features,
            "original_text": text,
            "normalized_text": text_lower,
        }

    def _extract_key(self, text: str) -> Optional[str]:
        """Extract musical key from text."""
        # Pattern for key mentions like "C major", "Dm", "F# minor"
        pattern = r'\b([A-G][#b]?)\s*(major|minor|m(?!ajor|inor)|maj)?\b'

        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            key = match.group(1).upper()
            mode = match.group(2)

            if mode:
                mode_lower = mode.lower()
                if mode_lower in ['m', 'minor']:
                    return f"{key} minor"
                elif mode_lower in ['maj', 'major']:
                    return f"{key} major"

            return key

        return None

    def _extract_mode(self, text: str) -> Optional[str]:
        """Extract musical mode from text."""
        for mode in self.MUSICAL_MODES:
            if mode in text:
                return mode
        return None

    def _extract_genre(self, text: str) -> Optional[str]:
        """Extract genre from text."""
        for genre in self.GENRES:
            if genre in text:
                return genre
        return None

    def _extract_tempo(self, text: str) -> Optional[tuple[int, int]]:
        """Extract tempo range from text."""
        # Check for explicit BPM
        bpm_match = re.search(r'(\d+)\s*bpm', text)
        if bpm_match:
            bpm = int(bpm_match.group(1))
            return (max(40, bpm - 10), min(250, bpm + 10))

        # Check for tempo words
        for word, tempo_range in self.TEMPO_WORDS.items():
            if word in text:
                return tempo_range

        return None

    def _extract_chords(self, text: str) -> list[str]:
        """Extract chord mentions from text."""
        # Pattern for chord symbols like "Cmaj7", "Dm7", "G7", "F#m"
        pattern = r'\b([A-G][#b]?)(maj|min|m|dim|aug|sus[24]?)?(\d+)?\b'

        matches = re.findall(pattern, text)
        chords = []

        for root, quality, extension in matches:
            chord = root.upper()
            if quality:
                chord += quality.lower()
            if extension:
                chord += extension
            chords.append(chord)

        return chords

    def _extract_instruments(self, text: str) -> list[str]:
        """Extract instrument mentions from text."""
        instruments = [
            "piano", "guitar", "bass", "drums", "violin", "cello",
            "flute", "saxophone", "trumpet", "synthesizer", "organ",
            "harp", "clarinet", "oboe", "trombone", "vibraphone"
        ]

        found = []
        for instrument in instruments:
            if instrument in text:
                found.append(instrument)

        return found

    def get_musical_context(self, text: str) -> dict:
        """
        Get full musical context from text for the reasoning module.

        Args:
            text: User's text description.

        Returns:
            Dictionary with musical context for reasoning.
        """
        result = self.tokenize(text)
        features = result["features"]

        context = {
            "tonality": features["key"],
            "mode": features["mode"],
            "style": features["genre"],
            "tempo": features["tempo_range"],
            "harmonic_elements": features["chord_mentions"],
            "instrumentation": features["instruments"],
            "raw_prompt": text,
        }

        # Add derived context
        if features["genre"] == "jazz":
            context["suggested_elements"] = [
                "extended_chords", "tritone_substitution",
                "walking_bass", "swing_rhythm"
            ]
        elif features["genre"] == "classical":
            context["suggested_elements"] = [
                "voice_leading", "counterpoint", "formal_structure"
            ]

        return context
