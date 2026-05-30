/**
 * MIDI Synthesizer Component
 *
 * Synthesizes audio from MIDI files using Tone.js
 * Provides playback controls and tempo adjustment
 */

import { useEffect, useRef, useState } from 'react';
import * as Tone from 'tone';
import { Midi } from '@tonejs/midi';

interface MIDISynthesizerProps {
  midiUrl: string;
  onPlaybackStart?: () => void;
  onPlaybackEnd?: () => void;
  autoPlay?: boolean;
}

export default function MIDISynthesizer({
  midiUrl,
  onPlaybackStart,
  onPlaybackEnd,
  autoPlay = false,
}: MIDISynthesizerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tempo, setTempo] = useState(120);
  const synthRef = useRef<Tone.PolySynth | null>(null);
  const partRef = useRef<Tone.Part | null>(null);

  // Initialize synth
  useEffect(() => {
    // Create polyphonic synthesizer
    const synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: {
        type: 'triangle',
      },
      envelope: {
        attack: 0.005,
        decay: 0.1,
        sustain: 0.3,
        release: 1,
      },
    }).toDestination();

    synth.volume.value = -10; // Reduce volume a bit
    synthRef.current = synth;

    return () => {
      synth.disconnect();
      synth.dispose();
    };
  }, []);

  // Load and parse MIDI file
  useEffect(() => {
    if (!midiUrl || !synthRef.current) return;

    const loadMIDI = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch MIDI file
        const response = await fetch(midiUrl);
        const midiData = await response.arrayBuffer();

        // Parse MIDI with @tonejs/midi
        const midi = new Midi(midiData);

        console.log('MIDI loaded:', {
          name: midi.name,
          duration: midi.duration,
          tracks: midi.tracks.length,
          tempo: midi.header.tempos[0]?.bpm || 120,
        });

        // Set tempo from MIDI file if available
        if (midi.header.tempos.length > 0) {
          setTempo(midi.header.tempos[0].bpm);
        }

        // Convert MIDI tracks to Tone.js format
        // We'll combine all tracks into a single part
        const allNotes: any[] = [];

        midi.tracks.forEach((track) => {
          track.notes.forEach((note) => {
            allNotes.push({
              time: note.time,
              note: note.name,
              duration: note.duration,
              velocity: note.velocity,
            });
          });
        });

        // Sort notes by time
        allNotes.sort((a, b) => a.time - b.time);

        console.log('Parsed notes:', allNotes.length);

        // Create Tone.js Part
        const part = new Tone.Part((time, note) => {
          synthRef.current?.triggerAttackRelease(
            note.note,
            note.duration,
            time,
            note.velocity
          );
        }, allNotes);

        part.loop = false;
        partRef.current = part;

        setIsLoading(false);

        if (autoPlay) {
          handlePlay();
        }
      } catch (err) {
        console.error('Error loading MIDI:', err);
        setError('Error al cargar archivo MIDI');
        setIsLoading(false);
      }
    };

    loadMIDI();

    return () => {
      if (partRef.current) {
        partRef.current.dispose();
      }
    };
  }, [midiUrl, autoPlay]);

  // Update tempo
  useEffect(() => {
    Tone.Transport.bpm.value = tempo;
  }, [tempo]);

  const handlePlay = async () => {
    if (!partRef.current) return;

    try {
      // Start Tone.js audio context
      await Tone.start();

      setIsPlaying(true);
      onPlaybackStart?.();

      // Start transport and part
      partRef.current.start(0);
      Tone.Transport.start();

      // Calculate the duration of the part
      const duration = partRef.current.loopEnd || 10; // Default to 10 seconds if no duration

      // Schedule stop callback
      Tone.Transport.scheduleOnce(() => {
        handleStop();
      }, `+${duration}`);

    } catch (err) {
      console.error('Error playing MIDI:', err);
      setError('Error al reproducir');
    }
  };

  const handlePause = () => {
    Tone.Transport.pause();
    setIsPlaying(false);
  };

  const handleStop = () => {
    Tone.Transport.stop();
    setIsPlaying(false);
    onPlaybackEnd?.();
  };

  const handleTempoChange = (newTempo: number) => {
    setTempo(newTempo);
  };

  if (error) {
    return (
      <div className="midi-synth-error">
        <p>❌ {error}</p>
      </div>
    );
  }

  return (
    <div className="midi-synthesizer">
      <div className="synth-controls">
        <button
          className="btn-synth"
          onClick={isPlaying ? handlePause : handlePlay}
          disabled={isLoading || !partRef.current}
        >
          {isPlaying ? '⏸️ Pausar' : '▶️ Reproducir'}
        </button>
        <button
          className="btn-synth"
          onClick={handleStop}
          disabled={!isPlaying}
        >
          ⏹️ Detener
        </button>

        <div className="tempo-control">
          <label>
            Tempo: {tempo} BPM
            <input
              type="range"
              min="40"
              max="240"
              value={tempo}
              onChange={(e) => handleTempoChange(Number(e.target.value))}
              className="tempo-slider"
            />
          </label>
        </div>
      </div>

      {isLoading && <p className="synth-status">⏳ Cargando MIDI...</p>}
    </div>
  );
}
