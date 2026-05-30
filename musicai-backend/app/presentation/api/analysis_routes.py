"""
Music Analysis API Routes.

Handles music analysis and transformation requests.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pathlib import Path

from app.application.dtos import (
    MusicAnalysisRequest,
    MusicAnalysisResponse,
    TransformationRequest,
    TransformationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/music", tags=["analysis"])


def get_services():
    """Dependency to get AI services."""
    from app.main import music21_service, ollama_service
    return {
        "music21": music21_service,
        "ollama": ollama_service,
    }


@router.post(
    "/analyze",
    response_model=MusicAnalysisResponse,
    summary="Analyze music",
    description="Analyze a musical piece and extract musical features."
)
async def analyze_music(
    request: MusicAnalysisRequest,
    services: dict = Depends(get_services)
):
    """
    Analyze a musical piece.

    Currently supports analyzing existing pieces by ID.
    Future: Support file upload for analysis.
    """
    try:
        if not request.piece_id:
            raise HTTPException(
                status_code=400,
                detail="piece_id is required (file upload not yet implemented)"
            )

        # TODO: Load piece from database
        # For now, return mock data
        logger.info(f"Analyzing piece: {request.piece_id}")

        # Mock analysis (in production, load actual piece and analyze)
        analysis = {
            "key": "C major",
            "tempo": 120,
            "time_signature": "4/4",
            "duration": 30.0,
            "chords": ["C", "G", "Am", "F"],
            "note_count": 150,
            "pitch_range": {"lowest": 60, "highest": 72}
        }

        # Generate explanation if requested
        explanation = None
        if request.generate_explanation and services["ollama"]:
            try:
                explanation = services["ollama"].explain_analysis(analysis)
            except Exception as e:
                logger.warning(f"Could not generate explanation: {e}")

        return MusicAnalysisResponse(
            piece_id=request.piece_id,
            analysis=analysis,
            explanation=explanation
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing music: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/analyze/upload",
    response_model=MusicAnalysisResponse,
    summary="Analyze uploaded file",
    description="Upload and analyze a MIDI or audio file."
)
async def analyze_upload(
    file: UploadFile = File(..., description="MIDI or audio file"),
    generate_explanation: bool = False,
    services: dict = Depends(get_services)
):
    """
    Analyze an uploaded music file.

    Supports MIDI files. Audio files require basic-pitch (not yet installed).
    """
    try:
        logger.info(f"Analyzing uploaded file: {file.filename}")

        # Read file
        content = await file.read()

        # Check file type
        if file.filename.endswith('.mid') or file.filename.endswith('.midi'):
            # Parse MIDI
            stream_obj = services["music21"].from_midi_bytes(content)

            # Analyze
            analysis = services["music21"].analyze(stream_obj)

            # Generate piece ID
            piece_id = f"upload_{uuid.uuid4().hex[:12]}"

            # Generate explanation if requested
            explanation = None
            if generate_explanation and services["ollama"]:
                try:
                    explanation = services["ollama"].explain_analysis(analysis)
                except Exception as e:
                    logger.warning(f"Could not generate explanation: {e}")

            return MusicAnalysisResponse(
                piece_id=piece_id,
                analysis=analysis,
                explanation=explanation
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Only MIDI files supported currently."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/transform",
    response_model=TransformationResponse,
    summary="Transform music",
    description="Apply transformations like transpose, augment, or tempo change."
)
async def transform_music(
    request: TransformationRequest,
    services: dict = Depends(get_services)
):
    """
    Transform a musical piece.

    Supported transformations:
    - transpose: Change pitch by semitones
    - augment: Change rhythm speed
    - change_tempo: Change playback tempo
    """
    try:
        logger.info(f"Transforming piece {request.piece_id}: {request.transformation_type}")

        # TODO: Load piece from database
        # For now, return mock response
        new_piece_id = f"piece_{uuid.uuid4().hex[:12]}"

        transformation_desc = ""
        if request.transformation_type == "transpose":
            transformation_desc = f"transpose {request.semitones:+d} semitones"
        elif request.transformation_type == "augment":
            transformation_desc = f"augment {request.factor}x"
        elif request.transformation_type == "change_tempo":
            transformation_desc = f"change tempo to {request.tempo} BPM"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown transformation: {request.transformation_type}"
            )

        return TransformationResponse(
            original_piece_id=request.piece_id,
            new_piece_id=new_piece_id,
            transformation_applied=transformation_desc,
            message="Transformation completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transforming music: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/download/{piece_id}/{format}",
    summary="Download music file",
    description="Download a music file in specified format (audio, midi, musicxml, abc)."
)
async def download_file(
    piece_id: str,
    format: str,
    services: dict = Depends(get_services)
):
    """
    Download a music file.

    Supported formats:
    - audio: WAV file
    - midi: MIDI file
    - musicxml: MusicXML file
    - abc: ABC notation file
    """
    import tempfile

    try:
        # Define format mappings
        format_config = {
            "audio": {"ext": ".wav", "media_type": "audio/wav"},
            "midi": {"ext": ".mid", "media_type": "audio/midi"},
            "musicxml": {"ext": ".musicxml", "media_type": "application/vnd.recordare.musicxml+xml"},
            "abc": {"ext": ".abc", "media_type": "text/plain"},
        }

        if format not in format_config:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        config = format_config[format]
        filename = f"{piece_id}{config['ext']}"

        # Search for file in multiple locations
        search_paths = [
            # Primary storage
            Path("storage") / filename,
            # Temp directory (used by streaming endpoint)
            Path(tempfile.gettempdir()) / "musicai" / piece_id / filename,
        ]

        file_path = None
        for path in search_paths:
            if path.exists():
                file_path = path
                logger.info(f"Found file at: {path}")
                break

        if not file_path:
            logger.warning(f"File not found in any location: {filename}")
            logger.warning(f"Searched: {[str(p) for p in search_paths]}")
            raise HTTPException(status_code=404, detail=f"File not found: {piece_id}.{format}")

        return FileResponse(
            path=str(file_path),
            media_type=config['media_type'],
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
