/**
 * Sheet Music Viewer Component
 *
 * Displays musical notation using OpenSheetMusicDisplay (OSMD)
 * Supports MusicXML rendering with zoom and playback controls
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import * as Tone from 'tone';
import { Midi } from '@tonejs/midi';
import SheetMusicEditor from './SheetMusicEditor';
import { parseMusicXMLToVexFlow, saveEditedScore, type VexFlowNote } from '../../services/musicxmlService';

interface SheetMusicViewerProps {
  musicxmlUrl: string;
  midiUrl?: string;
  audioUrl?: string;
  pieceId?: string;
  onPlayWav?: () => void;
  onPlayMidi?: () => void;
  onEdit?: () => void;
  onScoreUpdated?: (newMusicXmlUrl: string) => void;
  showControls?: boolean;
  zoom?: number;
  allowEditing?: boolean;
}

type PlaybackMode = 'midi' | 'wav';

interface MidiNote {
  time: number;
  note: string;
  duration: number;
  velocity: number;
}

export default function SheetMusicViewer({
  musicxmlUrl,
  midiUrl,
  audioUrl,
  pieceId,
  onPlayWav,
  onPlayMidi,
  onEdit,
  onScoreUpdated,
  showControls = true,
  zoom = 1.0,
}: SheetMusicViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentZoom, setCurrentZoom] = useState(zoom);
  const [isEditing, setIsEditing] = useState(false);
  const [editableNotes, setEditableNotes] = useState<VexFlowNote[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Playback state
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>('midi');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMidiLoaded, setIsMidiLoaded] = useState(false);
  const [currentMeasure, setCurrentMeasure] = useState(0);
  const [totalMeasures, setTotalMeasures] = useState(0);
  const [showModeMenu, setShowModeMenu] = useState(false);

  // Audio refs
  const synthRef = useRef<Tone.PolySynth | null>(null);
  const partRef = useRef<Tone.Part | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const midiNotesRef = useRef<MidiNote[]>([]);
  const measureTimesRef = useRef<number[]>([]);
  const modeMenuRef = useRef<HTMLDivElement>(null);

  // Close mode menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modeMenuRef.current && !modeMenuRef.current.contains(event.target as Node)) {
        setShowModeMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Initialize synth
  useEffect(() => {
    const synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: 'triangle' },
      envelope: {
        attack: 0.005,
        decay: 0.1,
        sustain: 0.3,
        release: 1,
      },
    }).toDestination();
    synth.volume.value = -10;
    synthRef.current = synth;

    return () => {
      synth.disconnect();
      synth.dispose();
    };
  }, []);

  // Load MIDI file
  useEffect(() => {
    if (!midiUrl || !synthRef.current) return;

    const loadMIDI = async () => {
      try {
        const response = await fetch(midiUrl);
        const midiData = await response.arrayBuffer();
        const midi = new Midi(midiData);

        console.log('MIDI loaded:', {
          duration: midi.duration,
          tracks: midi.tracks.length,
          tempo: midi.header.tempos[0]?.bpm || 120,
        });

        // Get tempo and time signature info
        const tempo = midi.header.tempos[0]?.bpm || 120;
        const timeSignature = midi.header.timeSignatures[0] || { numerator: 4, denominator: 4 };
        const beatsPerMeasure = timeSignature.timeSignature?.[0] || 4;
        const secondsPerBeat = 60 / tempo;
        const secondsPerMeasure = secondsPerBeat * beatsPerMeasure;

        // Calculate measure times
        const measureTimes: number[] = [];
        const numMeasures = Math.ceil(midi.duration / secondsPerMeasure);
        for (let i = 0; i <= numMeasures; i++) {
          measureTimes.push(i * secondsPerMeasure);
        }
        measureTimesRef.current = measureTimes;
        setTotalMeasures(numMeasures);

        // Convert MIDI tracks to notes
        const allNotes: MidiNote[] = [];
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
        allNotes.sort((a, b) => a.time - b.time);
        midiNotesRef.current = allNotes;

        // Create Tone.js Part
        if (partRef.current) {
          partRef.current.dispose();
        }

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

        Tone.Transport.bpm.value = tempo;
        setIsMidiLoaded(true);
      } catch (err) {
        console.error('Error loading MIDI:', err);
      }
    };

    loadMIDI();

    return () => {
      if (partRef.current) {
        partRef.current.dispose();
        partRef.current = null;
      }
    };
  }, [midiUrl]);

  // Initialize and load MusicXML
  useEffect(() => {
    if (!containerRef.current || !musicxmlUrl) return;

    const loadScore = async () => {
      try {
        setIsLoading(true);
        setError(null);

        if (containerRef.current) {
          containerRef.current.innerHTML = '';
        }

        if (osmdRef.current) {
          osmdRef.current.clear();
        }

        const osmd = new OpenSheetMusicDisplay(containerRef.current!, {
          autoResize: true,
          backend: 'svg',
          drawTitle: false,
          drawComposer: false,
          drawPartNames: false,
          drawFingerings: false,
          drawPartAbbreviations: false,
          drawLyricist: false,
          drawCredits: false,
          drawUpToMeasureNumber: Number.MAX_SAFE_INTEGER,
          drawFromMeasureNumber: 1,
        });

        osmdRef.current = osmd;
        await osmd.load(musicxmlUrl);
        osmd.zoom = currentZoom;
        osmd.render();

        setIsLoading(false);
      } catch (err) {
        console.error('Error loading MusicXML:', err);
        setError('Error al cargar la partitura');
        setIsLoading(false);
      }
    };

    loadScore();

    return () => {
      if (osmdRef.current) {
        osmdRef.current.clear();
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [musicxmlUrl]);

  // Handle zoom changes
  useEffect(() => {
    if (osmdRef.current && !isLoading) {
      osmdRef.current.zoom = currentZoom;
      osmdRef.current.render();
    }
  }, [currentZoom, isLoading]);

  // Force white background and black notation after render
  useEffect(() => {
    if (!isLoading && containerRef.current) {
      // Apply styles to SVG elements after OSMD renders
      const svg = containerRef.current.querySelector('svg');
      if (svg) {
        svg.style.backgroundColor = '#ffffff';

        // Force black fill for all path and text elements
        const paths = svg.querySelectorAll('path');
        paths.forEach((path) => {
          const currentFill = path.getAttribute('fill');
          // Only change if it's not transparent/none
          if (currentFill && currentFill !== 'none' && currentFill !== 'transparent') {
            path.style.fill = '#000000';
          }
        });

        const texts = svg.querySelectorAll('text');
        texts.forEach((text) => {
          text.style.fill = '#000000';
        });

        // Force black stroke for lines
        const lines = svg.querySelectorAll('line, polyline');
        lines.forEach((line) => {
          const el = line as SVGElement;
          el.style.stroke = '#000000';
        });
      }
    }
  }, [isLoading, musicxmlUrl, currentZoom]);

  const handleZoomIn = () => setCurrentZoom((prev) => Math.min(prev + 0.25, 2.0));
  const handleZoomOut = () => setCurrentZoom((prev) => Math.max(prev - 0.25, 0.5));

  // Playback controls
  const handlePlay = useCallback(async () => {
    if (playbackMode === 'midi') {
      if (!partRef.current || !isMidiLoaded) return;

      await Tone.start();
      setIsPlaying(true);
      onPlayMidi?.();

      partRef.current.start(0);
      Tone.Transport.start();

      // Schedule stop
      const duration = midiNotesRef.current.length > 0
        ? Math.max(...midiNotesRef.current.map(n => n.time + n.duration))
        : 10;

      Tone.Transport.scheduleOnce(() => {
        handleStop();
      }, `+${duration}`);

    } else if (playbackMode === 'wav' && audioUrl) {
      if (!audioRef.current) {
        audioRef.current = new Audio(audioUrl);
        audioRef.current.onended = () => setIsPlaying(false);
      }
      audioRef.current.play();
      setIsPlaying(true);
      onPlayWav?.();
    }
  }, [playbackMode, isMidiLoaded, audioUrl, onPlayMidi, onPlayWav]);

  const handlePause = useCallback(() => {
    if (playbackMode === 'midi') {
      Tone.Transport.pause();
    } else if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsPlaying(false);
  }, [playbackMode]);

  const handleStop = useCallback(() => {
    if (playbackMode === 'midi') {
      Tone.Transport.stop();
      Tone.Transport.position = 0;
    } else if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setCurrentMeasure(0);
  }, [playbackMode]);

  const handleGoToStart = useCallback(() => {
    handleStop();
  }, [handleStop]);

  const handleNextMeasure = useCallback(() => {
    if (playbackMode !== 'midi' || !measureTimesRef.current.length) return;

    const nextMeasure = Math.min(currentMeasure + 1, totalMeasures - 1);
    const nextTime = measureTimesRef.current[nextMeasure] || 0;

    Tone.Transport.position = nextTime;
    setCurrentMeasure(nextMeasure);

    // If playing, continue from new position
    if (isPlaying) {
      Tone.Transport.start();
    }
  }, [playbackMode, currentMeasure, totalMeasures, isPlaying]);

  const handleEditClick = async () => {
    try {
      setIsLoading(true);
      const notes = await parseMusicXMLToVexFlow(musicxmlUrl);
      setEditableNotes(notes);
      setIsEditing(true);
      setIsLoading(false);
    } catch (error) {
      console.error('Error parsing MusicXML for editing:', error);
      const defaultNotes = [
        { keys: ['c/4'], duration: 'q' },
        { keys: ['d/4'], duration: 'q' },
        { keys: ['e/4'], duration: 'q' },
        { keys: ['f/4'], duration: 'q' },
      ];
      setEditableNotes(defaultNotes);
      setIsEditing(true);
      setIsLoading(false);
    }
  };

  const handleSaveEdit = async (notes: VexFlowNote[]) => {
    if (!pieceId) {
      alert('No se puede guardar: falta el ID de la pieza');
      return;
    }

    setIsSaving(true);

    try {
      const result = await saveEditedScore(pieceId, notes);

      if (result.success && result.musicxml_url) {
        setEditableNotes(notes);
        setIsEditing(false);
        if (onScoreUpdated) {
          onScoreUpdated(result.musicxml_url);
        }
        alert('✅ Partitura guardada exitosamente');
      } else {
        throw new Error(result.error || 'Error desconocido');
      }
    } catch (error: any) {
      console.error('Error saving edited score:', error);
      alert(`❌ Error al guardar: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  if (error) {
    return (
      <div className="sheet-music-error">
        <p>❌ {error}</p>
      </div>
    );
  }

  if (isEditing && editableNotes.length > 0) {
    return (
      <SheetMusicEditor
        initialNotes={editableNotes}
        onSave={handleSaveEdit}
        onCancel={handleCancelEdit}
      />
    );
  }

  const canPlay = (playbackMode === 'midi' && isMidiLoaded) || (playbackMode === 'wav' && audioUrl);

  return (
    <div className="sheet-music-viewer">
      {showControls && (
        <div className="sheet-music-controls sheet-music-controls-minimal">
          {/* Playback controls */}
          <div className="control-group playback-controls">
            {/* Mode selector */}
            <div className="mode-selector" ref={modeMenuRef}>
              <button
                className="btn-mode"
                onClick={() => setShowModeMenu(!showModeMenu)}
                title="Seleccionar modo de reproducción"
              >
                {playbackMode === 'midi' ? '🎹' : '🔊'} ▾
              </button>
              {showModeMenu && (
                <div className="mode-dropdown">
                  <button
                    className={`dropdown-item ${playbackMode === 'wav' ? 'active' : ''}`}
                    onClick={() => { setPlaybackMode('wav'); setShowModeMenu(false); handleStop(); }}
                    disabled={!audioUrl}
                  >
                    🔊 WAV (mejor calidad)
                  </button>
                  <button
                    className={`dropdown-item ${playbackMode === 'midi' ? 'active' : ''}`}
                    onClick={() => { setPlaybackMode('midi'); setShowModeMenu(false); handleStop(); }}
                    disabled={!midiUrl}
                  >
                    🎹 MIDI (control avanzado)
                  </button>
                </div>
              )}
            </div>

            {/* Transport controls */}
            <button
              className="btn-transport"
              onClick={handleGoToStart}
              disabled={!canPlay}
              title="Ir al inicio"
            >
              ⏮️
            </button>
            <button
              className="btn-transport btn-play-main"
              onClick={isPlaying ? handlePause : handlePlay}
              disabled={!canPlay}
              title={isPlaying ? 'Pausar' : 'Reproducir'}
            >
              {isPlaying ? '⏸️' : '▶️'}
            </button>
            {playbackMode === 'midi' && (
              <button
                className="btn-transport"
                onClick={handleNextMeasure}
                disabled={!isMidiLoaded || currentMeasure >= totalMeasures - 1}
                title="Siguiente compás"
              >
                ⏭️
              </button>
            )}
          </div>

          {/* Zoom controls */}
          <div className="control-group zoom-controls">
            <button
              className="btn-zoom btn-zoom-minimal"
              onClick={handleZoomOut}
              disabled={currentZoom <= 0.5}
              title="Alejar"
            >
              −
            </button>
            <span className="zoom-level zoom-level-minimal">{Math.round(currentZoom * 100)}%</span>
            <button
              className="btn-zoom btn-zoom-minimal"
              onClick={handleZoomIn}
              disabled={currentZoom >= 2.0}
              title="Acercar"
            >
              +
            </button>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="sheet-music-loading">
          <p>⏳ Cargando partitura...</p>
        </div>
      )}

      <div
        ref={containerRef}
        className="sheet-music-container"
        style={{
          width: '100%',
          minHeight: '200px',
          overflow: 'auto',
          display: isLoading ? 'none' : 'block',
          backgroundColor: '#ffffff',
        }}
      />
    </div>
  );
}
