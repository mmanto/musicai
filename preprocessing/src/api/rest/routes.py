"""REST API routes for preprocessing service."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel

from ...tokenizer import BPETokenizer, TextTokenizer
from ...audio import AudioFeatureExtractor, SpectrogramGenerator, AudioToMidiConverter
from ...config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize components
bpe_tokenizer = BPETokenizer()
text_tokenizer = TextTokenizer()
feature_extractor = AudioFeatureExtractor()
spectrogram_generator = SpectrogramGenerator()
audio_to_midi = AudioToMidiConverter()


# Response models
class TokenResponse(BaseModel):
    request_id: str
    tokens: list[int]
    num_tokens: int
    features: dict


class FeaturesResponse(BaseModel):
    request_id: str
    tempo: float
    key: str
    time_signature: str
    duration: float
    features: dict


class MidiConversionResponse(BaseModel):
    request_id: str
    num_notes: int
    confidence: float
    duration: float
    notes: list[dict]


class TextTokenResponse(BaseModel):
    request_id: str
    tokens: list[str]
    features: dict
    musical_context: dict


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
    )


@router.post("/tokenize/midi", response_model=TokenResponse)
async def tokenize_midi(
    file: UploadFile = File(...),
):
    """
    Tokenize a MIDI file into BPE tokens.

    Args:
        file: MIDI file upload.

    Returns:
        Token response with BPE tokens and features.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Tokenizing MIDI file: {file.filename} (request_id={request_id})")

    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be MIDI format (.mid or .midi)")

    try:
        midi_data = await file.read()
        result = bpe_tokenizer.tokenize_midi(midi_data)

        return TokenResponse(
            request_id=request_id,
            tokens=result["tokens"],
            num_tokens=len(result["tokens"]),
            features=result["features"],
        )
    except Exception as e:
        logger.error(f"Error tokenizing MIDI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tokenize/audio", response_model=TokenResponse)
async def tokenize_audio(
    file: UploadFile = File(...),
    onset_threshold: float = Form(0.5),
    frame_threshold: float = Form(0.3),
):
    """
    Tokenize audio by converting to MIDI first, then tokenizing.

    Args:
        file: Audio file upload (wav, mp3, flac).
        onset_threshold: Threshold for note onset detection.
        frame_threshold: Threshold for frame detection.

    Returns:
        Token response with BPE tokens and features.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Tokenizing audio file: {file.filename} (request_id={request_id})")

    # Determine format
    suffix = file.filename.split('.')[-1].lower()
    if suffix not in ['wav', 'mp3', 'flac']:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        audio_data = await file.read()

        # Convert to MIDI
        midi_result = audio_to_midi.convert(
            audio_data,
            audio_format=suffix,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
        )

        # Tokenize the MIDI
        token_result = bpe_tokenizer.tokenize_midi(midi_result["midi_data"])

        # Merge features
        features = token_result["features"]
        features["conversion_confidence"] = midi_result["confidence"]
        features["num_notes"] = float(midi_result["num_notes"])

        return TokenResponse(
            request_id=request_id,
            tokens=token_result["tokens"],
            num_tokens=len(token_result["tokens"]),
            features=features,
        )
    except Exception as e:
        logger.error(f"Error tokenizing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tokenize/text", response_model=TextTokenResponse)
async def tokenize_text(
    text: str = Form(...),
):
    """
    Tokenize text description and extract musical context.

    Args:
        text: Musical description text.

    Returns:
        Token response with extracted features and musical context.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Tokenizing text (request_id={request_id})")

    try:
        result = text_tokenizer.tokenize(text)
        context = text_tokenizer.get_musical_context(text)

        return TextTokenResponse(
            request_id=request_id,
            tokens=result["tokens"],
            features=result["features"],
            musical_context=context,
        )
    except Exception as e:
        logger.error(f"Error tokenizing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/extract", response_model=FeaturesResponse)
async def extract_features(
    file: UploadFile = File(...),
):
    """
    Extract musical features from audio file.

    Args:
        file: Audio file upload.

    Returns:
        Features response with tempo, key, time signature, etc.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Extracting features from: {file.filename} (request_id={request_id})")

    suffix = file.filename.split('.')[-1].lower()
    if suffix not in ['wav', 'mp3', 'flac']:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        audio_data = await file.read()
        features = feature_extractor.extract_all(audio_data, suffix)

        return FeaturesResponse(
            request_id=request_id,
            tempo=features["tempo"],
            key=features["key_string"],
            time_signature=features["time_signature"],
            duration=features["duration"],
            features=features,
        )
    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/spectrogram")
async def generate_spectrogram(
    file: UploadFile = File(...),
    spectrogram_type: str = Form("mel"),
    use_gpu: bool = Form(False),
):
    """
    Generate spectrogram from audio.

    Args:
        file: Audio file upload.
        spectrogram_type: Type of spectrogram (mel, cqt, mfcc).
        use_gpu: Whether to use GPU acceleration.

    Returns:
        Spectrogram data and metadata.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Generating {spectrogram_type} spectrogram (request_id={request_id})")

    suffix = file.filename.split('.')[-1].lower()
    if suffix not in ['wav', 'mp3', 'flac']:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        audio_data = await file.read()

        if spectrogram_type == "mel":
            result = spectrogram_generator.generate_mel_spectrogram(
                audio_data, suffix, use_gpu
            )
        elif spectrogram_type == "cqt":
            result = spectrogram_generator.generate_cqt(audio_data, suffix)
        elif spectrogram_type == "mfcc":
            result = spectrogram_generator.generate_mfcc(audio_data, suffix)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown spectrogram type: {spectrogram_type}"
            )

        result["request_id"] = request_id
        return result

    except Exception as e:
        logger.error(f"Error generating spectrogram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/audio-to-midi", response_model=MidiConversionResponse)
async def convert_audio_to_midi(
    file: UploadFile = File(...),
    onset_threshold: float = Form(0.5),
    frame_threshold: float = Form(0.3),
    min_note_length: float = Form(0.058),
):
    """
    Convert audio file to MIDI.

    Args:
        file: Audio file upload.
        onset_threshold: Threshold for note onset detection.
        frame_threshold: Threshold for frame detection.
        min_note_length: Minimum note duration.

    Returns:
        MIDI conversion result with notes and confidence.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Converting audio to MIDI: {file.filename} (request_id={request_id})")

    suffix = file.filename.split('.')[-1].lower()
    if suffix not in ['wav', 'mp3', 'flac']:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        audio_data = await file.read()
        result = audio_to_midi.convert(
            audio_data,
            audio_format=suffix,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            min_note_length=min_note_length,
        )

        return MidiConversionResponse(
            request_id=request_id,
            num_notes=result["num_notes"],
            confidence=result["confidence"],
            duration=result["duration"],
            notes=result["notes"],
        )
    except Exception as e:
        logger.error(f"Error converting to MIDI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/audio-to-midi/download")
async def download_midi_from_audio(
    file: UploadFile = File(...),
    onset_threshold: float = Form(0.5),
    frame_threshold: float = Form(0.3),
):
    """
    Convert audio to MIDI and return the MIDI file.

    Args:
        file: Audio file upload.
        onset_threshold: Note onset threshold.
        frame_threshold: Frame threshold.

    Returns:
        MIDI file bytes.
    """
    from fastapi.responses import Response

    suffix = file.filename.split('.')[-1].lower()
    if suffix not in ['wav', 'mp3', 'flac']:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        audio_data = await file.read()
        result = audio_to_midi.convert(
            audio_data,
            audio_format=suffix,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
        )

        filename = file.filename.rsplit('.', 1)[0] + '.mid'

        return Response(
            content=result["midi_data"],
            media_type="audio/midi",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error converting to MIDI: {e}")
        raise HTTPException(status_code=500, detail=str(e))
