"""
MusicGen Service - Audio generation using Meta's MusicGen.

This service handles:
- Text-to-music generation
- Melody-guided generation
- Audio file management
"""

import logging
import torch
import torchaudio
from typing import Optional, Dict, Any
from pathlib import Path
import numpy as np

from transformers import AutoProcessor, MusicgenForConditionalGeneration

logger = logging.getLogger(__name__)


class MusicGenService:
    """
    Service for generating music using Meta's MusicGen model.

    Supports text-to-music and melody-guided generation.
    """

    def __init__(
        self,
        model_name: str = "facebook/musicgen-medium",
        use_gpu: bool = True,
        device: Optional[str] = None
    ):
        """
        Initialize MusicGen service.

        Args:
            model_name: HuggingFace model identifier
            use_gpu: Whether to use GPU if available
            device: Specific device to use (optional)
        """
        self.model_name = model_name

        # Determine device
        if device:
            self.device = device
        elif use_gpu and torch.cuda.is_available():
            self.device = "cuda"
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.device = "cpu"
            logger.info("Using CPU (GPU not available or disabled)")

        # Load model and processor
        logger.info(f"Loading MusicGen model: {model_name}")
        try:
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = MusicgenForConditionalGeneration.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            logger.info(f"MusicGen model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Error loading MusicGen model: {e}")
            raise RuntimeError(f"Could not load MusicGen model: {e}")

        # Model sampling rate
        self.sampling_rate = self.model.config.audio_encoder.sampling_rate

    def generate_from_text(
        self,
        prompt: str,
        duration: int = 30,
        temperature: float = 1.0,
        top_k: int = 250,
        top_p: float = 0.0,
        guidance_scale: float = 3.0,
        max_new_tokens: Optional[int] = None
    ) -> tuple[np.ndarray, int]:
        """
        Generate music from text description.

        Args:
            prompt: Text description of the music to generate
            duration: Duration in seconds (default: 30)
            temperature: Sampling temperature (higher = more random)
            top_k: Top-k sampling parameter
            top_p: Top-p (nucleus) sampling parameter
            guidance_scale: Classifier-free guidance scale
            max_new_tokens: Maximum tokens to generate (overrides duration)

        Returns:
            Tuple of (audio_array, sampling_rate)
        """
        try:
            logger.info(f"Generating music from prompt: '{prompt}' ({duration}s)")

            # Process text prompt
            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            # Calculate max tokens from duration if not specified
            if max_new_tokens is None:
                # MusicGen generates 50 tokens per second
                max_new_tokens = int(duration * 50)

            # Generate
            with torch.no_grad():
                audio_values = self.model.generate(
                    **inputs,
                    do_sample=True,
                    guidance_scale=guidance_scale,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                )

            # Convert to numpy array
            audio_array = audio_values[0, 0].cpu().numpy()

            logger.info(f"Generated audio: {len(audio_array) / self.sampling_rate:.2f}s")
            return audio_array, self.sampling_rate

        except Exception as e:
            logger.error(f"Error generating music: {e}")
            raise RuntimeError(f"Could not generate music: {e}")

    def generate_with_melody(
        self,
        prompt: str,
        melody_audio: np.ndarray,
        melody_sr: int,
        duration: int = 30,
        temperature: float = 1.0,
        guidance_scale: float = 3.0
    ) -> tuple[np.ndarray, int]:
        """
        Generate music conditioned on a melody.

        Args:
            prompt: Text description
            melody_audio: Melody audio as numpy array
            melody_sr: Sampling rate of melody audio
            duration: Duration in seconds
            temperature: Sampling temperature
            guidance_scale: Guidance scale

        Returns:
            Tuple of (audio_array, sampling_rate)
        """
        try:
            logger.info(f"Generating music with melody guidance: '{prompt}'")

            # Resample melody if needed
            if melody_sr != self.sampling_rate:
                logger.info(f"Resampling melody from {melody_sr} to {self.sampling_rate} Hz")
                melody_tensor = torch.from_numpy(melody_audio).unsqueeze(0)
                melody_tensor = torchaudio.transforms.Resample(
                    orig_freq=melody_sr,
                    new_freq=self.sampling_rate
                )(melody_tensor)
                melody_audio = melody_tensor.squeeze(0).numpy()

            # Process inputs
            inputs = self.processor(
                text=[prompt],
                audio=[melody_audio],
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            # Generate
            max_new_tokens = int(duration * 50)
            with torch.no_grad():
                audio_values = self.model.generate(
                    **inputs,
                    do_sample=True,
                    guidance_scale=guidance_scale,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )

            # Convert to numpy
            audio_array = audio_values[0, 0].cpu().numpy()

            logger.info(f"Generated melody-guided audio: {len(audio_array) / self.sampling_rate:.2f}s")
            return audio_array, self.sampling_rate

        except Exception as e:
            logger.error(f"Error generating music with melody: {e}")
            raise RuntimeError(f"Could not generate music with melody: {e}")

    def save_audio(
        self,
        audio_array: np.ndarray,
        output_path: str,
        sampling_rate: Optional[int] = None
    ) -> str:
        """
        Save audio array to file.

        Args:
            audio_array: Audio as numpy array
            output_path: Path to save file
            sampling_rate: Sampling rate (uses model default if None)

        Returns:
            Path to saved file
        """
        try:
            import soundfile as sf

            sr = sampling_rate or self.sampling_rate

            # Convert to tensor for resampling
            audio_tensor = torch.from_numpy(audio_array).unsqueeze(0)

            # Resample to 44.1kHz for better browser compatibility
            target_sr = 44100
            if sr != target_sr:
                logger.info(f"Resampling audio from {sr}Hz to {target_sr}Hz for browser compatibility")
                resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
                audio_tensor = resampler(audio_tensor)
                sr = target_sr

            # Convert mono to stereo for better browser compatibility
            if audio_tensor.shape[0] == 1:
                audio_tensor = audio_tensor.repeat(2, 1)

            # Convert back to numpy array (transpose for soundfile: samples x channels)
            audio_data = audio_tensor.cpu().numpy().T

            # Ensure output directory exists
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Use soundfile for saving (simple and reliable)
            sf.write(output_path, audio_data, sr, subtype='PCM_16')
            logger.info(f"Saved audio to: {output_path} (stereo, {sr}Hz, 16-bit PCM)")

            return output_path

        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            raise RuntimeError(f"Could not save audio: {e}")

    def load_audio(self, audio_path: str) -> tuple[np.ndarray, int]:
        """
        Load audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio_array, sampling_rate)
        """
        try:
            audio_tensor, sr = torchaudio.load(audio_path)

            # Convert to mono if stereo
            if audio_tensor.shape[0] > 1:
                audio_tensor = torch.mean(audio_tensor, dim=0, keepdim=True)

            audio_array = audio_tensor.squeeze(0).numpy()

            logger.info(f"Loaded audio from: {audio_path} ({len(audio_array) / sr:.2f}s)")
            return audio_array, sr

        except Exception as e:
            logger.error(f"Error loading audio: {e}")
            raise RuntimeError(f"Could not load audio: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "sampling_rate": self.sampling_rate,
            "config": {
                "vocab_size": self.model.config.vocab_size,
                "max_position_embeddings": self.model.config.max_position_embeddings,
                "num_codebooks": self.model.config.num_codebooks,
            }
        }
