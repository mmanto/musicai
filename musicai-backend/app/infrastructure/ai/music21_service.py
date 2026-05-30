"""
Music21 Service - Central music processing hub.

This service handles all music21 operations:
- Format conversions (MIDI, MusicXML, ABC, audio)
- Musical analysis
- Transformations
- Serialization/deserialization
"""

import io
import json
import logging
from typing import Optional, Dict, Any, List, BinaryIO
from pathlib import Path

import music21
from music21 import stream, converter, analysis, chord, key, meter, tempo, note, scale, pitch, clef
from music21.freezeThaw import StreamFreezer, StreamThawer

logger = logging.getLogger(__name__)


class Music21Service:
    """
    Central service for music21 operations.

    All musical data flows through music21.stream.Stream objects.
    """

    def __init__(self):
        """Initialize music21 service."""
        # Configure music21 environment
        music21.environment.UserSettings()['warnings'] = 0  # Suppress warnings
        logger.info("Music21 service initialized")

    # ==================== INPUT METHODS ====================

    def from_midi_bytes(self, midi_bytes: bytes) -> stream.Stream:
        """
        Convert MIDI bytes to music21 Stream.

        Args:
            midi_bytes: MIDI file as bytes

        Returns:
            music21.stream.Stream object
        """
        try:
            midi_file = io.BytesIO(midi_bytes)
            score = converter.parse(midi_file, format='midi')
            logger.info(f"Converted MIDI to Stream: {len(score.flatten().notes)} notes")
            return score
        except Exception as e:
            logger.error(f"Error converting MIDI to Stream: {e}")
            raise ValueError(f"Invalid MIDI data: {e}")

    def from_midi_file(self, file_path: str) -> stream.Stream:
        """
        Load MIDI file and convert to Stream.

        Args:
            file_path: Path to MIDI file

        Returns:
            music21.stream.Stream object
        """
        try:
            score = converter.parse(file_path)
            logger.info(f"Loaded MIDI file: {file_path}")
            return score
        except Exception as e:
            logger.error(f"Error loading MIDI file: {e}")
            raise ValueError(f"Could not load MIDI file: {e}")

    def from_musicxml(self, musicxml_str: str) -> stream.Stream:
        """
        Parse MusicXML string to Stream.

        Args:
            musicxml_str: MusicXML as string

        Returns:
            music21.stream.Stream object
        """
        try:
            score = converter.parse(musicxml_str, format='musicxml')
            logger.info("Converted MusicXML to Stream")
            return score
        except Exception as e:
            logger.error(f"Error parsing MusicXML: {e}")
            raise ValueError(f"Invalid MusicXML: {e}")

    def from_abc(self, abc_str: str) -> stream.Stream:
        """
        Parse ABC notation to Stream.

        Args:
            abc_str: ABC notation as string

        Returns:
            music21.stream.Stream object
        """
        try:
            score = converter.parse(abc_str, format='abc')
            logger.info("Converted ABC to Stream")
            return score
        except Exception as e:
            logger.error(f"Error parsing ABC: {e}")
            raise ValueError(f"Invalid ABC notation: {e}")

    # ==================== OUTPUT METHODS ====================

    def to_midi_bytes(self, score: stream.Stream) -> bytes:
        """
        Convert Stream to MIDI bytes.

        Args:
            score: music21.stream.Stream object

        Returns:
            MIDI file as bytes
        """
        try:
            import tempfile
            # music21 requires a file path, so use temporary file
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
                tmp_path = tmp_file.name

            score.write('midi', fp=tmp_path)

            # Read bytes from temp file
            with open(tmp_path, 'rb') as f:
                midi_bytes = f.read()

            # Clean up
            Path(tmp_path).unlink()

            logger.info("Converted Stream to MIDI bytes")
            return midi_bytes
        except Exception as e:
            logger.error(f"Error converting to MIDI: {e}")
            raise ValueError(f"Could not convert to MIDI: {e}")

    def to_musicxml(self, score: stream.Stream) -> str:
        """
        Convert Stream to MusicXML string.

        Args:
            score: music21.stream.Stream object

        Returns:
            MusicXML as string
        """
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.musicxml', delete=False) as tmp_file:
                tmp_path = tmp_file.name

            score.write('musicxml', fp=tmp_path)

            with open(tmp_path, 'r') as f:
                musicxml_str = f.read()

            Path(tmp_path).unlink()
            logger.info("Converted Stream to MusicXML")
            return musicxml_str
        except Exception as e:
            logger.error(f"Error converting to MusicXML: {e}")
            raise ValueError(f"Could not convert to MusicXML: {e}")

    def to_abc(self, score: stream.Stream) -> str:
        """
        Convert Stream to ABC notation.

        Args:
            score: music21.stream.Stream object

        Returns:
            ABC notation as string
        """
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.abc', delete=False) as tmp_file:
                tmp_path = tmp_file.name

            score.write('abc', fp=tmp_path)

            with open(tmp_path, 'r') as f:
                abc_str = f.read()

            Path(tmp_path).unlink()
            logger.info("Converted Stream to ABC")
            return abc_str
        except Exception as e:
            logger.error(f"Error converting to ABC: {e}")
            raise ValueError(f"Could not convert to ABC: {e}")

    def to_json(self, score: stream.Stream) -> str:
        """
        Serialize Stream to JSON using freezeThaw.

        Args:
            score: music21.stream.Stream object

        Returns:
            JSON string representation
        """
        try:
            freezer = StreamFreezer(score)
            json_str = freezer.writeStr(fmt='json')
            logger.info("Serialized Stream to JSON")
            return json_str
        except Exception as e:
            logger.error(f"Error serializing to JSON: {e}")
            raise ValueError(f"Could not serialize to JSON: {e}")

    def from_json(self, json_str: str) -> stream.Stream:
        """
        Deserialize JSON to Stream using freezeThaw.

        Args:
            json_str: JSON string representation

        Returns:
            music21.stream.Stream object
        """
        try:
            thawer = StreamThawer()
            score = thawer.parseData(json_str)
            logger.info("Deserialized JSON to Stream")
            return score
        except Exception as e:
            logger.error(f"Error deserializing JSON: {e}")
            raise ValueError(f"Could not deserialize JSON: {e}")

    # ==================== ANALYSIS METHODS ====================

    def analyze(self, score: stream.Stream) -> Dict[str, Any]:
        """
        Perform comprehensive musical analysis.

        Args:
            score: music21.stream.Stream object

        Returns:
            Dictionary with analysis results
        """
        try:
            analysis_result = {}

            # Key detection
            try:
                detected_key = score.analyze('key')
                analysis_result['key'] = str(detected_key)
            except Exception as e:
                logger.warning(f"Could not detect key: {e}")
                analysis_result['key'] = None

            # Tempo detection
            try:
                tempo_marks = score.flatten().getElementsByClass(tempo.MetronomeMark)
                if tempo_marks:
                    analysis_result['tempo'] = int(tempo_marks[0].number)
                else:
                    analysis_result['tempo'] = None
            except Exception as e:
                logger.warning(f"Could not detect tempo: {e}")
                analysis_result['tempo'] = None

            # Time signature
            try:
                time_sigs = score.flatten().getElementsByClass(meter.TimeSignature)
                if time_sigs:
                    analysis_result['time_signature'] = time_sigs[0].ratioString
                else:
                    analysis_result['time_signature'] = "4/4"
            except Exception as e:
                logger.warning(f"Could not detect time signature: {e}")
                analysis_result['time_signature'] = "4/4"

            # Duration
            analysis_result['duration'] = score.duration.quarterLength

            # Chord analysis
            try:
                chords_stream = score.chordify()
                chord_list = []
                for c in chords_stream.flatten().getElementsByClass(chord.Chord):
                    chord_list.append(c.pitchedCommonName)
                analysis_result['chords'] = chord_list[:20]  # Limit to first 20
            except Exception as e:
                logger.warning(f"Could not analyze chords: {e}")
                analysis_result['chords'] = []

            # Note count
            notes = score.flatten().notes
            analysis_result['note_count'] = len(notes)

            # Pitch range
            if notes:
                pitches = [n.pitch.midi for n in notes if hasattr(n, 'pitch')]
                if pitches:
                    analysis_result['pitch_range'] = {
                        'lowest': min(pitches),
                        'highest': max(pitches)
                    }

            logger.info(f"Analysis complete: {analysis_result.get('key')}, {analysis_result.get('tempo')} BPM")
            return analysis_result

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            raise ValueError(f"Could not analyze score: {e}")

    # ==================== TRANSFORMATION METHODS ====================

    def transpose(self, score: stream.Stream, semitones: int) -> stream.Stream:
        """
        Transpose score by semitones.

        Args:
            score: music21.stream.Stream object
            semitones: Number of semitones (+/-)

        Returns:
            Transposed Stream
        """
        try:
            transposed = score.transpose(semitones)
            logger.info(f"Transposed by {semitones} semitones")
            return transposed
        except Exception as e:
            logger.error(f"Error transposing: {e}")
            raise ValueError(f"Could not transpose: {e}")

    def change_tempo(self, score: stream.Stream, new_tempo: int) -> stream.Stream:
        """
        Change tempo of score.

        Args:
            score: music21.stream.Stream object
            new_tempo: New tempo in BPM

        Returns:
            Stream with new tempo
        """
        try:
            # Create a copy
            new_score = score.copy()

            # Remove existing tempo marks
            for m in new_score.flatten().getElementsByClass(tempo.MetronomeMark):
                new_score.remove(m)

            # Add new tempo mark
            new_score.insert(0, tempo.MetronomeMark(number=new_tempo))

            logger.info(f"Changed tempo to {new_tempo} BPM")
            return new_score
        except Exception as e:
            logger.error(f"Error changing tempo: {e}")
            raise ValueError(f"Could not change tempo: {e}")

    def augment(self, score: stream.Stream, factor: float) -> stream.Stream:
        """
        Augment (slow down) or diminish (speed up) note durations.

        Args:
            score: music21.stream.Stream object
            factor: Multiplication factor (2.0 = twice as slow, 0.5 = twice as fast)

        Returns:
            Augmented Stream
        """
        try:
            augmented = score.augmentOrDiminish(factor)
            logger.info(f"Augmented by factor {factor}")
            return augmented
        except Exception as e:
            logger.error(f"Error augmenting: {e}")
            raise ValueError(f"Could not augment: {e}")

    def retrograde(self, score: stream.Stream) -> stream.Stream:
        """
        Reverse the score (retrograde).

        Args:
            score: music21.stream.Stream object

        Returns:
            Reversed Stream
        """
        try:
            reversed_score = score.retrograde()
            logger.info("Created retrograde")
            return reversed_score
        except Exception as e:
            logger.error(f"Error creating retrograde: {e}")
            raise ValueError(f"Could not create retrograde: {e}")

    # ==================== GENERATION METHODS ====================

    def create_scale(
        self,
        tonic: str = 'C',
        scale_type: str = 'major',
        octaves: int = 1,
        duration_per_note: float = 1.0,
        tempo_bpm: int = 120,
        clef_type: str = 'treble'
    ) -> stream.Stream:
        """
        Create a musical scale.

        Args:
            tonic: Root note (e.g., 'C', 'D', 'F#', 'Bb')
            scale_type: Type of scale ('major', 'minor', 'harmonic minor', 'melodic minor',
                       'chromatic', 'whole tone', 'pentatonic', etc.)
            octaves: Number of octaves to generate
            duration_per_note: Duration of each note in quarter notes
            tempo_bpm: Tempo in BPM
            clef_type: Clef type - 'treble', 'bass', 'alto', or 'tenor'

        Returns:
            music21.stream.Stream with the scale
        """
        try:
            s = stream.Stream()

            # Add tempo
            s.insert(0, tempo.MetronomeMark(number=tempo_bpm))

            # Add time signature
            s.insert(0, meter.TimeSignature('4/4'))

            # Add clef
            clef_map = {
                'treble': clef.TrebleClef(),
                'bass': clef.BassClef(),
                'alto': clef.AltoClef(),
                'tenor': clef.TenorClef(),
            }
            selected_clef = clef_map.get(clef_type.lower(), clef.TrebleClef())
            s.insert(0, selected_clef)

            # Create scale object
            scale_map = {
                'major': scale.MajorScale,
                'minor': scale.MinorScale,
                'natural minor': scale.MinorScale,
                'harmonic minor': scale.HarmonicMinorScale,
                'melodic minor': scale.MelodicMinorScale,
                'chromatic': scale.ChromaticScale,
                'whole tone': scale.WholeToneScale,
                'pentatonic': scale.MajorScale,  # Maintain compatibility (defaults to major)
                'pentatonic major': scale.MajorScale,
                'pentatonic minor': scale.MinorScale,
                'dorian': scale.DorianScale,
                'phrygian': scale.PhrygianScale,
                'lydian': scale.LydianScale,
                'mixolydian': scale.MixolydianScale,
                'locrian': scale.LocrianScale,
            }

            scale_class = scale_map.get(scale_type.lower(), scale.MajorScale)
            scale_obj = scale_class(tonic)

            # Generate scale notes
            # Adjust starting octave based on clef for comfortable reading
            # Treble: octave 4 (middle C area), Bass: octave 3 (below middle C)
            base_octave = 3 if clef_type.lower() == 'bass' else 4
            start_pitch = pitch.Pitch(f"{tonic}{base_octave}")

            # Get the pitches for one octave first
            base_pitches = scale_obj.getPitches(start_pitch, start_pitch.transpose(12))

            # Build pitches for all requested octaves
            pitches = []
            for octave_offset in range(octaves):
                for i, p in enumerate(base_pitches[:-1]):  # Exclude last to avoid duplication
                    transposed = p.transpose(12 * octave_offset)
                    pitches.append(transposed)

            # Add the final tonic one octave up to complete the scale
            final_pitch = start_pitch.transpose(12 * octaves)
            pitches.append(final_pitch)

            # For pentatonic scales, use only specific scale degrees
            if 'pentatonic' in scale_type.lower():
                if 'minor' in scale_type.lower():
                    # Pentatonic minor: 1, ♭3, 4, 5, ♭7
                    # These correspond to degrees 1, 3, 4, 5, 7 of the natural minor scale
                    pentatonic_degrees = [1, 3, 4, 5, 7]
                else:
                    # Pentatonic major: 1, 2, 3, 5, 6
                    pentatonic_degrees = [1, 2, 3, 5, 6]

                filtered_pitches = []
                for octave_offset in range(octaves):
                    current_octave = base_octave + octave_offset
                    tonic_pitch = pitch.Pitch(f"{tonic}{current_octave}")

                    for degree in pentatonic_degrees:
                        # Get the pitch from the scale degree
                        scale_pitch = scale_obj.pitchFromDegree(degree)
                        # Create pitch with correct octave, adjusting if note is below tonic
                        new_pitch = pitch.Pitch(scale_pitch.name + str(current_octave))
                        # If this pitch is below the tonic, move it up an octave
                        if new_pitch.midi < tonic_pitch.midi:
                            new_pitch = new_pitch.transpose(12)
                        filtered_pitches.append(new_pitch)
                # Add final tonic
                filtered_pitches.append(start_pitch.transpose(12 * octaves))
                pitches = filtered_pitches

            # Add notes to stream
            for p in pitches:
                n = note.Note(p, quarterLength=duration_per_note)
                s.append(n)

            # Debug: log each pitch with octave and MIDI number
            pitch_details = [f"{p.nameWithOctave}(midi:{p.midi})" for p in pitches]
            logger.info(f"Created {scale_type} scale in {tonic}: {len(pitches)} notes - Pitches: {' -> '.join(pitch_details)}")
            return s

        except Exception as e:
            logger.error(f"Error creating scale: {e}")
            raise ValueError(f"Could not create scale: {e}")

    def create_chord_progression(
        self,
        chord_symbols: List[str],
        duration_per_chord: float = 4.0,
        tempo_bpm: int = 120,
        clef_type: str = 'treble'
    ) -> stream.Stream:
        """
        Create a chord progression.

        Args:
            chord_symbols: List of chord symbols (e.g., ['C', 'Am', 'F', 'G', 'Bb'])
            duration_per_chord: Duration of each chord in quarter notes
            tempo_bpm: Tempo in BPM
            clef_type: Clef type - 'treble' (G clef/clave de sol), 'bass' (F clef/clave de fa),
                      'alto' (C clef), or 'tenor'

        Returns:
            music21.stream.Stream with the chord progression
        """
        try:
            from music21 import harmony

            s = stream.Stream()

            # Add tempo
            s.insert(0, tempo.MetronomeMark(number=tempo_bpm))

            # Add time signature
            s.insert(0, meter.TimeSignature('4/4'))

            # Add clef
            clef_map = {
                'treble': clef.TrebleClef(),
                'bass': clef.BassClef(),
                'alto': clef.AltoClef(),
                'tenor': clef.TenorClef(),
            }
            selected_clef = clef_map.get(clef_type.lower(), clef.TrebleClef())
            s.insert(0, selected_clef)

            # Normalize chord symbols: Convert 'Bb' -> 'B-', 'Eb' -> 'E-', etc.
            def normalize_chord_symbol(symbol: str) -> str:
                """Convert flat notation from 'b' to '-' for music21 compatibility."""
                # Replace lowercase 'b' with '-' for flats (but not uppercase B)
                # Handle cases like Bb, Eb, Ab, Db, Gb, Cb, Fb
                normalized = symbol

                # Replace common flat patterns
                replacements = {
                    'Cb': 'C-', 'Db': 'D-', 'Eb': 'E-', 'Fb': 'F-',
                    'Gb': 'G-', 'Ab': 'A-', 'Bb': 'B-'
                }

                for old, new in replacements.items():
                    if symbol.startswith(old):
                        normalized = symbol.replace(old, new, 1)
                        break

                return normalized

            # Determine octave adjustment based on clef for comfortable reading range
            # Treble clef: octave 4-5 is comfortable (middle C and above)
            # Bass clef: octave 2-3 is comfortable (below middle C)
            # Alto/Tenor: octave 3-4
            octave_adjustment = {
                'treble': 12,  # Transpose up 1 octave (ChordSymbol defaults to octave 2-3)
                'bass': 0,     # Keep default octave 2-3
                'alto': 6,     # Transpose up half octave
                'tenor': 6,    # Transpose up half octave
            }
            transpose_semitones = octave_adjustment.get(clef_type.lower(), 12)

            # Add chords
            for chord_symbol in chord_symbols:
                try:
                    # Normalize the chord symbol
                    normalized_symbol = normalize_chord_symbol(chord_symbol)

                    # Use harmony.ChordSymbol which properly expands chord symbols into full triads/7ths
                    cs = harmony.ChordSymbol(normalized_symbol)
                    cs.quarterLength = duration_per_chord

                    # Convert ChordSymbol to Chord and transpose if needed
                    c = chord.Chord(cs.pitches)
                    if transpose_semitones != 0:
                        c = c.transpose(transpose_semitones)
                    c.quarterLength = duration_per_chord
                    s.append(c)

                    logger.debug(f"Added chord '{chord_symbol}' (normalized: '{normalized_symbol}') = {cs.pitchedCommonName}, transposed {transpose_semitones} semitones")
                except Exception as e:
                    logger.warning(f"Could not parse chord '{chord_symbol}': {e}")
                    # Add a default C major chord
                    c = chord.Chord(['C4', 'E4', 'G4'])
                    c.quarterLength = duration_per_chord
                    s.append(c)

            logger.info(f"Created chord progression with {len(chord_symbols)} chords")
            return s

        except Exception as e:
            logger.error(f"Error creating chord progression: {e}")
            raise ValueError(f"Could not create chord progression: {e}")

    def create_arpeggio(
        self,
        root: str = 'C',
        chord_type: str = 'major',
        octaves: int = 1,
        direction: str = 'ascending',
        duration_per_note: float = 0.5,
        tempo_bpm: int = 120
    ) -> stream.Stream:
        """
        Create an arpeggio pattern.

        Args:
            root: Root note of the chord
            chord_type: Type of chord ('major', 'minor', 'diminished', 'augmented', '7', 'maj7', 'min7')
            octaves: Number of octaves to span
            direction: 'ascending', 'descending', or 'both'
            duration_per_note: Duration of each note in quarter notes
            tempo_bpm: Tempo in BPM

        Returns:
            music21.stream.Stream with the arpeggio
        """
        try:
            s = stream.Stream()

            # Add tempo
            s.insert(0, tempo.MetronomeMark(number=tempo_bpm))

            # Add time signature
            s.insert(0, meter.TimeSignature('4/4'))

            # Create chord
            chord_symbol = root + chord_type.replace(' ', '')
            c = chord.Chord(chord_symbol)

            # Get pitches and extend across octaves
            base_pitches = c.pitches
            pitches = []
            for octave in range(octaves + 1):
                for p in base_pitches:
                    pitches.append(p.transpose(12 * octave))

            # Apply direction
            if direction == 'descending':
                pitches = list(reversed(pitches))
            elif direction == 'both':
                pitches = pitches + list(reversed(pitches[:-1]))

            # Add notes to stream
            for p in pitches:
                n = note.Note(p, quarterLength=duration_per_note)
                s.append(n)

            logger.info(f"Created {chord_type} arpeggio on {root}: {len(pitches)} notes")
            return s

        except Exception as e:
            logger.error(f"Error creating arpeggio: {e}")
            raise ValueError(f"Could not create arpeggio: {e}")

    # ==================== UTILITY METHODS ====================

    def get_metadata(self, score: stream.Stream) -> Dict[str, str]:
        """
        Extract metadata from Stream.

        Args:
            score: music21.stream.Stream object

        Returns:
            Dictionary with metadata
        """
        metadata = {}
        if score.metadata:
            if score.metadata.title:
                metadata['title'] = score.metadata.title
            if score.metadata.composer:
                metadata['composer'] = score.metadata.composer
            if score.metadata.copyright:
                metadata['copyright'] = score.metadata.copyright

        return metadata

    def set_metadata(self, score: stream.Stream, title: Optional[str] = None,
                    composer: Optional[str] = None) -> stream.Stream:
        """
        Set metadata on Stream.

        Args:
            score: music21.stream.Stream object
            title: Title of piece
            composer: Composer name

        Returns:
            Stream with metadata
        """
        if not score.metadata:
            score.metadata = music21.metadata.Metadata()

        if title:
            score.metadata.title = title
        if composer:
            score.metadata.composer = composer

        return score
