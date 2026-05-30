"""
Musical concept validator service.
Validates user statements about music theory and detects incongruencies.
"""
from typing import Optional, Dict, Any, List, Tuple
from app.domain.models.conversation_context import MusicalConcept


class MusicValidator:
    """
    Validates musical concepts and user statements about music theory.
    """

    # Note name mappings (Spanish to English)
    NOTE_MAPPING = {
        "do": "C", "re": "D", "mi": "E", "fa": "F",
        "sol": "G", "la": "A", "si": "B",
        "c": "C", "d": "D", "e": "E", "f": "F",
        "g": "G", "a": "A", "b": "B"
    }

    # Scale interval patterns (semitones from tonic)
    SCALE_PATTERNS = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "natural_minor": [0, 2, 3, 5, 7, 8, 10],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
        "pentatonic_major": [0, 2, 4, 7, 9],
        "pentatonic_minor": [0, 3, 5, 7, 10],
        "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "lydian": [0, 2, 4, 6, 7, 9, 11],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "locrian": [0, 1, 3, 5, 6, 8, 10],
    }

    # Note pitch classes (C=0, C#=1, D=2, etc.)
    NOTE_PITCHES = {
        "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
        "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
    }

    # Chord interval patterns
    CHORD_PATTERNS = {
        "major": [0, 4, 7],
        "minor": [0, 3, 7],
        "diminished": [0, 3, 6],
        "augmented": [0, 4, 8],
        "sus2": [0, 2, 7],
        "sus4": [0, 5, 7],
        "major7": [0, 4, 7, 11],
        "minor7": [0, 3, 7, 10],
        "dominant7": [0, 4, 7, 10],
        "diminished7": [0, 3, 6, 9],
        "half-diminished7": [0, 3, 6, 10],
    }

    def __init__(self):
        pass

    def normalize_note_name(self, note: str) -> Optional[str]:
        """Convert note name (Spanish or English) to English uppercase."""
        note_clean = note.strip().lower()
        return self.NOTE_MAPPING.get(note_clean)

    def get_scale_notes(self, tonic: str, scale_type: str) -> Optional[List[str]]:
        """
        Get the notes in a scale given tonic and scale type.
        Returns list of note names, or None if invalid.
        """
        tonic_normalized = self.normalize_note_name(tonic)
        if not tonic_normalized:
            return None

        # Normalize scale type
        scale_type_normalized = scale_type.lower().replace(" ", "_")

        if scale_type_normalized not in self.SCALE_PATTERNS:
            return None

        # Get tonic pitch
        tonic_pitch = self.NOTE_PITCHES.get(tonic_normalized)
        if tonic_pitch is None:
            return None

        # Calculate scale notes
        pattern = self.SCALE_PATTERNS[scale_type_normalized]
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        scale_notes = []
        for interval in pattern:
            pitch = (tonic_pitch + interval) % 12
            scale_notes.append(note_names[pitch])

        return scale_notes

    def get_chord_notes(self, root: str, chord_type: str) -> Optional[List[str]]:
        """
        Get the notes in a chord given root and chord type.
        Returns list of note names, or None if invalid.
        """
        root_normalized = self.normalize_note_name(root)
        if not root_normalized:
            return None

        # Normalize chord type
        chord_type_normalized = chord_type.lower().replace(" ", "_")

        if chord_type_normalized not in self.CHORD_PATTERNS:
            return None

        # Get root pitch
        root_pitch = self.NOTE_PITCHES.get(root_normalized)
        if root_pitch is None:
            return None

        # Calculate chord notes
        pattern = self.CHORD_PATTERNS[chord_type_normalized]
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        chord_notes = []
        for interval in pattern:
            pitch = (root_pitch + interval) % 12
            chord_notes.append(note_names[pitch])

        return chord_notes

    def validate_scale_statement(
        self,
        statement: str,
        concept: MusicalConcept
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate a user statement about a scale.

        Args:
            statement: User's statement (e.g., "debe comenzar con la tónica en la")
            concept: The MusicalConcept being referred to

        Returns:
            (is_valid, explanation, correction_data)
        """
        if concept.concept_type != "scale":
            return False, "El concepto no es una escala.", None

        statement_lower = statement.lower()

        # Check if asking about starting note (tonic)
        if any(keyword in statement_lower for keyword in ["comenzar", "empezar", "iniciar", "tónica"]):
            # Extract claimed starting note
            claimed_tonic = None
            for note_spanish, note_english in self.NOTE_MAPPING.items():
                if note_spanish in statement_lower:
                    claimed_tonic = note_english
                    break

            if not claimed_tonic:
                return False, "No pude identificar la nota mencionada en tu afirmación.", None

            # Get actual scale notes
            actual_notes = self.get_scale_notes(concept.tonic, concept.scale_type)
            if not actual_notes:
                return False, "No pude validar la escala.", None

            actual_tonic = actual_notes[0]

            # Validate
            if claimed_tonic == actual_tonic:
                return True, (
                    f"¡Correcto! La escala {concept.description} comienza con su tónica {actual_tonic}. "
                    f"Las notas de esta escala son: {', '.join(actual_notes)}. "
                    f"La tónica es el punto de reposo y le da nombre a la escala."
                ), None
            else:
                return False, (
                    f"Incorrecto. La escala {concept.description} comienza con {actual_tonic}, no con {claimed_tonic}. "
                    f"Las notas de la escala son: {', '.join(actual_notes)}. "
                    f"La tónica siempre es la primera nota y le da nombre a la escala."
                ), {
                    "actual_tonic": actual_tonic,
                    "claimed_tonic": claimed_tonic,
                    "scale_notes": actual_notes
                }

        # Check if asking about notes in scale
        elif any(keyword in statement_lower for keyword in ["contiene", "tiene", "incluye", "nota"]):
            claimed_note = None
            for note_spanish, note_english in self.NOTE_MAPPING.items():
                if note_spanish in statement_lower:
                    claimed_note = note_english
                    break

            if not claimed_note:
                return False, "No pude identificar la nota mencionada en tu afirmación.", None

            actual_notes = self.get_scale_notes(concept.tonic, concept.scale_type)
            if not actual_notes:
                return False, "No pude validar la escala.", None

            # Check for enharmonic equivalents
            claimed_pitch = self.NOTE_PITCHES.get(claimed_note)
            actual_pitches = [self.NOTE_PITCHES.get(n) for n in actual_notes]

            if claimed_pitch in actual_pitches:
                return True, (
                    f"¡Correcto! La nota {claimed_note} está en la escala {concept.description}. "
                    f"Las notas completas son: {', '.join(actual_notes)}."
                ), None
            else:
                return False, (
                    f"Incorrecto. La nota {claimed_note} no está en la escala {concept.description}. "
                    f"Las notas de esta escala son: {', '.join(actual_notes)}."
                ), {
                    "claimed_note": claimed_note,
                    "scale_notes": actual_notes
                }

        return False, "No pude interpretar tu afirmación. ¿Puedes reformularla?", None

    def validate_chord_statement(
        self,
        statement: str,
        concept: MusicalConcept
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate a user statement about a chord.
        """
        if concept.concept_type != "chord":
            return False, "El concepto no es un acorde.", None

        statement_lower = statement.lower()

        # Check if asking about chord notes
        if any(keyword in statement_lower for keyword in ["contiene", "tiene", "incluye", "nota"]):
            claimed_note = None
            for note_spanish, note_english in self.NOTE_MAPPING.items():
                if note_spanish in statement_lower:
                    claimed_note = note_english
                    break

            if not claimed_note:
                return False, "No pude identificar la nota mencionada en tu afirmación.", None

            actual_notes = self.get_chord_notes(concept.tonic, concept.chord_type)
            if not actual_notes:
                return False, "No pude validar el acorde.", None

            claimed_pitch = self.NOTE_PITCHES.get(claimed_note)
            actual_pitches = [self.NOTE_PITCHES.get(n) for n in actual_notes]

            if claimed_pitch in actual_pitches:
                return True, (
                    f"¡Correcto! La nota {claimed_note} está en el acorde {concept.description}. "
                    f"Las notas del acorde son: {', '.join(actual_notes)}."
                ), None
            else:
                return False, (
                    f"Incorrecto. La nota {claimed_note} no está en el acorde {concept.description}. "
                    f"Las notas del acorde son: {', '.join(actual_notes)}."
                ), {
                    "claimed_note": claimed_note,
                    "chord_notes": actual_notes
                }

        return False, "No pude interpretar tu afirmación sobre el acorde.", None

    def detect_incongruency(
        self,
        user_request: str,
        generated_concept: Dict[str, Any]
    ) -> Optional[str]:
        """
        Detect if there's an incongruency between what the user requested
        and what was generated.

        Returns alert message if incongruency detected, None otherwise.
        """
        user_request_lower = user_request.lower()

        # Extract requested tonic from user input
        requested_tonic = None
        for note_spanish, note_english in self.NOTE_MAPPING.items():
            if note_spanish in user_request_lower:
                requested_tonic = note_english
                break

        # Extract requested scale type
        requested_scale_type = None
        for scale_type in self.SCALE_PATTERNS.keys():
            if scale_type.replace("_", " ") in user_request_lower:
                requested_scale_type = scale_type
                break

        # Compare with generated
        generated_tonic = generated_concept.get("tonic")
        generated_scale_type = generated_concept.get("scale_type")

        issues = []

        if requested_tonic and generated_tonic:
            if requested_tonic != generated_tonic:
                issues.append(
                    f"Solicitaste tónica {requested_tonic} pero se generó {generated_tonic}"
                )

        if requested_scale_type and generated_scale_type:
            if requested_scale_type != generated_scale_type:
                issues.append(
                    f"Solicitaste escala {requested_scale_type} pero se generó {generated_scale_type}"
                )

        if issues:
            return "⚠️ Alerta de incongruencia detectada: " + "; ".join(issues)

        return None


# Global instance
music_validator = MusicValidator()
