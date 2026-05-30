/**
 * Sheet Music Editor Component
 *
 * Basic music notation editor using VexFlow
 * Allows editing notes, durations, and basic musical elements
 */

import { useEffect, useRef, useState } from 'react';
import { Renderer, Stave, StaveNote, Voice, Formatter, Accidental } from 'vexflow';

interface Note {
  keys: string[];
  duration: string;
  accidental?: string;
}

interface SheetMusicEditorProps {
  initialNotes?: Note[];
  onSave?: (notes: Note[]) => void;
  onCancel?: () => void;
}

const DEFAULT_NOTES: Note[] = [
  { keys: ['c/4'], duration: 'q' },
  { keys: ['d/4'], duration: 'q' },
  { keys: ['e/4'], duration: 'q' },
  { keys: ['f/4'], duration: 'q' },
];

export default function SheetMusicEditor({
  initialNotes = DEFAULT_NOTES,
  onSave,
  onCancel,
}: SheetMusicEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [notes, setNotes] = useState<Note[]>(initialNotes);
  const [selectedNoteIndex, setSelectedNoteIndex] = useState<number | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Update notes if initialNotes prop changes (important for when parent loads data asynchronously)
  useEffect(() => {
    console.log('🎵 SheetMusicEditor: Received initialNotes:', initialNotes);
    if (initialNotes && initialNotes.length > 0) {
      setNotes(initialNotes);
    }
  }, [initialNotes]);

  // Render the staff with VexFlow
  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous content
    containerRef.current.innerHTML = '';

    try {
      // Calculate total ticks needed
      const durationToTicks: { [key: string]: number } = {
        'w': 4096,   // whole note = 4 beats
        'h': 2048,   // half note = 2 beats
        'q': 1024,   // quarter note = 1 beat
        '8': 512,    // eighth note = 0.5 beats
        '16': 256,   // sixteenth note = 0.25 beats
        '32': 128,   // thirty-second note = 0.125 beats
      };

      const totalTicks = notes.reduce((sum, note) => {
        return sum + (durationToTicks[note.duration] || 1024);
      }, 0);

      const ticksPerMeasure = 4096; // 4/4 time signature
      const numMeasures = Math.max(1, Math.ceil(totalTicks / ticksPerMeasure));

      console.log(`📊 Total ticks: ${totalTicks}, Measures needed: ${numMeasures}`);

      // Calculate canvas height based on number of measures
      const staveHeight = 120;
      const measuresPerRow = 2;
      const numRows = Math.ceil(numMeasures / measuresPerRow);
      const canvasHeight = Math.max(200, numRows * staveHeight + 40);

      const renderer = new Renderer(
        containerRef.current,
        Renderer.Backends.SVG
      );

      renderer.resize(800, canvasHeight);
      const context = renderer.getContext();

      // Split notes into measures
      const notesPerMeasure: Note[][] = [];
      let currentMeasureNotes: Note[] = [];
      let currentMeasureTicks = 0;

      notes.forEach((note) => {
        const noteTicks = durationToTicks[note.duration] || 1024;

        if (currentMeasureTicks + noteTicks > ticksPerMeasure && currentMeasureNotes.length > 0) {
          // Start new measure
          notesPerMeasure.push(currentMeasureNotes);
          currentMeasureNotes = [note];
          currentMeasureTicks = noteTicks;
        } else {
          currentMeasureNotes.push(note);
          currentMeasureTicks += noteTicks;
        }
      });

      // Add the last measure
      if (currentMeasureNotes.length > 0) {
        notesPerMeasure.push(currentMeasureNotes);
      }

      // If no notes, create one empty measure
      if (notesPerMeasure.length === 0) {
        notesPerMeasure.push([]);
      }

      console.log(`🎼 Split into ${notesPerMeasure.length} measures`);

      // Draw each measure
      const staveWidth = 370;
      const stavesPerRow = 2;
      let globalNoteIndex = 0;

      notesPerMeasure.forEach((measureNotes, measureIndex) => {
        const row = Math.floor(measureIndex / stavesPerRow);
        const col = measureIndex % stavesPerRow;
        const x = 10 + col * staveWidth;
        const y = 40 + row * staveHeight;

        // Create stave for this measure
        const stave = new Stave(x, y, staveWidth - 20);

        // Only show clef and time signature on first measure
        if (measureIndex === 0) {
          stave.addClef('treble');
          stave.addTimeSignature('4/4');
        }

        stave.setContext(context).draw();

        // Create VexFlow notes for this measure
        if (measureNotes.length > 0) {
          const vexNotes = measureNotes.map((note) => {
            const vexNote = new StaveNote({
              keys: note.keys,
              duration: note.duration,
            });

            // Add accidental if present
            if (note.accidental) {
              vexNote.addModifier(new Accidental(note.accidental), 0);
            }

            // Highlight selected note
            if (globalNoteIndex === selectedNoteIndex) {
              vexNote.setStyle({ fillStyle: 'blue', strokeStyle: 'blue' });
            }

            globalNoteIndex++;
            return vexNote;
          });

          // Calculate beats for this measure
          const measureTicks = measureNotes.reduce((sum, note) => {
            return sum + (durationToTicks[note.duration] || 1024);
          }, 0);
          const numBeats = measureTicks / 1024;

          // Create voice and format
          const voice = new Voice({
            num_beats: numBeats,
            beat_value: 4,
          });
          voice.addTickables(vexNotes);

          new Formatter()
            .joinVoices([voice])
            .format([voice], staveWidth - 40);

          voice.draw(context, stave);
        }
      });
    } catch (error) {
      console.error('Error rendering staff:', error);
    }
  }, [notes, selectedNoteIndex]);

  const handleNoteClick = (index: number) => {
    setSelectedNoteIndex(index === selectedNoteIndex ? null : index);
  };

  const handleChangePitch = (direction: 'up' | 'down') => {
    if (selectedNoteIndex === null) return;

    const pitchMap = ['c', 'd', 'e', 'f', 'g', 'a', 'b'];
    const newNotes = [...notes];
    const currentNote = newNotes[selectedNoteIndex];
    const [pitch, octave] = currentNote.keys[0].split('/');

    const currentIndex = pitchMap.indexOf(pitch);
    let newIndex = direction === 'up' ? currentIndex + 1 : currentIndex - 1;
    let newOctave = parseInt(octave);

    // Handle octave boundaries
    if (newIndex >= pitchMap.length) {
      newIndex = 0;
      newOctave++;
    } else if (newIndex < 0) {
      newIndex = pitchMap.length - 1;
      newOctave--;
    }

    newNotes[selectedNoteIndex] = {
      ...currentNote,
      keys: [`${pitchMap[newIndex]}/${newOctave}`],
    };

    setNotes(newNotes);
    setHasChanges(true);
  };

  const handleChangeDuration = (duration: string) => {
    if (selectedNoteIndex === null) return;

    const newNotes = [...notes];
    newNotes[selectedNoteIndex] = {
      ...newNotes[selectedNoteIndex],
      duration,
    };

    setNotes(newNotes);
    setHasChanges(true);
  };

  const handleAddNote = () => {
    const newNote: Note = { keys: ['c/4'], duration: 'q' };
    setNotes([...notes, newNote]);
    setHasChanges(true);
  };

  const handleDeleteNote = () => {
    if (selectedNoteIndex === null || notes.length <= 1) return;

    const newNotes = notes.filter((_, index) => index !== selectedNoteIndex);
    setNotes(newNotes);
    setSelectedNoteIndex(null);
    setHasChanges(true);
  };

  const handleSave = () => {
    onSave?.(notes);
  };

  const handleCancel = () => {
    if (hasChanges) {
      if (confirm('¿Descartar cambios?')) {
        onCancel?.();
      }
    } else {
      onCancel?.();
    }
  };

  return (
    <div className="sheet-music-editor">
      <div className="editor-header">
        <h3>Editor de Partitura</h3>
        <div className="editor-actions">
          <button className="btn-editor" onClick={handleSave} disabled={!hasChanges}>
            💾 Guardar
          </button>
          <button className="btn-editor" onClick={handleCancel}>
            ❌ Cancelar
          </button>
        </div>
      </div>

      <div className="editor-canvas" ref={containerRef} />

      <div className="editor-controls">
        <div className="control-section">
          <h4>Nota seleccionada:</h4>
          <p>{selectedNoteIndex !== null ? `Nota ${selectedNoteIndex + 1}` : 'Ninguna'}</p>
        </div>

        <div className="control-section">
          <h4>Altura:</h4>
          <button
            className="btn-control-small"
            onClick={() => handleChangePitch('up')}
            disabled={selectedNoteIndex === null}
          >
            ⬆️ Subir
          </button>
          <button
            className="btn-control-small"
            onClick={() => handleChangePitch('down')}
            disabled={selectedNoteIndex === null}
          >
            ⬇️ Bajar
          </button>
        </div>

        <div className="control-section">
          <h4>Duración:</h4>
          <button
            className="btn-control-small"
            onClick={() => handleChangeDuration('w')}
            disabled={selectedNoteIndex === null}
          >
            🎵 Redonda
          </button>
          <button
            className="btn-control-small"
            onClick={() => handleChangeDuration('h')}
            disabled={selectedNoteIndex === null}
          >
            🎵 Blanca
          </button>
          <button
            className="btn-control-small"
            onClick={() => handleChangeDuration('q')}
            disabled={selectedNoteIndex === null}
          >
            🎵 Negra
          </button>
          <button
            className="btn-control-small"
            onClick={() => handleChangeDuration('8')}
            disabled={selectedNoteIndex === null}
          >
            🎵 Corchea
          </button>
        </div>

        <div className="control-section">
          <h4>Acciones:</h4>
          <button className="btn-control-small" onClick={handleAddNote}>
            ➕ Agregar
          </button>
          <button
            className="btn-control-small"
            onClick={handleDeleteNote}
            disabled={selectedNoteIndex === null || notes.length <= 1}
          >
            🗑️ Eliminar
          </button>
        </div>
      </div>

      <div className="editor-instructions">
        <p>💡 <strong>Instrucciones:</strong></p>
        <ul>
          <li>Haz clic en una nota para seleccionarla (se pondrá azul)</li>
          <li>Usa los botones para cambiar la altura o duración</li>
          <li>Agrega o elimina notas según necesites</li>
          <li>Guarda los cambios cuando termines</li>
        </ul>
      </div>
    </div>
  );
}
