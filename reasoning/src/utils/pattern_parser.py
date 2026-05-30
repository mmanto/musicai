"""
Musical pattern parser for extracting musical concepts from natural language text.

This module provides deterministic parsing of musical patterns (scales, chords, arpeggios)
from Spanish text input, with fallback to LLM-based extraction.
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# Note mappings: Spanish → English
NOTE_MAPPING_ES_TO_EN = {
    'do': 'C', 'do#': 'C#', 'dob': 'Cb',
    're': 'D', 're#': 'D#', 'reb': 'Db',
    'mi': 'E', 'mi#': 'E#', 'mib': 'Eb',
    'fa': 'F', 'fa#': 'F#', 'fab': 'Fb',
    'sol': 'G', 'sol#': 'G#', 'solb': 'Gb',
    'la': 'A', 'la#': 'A#', 'lab': 'Ab',
    'si': 'B', 'si#': 'B#', 'sib': 'Bb',
}

# Scale type mappings: Spanish → English
SCALE_TYPE_MAPPING_ES_TO_EN = {
    'mayor': 'major',
    'menor': 'minor',
    'menor natural': 'minor',
    'menor armónica': 'harmonic minor',
    'menor armonica': 'harmonic minor',
    'armónica': 'harmonic minor',
    'armonica': 'harmonic minor',
    'menor melódica': 'melodic minor',
    'menor melodica': 'melodic minor',
    'melódica': 'melodic minor',
    'melodica': 'melodic minor',
    'pentatónica mayor': 'pentatonic major',
    'pentatonica mayor': 'pentatonic major',
    'pentatónica menor': 'pentatonic minor',
    'pentatonica menor': 'pentatonic minor',
    'pentatónica': 'pentatonic minor',
    'pentatonica': 'pentatonic minor',
    'cromática': 'chromatic',
    'cromatica': 'chromatic',
    'dórica': 'dorian',
    'dorica': 'dorian',
    'frigia': 'phrygian',
    'lidia': 'lydian',
    'mixolidia': 'mixolydian',
    'eólica': 'aeolian',
    'eolica': 'aeolian',
    'locria': 'locrian',
    'blues': 'blues',
}

# Clef mappings
CLEF_MAPPING_ES_TO_EN = {
    'clave de sol': 'treble',
    'sol': 'treble',
    'clave de fa': 'bass',
    'fa': 'bass',
    'clave de do': 'alto',
    'do': 'alto',
    'alto': 'alto',
    'tenor': 'tenor',
}


class PatternParser:
    """Parser for musical patterns from natural language."""

    def __init__(self):
        """Initialize the pattern parser."""
        self.note_map = NOTE_MAPPING_ES_TO_EN
        self.scale_map = SCALE_TYPE_MAPPING_ES_TO_EN
        self.clef_map = CLEF_MAPPING_ES_TO_EN

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse musical patterns from text.

        Args:
            text: Input text in Spanish

        Returns:
            List of detected musical concepts
        """
        text_lower = text.lower()
        concepts = []

        # Try to detect scales
        scale_concepts = self._parse_scales(text_lower)
        concepts.extend(scale_concepts)

        # Try to detect chords
        chord_concepts = self._parse_chords(text_lower)
        concepts.extend(chord_concepts)

        # Try to detect arpeggios
        arpeggio_concepts = self._parse_arpeggios(text_lower)
        concepts.extend(arpeggio_concepts)

        return concepts

    def _parse_scales(self, text: str) -> List[Dict[str, Any]]:
        """Parse scale patterns from text."""
        concepts = []

        # Check if text mentions scales
        if not any(keyword in text for keyword in ['escala', 'pentatónica', 'pentatonica']):
            return concepts

        # Pattern 1: "escala [tipo] de/en [nota]"
        # Example: "escala mayor de do", "escala pentatónica en la"
        pattern1 = r'escala\s+([a-záéíóú\s]+?)\s+(?:de|en)\s+([a-z]+#?b?)'
        matches1 = re.finditer(pattern1, text)

        for match in matches1:
            scale_type_es = match.group(1).strip()
            note_es = match.group(2).strip()

            scale_type_en = self._map_scale_type(scale_type_es)
            note_en = self.note_map.get(note_es)

            if note_en:
                concepts.append({
                    'type': 'scale',
                    'tonic': note_en,
                    'scale_type': scale_type_en or 'major'
                })

        # Pattern 2: "escala de/en [nota] [tipo]"
        # Example: "escala de do mayor", "escala en la menor"
        pattern2 = r'escala\s+(?:de|en)\s+([a-z]+#?b?)\s+([a-záéíóú\s]+)'
        matches2 = re.finditer(pattern2, text)

        for match in matches2:
            note_es = match.group(1).strip()
            scale_type_es = match.group(2).strip()

            note_en = self.note_map.get(note_es)
            scale_type_en = self._map_scale_type(scale_type_es)

            if note_en:
                concepts.append({
                    'type': 'scale',
                    'tonic': note_en,
                    'scale_type': scale_type_en or 'major'
                })

        # Pattern 3: "[nota] [tipo]" (without "escala" keyword)
        # Example: "do mayor", "la pentatónica menor"
        if not concepts:
            pattern3 = r'\b([a-z]+#?b?)\s+(mayor|menor|pentatónica|pentatonica|armónica|armonica|melódica|melodica|dórica|dorica|frigia|lidia|mixolidia|eólica|eolica|locria|blues)(?:\s+(mayor|menor))?'
            matches3 = re.finditer(pattern3, text)

            for match in matches3:
                note_es = match.group(1).strip()
                scale_type_part1 = match.group(2).strip()
                scale_type_part2 = match.group(3).strip() if match.group(3) else ''

                scale_type_es = f"{scale_type_part1} {scale_type_part2}".strip()

                note_en = self.note_map.get(note_es)
                scale_type_en = self._map_scale_type(scale_type_es)

                if note_en and scale_type_en:
                    concepts.append({
                        'type': 'scale',
                        'tonic': note_en,
                        'scale_type': scale_type_en
                    })

        # Detect clef if mentioned
        for concept in concepts:
            clef = self._detect_clef(text)
            if clef:
                concept['clef'] = clef

        return concepts

    def _parse_chords(self, text: str) -> List[Dict[str, Any]]:
        """Parse chord patterns from text."""
        concepts = []

        # Check if text mentions chords
        if 'acorde' not in text and 'progresión' not in text:
            return concepts

        # Pattern 1: "acorde de [nota] [cualidad]"
        # Example: "acorde de la menor", "acorde de do mayor"
        pattern1 = r'acorde\s+de\s+([a-z]+#?b?)\s+(mayor|menor)?'
        matches1 = re.finditer(pattern1, text)

        for match in matches1:
            note_es = match.group(1).strip()
            quality = match.group(2).strip() if match.group(2) else 'mayor'

            note_en = self.note_map.get(note_es)

            if note_en:
                # Convert to chord symbol
                if quality == 'menor':
                    symbol = f"{note_en}m"
                else:
                    symbol = note_en

                concepts.append({
                    'type': 'chord',
                    'symbol': symbol
                })

        # Pattern 2: Chord progression "C,Am,F,G" or "C-Am-F-G"
        progression_pattern = r'([A-G][#b]?m?(?:7|maj7|dim|aug)?(?:[,\-\s]+[A-G][#b]?m?(?:7|maj7|dim|aug)?)+)'
        matches2 = re.finditer(progression_pattern, text)

        for match in matches2:
            progression = match.group(1)
            # Clean up separators
            symbols = re.split(r'[,\-\s]+', progression)

            concepts.append({
                'type': 'chord_progression',
                'symbols': symbols
            })

        return concepts

    def _parse_arpeggios(self, text: str) -> List[Dict[str, Any]]:
        """Parse arpeggio patterns from text."""
        concepts = []

        # Check if text mentions arpeggios
        if 'arpegio' not in text:
            return concepts

        # Pattern: "arpegio [ascendente/descendente] de [nota] [tipo]"
        pattern = r'arpegio\s+(ascendente|descendente)?\s*(?:de|en)?\s*([a-z]+#?b?)\s+(mayor|menor)?'
        matches = re.finditer(pattern, text)

        for match in matches:
            direction = match.group(1) or 'ascendente'
            note_es = match.group(2).strip()
            quality = match.group(3) or 'mayor'

            note_en = self.note_map.get(note_es)

            if note_en:
                concepts.append({
                    'type': 'arpeggio',
                    'tonic': note_en,
                    'chord_type': 'minor' if quality == 'menor' else 'major',
                    'direction': 'descending' if direction == 'descendente' else 'ascending'
                })

        return concepts

    def _map_scale_type(self, scale_type_es: str) -> Optional[str]:
        """Map Spanish scale type to English."""
        scale_type_es = scale_type_es.strip().lower()

        # Try direct mapping
        if scale_type_es in self.scale_map:
            return self.scale_map[scale_type_es]

        # Try partial matches
        for es_key, en_value in self.scale_map.items():
            if es_key in scale_type_es or scale_type_es in es_key:
                return en_value

        return None

    def _detect_clef(self, text: str) -> Optional[str]:
        """Detect clef from text."""
        for clef_es, clef_en in self.clef_map.items():
            if clef_es in text:
                return clef_en

        return 'treble'  # Default

    def extract_concepts_for_visualization(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract musical concepts that should be visualized.

        This is typically called when the user explicitly requests to see
        a musical pattern (e.g., "muéstrame la escala de do mayor").

        Args:
            text: User message

        Returns:
            List of concepts to visualize
        """
        # Keywords that indicate visualization request
        visualization_keywords = [
            'muestra', 'muéstrame', 'mostrar', 'ver', 'visualiza',
            'escribe', 'genera', 'crea', 'dame'
        ]

        has_visualization_request = any(
            keyword in text.lower() for keyword in visualization_keywords
        )

        if has_visualization_request:
            return self.parse(text)

        # Also check if it's a direct pattern request without explicit "show me"
        # For example: "escala de do mayor" without "muéstrame"
        concepts = self.parse(text)

        # If we found specific patterns with concrete notes, assume visualization
        if concepts:
            return concepts

        return []


def is_theory_question(text: str) -> bool:
    """
    Detect if the text is a music theory question.

    Args:
        text: Input text

    Returns:
        True if it's a theory question
    """
    question_words = [
        'qué', 'que', 'cómo', 'como', 'cuál', 'cual', 'cuáles', 'cuales',
        'por qué', 'por que', 'explica', 'explicame', 'define',
        'diferencia', 'significa', 'es', 'son'
    ]

    music_terms = [
        'escala', 'acorde', 'arpegio', 'tonalidad', 'tono', 'semitono',
        'intervalo', 'nota', 'ritmo', 'compás', 'compas', 'clave',
        'mayor', 'menor', 'armonía', 'armonia', 'melodía', 'melodia',
        'contrapunto', 'modulación', 'modulacion'
    ]

    text_lower = text.lower()

    has_question_word = any(word in text_lower for word in question_words)
    has_music_term = any(term in text_lower for term in music_terms)

    # Also check for question marks
    has_question_mark = '?' in text

    return (has_question_word or has_question_mark) and has_music_term


def is_validation_question(text: str) -> bool:
    """
    Detect if the text is asking to validate a musical statement.

    Args:
        text: Input text

    Returns:
        True if it's a validation question
    """
    validation_keywords = [
        'es correcto', 'está bien', 'esta bien', 'es cierto',
        'es verdad', 'debe', 'debería', 'deberia', 'tiene que',
        'comienza con', 'empieza con', 'contiene', 'tiene'
    ]

    text_lower = text.lower()

    return any(keyword in text_lower for keyword in validation_keywords)
