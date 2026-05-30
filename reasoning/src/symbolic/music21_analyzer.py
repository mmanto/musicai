"""Music21-based symbolic music analyzer."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import music21 as m21
from music21 import chord, key, roman, stream, interval, pitch

from ..config import get_settings

logger = logging.getLogger(__name__)


class Music21Analyzer:
    """Analyzes musical content using music21 library."""

    def __init__(self):
        """Initialize the analyzer."""
        self.settings = get_settings()
        self._setup_music21()

    def _setup_music21(self) -> None:
        """Configure music21 environment."""
        # Set cache directory
        cache_dir = Path(self.settings.MUSIC21_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Disable lilypond if not needed
        if not self.settings.MUSIC21_USE_LILYPOND:
            m21.environment.set('musicxmlPath', None)

        logger.info("Music21 analyzer initialized")

    def analyze_score(self, music_data: bytes, format: str = "musicxml") -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a musical score.

        Args:
            music_data: Musical content as bytes
            format: Format of the music data (musicxml, midi, abc)

        Returns:
            Dictionary with complete analysis results
        """
        try:
            # Parse the score
            score = self._parse_score(music_data, format)

            # Perform various analyses
            analysis = {
                "metadata": self._extract_metadata(score),
                "key_analysis": self._analyze_key(score),
                "harmonic_analysis": self._analyze_harmony(score),
                "melodic_analysis": self._analyze_melody(score),
                "rhythmic_analysis": self._analyze_rhythm(score),
                "form_analysis": self._analyze_form(score),
                "voice_leading": self._analyze_voice_leading(score),
                "statistics": self._compute_statistics(score)
            }

            logger.info("Score analysis completed successfully")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing score: {e}")
            raise

    def _parse_score(self, music_data: bytes, format: str) -> m21.stream.Score:
        """Parse music data into a music21 Score object."""
        try:
            if format == "musicxml":
                score = m21.converter.parse(music_data, format='musicxml')
            elif format == "midi":
                score = m21.converter.parse(music_data, format='midi')
            elif format == "abc":
                score = m21.converter.parse(music_data, format='abc')
            else:
                raise ValueError(f"Unsupported format: {format}")

            return score

        except Exception as e:
            logger.error(f"Error parsing score: {e}")
            raise

    def _extract_metadata(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Extract metadata from the score."""
        metadata = score.metadata

        return {
            "title": metadata.title if metadata else None,
            "composer": metadata.composer if metadata else None,
            "time_signature": str(score.recurse().getElementsByClass(m21.meter.TimeSignature)[0])
                if score.recurse().getElementsByClass(m21.meter.TimeSignature) else None,
            "key_signature": str(score.recurse().getElementsByClass(m21.key.KeySignature)[0])
                if score.recurse().getElementsByClass(m21.key.KeySignature) else None,
            "tempo": score.metronomeMarkBoundaries()[0][2].number
                if score.metronomeMarkBoundaries() else None,
            "parts": len(score.parts),
            "measures": len(score.parts[0].getElementsByClass(m21.stream.Measure))
                if score.parts else 0
        }

    def _analyze_key(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Analyze key and tonality."""
        try:
            # Get key analysis from music21
            analyzed_key = score.analyze('key')

            # Analyze key confidence
            key_correlation = analyzed_key.correlationCoefficient

            # Detect modulations
            modulations = self._detect_modulations(score)

            return {
                "main_key": str(analyzed_key),
                "mode": analyzed_key.mode,
                "tonic": str(analyzed_key.tonic),
                "confidence": float(key_correlation),
                "modulations": modulations,
                "relative_key": str(analyzed_key.relative),
                "parallel_key": str(analyzed_key.parallel)
            }

        except Exception as e:
            logger.error(f"Error in key analysis: {e}")
            return {"error": str(e)}

    def _detect_modulations(self, score: m21.stream.Score) -> List[Dict[str, Any]]:
        """Detect key modulations throughout the piece."""
        modulations = []

        try:
            # Analyze key in windows
            measures = score.parts[0].getElementsByClass(m21.stream.Measure) if score.parts else []
            window_size = 4

            current_key = None
            for i in range(0, len(measures), window_size):
                window = measures[i:i+window_size]
                excerpt = m21.stream.Stream()
                for measure in window:
                    excerpt.append(measure)

                detected_key = excerpt.analyze('key')

                if current_key is None:
                    current_key = str(detected_key)
                elif str(detected_key) != current_key:
                    modulations.append({
                        "measure": i + 1,
                        "from_key": current_key,
                        "to_key": str(detected_key),
                        "confidence": detected_key.correlationCoefficient
                    })
                    current_key = str(detected_key)

        except Exception as e:
            logger.error(f"Error detecting modulations: {e}")

        return modulations

    def _analyze_harmony(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Analyze harmonic content and chord progressions."""
        try:
            chords_data = []
            progressions = []

            # Extract chords from each part
            chordified = score.chordify()

            analyzed_key = score.analyze('key')

            for chord_obj in chordified.recurse().getElementsByClass(chord.Chord):
                # Get chord details
                chord_symbol = chord_obj.pitchedCommonName

                # Try to get Roman numeral
                try:
                    rn = roman.romanNumeralFromChord(chord_obj, analyzed_key)
                    roman_numeral = str(rn.figure)
                except:
                    roman_numeral = None

                chord_info = {
                    "offset": float(chord_obj.offset),
                    "duration": float(chord_obj.duration.quarterLength),
                    "pitches": [str(p) for p in chord_obj.pitches],
                    "root": str(chord_obj.root()),
                    "bass": str(chord_obj.bass()),
                    "chord_symbol": chord_symbol,
                    "roman_numeral": roman_numeral,
                    "quality": chord_obj.quality if hasattr(chord_obj, 'quality') else None,
                    "inversion": chord_obj.inversion()
                }

                chords_data.append(chord_info)

            # Analyze chord progressions
            if chords_data:
                progressions = self._extract_progressions(chords_data)

            return {
                "chords": chords_data[:50],  # Limit to first 50 chords
                "total_chords": len(chords_data),
                "progressions": progressions,
                "harmonic_rhythm": self._analyze_harmonic_rhythm(chords_data)
            }

        except Exception as e:
            logger.error(f"Error in harmonic analysis: {e}")
            return {"error": str(e)}

    def _extract_progressions(self, chords_data: List[Dict]) -> List[Dict[str, Any]]:
        """Extract common chord progressions."""
        progressions = []

        # Common progressions to detect
        common_patterns = [
            ["I", "IV", "V", "I"],
            ["I", "V", "vi", "IV"],
            ["ii", "V", "I"],
            ["I", "vi", "IV", "V"]
        ]

        # Extract Roman numerals
        roman_sequence = [c.get("roman_numeral") for c in chords_data if c.get("roman_numeral")]

        # Find patterns
        for pattern in common_patterns:
            for i in range(len(roman_sequence) - len(pattern) + 1):
                window = roman_sequence[i:i+len(pattern)]
                if window == pattern:
                    progressions.append({
                        "pattern": " - ".join(pattern),
                        "start_measure": i + 1,
                        "type": self._classify_progression(pattern)
                    })

        return progressions[:10]  # Limit to first 10

    def _classify_progression(self, pattern: List[str]) -> str:
        """Classify type of chord progression."""
        pattern_str = "-".join(pattern)

        if pattern_str in ["I-IV-V-I", "I-IV-V"]:
            return "authentic_cadence"
        elif pattern_str in ["ii-V-I"]:
            return "jazz_turnaround"
        elif pattern_str in ["I-V-vi-IV"]:
            return "pop_progression"
        else:
            return "other"

    def _analyze_harmonic_rhythm(self, chords_data: List[Dict]) -> Dict[str, Any]:
        """Analyze rate of harmonic change."""
        if not chords_data:
            return {}

        durations = [c["duration"] for c in chords_data]

        return {
            "average_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "changes_per_measure": len(chords_data) / (chords_data[-1]["offset"] / 4)
                if chords_data else 0
        }

    def _analyze_melody(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Analyze melodic content."""
        try:
            # Get the top part (melody)
            melody_part = score.parts[0] if score.parts else score

            # Extract notes
            notes = melody_part.recurse().getElementsByClass(m21.note.Note)

            # Analyze intervals
            intervals = []
            pitches = []

            prev_note = None
            for note in notes:
                pitches.append(str(note.pitch))

                if prev_note:
                    intv = interval.Interval(prev_note, note)
                    intervals.append({
                        "name": intv.name,
                        "semitones": intv.semitones,
                        "direction": intv.direction.name
                    })

                prev_note = note

            # Analyze contour
            contour = self._analyze_contour(list(notes))

            # Find motifs
            motifs = self._find_motifs(list(notes))

            return {
                "pitch_range": {
                    "lowest": str(min(notes, key=lambda n: n.pitch.midi).pitch) if notes else None,
                    "highest": str(max(notes, key=lambda n: n.pitch.midi).pitch) if notes else None,
                    "span_semitones": max(n.pitch.midi for n in notes) - min(n.pitch.midi for n in notes)
                        if notes else 0
                },
                "intervals": {
                    "total": len(intervals),
                    "most_common": self._most_common_intervals(intervals),
                    "leaps": sum(1 for i in intervals if abs(i["semitones"]) > 2)
                },
                "contour": contour,
                "motifs": motifs[:5]  # Top 5 motifs
            }

        except Exception as e:
            logger.error(f"Error in melodic analysis: {e}")
            return {"error": str(e)}

    def _analyze_contour(self, notes: List[m21.note.Note]) -> Dict[str, Any]:
        """Analyze melodic contour."""
        if len(notes) < 2:
            return {}

        directions = []
        for i in range(1, len(notes)):
            diff = notes[i].pitch.midi - notes[i-1].pitch.midi
            if diff > 0:
                directions.append("up")
            elif diff < 0:
                directions.append("down")
            else:
                directions.append("same")

        return {
            "ascending": directions.count("up"),
            "descending": directions.count("down"),
            "repeated": directions.count("same"),
            "overall_direction": max(set(directions), key=directions.count) if directions else None
        }

    def _find_motifs(self, notes: List[m21.note.Note]) -> List[Dict[str, Any]]:
        """Identify repeated melodic motifs."""
        motifs = []
        motif_length = 4

        if len(notes) < motif_length:
            return motifs

        # Extract pitch sequences
        sequences = []
        for i in range(len(notes) - motif_length + 1):
            seq = tuple(n.pitch.midi for n in notes[i:i+motif_length])
            sequences.append((seq, i))

        # Find repeated sequences
        from collections import Counter
        sequence_counts = Counter([s[0] for s in sequences])

        for seq, count in sequence_counts.most_common(5):
            if count > 1:
                motifs.append({
                    "pitches": [pitch.Pitch(midi=m).nameWithOctave for m in seq],
                    "occurrences": count
                })

        return motifs

    def _most_common_intervals(self, intervals: List[Dict]) -> List[Dict[str, Any]]:
        """Find most common intervals."""
        from collections import Counter

        interval_names = [i["name"] for i in intervals]
        counts = Counter(interval_names)

        return [
            {"interval": name, "count": count}
            for name, count in counts.most_common(5)
        ]

    def _analyze_rhythm(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Analyze rhythmic patterns."""
        try:
            # Get all notes and rests
            all_elements = score.recurse().getElementsByClass([m21.note.Note, m21.note.Rest])

            # Collect durations
            durations = [e.duration.quarterLength for e in all_elements]

            # Analyze syncopation
            syncopation_score = self._analyze_syncopation(score)

            return {
                "duration_variety": len(set(durations)),
                "most_common_duration": max(set(durations), key=durations.count) if durations else None,
                "shortest_note": min(durations) if durations else None,
                "longest_note": max(durations) if durations else None,
                "syncopation_level": syncopation_score,
                "rest_ratio": sum(1 for e in all_elements if isinstance(e, m21.note.Rest)) / len(all_elements)
                    if all_elements else 0
            }

        except Exception as e:
            logger.error(f"Error in rhythmic analysis: {e}")
            return {"error": str(e)}

    def _analyze_syncopation(self, score: m21.stream.Score) -> float:
        """Measure level of syncopation."""
        # Simple heuristic: notes starting on weak beats
        syncopation_count = 0
        total_notes = 0

        for part in score.parts:
            for measure in part.getElementsByClass(m21.stream.Measure):
                ts = measure.timeSignature or m21.meter.TimeSignature('4/4')

                for note in measure.getElementsByClass(m21.note.Note):
                    total_notes += 1
                    beat_strength = ts.getAccentWeight(note.offset % ts.barDuration.quarterLength)

                    # If note starts on weak beat, it might be syncopated
                    if beat_strength < 0.5:
                        syncopation_count += 1

        return syncopation_count / total_notes if total_notes > 0 else 0

    def _analyze_form(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Analyze musical form and structure."""
        try:
            measures = score.parts[0].getElementsByClass(m21.stream.Measure) if score.parts else []

            # Detect sections based on repeats and similarities
            sections = self._detect_sections(list(measures))

            # Identify repeats
            repeats = [
                {
                    "measure": i+1,
                    "type": "repeat_sign"
                }
                for i, m in enumerate(measures)
                if m.getElementsByClass(m21.bar.Repeat)
            ]

            return {
                "total_measures": len(measures),
                "sections": sections,
                "repeats": repeats,
                "estimated_form": self._estimate_form(sections)
            }

        except Exception as e:
            logger.error(f"Error in form analysis: {e}")
            return {"error": str(e)}

    def _detect_sections(self, measures: List[m21.stream.Measure]) -> List[Dict[str, Any]]:
        """Detect musical sections."""
        sections = []
        section_size = 8  # Typical phrase length

        for i in range(0, len(measures), section_size):
            sections.append({
                "start_measure": i + 1,
                "end_measure": min(i + section_size, len(measures)),
                "label": chr(65 + len(sections))  # A, B, C, etc.
            })

        return sections

    def _estimate_form(self, sections: List[Dict]) -> str:
        """Estimate overall form structure."""
        num_sections = len(sections)

        if num_sections <= 2:
            return "binary"
        elif num_sections == 3:
            return "ternary_ABA"
        elif num_sections == 4:
            return "quaternary"
        else:
            return "through_composed"

    def _analyze_voice_leading(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Analyze voice leading and counterpoint."""
        if len(score.parts) < 2:
            return {"message": "Requires multiple parts for voice leading analysis"}

        try:
            violations = []

            # Check parallel fifths and octaves
            parallel_violations = self._check_parallel_motion(score)
            violations.extend(parallel_violations)

            # Check voice crossing
            crossing_violations = self._check_voice_crossing(score)
            violations.extend(crossing_violations)

            return {
                "total_violations": len(violations),
                "violations": violations[:20],  # Limit output
                "quality_score": max(0, 100 - len(violations) * 5)  # Simple scoring
            }

        except Exception as e:
            logger.error(f"Error in voice leading analysis: {e}")
            return {"error": str(e)}

    def _check_parallel_motion(self, score: m21.stream.Score) -> List[Dict[str, Any]]:
        """Check for parallel fifths and octaves."""
        violations = []

        # Compare adjacent parts
        for i in range(len(score.parts) - 1):
            part1 = score.parts[i]
            part2 = score.parts[i + 1]

            notes1 = list(part1.recurse().getElementsByClass(m21.note.Note))
            notes2 = list(part2.recurse().getElementsByClass(m21.note.Note))

            # Simple check on simultaneous notes
            for j in range(min(len(notes1), len(notes2)) - 1):
                intv1 = interval.Interval(notes2[j], notes1[j])
                intv2 = interval.Interval(notes2[j+1], notes1[j+1])

                # Check for parallel perfect intervals
                if intv1.simpleName == intv2.simpleName:
                    if intv1.simpleName in ['P5', 'P8']:
                        violations.append({
                            "type": f"parallel_{intv1.simpleName}",
                            "location": f"parts_{i}-{i+1}_note_{j}",
                            "severity": "high"
                        })

        return violations

    def _check_voice_crossing(self, score: m21.stream.Score) -> List[Dict[str, Any]]:
        """Check for voice crossing."""
        violations = []

        for i in range(len(score.parts) - 1):
            upper_part = score.parts[i]
            lower_part = score.parts[i + 1]

            upper_notes = list(upper_part.recurse().getElementsByClass(m21.note.Note))
            lower_notes = list(lower_part.recurse().getElementsByClass(m21.note.Note))

            for j in range(min(len(upper_notes), len(lower_notes))):
                if upper_notes[j].pitch.midi < lower_notes[j].pitch.midi:
                    violations.append({
                        "type": "voice_crossing",
                        "location": f"parts_{i}-{i+1}_note_{j}",
                        "severity": "medium"
                    })

        return violations

    def _compute_statistics(self, score: m21.stream.Score) -> Dict[str, Any]:
        """Compute general statistics about the score."""
        try:
            all_notes = list(score.recurse().getElementsByClass(m21.note.Note))

            return {
                "total_notes": len(all_notes),
                "total_duration": float(score.duration.quarterLength),
                "tempo_markings": len(list(score.recurse().getElementsByClass(m21.tempo.MetronomeMark))),
                "dynamic_markings": len(list(score.recurse().getElementsByClass(m21.dynamics.Dynamic))),
                "articulations": sum(len(n.articulations) for n in all_notes),
                "parts": len(score.parts),
                "instruments": [str(part.getInstrument().instrumentName)
                               for part in score.parts] if score.parts else []
            }

        except Exception as e:
            logger.error(f"Error computing statistics: {e}")
            return {"error": str(e)}

    def validate_music_theory(self, score_data: bytes, rules: List[str]) -> Dict[str, Any]:
        """
        Validate score against music theory rules.

        Args:
            score_data: Musical content as bytes
            rules: List of rules to check (e.g., ["parallel_fifths", "voice_range"])

        Returns:
            Validation results
        """
        try:
            score = self._parse_score(score_data, "musicxml")

            results = {
                "valid": True,
                "violations": [],
                "warnings": []
            }

            for rule in rules:
                if rule == "parallel_fifths":
                    violations = self._check_parallel_motion(score)
                    if violations:
                        results["valid"] = False
                        results["violations"].extend(violations)

                elif rule == "voice_range":
                    range_issues = self._check_voice_ranges(score)
                    if range_issues:
                        results["warnings"].extend(range_issues)

            return results

        except Exception as e:
            logger.error(f"Error in validation: {e}")
            raise

    def _check_voice_ranges(self, score: m21.stream.Score) -> List[Dict[str, Any]]:
        """Check if voices stay within typical ranges."""
        issues = []

        typical_ranges = {
            "soprano": (60, 81),  # C4 to A5
            "alto": (55, 74),      # G3 to D5
            "tenor": (48, 69),     # C3 to A4
            "bass": (40, 62)       # E2 to D4
        }

        for part_idx, part in enumerate(score.parts):
            notes = list(part.recurse().getElementsByClass(m21.note.Note))

            if not notes:
                continue

            # Guess voice type from average pitch
            avg_midi = sum(n.pitch.midi for n in notes) / len(notes)

            if avg_midi > 67:
                voice_type = "soprano"
            elif avg_midi > 59:
                voice_type = "alto"
            elif avg_midi > 52:
                voice_type = "tenor"
            else:
                voice_type = "bass"

            min_allowed, max_allowed = typical_ranges[voice_type]

            for note in notes:
                if note.pitch.midi < min_allowed or note.pitch.midi > max_allowed:
                    issues.append({
                        "type": "out_of_range",
                        "part": part_idx,
                        "voice": voice_type,
                        "note": str(note.pitch),
                        "severity": "low"
                    })

        return issues

    # =========================================================================
    # MUSIC GENERATION METHODS (for chat-teacher endpoint)
    # =========================================================================

    def create_scale(
        self,
        tonic: str,
        scale_type: str = "major",
        octaves: int = 1,
        duration_per_note: float = 1.0,
        tempo_bpm: int = 120,
        clef_type: str = "treble"
    ) -> m21.stream.Stream:
        """
        Create a musical scale.

        Args:
            tonic: Root note (C, D, E, F, G, A, B, with optional # or b)
            scale_type: Type of scale (major, minor, harmonic minor, pentatonic minor, etc.)
            octaves: Number of octaves to generate
            duration_per_note: Duration of each note in quarter notes
            tempo_bpm: Tempo in beats per minute
            clef_type: Clef to use (treble, bass, alto, tenor)

        Returns:
            music21 Stream with the scale
        """
        try:
            # Create a part (single staff)
            part = m21.stream.Part()

            # Add tempo marking
            part.append(m21.tempo.MetronomeMark(number=tempo_bpm))

            # Add time signature (4/4 default)
            part.append(m21.meter.TimeSignature('4/4'))

            # Add clef
            clef_map = {
                'treble': m21.clef.TrebleClef(),
                'bass': m21.clef.BassClef(),
                'alto': m21.clef.AltoClef(),
                'tenor': m21.clef.TenorClef()
            }
            part.append(clef_map.get(clef_type, m21.clef.TrebleClef()))

            # Create scale object
            scale_obj = self._get_scale_object(tonic, scale_type)

            # Get pitches for the requested octaves
            pitches = self._get_scale_pitches(scale_obj, tonic, octaves, scale_type)

            # Add notes to the part
            for p in pitches:
                n = m21.note.Note(p, quarterLength=duration_per_note)
                part.append(n)

            # Create score and add part
            score = m21.stream.Score()
            score.append(part)

            logger.info(f"Created scale: {tonic} {scale_type}, {octaves} octaves")
            return score

        except Exception as e:
            logger.error(f"Error creating scale: {e}")
            raise

    def _get_scale_object(self, tonic: str, scale_type: str):
        """Get music21 scale object for the given type."""
        from music21 import scale as m21scale

        # Parse tonic
        tonic_pitch = m21.pitch.Pitch(tonic)

        # Map scale types to music21 scale classes
        scale_map = {
            'major': m21scale.MajorScale,
            'minor': m21scale.MinorScale,
            'harmonic minor': m21scale.HarmonicMinorScale,
            'melodic minor': m21scale.MelodicMinorScale,
            'chromatic': m21scale.ChromaticScale,
            'dorian': m21scale.DorianScale,
            'phrygian': m21scale.PhrygianScale,
            'lydian': m21scale.LydianScale,
            'mixolydian': m21scale.MixolydianScale,
            'aeolian': m21scale.MinorScale,  # Aeolian is natural minor
            'locrian': m21scale.LocrianScale,
        }

        scale_class = scale_map.get(scale_type.lower(), m21scale.MajorScale)
        return scale_class(tonic_pitch)

    def _get_scale_pitches(self, scale_obj, tonic: str, octaves: int, scale_type: str) -> List[m21.pitch.Pitch]:
        """Get pitches for a scale across multiple octaves."""
        pitches = []

        # Special handling for pentatonic scales
        if 'pentatonic' in scale_type.lower():
            return self._get_pentatonic_pitches(tonic, scale_type, octaves)

        # For other scales, use music21's getPitches
        tonic_pitch = m21.pitch.Pitch(tonic)
        start_octave = tonic_pitch.octave

        for octave_offset in range(octaves):
            current_octave = start_octave + octave_offset

            # Get scale degrees (1-7 for diatonic, 1-12 for chromatic)
            if 'chromatic' in scale_type.lower():
                degrees = range(1, 13)
            else:
                degrees = range(1, 8)

            for degree in degrees:
                try:
                    p = scale_obj.pitchFromDegree(degree)
                    p.octave = current_octave
                    pitches.append(p)
                except:
                    pass

        # Add final tonic note (octave higher)
        final_pitch = m21.pitch.Pitch(tonic)
        final_pitch.octave = start_octave + octaves
        pitches.append(final_pitch)

        return pitches

    def _get_pentatonic_pitches(self, tonic: str, scale_type: str, octaves: int) -> List[m21.pitch.Pitch]:
        """Get pitches for pentatonic scales."""
        pitches = []
        tonic_pitch = m21.pitch.Pitch(tonic)
        start_octave = tonic_pitch.octave

        # Pentatonic scale intervals from tonic
        if 'major' in scale_type.lower() or scale_type.lower() == 'pentatonic':
            # Major pentatonic: 1, 2, 3, 5, 6
            intervals = [0, 2, 4, 7, 9]
        else:
            # Minor pentatonic: 1, b3, 4, 5, b7
            intervals = [0, 3, 5, 7, 10]

        for octave_offset in range(octaves):
            current_octave = start_octave + octave_offset

            for interval_semitones in intervals:
                p = m21.pitch.Pitch(tonic)
                p.octave = current_octave
                p = p.transpose(interval_semitones)
                pitches.append(p)

        # Add final tonic
        final_pitch = m21.pitch.Pitch(tonic)
        final_pitch.octave = start_octave + octaves
        pitches.append(final_pitch)

        return pitches

    def create_chord_progression(
        self,
        chord_symbols: List[str],
        duration_per_chord: float = 2.0,
        tempo_bpm: int = 120,
        clef_type: str = "treble"
    ) -> m21.stream.Stream:
        """
        Create a chord progression from chord symbols.

        Args:
            chord_symbols: List of chord symbols (e.g., ['C', 'Am', 'F', 'G'])
            duration_per_chord: Duration of each chord in quarter notes
            tempo_bpm: Tempo in beats per minute
            clef_type: Clef to use

        Returns:
            music21 Stream with the chord progression
        """
        try:
            # Create a part
            part = m21.stream.Part()

            # Add tempo
            part.append(m21.tempo.MetronomeMark(number=tempo_bpm))

            # Add time signature
            part.append(m21.meter.TimeSignature('4/4'))

            # Add clef
            clef_map = {
                'treble': m21.clef.TrebleClef(),
                'bass': m21.clef.BassClef(),
                'alto': m21.clef.AltoClef(),
                'tenor': m21.clef.TenorClef()
            }
            part.append(clef_map.get(clef_type, m21.clef.TrebleClef()))

            # Create chords
            for symbol in chord_symbols:
                try:
                    # Parse chord symbol
                    chord_obj = m21.harmony.ChordSymbol(symbol)
                    chord_obj.quarterLength = duration_per_chord
                    part.append(chord_obj)
                except Exception as e:
                    logger.warning(f"Could not parse chord symbol '{symbol}': {e}")
                    continue

            # Create score
            score = m21.stream.Score()
            score.append(part)

            logger.info(f"Created chord progression: {', '.join(chord_symbols)}")
            return score

        except Exception as e:
            logger.error(f"Error creating chord progression: {e}")
            raise

    def create_arpeggio(
        self,
        tonic: str,
        chord_type: str = "major",
        direction: str = "ascending",
        octaves: int = 1,
        duration_per_note: float = 0.5,
        tempo_bpm: int = 120,
        clef_type: str = "treble"
    ) -> m21.stream.Stream:
        """
        Create an arpeggio (broken chord).

        Args:
            tonic: Root note of the chord
            chord_type: Type of chord (major, minor, diminished, augmented)
            direction: Direction of arpeggio (ascending, descending, ascending_descending)
            octaves: Number of octaves
            duration_per_note: Duration of each note
            tempo_bpm: Tempo in BPM
            clef_type: Clef to use

        Returns:
            music21 Stream with the arpeggio
        """
        try:
            # Create a part
            part = m21.stream.Part()

            # Add tempo
            part.append(m21.tempo.MetronomeMark(number=tempo_bpm))

            # Add time signature
            part.append(m21.meter.TimeSignature('4/4'))

            # Add clef
            clef_map = {
                'treble': m21.clef.TrebleClef(),
                'bass': m21.clef.BassClef(),
                'alto': m21.clef.AltoClef(),
                'tenor': m21.clef.TenorClef()
            }
            part.append(clef_map.get(clef_type, m21.clef.TrebleClef()))

            # Get chord pitches
            chord_obj = self._create_chord_from_type(tonic, chord_type)
            base_pitches = chord_obj.pitches

            # Build arpeggio pitches across octaves
            arpeggio_pitches = []

            tonic_pitch = m21.pitch.Pitch(tonic)
            start_octave = tonic_pitch.octave

            for octave_offset in range(octaves):
                for p in base_pitches:
                    new_pitch = m21.pitch.Pitch(p.name)
                    new_pitch.octave = start_octave + octave_offset
                    arpeggio_pitches.append(new_pitch)

            # Add final tonic note (octave higher)
            final_pitch = m21.pitch.Pitch(tonic)
            final_pitch.octave = start_octave + octaves
            arpeggio_pitches.append(final_pitch)

            # Apply direction
            if direction == "descending":
                arpeggio_pitches = list(reversed(arpeggio_pitches))
            elif direction == "ascending_descending":
                arpeggio_pitches = arpeggio_pitches + list(reversed(arpeggio_pitches[:-1]))

            # Add notes to part
            for p in arpeggio_pitches:
                n = m21.note.Note(p, quarterLength=duration_per_note)
                part.append(n)

            # Create score
            score = m21.stream.Score()
            score.append(part)

            logger.info(f"Created arpeggio: {tonic} {chord_type} {direction}, {octaves} octaves")
            return score

        except Exception as e:
            logger.error(f"Error creating arpeggio: {e}")
            raise

    def _create_chord_from_type(self, tonic: str, chord_type: str) -> m21.chord.Chord:
        """Create a chord object from tonic and type."""
        tonic_pitch = m21.pitch.Pitch(tonic)

        # Map chord types to interval structures (semitones from root)
        chord_intervals = {
            'major': [0, 4, 7],              # Root, Major 3rd, Perfect 5th
            'minor': [0, 3, 7],              # Root, Minor 3rd, Perfect 5th
            'diminished': [0, 3, 6],         # Root, Minor 3rd, Diminished 5th
            'augmented': [0, 4, 8],          # Root, Major 3rd, Augmented 5th
            'major7': [0, 4, 7, 11],         # Major + Major 7th
            'minor7': [0, 3, 7, 10],         # Minor + Minor 7th
            'dominant7': [0, 4, 7, 10],      # Major + Minor 7th
            '7': [0, 4, 7, 10],              # Alias for dominant7
        }

        intervals = chord_intervals.get(chord_type.lower(), chord_intervals['major'])

        # Create pitches
        pitches = []
        for interval_semitones in intervals:
            p = tonic_pitch.transpose(interval_semitones)
            pitches.append(p)

        return m21.chord.Chord(pitches)

    def to_musicxml(self, score: m21.stream.Stream) -> str:
        """
        Convert music21 Stream to MusicXML string.

        Args:
            score: music21 Stream/Score object

        Returns:
            MusicXML content as string
        """
        try:
            # Use music21's built-in MusicXML exporter
            from music21.musicxml import m21ToXml

            gex = m21ToXml.GeneralObjectExporter(score)
            musicxml_str = gex.parse()

            # If bytes, decode to string
            if isinstance(musicxml_str, bytes):
                return musicxml_str.decode('utf-8')

            return musicxml_str

        except Exception as e:
            logger.error(f"Error converting to MusicXML: {e}")
            raise

    def to_midi_bytes(self, score: m21.stream.Stream) -> bytes:
        """
        Convert music21 Stream to MIDI bytes.

        Args:
            score: music21 Stream/Score object

        Returns:
            MIDI file content as bytes
        """
        try:
            from music21.midi import translate
            import io

            # Convert to MIDI
            midi_data = translate.streamToMidiFile(score)

            # Write to bytes
            midi_bytes = io.BytesIO()
            midi_data.writestr(midi_bytes)
            midi_bytes.seek(0)

            return midi_bytes.read()

        except Exception as e:
            logger.error(f"Error converting to MIDI: {e}")
            raise
