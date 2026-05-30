"""Music generation interface."""

import logging
from typing import Optional, Generator
from pathlib import Path

import torch

from ..model import MusicTransformer
from ..config import get_settings, ModelConfig

logger = logging.getLogger(__name__)


class MusicGenerator:
    """
    High-level interface for music generation.

    Handles model loading, device management, and generation.
    """

    def __init__(
        self,
        checkpoint_path: Optional[Path] = None,
        device: Optional[str] = None,
        use_fp16: Optional[bool] = None,
    ):
        """
        Initialize generator.

        Args:
            checkpoint_path: Path to model checkpoint.
            device: Device to use (cuda/cpu).
            use_fp16: Whether to use FP16 inference.
        """
        settings = get_settings()

        self.device = device or settings.DEVICE
        self.use_fp16 = use_fp16 if use_fp16 is not None else settings.USE_FP16

        # Check CUDA availability
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"
            self.use_fp16 = False

        # Load or create model
        if checkpoint_path and Path(checkpoint_path).exists():
            self.model = MusicTransformer.load(checkpoint_path, self.device)
        else:
            config = ModelConfig.from_settings(settings)
            self.model = MusicTransformer(config)
            self.model.to(self.device)

        # Apply FP16 if requested
        if self.use_fp16 and self.device == "cuda":
            self.model = self.model.half()
            logger.info("Using FP16 inference")

        self.model.eval()
        logger.info(
            f"MusicGenerator initialized on {self.device}, "
            f"{self.model.num_parameters:,} parameters"
        )

    @torch.no_grad()
    def generate(
        self,
        input_tokens: list[int],
        max_length: int = 512,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
        repetition_penalty: float = 1.0,
    ) -> dict:
        """
        Generate music from input tokens.

        Args:
            input_tokens: List of input token IDs.
            max_length: Maximum generation length.
            temperature: Sampling temperature.
            top_k: Top-k sampling.
            top_p: Nucleus sampling.
            repetition_penalty: Repetition penalty.

        Returns:
            Dictionary with generated tokens and metadata.
        """
        # Convert to tensor
        tokens_tensor = torch.tensor([input_tokens], device=self.device)

        if self.use_fp16:
            with torch.cuda.amp.autocast():
                generated = self.model.generate(
                    tokens_tensor,
                    max_length=max_length,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty,
                )
        else:
            generated = self.model.generate(
                tokens_tensor,
                max_length=max_length,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
            )

        generated_tokens = generated[0].cpu().tolist()

        return {
            "generated_tokens": generated_tokens,
            "input_length": len(input_tokens),
            "output_length": len(generated_tokens),
            "new_tokens": len(generated_tokens) - len(input_tokens),
        }

    @torch.no_grad()
    def generate_stream(
        self,
        input_tokens: list[int],
        max_length: int = 512,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
    ) -> Generator[dict, None, None]:
        """
        Generate music token by token (streaming).

        Args:
            input_tokens: List of input token IDs.
            max_length: Maximum generation length.
            temperature: Sampling temperature.
            top_k: Top-k sampling.
            top_p: Nucleus sampling.

        Yields:
            Dictionary with token and probability for each generated token.
        """
        tokens_tensor = torch.tensor([input_tokens], device=self.device)
        generated = tokens_tensor.clone()

        for i in range(max_length):
            # Get logits
            if self.use_fp16:
                with torch.cuda.amp.autocast():
                    outputs = self.model.forward(generated)
            else:
                outputs = self.model.forward(generated)

            next_token_logits = outputs["logits"][:, -1, :] / temperature

            # Apply top-k
            if top_k > 0:
                indices_to_remove = next_token_logits < torch.topk(next_token_logits, top_k)[0][..., -1, None]
                next_token_logits[indices_to_remove] = float('-inf')

            # Sample
            probs = torch.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            prob = probs[0, next_token[0, 0]].item()

            # Yield token
            token_id = next_token[0, 0].item()
            yield {
                "token": token_id,
                "probability": prob,
                "position": len(input_tokens) + i,
            }

            # Append
            generated = torch.cat([generated, next_token], dim=1)

            # Check max length
            if generated.size(1) >= self.model.config.max_seq_length:
                break

    @torch.no_grad()
    def get_embeddings(
        self,
        tokens: list[int],
        layer: int = -1,
    ) -> list[float]:
        """
        Get embeddings for tokens.

        Args:
            tokens: List of token IDs.
            layer: Layer to extract from (-1 for last).

        Returns:
            Flattened embeddings list.
        """
        tokens_tensor = torch.tensor([tokens], device=self.device)
        embeddings = self.model.get_embeddings(tokens_tensor, layer)
        return embeddings[0].cpu().flatten().tolist()

    @torch.no_grad()
    def continue_sequence(
        self,
        input_tokens: list[int],
        continuation_length: int = 256,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
        style_hint: Optional[str] = None,
    ) -> dict:
        """
        Continue a musical sequence.

        Args:
            input_tokens: Existing sequence to continue.
            continuation_length: Number of tokens to generate.
            temperature: Sampling temperature.
            top_k: Top-k sampling.
            top_p: Nucleus sampling.
            style_hint: Optional style guidance (not used yet).

        Returns:
            Dictionary with continuation tokens.
        """
        result = self.generate(
            input_tokens,
            max_length=continuation_length,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

        # Extract only the continuation
        continuation = result["generated_tokens"][len(input_tokens):]

        return {
            "continuation_tokens": continuation,
            "full_sequence": result["generated_tokens"],
            "continuation_length": len(continuation),
            "style_hint": style_hint,
        }

    def save_checkpoint(self, path: Path):
        """Save model checkpoint."""
        self.model.save(path)

    def load_checkpoint(self, path: Path):
        """Load model checkpoint."""
        self.model = MusicTransformer.load(path, self.device)
        if self.use_fp16 and self.device == "cuda":
            self.model = self.model.half()
        self.model.eval()
