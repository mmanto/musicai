"""Music ontology definition and initialization."""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum

from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Node types in the music ontology."""
    # Core musical concepts
    NOTE = "Note"
    CHORD = "Chord"
    SCALE = "Scale"
    KEY = "Key"
    MODE = "Mode"
    INTERVAL = "Interval"

    # Harmonic concepts
    PROGRESSION = "Progression"
    CADENCE = "Cadence"
    FUNCTION = "HarmonicFunction"

    # Rhythmic concepts
    RHYTHM = "Rhythm"
    METER = "Meter"
    TEMPO = "Tempo"

    # Structural concepts
    FORM = "Form"
    SECTION = "Section"
    PHRASE = "Phrase"

    # Style and genre
    GENRE = "Genre"
    STYLE = "Style"
    ERA = "Era"

    # Theory
    RULE = "TheoreticalRule"
    TECHNIQUE = "Technique"


class RelationType(str, Enum):
    """Relationship types in the music ontology."""
    # Hierarchical
    CONTAINS = "CONTAINS"
    PART_OF = "PART_OF"
    IS_A = "IS_A"

    # Musical relationships
    FOLLOWS = "FOLLOWS"
    RESOLVES_TO = "RESOLVES_TO"
    SIMILAR_TO = "SIMILAR_TO"
    CONTRASTS_WITH = "CONTRASTS_WITH"

    # Functional relationships
    FUNCTIONS_AS = "FUNCTIONS_AS"
    IMPLIES = "IMPLIES"
    REQUIRES = "REQUIRES"

    # Contextual
    USED_IN = "USED_IN"
    CHARACTERISTIC_OF = "CHARACTERISTIC_OF"
    DERIVED_FROM = "DERIVED_FROM"


class MusicOntology:
    """Music knowledge graph ontology."""

    def __init__(self, client: Neo4jClient):
        """Initialize ontology with Neo4j client."""
        self.client = client

    def initialize(self) -> None:
        """Initialize the music ontology with base concepts."""
        logger.info("Initializing music ontology...")

        self._create_constraints()
        self._create_indexes()
        self._populate_notes()
        self._populate_intervals()
        self._populate_scales()
        self._populate_chords()
        self._populate_harmonic_functions()
        self._populate_cadences()
        self._populate_forms()
        self._populate_genres()

        logger.info("Music ontology initialized successfully")

    def _create_constraints(self) -> None:
        """Create uniqueness constraints."""
        constraints = [
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{nt.value}) REQUIRE n.name IS UNIQUE"
            for nt in NodeType
        ]
        for constraint in constraints:
            try:
                self.client.execute_query(constraint)
            except Exception as e:
                logger.warning(f"Constraint already exists or failed: {e}")

    def _create_indexes(self) -> None:
        """Create indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Note) ON (n.midi_number)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Chord) ON (n.quality)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Scale) ON (n.quality)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Key) ON (n.tonic)",
        ]
        for index in indexes:
            try:
                self.client.execute_query(index)
            except Exception as e:
                logger.warning(f"Index creation failed: {e}")

    def _populate_notes(self) -> None:
        """Populate note nodes."""
        notes = [
            {"name": "C", "midi_number": 60, "frequency": 261.63},
            {"name": "C#", "midi_number": 61, "frequency": 277.18},
            {"name": "D", "midi_number": 62, "frequency": 293.66},
            {"name": "D#", "midi_number": 63, "frequency": 311.13},
            {"name": "E", "midi_number": 64, "frequency": 329.63},
            {"name": "F", "midi_number": 65, "frequency": 349.23},
            {"name": "F#", "midi_number": 66, "frequency": 369.99},
            {"name": "G", "midi_number": 67, "frequency": 392.00},
            {"name": "G#", "midi_number": 68, "frequency": 415.30},
            {"name": "A", "midi_number": 69, "frequency": 440.00},
            {"name": "A#", "midi_number": 70, "frequency": 466.16},
            {"name": "B", "midi_number": 71, "frequency": 493.88},
        ]

        query = """
        UNWIND $notes AS note
        MERGE (n:Note {name: note.name})
        SET n.midi_number = note.midi_number,
            n.frequency = note.frequency
        """
        self.client.execute_query(query, {"notes": notes})
        logger.info("Populated notes")

    def _populate_intervals(self) -> None:
        """Populate interval nodes and relationships."""
        intervals = [
            {"name": "Unison", "semitones": 0, "quality": "Perfect"},
            {"name": "Minor Second", "semitones": 1, "quality": "Minor"},
            {"name": "Major Second", "semitones": 2, "quality": "Major"},
            {"name": "Minor Third", "semitones": 3, "quality": "Minor"},
            {"name": "Major Third", "semitones": 4, "quality": "Major"},
            {"name": "Perfect Fourth", "semitones": 5, "quality": "Perfect"},
            {"name": "Tritone", "semitones": 6, "quality": "Augmented"},
            {"name": "Perfect Fifth", "semitones": 7, "quality": "Perfect"},
            {"name": "Minor Sixth", "semitones": 8, "quality": "Minor"},
            {"name": "Major Sixth", "semitones": 9, "quality": "Major"},
            {"name": "Minor Seventh", "semitones": 10, "quality": "Minor"},
            {"name": "Major Seventh", "semitones": 11, "quality": "Major"},
            {"name": "Octave", "semitones": 12, "quality": "Perfect"},
        ]

        query = """
        UNWIND $intervals AS interval
        MERGE (i:Interval {name: interval.name})
        SET i.semitones = interval.semitones,
            i.quality = interval.quality
        """
        self.client.execute_query(query, {"intervals": intervals})
        logger.info("Populated intervals")

    def _populate_scales(self) -> None:
        """Populate scale nodes."""
        scales = [
            {"name": "Major", "pattern": [2, 2, 1, 2, 2, 2, 1], "quality": "Major"},
            {"name": "Natural Minor", "pattern": [2, 1, 2, 2, 1, 2, 2], "quality": "Minor"},
            {"name": "Harmonic Minor", "pattern": [2, 1, 2, 2, 1, 3, 1], "quality": "Minor"},
            {"name": "Melodic Minor", "pattern": [2, 1, 2, 2, 2, 2, 1], "quality": "Minor"},
            {"name": "Dorian", "pattern": [2, 1, 2, 2, 2, 1, 2], "quality": "Modal"},
            {"name": "Phrygian", "pattern": [1, 2, 2, 2, 1, 2, 2], "quality": "Modal"},
            {"name": "Lydian", "pattern": [2, 2, 2, 1, 2, 2, 1], "quality": "Modal"},
            {"name": "Mixolydian", "pattern": [2, 2, 1, 2, 2, 1, 2], "quality": "Modal"},
            {"name": "Pentatonic Major", "pattern": [2, 2, 3, 2, 3], "quality": "Pentatonic"},
            {"name": "Pentatonic Minor", "pattern": [3, 2, 2, 3, 2], "quality": "Pentatonic"},
            {"name": "Blues", "pattern": [3, 2, 1, 1, 3, 2], "quality": "Blues"},
        ]

        query = """
        UNWIND $scales AS scale
        MERGE (s:Scale {name: scale.name})
        SET s.pattern = scale.pattern,
            s.quality = scale.quality
        """
        self.client.execute_query(query, {"scales": scales})
        logger.info("Populated scales")

    def _populate_chords(self) -> None:
        """Populate chord nodes."""
        chords = [
            {"name": "Major", "intervals": [0, 4, 7], "quality": "Major", "symbol": ""},
            {"name": "Minor", "intervals": [0, 3, 7], "quality": "Minor", "symbol": "m"},
            {"name": "Diminished", "intervals": [0, 3, 6], "quality": "Diminished", "symbol": "dim"},
            {"name": "Augmented", "intervals": [0, 4, 8], "quality": "Augmented", "symbol": "aug"},
            {"name": "Major 7th", "intervals": [0, 4, 7, 11], "quality": "Major", "symbol": "maj7"},
            {"name": "Dominant 7th", "intervals": [0, 4, 7, 10], "quality": "Dominant", "symbol": "7"},
            {"name": "Minor 7th", "intervals": [0, 3, 7, 10], "quality": "Minor", "symbol": "m7"},
            {"name": "Half-Diminished 7th", "intervals": [0, 3, 6, 10], "quality": "Half-Diminished", "symbol": "m7b5"},
            {"name": "Diminished 7th", "intervals": [0, 3, 6, 9], "quality": "Diminished", "symbol": "dim7"},
        ]

        query = """
        UNWIND $chords AS chord
        MERGE (c:Chord {name: chord.name})
        SET c.intervals = chord.intervals,
            c.quality = chord.quality,
            c.symbol = chord.symbol
        """
        self.client.execute_query(query, {"chords": chords})
        logger.info("Populated chords")

    def _populate_harmonic_functions(self) -> None:
        """Populate harmonic function nodes."""
        functions = [
            {"name": "Tonic", "stability": "Stable", "tension": 0},
            {"name": "Subdominant", "stability": "Transitional", "tension": 3},
            {"name": "Dominant", "stability": "Unstable", "tension": 7},
            {"name": "Pre-Dominant", "stability": "Transitional", "tension": 4},
        ]

        query = """
        UNWIND $functions AS func
        MERGE (f:HarmonicFunction {name: func.name})
        SET f.stability = func.stability,
            f.tension = func.tension
        """
        self.client.execute_query(query, {"functions": functions})

        # Create relationships
        self.client.execute_query("""
            MATCH (t:HarmonicFunction {name: 'Tonic'})
            MATCH (s:HarmonicFunction {name: 'Subdominant'})
            MATCH (d:HarmonicFunction {name: 'Dominant'})
            MERGE (t)-[:FOLLOWS]->(s)
            MERGE (s)-[:FOLLOWS]->(d)
            MERGE (d)-[:RESOLVES_TO]->(t)
        """)
        logger.info("Populated harmonic functions")

    def _populate_cadences(self) -> None:
        """Populate cadence nodes."""
        cadences = [
            {"name": "Authentic", "strength": "Strong", "formula": "V-I"},
            {"name": "Half", "strength": "Weak", "formula": "I-V"},
            {"name": "Plagal", "strength": "Moderate", "formula": "IV-I"},
            {"name": "Deceptive", "strength": "Weak", "formula": "V-vi"},
        ]

        query = """
        UNWIND $cadences AS cadence
        MERGE (c:Cadence {name: cadence.name})
        SET c.strength = cadence.strength,
            c.formula = cadence.formula
        """
        self.client.execute_query(query, {"cadences": cadences})
        logger.info("Populated cadences")

    def _populate_forms(self) -> None:
        """Populate musical form nodes."""
        forms = [
            {"name": "Binary", "structure": "AB", "repetition": True},
            {"name": "Ternary", "structure": "ABA", "repetition": True},
            {"name": "Rondo", "structure": "ABACA", "repetition": True},
            {"name": "Sonata", "structure": "Exposition-Development-Recapitulation", "repetition": False},
            {"name": "Theme and Variations", "structure": "A A' A'' ...", "repetition": True},
        ]

        query = """
        UNWIND $forms AS form
        MERGE (f:Form {name: form.name})
        SET f.structure = form.structure,
            f.repetition = form.repetition
        """
        self.client.execute_query(query, {"forms": forms})
        logger.info("Populated forms")

    def _populate_genres(self) -> None:
        """Populate genre nodes."""
        genres = [
            {"name": "Classical", "era": "Various", "characteristics": ["Formal structure", "Written notation"]},
            {"name": "Jazz", "era": "20th Century", "characteristics": ["Improvisation", "Swing rhythm"]},
            {"name": "Rock", "era": "20th Century", "characteristics": ["Electric instruments", "Strong beat"]},
            {"name": "Pop", "era": "20th-21st Century", "characteristics": ["Catchy melodies", "Verse-chorus form"]},
            {"name": "Electronic", "era": "20th-21st Century", "characteristics": ["Synthesizers", "Digital production"]},
        ]

        query = """
        UNWIND $genres AS genre
        MERGE (g:Genre {name: genre.name})
        SET g.era = genre.era,
            g.characteristics = genre.characteristics
        """
        self.client.execute_query(query, {"genres": genres})
        logger.info("Populated genres")

    def query_related_concepts(
        self,
        concept_name: str,
        relationship_type: Optional[str] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Query related musical concepts."""
        rel_pattern = f"[r:{relationship_type}*1..{max_depth}]" if relationship_type else f"[r*1..{max_depth}]"
        query = f"""
        MATCH (n)-{rel_pattern}-(related)
        WHERE toLower(n.name) = toLower($concept_name)
        RETURN DISTINCT related, r
        """
        return self.client.execute_query(query, {"concept_name": concept_name})

    def get_scale_chords(self, scale_name: str) -> List[Dict[str, Any]]:
        """Get chords that belong to a scale."""
        query = """
        MATCH (s:Scale {name: $scale_name})-[:CONTAINS]->(c:Chord)
        RETURN c
        """
        return self.client.execute_query(query, {"scale_name": scale_name})

    def get_chord_progressions(self, genre: str) -> List[Dict[str, Any]]:
        """Get common chord progressions for a genre."""
        query = """
        MATCH (g:Genre {name: $genre})-[:CHARACTERISTIC_OF]->(p:Progression)
        RETURN p
        """
        return self.client.execute_query(query, {"genre": genre})
