/**
 * Audio Player Component with Waveform Visualization
 *
 * Uses WaveSurfer.js for audio playback and waveform visualization.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { downloadFile, getMidiUrl } from '../services/api';
import './AudioPlayer.css';

interface AudioPlayerProps {
  pieceId: string;
  audioUrl: string;
  title?: string;
  showDownloads?: boolean;
}

export default function AudioPlayer({
  pieceId,
  audioUrl,
  title,
  showDownloads = true,
}: AudioPlayerProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const downloadMenuRef = useRef<HTMLDivElement>(null);

  // Close download menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (downloadMenuRef.current && !downloadMenuRef.current.contains(event.target as Node)) {
        setShowDownloadMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Initialize WaveSurfer
  useEffect(() => {
    if (!waveformRef.current || !audioUrl) return;

    let ws: WaveSurfer | null = null;
    let isDestroyed = false;

    const initWaveSurfer = async () => {
      try {
        // Create WaveSurfer instance
        ws = WaveSurfer.create({
          container: waveformRef.current!,
          waveColor: '#667eea',
          progressColor: '#764ba2',
          cursorColor: '#333',
          barWidth: 2,
          barRadius: 3,
          cursorWidth: 1,
          height: 100,
          barGap: 2,
          responsive: true,
          normalize: true,
          backend: 'WebAudio',
        });

        wavesurferRef.current = ws;

        // Event listeners
        ws.on('ready', () => {
          if (!isDestroyed && ws) {
            setDuration(ws.getDuration());
            setIsLoading(false);
            ws.setVolume(volume);
          }
        });

        ws.on('audioprocess', () => {
          if (!isDestroyed && ws) {
            setCurrentTime(ws.getCurrentTime());
          }
        });

        ws.on('play', () => {
          if (!isDestroyed) setIsPlaying(true);
        });

        ws.on('pause', () => {
          if (!isDestroyed) setIsPlaying(false);
        });

        ws.on('finish', () => {
          if (!isDestroyed) setIsPlaying(false);
        });

        ws.on('error', (err) => {
          console.error('WaveSurfer error:', err);
          if (!isDestroyed) {
            setError('Error al cargar el audio');
            setIsLoading(false);
          }
        });

        // Load audio after setting up listeners
        await ws.load(audioUrl);

      } catch (err) {
        console.error('Error initializing WaveSurfer:', err);
        if (!isDestroyed) {
          setError('Error al inicializar el reproductor');
          setIsLoading(false);
        }
      }
    };

    initWaveSurfer();

    // Cleanup
    return () => {
      isDestroyed = true;
      if (ws) {
        ws.destroy();
      }
      wavesurferRef.current = null;
    };
  }, [audioUrl]);

  // Update volume
  useEffect(() => {
    if (wavesurferRef.current) {
      wavesurferRef.current.setVolume(volume);
    }
  }, [volume]);

  const togglePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause();
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!wavesurferRef.current || !waveformRef.current) return;

    const bounds = waveformRef.current.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const progress = x / bounds.width;
    wavesurferRef.current.seekTo(progress);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleDownload = async (format: 'audio' | 'midi' | 'musicxml' | 'abc') => {
    try {
      const blob = await downloadFile(pieceId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${pieceId}.${format === 'audio' ? 'wav' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(`Error downloading ${format}:`, err);
      alert(`Error al descargar el archivo ${format}`);
    }
  };

  if (error) {
    return (
      <div className="audio-player error">
        <p>❌ {error}</p>
      </div>
    );
  }

  return (
    <div className="audio-player">
      {title && <div className="audio-title">{title}</div>}

      {/* Waveform */}
      <div
        ref={waveformRef}
        className={`waveform ${isLoading ? 'loading' : ''}`}
        onClick={handleSeek}
      />

      {isLoading && <div className="loading-text">Cargando audio...</div>}

      {/* Controls */}
      <div className="controls">
        <button
          className="btn-play"
          onClick={togglePlayPause}
          disabled={isLoading}
        >
          {isPlaying ? '⏸️' : '▶️'}
        </button>

        <div className="time-display">
          <span>{formatTime(currentTime)}</span>
          <span>/</span>
          <span>{formatTime(duration)}</span>
        </div>

        <div className="volume-control">
          <span className="volume-icon">🔊</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={(e) => setVolume(Number(e.target.value))}
            className="volume-slider"
          />
        </div>
      </div>

      {/* Download Menu */}
      {showDownloads && (
        <div className="download-menu-container" ref={downloadMenuRef}>
          <button
            className="btn-download-toggle"
            onClick={() => setShowDownloadMenu(!showDownloadMenu)}
            title="Opciones de descarga"
          >
            ⬇️ Descargar
          </button>
          {showDownloadMenu && (
            <div className="download-dropdown">
              <button
                className="dropdown-item"
                onClick={() => { handleDownload('audio'); setShowDownloadMenu(false); }}
              >
                🎵 Audio WAV
              </button>
              <button
                className="dropdown-item"
                onClick={() => { handleDownload('midi'); setShowDownloadMenu(false); }}
              >
                🎹 MIDI
              </button>
              <button
                className="dropdown-item"
                onClick={() => { handleDownload('musicxml'); setShowDownloadMenu(false); }}
              >
                📄 MusicXML
              </button>
              <button
                className="dropdown-item"
                onClick={() => { handleDownload('abc'); setShowDownloadMenu(false); }}
              >
                📝 ABC
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
