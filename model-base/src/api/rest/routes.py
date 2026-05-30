"""REST API routes for model-base service."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ...inference import MusicGenerator
from ...config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize generator (lazy loading)
_generator: Optional[MusicGenerator] = None


def get_generator() -> MusicGenerator:
    """Get or create generator instance."""
    global _generator
    if _generator is None:
        _generator = MusicGenerator()
    return _generator


# Request/Response models
class GenerateRequest(BaseModel):
    input_tokens: list[int]
    max_length: int = 512
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    repetition_penalty: float = 1.0


class GenerateResponse(BaseModel):
    request_id: str
    generated_tokens: list[int]
    input_length: int
    output_length: int
    new_tokens: int


class ContinueRequest(BaseModel):
    input_tokens: list[int]
    continuation_length: int = 256
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    style_hint: Optional[str] = None


class ContinueResponse(BaseModel):
    request_id: str
    continuation_tokens: list[int]
    full_sequence: list[int]
    continuation_length: int


class EmbeddingsRequest(BaseModel):
    tokens: list[int]
    layer: int = -1


class EmbeddingsResponse(BaseModel):
    request_id: str
    embeddings: list[float]
    seq_length: int
    hidden_dim: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    model_loaded: bool
    device: str
    num_parameters: int


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()

    try:
        generator = get_generator()
        model_loaded = True
        num_params = generator.model.num_parameters
        device = generator.device
    except Exception:
        model_loaded = False
        num_params = 0
        device = "unknown"

    return HealthResponse(
        status="healthy" if model_loaded else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        model_loaded=model_loaded,
        device=device,
        num_parameters=num_params,
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate music from input tokens.

    Args:
        request: Generation request with tokens and parameters.

    Returns:
        Generated token sequence.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Generate request (id={request_id}): {len(request.input_tokens)} input tokens")

    try:
        generator = get_generator()
        result = generator.generate(
            input_tokens=request.input_tokens,
            max_length=request.max_length,
            temperature=request.temperature,
            top_k=request.top_k,
            top_p=request.top_p,
            repetition_penalty=request.repetition_penalty,
        )

        return GenerateResponse(
            request_id=request_id,
            generated_tokens=result["generated_tokens"],
            input_length=result["input_length"],
            output_length=result["output_length"],
            new_tokens=result["new_tokens"],
        )

    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """
    Stream generated tokens one by one.

    Args:
        request: Generation request.

    Returns:
        Server-sent events stream of tokens.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Stream generate request (id={request_id})")

    try:
        generator = get_generator()

        def event_generator():
            for token_data in generator.generate_stream(
                input_tokens=request.input_tokens,
                max_length=request.max_length,
                temperature=request.temperature,
                top_k=request.top_k,
                top_p=request.top_p,
            ):
                token_data["request_id"] = request_id
                yield f"data: {json.dumps(token_data)}\n\n"

            # Send end event
            yield f"data: {json.dumps({'is_end': True, 'request_id': request_id})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Stream generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continue", response_model=ContinueResponse)
async def continue_sequence(request: ContinueRequest):
    """
    Continue a musical sequence.

    Args:
        request: Continuation request.

    Returns:
        Continuation tokens.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Continue request (id={request_id})")

    try:
        generator = get_generator()
        result = generator.continue_sequence(
            input_tokens=request.input_tokens,
            continuation_length=request.continuation_length,
            temperature=request.temperature,
            top_k=request.top_k,
            top_p=request.top_p,
            style_hint=request.style_hint,
        )

        return ContinueResponse(
            request_id=request_id,
            continuation_tokens=result["continuation_tokens"],
            full_sequence=result["full_sequence"],
            continuation_length=result["continuation_length"],
        )

    except Exception as e:
        logger.error(f"Continuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings", response_model=EmbeddingsResponse)
async def get_embeddings(request: EmbeddingsRequest):
    """
    Get embeddings for tokens.

    Args:
        request: Embeddings request.

    Returns:
        Token embeddings.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Embeddings request (id={request_id})")

    try:
        generator = get_generator()
        embeddings = generator.get_embeddings(
            tokens=request.tokens,
            layer=request.layer,
        )

        settings = get_settings()

        return EmbeddingsResponse(
            request_id=request_id,
            embeddings=embeddings,
            seq_length=len(request.tokens),
            hidden_dim=settings.D_MODEL,
        )

    except Exception as e:
        logger.error(f"Embeddings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/info")
async def model_info():
    """Get model information."""
    try:
        generator = get_generator()
        config = generator.model.config

        return {
            "vocab_size": config.vocab_size,
            "d_model": config.d_model,
            "n_heads": config.n_heads,
            "n_layers": config.n_layers,
            "d_ff": config.d_ff,
            "max_seq_length": config.max_seq_length,
            "num_parameters": generator.model.num_parameters,
            "device": generator.device,
            "fp16": generator.use_fp16,
        }

    except Exception as e:
        logger.error(f"Model info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
