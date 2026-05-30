/**
 * InlineNotation Component
 *
 * Renders small inline musical notation using VexFlow.
 * Supports scales, chords, notes, intervals, and progressions.
 */

import { useEffect, useRef, useState } from 'react';
import { Renderer, Stave, StaveNote, Voice, Formatter, Accidental } from 'vexflow';
import './InlineNotation.css';

type NotationType = 'scale' | 'chord' | 'notes' | 'interval' | 'progression';

interface InlineNotationProps {
  type: NotationType;
  content: string;
  onClick?: () => void;
}

// Spanish to English note mapping
const NOTE_MAP: Record<string, string> = {
  'do': 'c', 'do#': 'c#', 'dob': 'cb',
  're': 'd', 're#': 'd#', 'reb': 'db',
  'mi': 'e', 'mi#': 'e#', 'mib': 'eb',
  'fa': 'f', 'fa#': 'f#', 'fab': 'fb',
  'sol': 'g', 'sol#': 'g#', 'solb': 'gb',
  'la': 'a', 'la#': 'a#', 'lab': 'ab',
  'si': 'b', 'si#': 'b#', 'sib': 'bb',
};

// Scale patterns (intervals from root)
const SCALE_PATTERNS: Record<string, number[]> = {
  'mayor': [0, 2, 4, 5, 7, 9, 11, 12],
  'major': [0, 2, 4, 5, 7, 9, 11, 12],
  'menor': [0, 2, 3, 5, 7, 8, 10, 12],
  'minor': [0, 2, 3, 5, 7, 8, 10, 12],
  'pentatonica mayor': [0, 2, 4, 7, 9, 12],
  'pentatonica menor': [0, 3, 5, 7, 10, 12],
  'pentatónica mayor': [0, 2, 4, 7, 9, 12],
  'pentatónica menor': [0, 3, 5, 7, 10, 12],
  'cromatica': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  'cromática': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
};

// Chord patterns (intervals from root)
const CHORD_PATTERNS: Record<string, number[]> = {
  'mayor': [0, 4, 7],
  'major': [0, 4, 7],
  'm': [0, 3, 7],
  'menor': [0, 3, 7],
  'minor': [0, 3, 7],
  '7': [0, 4, 7, 10],
  'maj7': [0, 4, 7, 11],
  'm7': [0, 3, 7, 10],
  'dim': [0, 3, 6],
  'aug': [0, 4, 8],
};

// All chromatic notes for calculation
const CHROMATIC_NOTES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b'];

function getNoteIndex(note: string): number {
  const baseNote = note.replace('#', '').replace('b', '');
  let index = CHROMATIC_NOTES.indexOf(baseNote);
  if (note.includes('#')) index += 1;
  if (note.includes('b')) index -= 1;
  return (index + 12) % 12;
}

function getNoteFromIndex(index: number, octave: number): string {
  const normalizedIndex = ((index % 12) + 12) % 12;
  const note = CHROMATIC_NOTES[normalizedIndex];
  const actualOctave = octave + Math.floor(index / 12);
  return `${note}/${actualOctave}`;
}

function parseSpanishNote(text: string): { note: string; accidental?: string } | null {
  const lower = text.toLowerCase().trim();

  // Check for accidentals first
  for (const [spanish, english] of Object.entries(NOTE_MAP)) {
    if (lower === spanish || lower.startsWith(spanish)) {
      const accidental = english.includes('#') ? '#' : english.includes('b') ? 'b' : undefined;
      return { note: english.replace('#', '').replace('b', ''), accidental };
    }
  }
  return null;
}

function parseScaleContent(content: string): { notes: string[]; accidentals: (string | undefined)[] } {
  const lower = content.toLowerCase().trim();
  const notes: string[] = [];
  const accidentals: (string | undefined)[] = [];

  // Parse "Do mayor", "La menor pentatónica", etc.
  let rootNote = 'c';
  let scaleType = 'mayor';

  for (const [spanish, english] of Object.entries(NOTE_MAP)) {
    if (lower.startsWith(spanish + ' ') || lower === spanish) {
      rootNote = english.replace('#', '').replace('b', '');
      const remaining = lower.substring(spanish.length).trim();

      // Find scale type
      for (const type of Object.keys(SCALE_PATTERNS)) {
        if (remaining.includes(type)) {
          scaleType = type;
          break;
        }
      }
      break;
    }
  }

  const pattern = SCALE_PATTERNS[scaleType] || SCALE_PATTERNS['mayor'];
  const rootIndex = getNoteIndex(rootNote);
  const baseOctave = 4;

  for (const interval of pattern) {
    const noteKey = getNoteFromIndex(rootIndex + interval, baseOctave);
    notes.push(noteKey);
    accidentals.push(undefined); // Simplified - could add accidental detection
  }

  return { notes, accidentals };
}

function parseChordContent(content: string): { notes: string[]; accidentals: (string | undefined)[] } {
  const lower = content.toLowerCase().trim();
  const notes: string[] = [];
  const accidentals: (string | undefined)[] = [];

  let rootNote = 'c';
  let chordType = 'mayor';

  // Parse chord like "Sol7", "Rem", "Do mayor"
  for (const [spanish, english] of Object.entries(NOTE_MAP)) {
    if (lower.startsWith(spanish)) {
      rootNote = english.replace('#', '').replace('b', '');
      const remaining = lower.substring(spanish.length).trim();

      // Find chord type
      for (const type of Object.keys(CHORD_PATTERNS)) {
        if (remaining === type || remaining.startsWith(type)) {
          chordType = type;
          break;
        }
      }
      break;
    }
  }

  const pattern = CHORD_PATTERNS[chordType] || CHORD_PATTERNS['mayor'];
  const rootIndex = getNoteIndex(rootNote);
  const baseOctave = 4;

  for (const interval of pattern) {
    const noteKey = getNoteFromIndex(rootIndex + interval, baseOctave);
    notes.push(noteKey);
    accidentals.push(undefined);
  }

  return { notes, accidentals };
}

function parseNotesContent(content: string): { notes: string[]; accidentals: (string | undefined)[] } {
  const notes: string[] = [];
  const accidentals: (string | undefined)[] = [];

  // Split by comma, space, or dash
  const parts = content.split(/[,\s-]+/).filter(p => p.trim());

  for (const part of parts) {
    const parsed = parseSpanishNote(part);
    if (parsed) {
      notes.push(`${parsed.note}/4`);
      accidentals.push(parsed.accidental);
    }
  }

  return { notes, accidentals };
}

export default function InlineNotation({ type, content, onClick }: InlineNotationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 120, height: 60 });

  useEffect(() => {
    if (!containerRef.current) return;

    try {
      // Clear previous content
      containerRef.current.innerHTML = '';

      let notesData: { notes: string[]; accidentals: (string | undefined)[] };
      let isChord = false;

      switch (type) {
        case 'scale':
          notesData = parseScaleContent(content);
          // Limit to first 8 notes for inline display
          notesData.notes = notesData.notes.slice(0, 8);
          notesData.accidentals = notesData.accidentals.slice(0, 8);
          break;
        case 'chord':
          notesData = parseChordContent(content);
          isChord = true;
          break;
        case 'notes':
          notesData = parseNotesContent(content);
          break;
        case 'interval':
          // For intervals, show two notes
          notesData = { notes: ['c/4', 'e/4'], accidentals: [undefined, undefined] };
          break;
        case 'progression':
          // For progressions, show chord symbols (simplified)
          notesData = { notes: ['c/4', 'f/4', 'g/4', 'c/5'], accidentals: [undefined, undefined, undefined, undefined] };
          break;
        default:
          notesData = { notes: ['c/4'], accidentals: [undefined] };
      }

      if (notesData.notes.length === 0) {
        setError(true);
        return;
      }

      // Calculate dimensions based on content
      const noteCount = isChord ? 1 : notesData.notes.length;
      const width = Math.max(80, Math.min(300, noteCount * 30 + 50));
      const height = 70;
      setDimensions({ width, height });

      // Create renderer
      const renderer = new Renderer(containerRef.current, Renderer.Backends.SVG);
      renderer.resize(width, height);
      const context = renderer.getContext();

      // Create stave (smaller for inline)
      const stave = new Stave(0, 0, width - 10);
      stave.addClef('treble');
      stave.setContext(context).draw();

      // Create notes
      let staveNotes: StaveNote[];

      if (isChord) {
        // Chord: all notes stacked
        const chordNote = new StaveNote({
          keys: notesData.notes,
          duration: 'w',
        });

        // Add accidentals
        notesData.accidentals.forEach((acc, i) => {
          if (acc) {
            chordNote.addModifier(new Accidental(acc), i);
          }
        });

        staveNotes = [chordNote];
      } else {
        // Scale/notes: sequential
        staveNotes = notesData.notes.map((note, i) => {
          const staveNote = new StaveNote({
            keys: [note],
            duration: notesData.notes.length > 4 ? '8' : 'q',
          });

          if (notesData.accidentals[i]) {
            staveNote.addModifier(new Accidental(notesData.accidentals[i]!), 0);
          }

          return staveNote;
        });
      }

      // Create voice and format
      const voice = new Voice({
        num_beats: staveNotes.length,
        beat_value: 4,
      }).setMode(Voice.Mode.SOFT);

      voice.addTickables(staveNotes);

      new Formatter().joinVoices([voice]).format([voice], width - 60);
      voice.draw(context, stave);

      setError(false);
    } catch (err) {
      console.error('InlineNotation error:', err);
      setError(true);
    }
  }, [type, content]);

  if (error) {
    // Fallback to text if rendering fails
    return (
      <span className="inline-notation-fallback" onClick={onClick}>
        {content}
      </span>
    );
  }

  return (
    <span
      className="inline-notation"
      onClick={onClick}
      title={content}
      style={{ width: dimensions.width, height: dimensions.height }}
    >
      <span ref={containerRef} className="inline-notation-container" />
    </span>
  );
}
