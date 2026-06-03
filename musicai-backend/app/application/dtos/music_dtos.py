"""Data Transfer Objects for Music API."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ==================== Generation DTOs ====================

class MusicGenerationRequest(BaseModel):
    """Request for music generation."""

    prompt: str = Field(..., min_length=1, max_length=500, description="Text description of the music to generate")
    duration: int = Field(default=30, ge=5, le=60, description="Duration in seconds")
    temperature: float = Field(default=1.0, ge=0.1, le=2.0, description="Sampling temperature")
    guidance_scale: float = Field(default=3.0, ge=1.0, le=15.0, description="Classifier-free guidance scale")

    # Optional metadata
    title: Optional[str] = Field(None, max_length=200, description="Title for the piece")
    project_id: Optional[str] = Field(None, description="Associated project ID")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A calm piano melody in C major",
                "duration": 30,
                "temperature": 1.0,
                "guidance_scale": 3.0,
                "title": "Peaceful Piano",
                "tags": ["piano", "calm", "ambient"]
            }
        }


class MusicGenerationResponse(BaseModel):
    """Response from music generation."""

    job_id: str = Field(..., description="Job ID for tracking generation progress")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "gen_123456789",
                "status": "pending",
                "message": "Music generation job created successfully"
            }
        }


class JobStatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    message: str

    # Available when completed
    piece_id: Optional[str] = None
    audio_url: Optional[str] = None
    midi_url: Optional[str] = None
    musicxml_url: Optional[str] = None

    # Error info if failed
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "gen_123456789",
                "status": "completed",
                "progress": 100,
                "message": "Generation completed successfully",
                "piece_id": "piece_987654321",
                "audio_url": "/api/v1/music/download/piece_987654321/audio",
                "midi_url": "/api/v1/music/download/piece_987654321/midi"
            }
        }


# ==================== Analysis DTOs ====================

class MusicAnalysisRequest(BaseModel):
    """Request for music analysis."""

    # Can be file upload or existing piece ID
    piece_id: Optional[str] = Field(None, description="Existing piece ID to analyze")

    # Analysis options
    include_chords: bool = Field(default=True, description="Include chord analysis")
    include_key: bool = Field(default=True, description="Include key detection")
    include_tempo: bool = Field(default=True, description="Include tempo detection")
    generate_explanation: bool = Field(default=False, description="Generate natural language explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "piece_id": "piece_987654321",
                "include_chords": True,
                "include_key": True,
                "include_tempo": True,
                "generate_explanation": True
            }
        }


class MusicAnalysisResponse(BaseModel):
    """Response from music analysis."""

    piece_id: str
    analysis: Dict[str, Any] = Field(..., description="Analysis results")
    explanation: Optional[str] = Field(None, description="Natural language explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "piece_id": "piece_987654321",
                "analysis": {
                    "key": "C major",
                    "tempo": 120,
                    "time_signature": "4/4",
                    "duration": 30.0,
                    "chords": ["C", "G", "Am", "F"],
                    "note_count": 150
                },
                "explanation": "This piece is in C major with a moderate tempo of 120 BPM..."
            }
        }


# ==================== Transformation DTOs ====================

class TransformationRequest(BaseModel):
    """Request for music transformation."""

    piece_id: str = Field(..., description="Piece ID to transform")
    transformation_type: str = Field(..., description="Type: transpose, augment, change_tempo")

    # Transformation parameters
    semitones: Optional[int] = Field(None, description="Semitones for transpose (can be negative)")
    factor: Optional[float] = Field(None, description="Factor for augment")
    tempo: Optional[int] = Field(None, ge=20, le=300, description="New tempo in BPM")

    # Metadata for new piece
    title: Optional[str] = None
    save_as_new: bool = Field(default=True, description="Save as new piece or update existing")

    class Config:
        json_schema_extra = {
            "example": {
                "piece_id": "piece_987654321",
                "transformation_type": "transpose",
                "semitones": 2,
                "title": "Transposed Version",
                "save_as_new": True
            }
        }


class TransformationResponse(BaseModel):
    """Response from transformation."""

    original_piece_id: str
    new_piece_id: str
    transformation_applied: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "original_piece_id": "piece_987654321",
                "new_piece_id": "piece_111222333",
                "transformation_applied": "transpose +2 semitones",
                "message": "Transformation completed successfully"
            }
        }


# ==================== Piece DTOs ====================

class MusicalPieceResponse(BaseModel):
    """Response with musical piece details."""

    id: str
    title: str
    description: Optional[str] = None

    # URLs for downloads
    audio_url: Optional[str] = None
    midi_url: Optional[str] = None
    musicxml_url: Optional[str] = None
    abc_url: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "piece_987654321",
                "title": "Peaceful Piano",
                "description": "A calm piano melody",
                "audio_url": "/api/v1/music/download/piece_987654321/audio",
                "midi_url": "/api/v1/music/download/piece_987654321/midi",
                "metadata": {
                    "key": "C major",
                    "tempo": 120,
                    "duration": 30.0
                },
                "tags": ["piano", "calm"],
                "created_at": "2025-11-01T23:00:00Z",
                "updated_at": "2025-11-01T23:00:00Z"
            }
        }


class PieceListResponse(BaseModel):
    """Response with list of pieces."""

    pieces: List[MusicalPieceResponse]
    total: int
    page: int = 1
    page_size: int = 20

    class Config:
        json_schema_extra = {
            "example": {
                "pieces": [],
                "total": 42,
                "page": 1,
                "page_size": 20
            }
        }


# ==================== Chat DTOs ====================

class ChatRequest(BaseModel):
    """Request for conversational chat with optional music generation."""

    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages for context"
    )
    session_id: Optional[str] = Field(None, description="Session ID for context tracking")
    score_id: Optional[str] = Field(None, description="Score ID for uploaded file context")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "¿Qué es una escala menor armónica?",
                "conversation_history": [
                    {"role": "user", "content": "Hola"},
                    {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"}
                ],
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class PatternData(BaseModel):
    """Data for a musical pattern to be generated."""

    pattern_type: str = Field(..., description="Type: scale, chord, arpeggio")
    tonic: Optional[str] = Field(None, description="Root note (e.g., C, D, F#)")
    scale_type: Optional[str] = Field(None, description="Scale type (major, minor, etc.)")
    chord_symbols: Optional[List[str]] = Field(None, description="Chord symbols")
    chord_type: Optional[str] = Field(None, description="Chord type (major, minor, etc.)")
    octaves: int = Field(default=1, description="Number of octaves")
    tempo: int = Field(default=120, description="Tempo in BPM")
    duration: float = Field(default=1.0, description="Duration per note")


class ChatResponse(BaseModel):
    """Response from chat endpoint with optional music generation."""

    type: str = Field(..., description="Response type: text, music, hybrid")
    content: Optional[str] = Field(None, description="Text content/explanation")
    job_id: Optional[str] = Field(None, description="Job ID if music is being generated")
    patterns: List[PatternData] = Field(
        default_factory=list,
        description="Patterns to be generated for visualization"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "hybrid",
                "content": "La escala menor armónica es una variación de la escala menor...",
                "job_id": "pat_123456789",
                "patterns": [{
                    "pattern_type": "scale",
                    "tonic": "A",
                    "scale_type": "harmonic minor",
                    "octaves": 1,
                    "tempo": 120
                }]
            }
        }


# ==================== Comparison DTOs ====================

class ComparisonRequest(BaseModel):
    """Request for comparing two musical concepts side by side."""

    concept1: PatternData = Field(..., description="First concept to compare")
    concept2: PatternData = Field(..., description="Second concept to compare")
    highlight_differences: bool = Field(default=True, description="Highlight differences in visualization")
    session_id: Optional[str] = Field(None, description="Session ID for context tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "concept1": {
                    "pattern_type": "scale",
                    "tonic": "A",
                    "scale_type": "pentatonic_major",
                    "octaves": 1,
                    "tempo": 120
                },
                "concept2": {
                    "pattern_type": "scale",
                    "tonic": "A",
                    "scale_type": "pentatonic_minor",
                    "octaves": 1,
                    "tempo": 120
                },
                "highlight_differences": True,
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ComparisonResponse(BaseModel):
    """Response from comparison endpoint."""

    job_id: str = Field(..., description="Job ID for the comparison visualization")
    concept1_piece_id: str = Field(..., description="Piece ID for first concept")
    concept2_piece_id: str = Field(..., description="Piece ID for second concept")
    differences: List[str] = Field(default_factory=list, description="List of differences between concepts")
    explanation: str = Field(..., description="Educational explanation of the comparison")

    # URLs for downloads
    concept1_musicxml_url: str
    concept2_musicxml_url: str
    concept1_audio_url: Optional[str] = None
    concept2_audio_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "cmp_123456789",
                "concept1_piece_id": "piece_111",
                "concept2_piece_id": "piece_222",
                "differences": [
                    "La pentatónica mayor tiene C# mientras que la menor tiene C natural",
                    "La pentatónica menor tiene un sonido más oscuro"
                ],
                "explanation": "Las escalas pentatónicas mayor y menor de La difieren en...",
                "concept1_musicxml_url": "/api/v1/music/download/piece_111/musicxml",
                "concept2_musicxml_url": "/api/v1/music/download/piece_222/musicxml"
            }
        }


# ==================== Process (Unified Input) DTOs ====================

class ProcessRequest(BaseModel):
    """Request for unified message processing."""

    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages for context"
    )
    session_id: Optional[str] = Field(None, description="Session ID for context tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "escala de la menor",
                "conversation_history": [],
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ProcessPatternData(BaseModel):
    """Pattern data returned from process endpoint."""

    pattern_type: str = Field(..., description="Type: scale, chord, arpeggio")
    tonic: Optional[str] = Field(None, description="Root note")
    scale_type: Optional[str] = Field(None, description="Scale type")
    chord_type: Optional[str] = Field(None, description="Chord type")
    chord_symbols: Optional[str] = Field(None, description="Chord symbols (comma separated)")
    octaves: int = Field(default=1)
    tempo: int = Field(default=120)
    duration: float = Field(default=1.0)
    clef: str = Field(default='treble')


class ProcessResponse(BaseModel):
    """Response from unified process endpoint."""

    intent: str = Field(..., description="Detected intent: pattern, theory, validation, creative, chat")
    should_stream: bool = Field(default=False, description="Whether to use streaming endpoint")
    pattern_data: Optional[ProcessPatternData] = Field(None, description="Pattern data if intent is pattern")
    confidence: float = Field(default=1.0, description="Confidence in intent detection")
    detected_keywords: List[str] = Field(default_factory=list, description="Keywords that triggered detection")

    class Config:
        json_schema_extra = {
            "example": {
                "intent": "pattern",
                "should_stream": False,
                "pattern_data": {
                    "pattern_type": "scale",
                    "tonic": "A",
                    "scale_type": "minor",
                    "octaves": 1,
                    "tempo": 120,
                    "duration": 1.0,
                    "clef": "treble"
                },
                "confidence": 0.95,
                "detected_keywords": ["pattern_request"]
            }
        }


# ==================== Error Response ====================

class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Generation failed",
                "detail": "Model loading error",
                "status_code": 500
            }
        }
