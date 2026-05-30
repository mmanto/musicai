"""Spectrogram generation using librosa and torchaudio."""

import logging
from typing import Optional
import tempfile
from pathlib import Path

import numpy as np
import librosa
import torch
import torchaudio

from ..config import get_settings

logger = logging.getLogger(__name__)


class SpectrogramGenerator:
    """
    Generate spectrograms from audio for model input.

    Supports Mel spectrograms and Constant-Q Transform (CQT).
    """

    def __init__(
        self,
        n_mels: Optional[int] = None,
        n_fft: Optional[int] = None,
        hop_length: Optional[int] = None,
        sample_rate: Optional[int] = None,
    ):
        """
        Initialize spectrogram generator.

        Args:
            n_mels: Number of mel bands.
            n_fft: FFT window size.
            hop_length: Hop length for STFT.
            sample_rate: Sample rate for processing.
        """
        settings = get_settings()

        self.n_mels = n_mels or settings.N_MELS
        self.n_fft = n_fft or settings.N_FFT
        self.hop_length = hop_length or settings.HOP_LENGTH
        self.sample_rate = sample_rate or settings.SAMPLE_RATE

        # Initialize torchaudio transforms
        self._init_transforms()

        logger.info(
            f"SpectrogramGenerator initialized: n_mels={self.n_mels}, "
            f"n_fft={self.n_fft}, hop_length={self.hop_length}"
        )

    def _init_transforms(self):
        """Initialize torchaudio transforms for GPU acceleration."""
        self.mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels,
            power=2.0,
        )

        self.amplitude_to_db = torchaudio.transforms.AmplitudeToDB(
            stype="power",
            top_db=80,
        )

    def generate_mel_spectrogram(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        use_gpu: bool = False,
    ) -> dict:
        """
        Generate mel spectrogram from audio.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format (wav, mp3, flac).
            use_gpu: Whether to use GPU for processing.

        Returns:
            Dictionary with spectrogram data and metadata.
        """
        # Load audio
        y, sr = self._load_audio(audio_data, audio_format)

        # Convert to tensor
        waveform = torch.from_numpy(y).float().unsqueeze(0)

        # Move to GPU if requested
        device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
        waveform = waveform.to(device)
        mel_transform = self.mel_transform.to(device)
        amplitude_to_db = self.amplitude_to_db.to(device)

        # Generate mel spectrogram
        mel_spec = mel_transform(waveform)
        mel_spec_db = amplitude_to_db(mel_spec)

        # Convert back to numpy
        mel_spec_np = mel_spec_db.squeeze().cpu().numpy()

        result = {
            "mel_spectrogram": mel_spec_np.flatten().tolist(),
            "n_mels": self.n_mels,
            "n_frames": mel_spec_np.shape[1],
            "sample_rate": sr,
            "hop_length": self.hop_length,
            "duration": len(y) / sr,
        }

        logger.debug(f"Generated mel spectrogram: shape={mel_spec_np.shape}")
        return result

    def generate_cqt(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        n_bins: int = 84,
        bins_per_octave: int = 12,
    ) -> dict:
        """
        Generate Constant-Q Transform spectrogram.

        CQT is better for music analysis as it has logarithmic frequency
        resolution matching musical pitch.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format.
            n_bins: Number of frequency bins.
            bins_per_octave: Bins per octave (12 for semitones).

        Returns:
            Dictionary with CQT data and metadata.
        """
        # Load audio
        y, sr = self._load_audio(audio_data, audio_format)

        # Compute CQT using librosa
        cqt = librosa.cqt(
            y,
            sr=sr,
            hop_length=self.hop_length,
            n_bins=n_bins,
            bins_per_octave=bins_per_octave,
        )

        # Convert to dB scale
        cqt_db = librosa.amplitude_to_db(np.abs(cqt), ref=np.max)

        result = {
            "cqt_spectrogram": cqt_db.flatten().tolist(),
            "n_bins": n_bins,
            "n_frames": cqt_db.shape[1],
            "bins_per_octave": bins_per_octave,
            "sample_rate": sr,
            "hop_length": self.hop_length,
            "duration": len(y) / sr,
        }

        logger.debug(f"Generated CQT: shape={cqt_db.shape}")
        return result

    def generate_mfcc(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        n_mfcc: int = 13,
    ) -> dict:
        """
        Generate MFCC features.

        Args:
            audio_data: Raw audio bytes.
            audio_format: Audio format.
            n_mfcc: Number of MFCC coefficients.

        Returns:
            Dictionary with MFCC data.
        """
        # Load audio
        y, sr = self._load_audio(audio_data, audio_format)

        # Compute MFCC
        mfccs = librosa.feature.mfcc(
            y=y,
            sr=sr,
            n_mfcc=n_mfcc,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        # Also compute deltas
        mfcc_delta = librosa.feature.delta(mfccs)
        mfcc_delta2 = librosa.feature.delta(mfccs, order=2)

        result = {
            "mfcc": mfccs.flatten().tolist(),
            "mfcc_delta": mfcc_delta.flatten().tolist(),
            "mfcc_delta2": mfcc_delta2.flatten().tolist(),
            "n_mfcc": n_mfcc,
            "n_frames": mfccs.shape[1],
            "sample_rate": sr,
        }

        logger.debug(f"Generated MFCC: shape={mfccs.shape}")
        return result

    def _load_audio(self, audio_data: bytes, audio_format: str) -> tuple[np.ndarray, int]:
        """Load audio from bytes."""
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_data)
            temp_path = Path(f.name)

        try:
            y, sr = librosa.load(temp_path, sr=self.sample_rate, mono=True)
            return y, sr
        finally:
            temp_path.unlink(missing_ok=True)

    def normalize_spectrogram(self, spectrogram: np.ndarray) -> np.ndarray:
        """
        Normalize spectrogram to [0, 1] range.

        Args:
            spectrogram: Input spectrogram array.

        Returns:
            Normalized spectrogram.
        """
        min_val = spectrogram.min()
        max_val = spectrogram.max()

        if max_val - min_val > 0:
            return (spectrogram - min_val) / (max_val - min_val)
        return spectrogram

    def resize_spectrogram(
        self,
        spectrogram: np.ndarray,
        target_frames: int,
    ) -> np.ndarray:
        """
        Resize spectrogram to target number of frames.

        Args:
            spectrogram: Input spectrogram (n_freq x n_frames).
            target_frames: Target number of time frames.

        Returns:
            Resized spectrogram.
        """
        import scipy.ndimage

        if spectrogram.shape[1] == target_frames:
            return spectrogram

        scale_factor = target_frames / spectrogram.shape[1]
        resized = scipy.ndimage.zoom(spectrogram, (1, scale_factor), order=1)

        return resized
