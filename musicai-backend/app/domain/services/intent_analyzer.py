"""
Intent Analyzer Service

Centralizes all input analysis logic for the MusicAI application.
Detects user intent and extracts musical parameters from natural language input.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Types of user intents the system can detect."""
    PATTERN = "pattern"           # Direct pattern request (scale, chord, arpeggio)
    THEORY_QUESTION = "theory"    # Question about music theory
    VALIDATION = "validation"     # User validating/questioning a concept
    CREATIVE = "creative"         # Creative music generation request
    CHAT = "chat"                 # General conversation


@dataclass
class PatternData:
    """Extracted pattern data from user input."""
    pattern_type: str  # 'scale', 'chord', 'arpeggio'
    tonic: Optional[str] = None
    scale_type: Optional[str] = None
    chord_type: Optional[str] = None
    chord_symbols: Optional[str] = None
    octaves: int = 1
    tempo: int = 120
    duration: float = 1.0
    clef: str = 'treble'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'pattern_type': self.pattern_type,
            'tonic': self.tonic,
            'scale_type': self.scale_type,
            'chord_type': self.chord_type,
            'chord_symbols': self.chord_symbols,
            'octaves': self.octaves,
            'tempo': self.tempo,
            'duration': self.duration,
            'clef': self.clef,
        }


@dataclass
class IntentAnalysisResult:
    """Result of analyzing user input."""
    intent: IntentType
    should_stream: bool = False
    pattern_data: Optional[PatternData] = None
    confidence: float = 1.0
    detected_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'intent': self.intent.value,
            'should_stream': self.should_stream,
            'pattern_data': self.pattern_data.to_dict() if self.pattern_data else None,
            'confidence': self.confidence,
            'detected_keywords': self.detected_keywords,
        }


class IntentAnalyzer:
    """
    Analyzes user input to determine intent and extract musical parameters.

    This service centralizes all the detection logic that was previously
    scattered across the frontend.
    """

    # Spanish to English note mapping
    TONIC_MAP: Dict[str, str] = {
        'do': 'C', 'do#': 'C#', 'dob': 'Cb',
        're': 'D', 're#': 'D#', 'reb': 'Db',
        'mi': 'E', 'mib': 'Eb',
        'fa': 'F', 'fa#': 'F#',
        'sol': 'G', 'sol#': 'G#', 'solb': 'Gb',
        'la': 'A', 'la#': 'A#', 'lab': 'Ab',
        'si': 'B', 'sib': 'Bb',
    }

    # Scale type mapping (Spanish to music21)
    SCALE_TYPE_MAP: Dict[str, str] = {
        'mayor': 'major',
        'minor': 'minor',
        'menor': 'minor',
        'armónica': 'harmonic minor',
        'armonica': 'harmonic minor',
        'melódica': 'melodic minor',
        'melodica': 'melodic minor',
        'cromática': 'chromatic',
        'cromatica': 'chromatic',
        'pentatónica': 'pentatonic major',
        'pentatonica': 'pentatonic major',
        'pentatónica mayor': 'pentatonic major',
        'pentatonica mayor': 'pentatonic major',
        'pentatónica menor': 'pentatonic minor',
        'pentatonica menor': 'pentatonic minor',
        'doria': 'dorian',
        'dorian': 'dorian',
        'frigia': 'phrygian',
        'phrygian': 'phrygian',
        'lidia': 'lydian',
        'lydian': 'lydian',
        'mixolidia': 'mixolydian',
        'mixolydian': 'mixolydian',
        'locria': 'locrian',
        'locrian': 'locrian',
    }

    # Chord quality mapping
    CHORD_QUALITY_MAP: Dict[str, str] = {
        'mayor': '',  # major is default
        'menor': 'm',
        'minor': 'm',
        'séptima': '7',
        'septima': '7',
        'maj7': 'maj7',
        'aumentado': 'aug',
        'disminuido': 'dim',
    }

    # Keywords for theory questions (ordered by specificity)
    # These keywords indicate a question about music theory
    THEORY_KEYWORDS: List[str] = [
        'qué es', 'que es',
        'explica', 'explicame', 'explícame',
        'diferencia entre', 'diferencias entre',
        'cómo funciona', 'cómo se',
        'cuál es', 'cual es',
        'cuáles son', 'cuales son',
        'por qué', 'por que', 'porqué',
        'para qué', 'para que',
        'muéstrame', 'muestrame',
        'ejemplos de',
        'dime sobre', 'háblame de', 'hablame de',
    ]

    # Strong theory keywords that override pattern detection
    # These indicate the user is ASKING about something, not requesting generation
    STRONG_THEORY_KEYWORDS: List[str] = [
        'qué es', 'que es',
        'qué se entiende', 'que se entiende',
        'qué significa', 'que significa',
        'explica', 'explicame', 'explícame',
        'cómo funciona', 'cómo se', 'como funciona', 'como se',
        'diferencia entre',
        'dime sobre', 'háblame de', 'hablame de',
        'cuéntame', 'cuentame',
        'por qué', 'por que',
        'para qué sirve', 'para que sirve',
        'cuándo se usa', 'cuando se usa',
        'en qué consiste', 'en que consiste',
    ]

    # Question indicators - if message contains these AND a musical term,
    # it's likely a question about music, not a generation request
    QUESTION_INDICATORS: List[str] = [
        '?',  # Question mark is a strong indicator
        'qué', 'que',
        'cómo', 'como',
        'cuál', 'cual',
        'cuándo', 'cuando',
        'dónde', 'donde',
        'por qué', 'porque',
        'para qué',
    ]

    # Keywords for validation questions
    VALIDATION_KEYWORDS: List[str] = [
        'debe', 'debería', 'tiene que', 'es correcto', 'está bien',
        'es verdad', 'cierto que', 'correcto que', 'debo', 'tengo que',
        'comienza con', 'empieza con', 'termina con', 'contiene',
        'incluye', 'tiene la nota', 'esa escala', 'ese acorde',
        'esta escala', 'este acorde', 'la escala', 'el acorde'
    ]

    def analyze(self, message: str, context: Optional[Dict[str, Any]] = None) -> IntentAnalysisResult:
        """
        Analyze user message to determine intent and extract parameters.

        Args:
            message: User's input message
            context: Optional conversation context for better analysis

        Returns:
            IntentAnalysisResult with detected intent and any extracted data
        """
        lower_message = message.lower().strip()
        detected_keywords = []

        logger.info(f"Analyzing message: {message[:100]}...")

        # Check if message contains a question mark - strong indicator of a question
        is_question = '?' in message

        # 1. First check for STRONG theory questions (these override pattern detection)
        # e.g., "qué es una escala pentatónica?" should be theory, not pattern
        strong_theory_keywords = []
        for keyword in self.STRONG_THEORY_KEYWORDS:
            if keyword in lower_message:
                strong_theory_keywords.append(keyword)

        if strong_theory_keywords:
            logger.info(f"Detected strong theory question: {strong_theory_keywords}")
            return IntentAnalysisResult(
                intent=IntentType.THEORY_QUESTION,
                should_stream=True,
                confidence=0.95,
                detected_keywords=strong_theory_keywords,
            )

        # 2. If message has question mark AND contains musical terms, it's likely a theory question
        # This catches cases like "que se entiende por escala mayor?"
        if is_question:
            musical_terms = ['escala', 'acorde', 'arpegio', 'nota', 'tono', 'semitono',
                           'intervalo', 'pentatónica', 'pentatonica', 'mayor', 'menor',
                           'armónica', 'melodica', 'cromática', 'modo', 'tonalidad']
            found_musical_terms = [term for term in musical_terms if term in lower_message]
            if found_musical_terms:
                logger.info(f"Detected question about music (has '?' and musical terms: {found_musical_terms})")
                return IntentAnalysisResult(
                    intent=IntentType.THEORY_QUESTION,
                    should_stream=True,
                    confidence=0.9,
                    detected_keywords=['question_with_musical_term'] + found_musical_terms,
                )

        # 3. Check for direct pattern requests (only if not a question)
        pattern_data = self._detect_pattern(lower_message)
        if pattern_data:
            logger.info(f"Detected pattern request: {pattern_data.pattern_type}")
            return IntentAnalysisResult(
                intent=IntentType.PATTERN,
                should_stream=False,
                pattern_data=pattern_data,
                confidence=0.95,
                detected_keywords=['pattern_request'],
            )

        # 4. Check for validation questions
        validation_keywords = []
        for keyword in self.VALIDATION_KEYWORDS:
            if keyword in lower_message:
                validation_keywords.append(keyword)

        if validation_keywords and context and context.get('last_concept'):
            logger.info(f"Detected validation question: {validation_keywords}")
            return IntentAnalysisResult(
                intent=IntentType.VALIDATION,
                should_stream=True,
                confidence=0.85,
                detected_keywords=validation_keywords,
            )

        # 5. Check for regular theory questions
        theory_keywords = []
        for keyword in self.THEORY_KEYWORDS:
            if keyword in lower_message:
                theory_keywords.append(keyword)

        if theory_keywords:
            logger.info(f"Detected theory question: {theory_keywords}")
            return IntentAnalysisResult(
                intent=IntentType.THEORY_QUESTION,
                should_stream=True,
                confidence=0.9,
                detected_keywords=theory_keywords,
            )

        # 6. Check for creative generation requests
        creative_keywords = ['crea', 'genera', 'compón', 'compone', 'improvisa', 'melodía', 'canción']
        for keyword in creative_keywords:
            if keyword in lower_message:
                detected_keywords.append(keyword)

        if detected_keywords and not any(k in lower_message for k in ['escala', 'acorde', 'arpegio']):
            logger.info(f"Detected creative request: {detected_keywords}")
            return IntentAnalysisResult(
                intent=IntentType.CREATIVE,
                should_stream=True,
                confidence=0.75,
                detected_keywords=detected_keywords,
            )

        # 7. Default to general chat with streaming
        logger.info("Defaulting to general chat")
        return IntentAnalysisResult(
            intent=IntentType.CHAT,
            should_stream=True,
            confidence=0.5,
            detected_keywords=[],
        )

    def _detect_pattern(self, lower_message: str) -> Optional[PatternData]:
        """Detect and extract pattern data from message."""

        # Detect clef first
        clef = self._detect_clef(lower_message)

        # Try to detect scale
        scale_data = self._detect_scale(lower_message, clef)
        if scale_data:
            return scale_data

        # Try to detect chord
        chord_data = self._detect_chord(lower_message, clef)
        if chord_data:
            return chord_data

        # Try to detect arpeggio
        arpeggio_data = self._detect_arpeggio(lower_message, clef)
        if arpeggio_data:
            return arpeggio_data

        return None

    def _detect_clef(self, lower_message: str) -> str:
        """Detect clef from message."""
        if 'clave de sol' in lower_message or 'treble' in lower_message:
            return 'treble'
        elif 'clave de fa' in lower_message or 'bass' in lower_message:
            return 'bass'
        elif 'clave de do' in lower_message or 'alto' in lower_message:
            return 'alto'
        elif 'tenor' in lower_message:
            return 'tenor'
        return 'treble'

    def _detect_scale(self, lower_message: str, clef: str) -> Optional[PatternData]:
        """Detect scale patterns in message."""

        # Must contain 'escala' or 'pentatonica/pentatónica'
        if not ('escala' in lower_message or 'pentatonica' in lower_message or 'pentatónica' in lower_message):
            return None

        tonic = 'C'
        scale_type = 'major'

        # Pattern 1: "escala pentatónica menor en la" or "escala pentatónica menor de la"
        match = re.search(
            r'escala\s+(pentat[oó]nica\s+(?:mayor|menor)|arm[oó]nica(?:\s+menor)?|mel[oó]dica(?:\s+menor)?|crom[aá]tica|mayor|menor|dor[ií]a|frigia|lidia|mixolidia|locria)\s+(?:de|en)\s+(do|re|mi|fa|sol|la|si)(?:#|b)?',
            lower_message,
            re.IGNORECASE
        )

        if match:
            type_spanish = match.group(1).strip().lower()
            tonic_spanish = match.group(2).strip().lower()
            scale_type = self.SCALE_TYPE_MAP.get(type_spanish, 'major')
            tonic = self.TONIC_MAP.get(tonic_spanish, 'C')
            logger.info(f"Pattern 1 matched: {tonic} {scale_type}")
        else:
            # Pattern 1b: "pentatónica de do mayor" (without "escala" prefix)
            match = re.search(
                r'(pentat[oó]nica)\s+(?:de|en)\s+(do|re|mi|fa|sol|la|si)(?:#|b)?\s*(mayor|menor)?',
                lower_message,
                re.IGNORECASE
            )

            if match:
                tonic_spanish = match.group(2).strip().lower()
                tonic = self.TONIC_MAP.get(tonic_spanish, 'C')
                pentatonic_type = f"pentatónica {match.group(3).lower()}" if match.group(3) else 'pentatónica'
                scale_type = self.SCALE_TYPE_MAP.get(pentatonic_type, 'pentatonic major')
                logger.info(f"Pattern 1b matched: {tonic} {scale_type}")
            else:
                # Pattern 2: "escala de do mayor" or "escala en la menor"
                match = re.search(
                    r'escala\s+(?:de|en)\s+(do|re|mi|fa|sol|la|si)(?:#|b)?\s*(pentat[oó]nica\s+(?:mayor|menor)|mayor|menor|arm[oó]nica|mel[oó]dica|crom[aá]tica|pentat[oó]nica|dor[ií]a|frigia|lidia|mixolidia|locria)?',
                    lower_message,
                    re.IGNORECASE
                )

                if match:
                    tonic_spanish = match.group(1).strip().lower()
                    tonic = self.TONIC_MAP.get(tonic_spanish, 'C')
                    if match.group(2):
                        type_spanish = match.group(2).strip().lower()
                        scale_type = self.SCALE_TYPE_MAP.get(type_spanish, 'major')
                    logger.info(f"Pattern 2 matched: {tonic} {scale_type}")
                else:
                    # Pattern 3: Simple "do mayor", "la menor" without "escala" prefix
                    match = re.search(
                        r'\b(do|re|mi|fa|sol|la|si)(?:#|b)?\s+(pentat[oó]nica\s+(?:mayor|menor)|mayor|menor|arm[oó]nica|mel[oó]dica|crom[aá]tica|pentat[oó]nica|dor[ií]a|frigia|lidia|mixolidia|locria)',
                        lower_message,
                        re.IGNORECASE
                    )

                    if match:
                        tonic_spanish = match.group(1).strip().lower()
                        type_spanish = match.group(2).strip().lower()
                        tonic = self.TONIC_MAP.get(tonic_spanish, 'C')
                        scale_type = self.SCALE_TYPE_MAP.get(type_spanish, 'major')
                        logger.info(f"Pattern 3 matched: {tonic} {scale_type}")
                    else:
                        # No pattern matched, but we have 'escala' keyword
                        logger.info("Scale keyword found but no specific pattern matched")

        return PatternData(
            pattern_type='scale',
            tonic=tonic,
            scale_type=scale_type,
            octaves=1,
            tempo=120,
            duration=1.0,
            clef=clef,
        )

    def _detect_chord(self, lower_message: str, clef: str) -> Optional[PatternData]:
        """Detect chord patterns in message."""

        # Check for chord keywords
        chord_match = re.search(
            r'acorde[s]?\s+(?:de\s+)?([a-z#b\s,]+?)(?:\s*$|\s+(?:en|con|y|a))',
            lower_message,
            re.IGNORECASE
        )

        if not chord_match and 'progresión' not in lower_message and 'progresion' not in lower_message:
            return None

        chord_symbols = 'C,Am,F,G'  # Default progression

        if chord_match:
            raw_chord = chord_match.group(1).strip()

            # Check if it's comma-separated (English format)
            if ',' in raw_chord:
                chord_symbols = raw_chord
            else:
                # Parse Spanish format
                chord_symbols = self._parse_spanish_chord(raw_chord)

        return PatternData(
            pattern_type='chord',
            chord_symbols=chord_symbols,
            tempo=90,
            duration=1.0,
            clef=clef,
        )

    def _parse_spanish_chord(self, raw_chord: str) -> str:
        """Parse Spanish chord notation to standard format."""
        note_name = ''
        quality = ''

        # Try compound note names like "si bemol"
        compound_match = re.search(r'(do|re|mi|fa|sol|la|si)\s+(bemol|sostenido|#|b)', raw_chord, re.IGNORECASE)

        if compound_match:
            note_key = compound_match.group(1) + ('b' if compound_match.group(2) in ['bemol', 'b'] else '#')
            note_name = self.TONIC_MAP.get(note_key, self.TONIC_MAP.get(compound_match.group(1), 'C'))

            # Check for quality
            quality_match = re.search(r'(mayor|menor|séptima|septima|maj7|aumentado|disminuido)', raw_chord, re.IGNORECASE)
            if quality_match:
                quality = self.CHORD_QUALITY_MAP.get(quality_match.group(1).lower(), '')
        else:
            # Simple note name
            simple_match = re.search(r'(do|re|mi|fa|sol|la|si|[a-g])(#|b)?', raw_chord, re.IGNORECASE)
            if simple_match:
                note_key = (simple_match.group(1) + (simple_match.group(2) or '')).lower()
                note_name = self.TONIC_MAP.get(note_key, simple_match.group(1).upper())

                quality_match = re.search(r'(mayor|menor|minor|séptima|septima|maj7|aumentado|disminuido)', raw_chord, re.IGNORECASE)
                if quality_match:
                    quality = self.CHORD_QUALITY_MAP.get(quality_match.group(1).lower(), '')

        return (note_name or 'C') + quality

    def _detect_arpeggio(self, lower_message: str, clef: str) -> Optional[PatternData]:
        """Detect arpeggio patterns in message."""

        if 'arpegio' not in lower_message and 'arpeggio' not in lower_message:
            return None

        # Try to extract root note
        tonic = 'C'
        chord_type = 'major'

        for spanish, english in self.TONIC_MAP.items():
            if spanish in lower_message:
                tonic = english
                break

        # Check for chord quality
        if 'menor' in lower_message or 'minor' in lower_message:
            chord_type = 'minor'
        elif 'aumentado' in lower_message:
            chord_type = 'augmented'
        elif 'disminuido' in lower_message:
            chord_type = 'diminished'
        elif '7' in lower_message or 'séptima' in lower_message or 'septima' in lower_message:
            chord_type = 'dominant7'

        return PatternData(
            pattern_type='arpeggio',
            tonic=tonic,
            chord_type=chord_type,
            octaves=1,
            tempo=120,
            duration=0.5,
            clef=clef,
        )


# Singleton instance
intent_analyzer = IntentAnalyzer()
