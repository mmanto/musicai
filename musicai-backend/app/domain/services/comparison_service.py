"""
Music comparison service.
Compares two musical concepts and highlights differences.
"""
import logging
from typing import List, Tuple, Dict, Any
from app.domain.services.music_validator import MusicValidator

logger = logging.getLogger(__name__)


class MusicComparisonService:
    """
    Service for comparing musical concepts and identifying differences.
    """

    def __init__(self):
        self.validator = MusicValidator()

    def compare_scales(
        self,
        tonic1: str,
        scale_type1: str,
        tonic2: str,
        scale_type2: str
    ) -> Tuple[List[str], str]:
        """
        Compare two scales and return differences.

        Args:
            tonic1: Tonic of first scale
            scale_type1: Type of first scale
            tonic2: Tonic of second scale
            scale_type2: Type of second scale

        Returns:
            (list of differences, educational explanation)
        """
        # Get notes for both scales
        notes1 = self.validator.get_scale_notes(tonic1, scale_type1)
        notes2 = self.validator.get_scale_notes(tonic2, scale_type2)

        if not notes1 or not notes2:
            return ([], "No se pudieron comparar las escalas.")

        differences = []
        explanation_parts = []

        # Compare tonics
        if tonic1 != tonic2:
            differences.append(f"Tónica diferente: {tonic1} vs {tonic2}")
            explanation_parts.append(
                f"La primera escala tiene tónica {tonic1}, mientras que la segunda tiene {tonic2}."
            )

        # Compare scale types
        if scale_type1 != scale_type2:
            differences.append(f"Tipo de escala diferente: {scale_type1} vs {scale_type2}")
            explanation_parts.append(
                f"Se comparan dos tipos de escala: {scale_type1} y {scale_type2}."
            )

        # Compare notes
        notes1_set = set(notes1)
        notes2_set = set(notes2)

        only_in_1 = notes1_set - notes2_set
        only_in_2 = notes2_set - notes1_set
        common = notes1_set & notes2_set

        if only_in_1:
            differences.append(f"Solo en la primera: {', '.join(sorted(only_in_1))}")
            explanation_parts.append(
                f"La primera escala tiene estas notas que la segunda no tiene: {', '.join(sorted(only_in_1))}."
            )

        if only_in_2:
            differences.append(f"Solo en la segunda: {', '.join(sorted(only_in_2))}")
            explanation_parts.append(
                f"La segunda escala tiene estas notas que la primera no tiene: {', '.join(sorted(only_in_2))}."
            )

        if common:
            explanation_parts.append(
                f"Notas en común: {', '.join(sorted(common))}."
            )

        # Compare number of notes
        if len(notes1) != len(notes2):
            differences.append(f"Número de notas diferente: {len(notes1)} vs {len(notes2)}")
            explanation_parts.append(
                f"La primera escala tiene {len(notes1)} notas, la segunda tiene {len(notes2)}."
            )

        # Generate educational explanation
        scale1_name = f"{tonic1} {scale_type1}"
        scale2_name = f"{tonic2} {scale_type2}"

        explanation = f"**Comparación: {scale1_name} vs {scale2_name}**\n\n"
        explanation += f"**Escala 1 ({scale1_name})**: {', '.join(notes1)}\n"
        explanation += f"**Escala 2 ({scale2_name})**: {', '.join(notes2)}\n\n"

        if explanation_parts:
            explanation += "**Diferencias identificadas:**\n"
            for part in explanation_parts:
                explanation += f"- {part}\n"
        else:
            explanation += "Las escalas son idénticas.\n"

        # Add musical context
        if not differences:
            explanation += "\nEstas escalas tienen las mismas notas y características."
        elif scale_type1 == scale_type2 and tonic1 != tonic2:
            explanation += f"\nAmbas son escalas {scale_type1}, pero en diferentes tonalidades."
        elif scale_type1 != scale_type2 and tonic1 == tonic2:
            explanation += f"\nAmbas tienen la misma tónica ({tonic1}), pero son tipos de escala diferentes. "
            explanation += "Esto afecta el color emocional y las aplicaciones musicales de cada una."

        return (differences, explanation)

    def compare_chords(
        self,
        root1: str,
        chord_type1: str,
        root2: str,
        chord_type2: str
    ) -> Tuple[List[str], str]:
        """
        Compare two chords and return differences.

        Args:
            root1: Root of first chord
            chord_type1: Type of first chord
            root2: Root of second chord
            chord_type2: Type of second chord

        Returns:
            (list of differences, educational explanation)
        """
        # Get notes for both chords
        notes1 = self.validator.get_chord_notes(root1, chord_type1)
        notes2 = self.validator.get_chord_notes(root2, chord_type2)

        if not notes1 or not notes2:
            return ([], "No se pudieron comparar los acordes.")

        differences = []
        explanation_parts = []

        # Compare roots
        if root1 != root2:
            differences.append(f"Raíz diferente: {root1} vs {root2}")
            explanation_parts.append(
                f"El primer acorde tiene raíz {root1}, mientras que el segundo tiene {root2}."
            )

        # Compare chord types
        if chord_type1 != chord_type2:
            differences.append(f"Tipo de acorde diferente: {chord_type1} vs {chord_type2}")
            explanation_parts.append(
                f"Se comparan dos tipos de acorde: {chord_type1} y {chord_type2}."
            )

        # Compare notes
        notes1_set = set(notes1)
        notes2_set = set(notes2)

        only_in_1 = notes1_set - notes2_set
        only_in_2 = notes2_set - notes1_set
        common = notes1_set & notes2_set

        if only_in_1:
            differences.append(f"Solo en el primero: {', '.join(sorted(only_in_1))}")
            explanation_parts.append(
                f"El primer acorde tiene estas notas que el segundo no tiene: {', '.join(sorted(only_in_1))}."
            )

        if only_in_2:
            differences.append(f"Solo en el segundo: {', '.join(sorted(only_in_2))}")
            explanation_parts.append(
                f"El segundo acorde tiene estas notas que el primero no tiene: {', '.join(sorted(only_in_2))}."
            )

        if common:
            explanation_parts.append(
                f"Notas en común: {', '.join(sorted(common))}."
            )

        # Generate educational explanation
        chord1_name = f"{root1} {chord_type1}"
        chord2_name = f"{root2} {chord_type2}"

        explanation = f"**Comparación: {chord1_name} vs {chord2_name}**\n\n"
        explanation += f"**Acorde 1 ({chord1_name})**: {', '.join(notes1)}\n"
        explanation += f"**Acorde 2 ({chord2_name})**: {', '.join(notes2)}\n\n"

        if explanation_parts:
            explanation += "**Diferencias identificadas:**\n"
            for part in explanation_parts:
                explanation += f"- {part}\n"
        else:
            explanation += "Los acordes son idénticos.\n"

        # Add musical context
        if not differences:
            explanation += "\nEstos acordes tienen las mismas notas y características."
        elif chord_type1 == chord_type2 and root1 != root2:
            explanation += f"\nAmbos son acordes {chord_type1}, pero con diferente raíz."
        elif chord_type1 != chord_type2 and root1 == root2:
            explanation += f"\nAmbos tienen la misma raíz ({root1}), pero son tipos de acorde diferentes. "
            explanation += "Esto cambia significativamente su sonoridad y función armónica."

        return (differences, explanation)

    def compare_concepts(
        self,
        concept1: Dict[str, Any],
        concept2: Dict[str, Any]
    ) -> Tuple[List[str], str]:
        """
        Compare two musical concepts (generic).

        Args:
            concept1: First concept dict with type, tonic/root, scale_type/chord_type, etc.
            concept2: Second concept dict

        Returns:
            (list of differences, educational explanation)
        """
        type1 = concept1.get('pattern_type', 'unknown')
        type2 = concept2.get('pattern_type', 'unknown')

        # Check if same type
        if type1 != type2:
            return (
                [f"Tipos diferentes: {type1} vs {type2}"],
                f"No se pueden comparar un {type1} con un {type2}. "
                f"Por favor compara conceptos del mismo tipo."
            )

        # Route to appropriate comparison method
        if type1 == 'scale':
            return self.compare_scales(
                concept1.get('tonic', 'C'),
                concept1.get('scale_type', 'major'),
                concept2.get('tonic', 'C'),
                concept2.get('scale_type', 'major')
            )
        elif type1 in ['chord', 'arpeggio']:
            return self.compare_chords(
                concept1.get('tonic', 'C'),
                concept1.get('chord_type', 'major'),
                concept2.get('tonic', 'C'),
                concept2.get('chord_type', 'major')
            )
        else:
            return (
                [],
                f"Tipo de comparación no soportado: {type1}"
            )


# Global instance
comparison_service = MusicComparisonService()
