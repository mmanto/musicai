"""Musical piece entity - Core domain model."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MusicalMetadata(BaseModel):
    """Metadata extracted from musical piece."""

    key: Optional[str] = None  # e.g., "C major", "Bb minor"
    tempo: Optional[int] = None  # BPM
    time_signature: Optional[str] = None  # e.g., "4/4", "3/4"
    duration: Optional[float] = None  # in seconds
    chords: Optional[List[str]] = None  # Chord progression
    instruments: Optional[List[str]] = None
    mood: Optional[str] = None  # e.g., "calm", "energetic"
    energy: Optional[float] = None  # 0.0 to 1.0
    style: Optional[str] = None  # e.g., "jazz", "classical"


class MusicalPiece(BaseModel):
    """
    Core entity representing a musical piece.

    This is the central domain model that uses music21.stream.Stream
    as the internal representation format.
    """

    id: Optional[str] = None
    user_id: str
    project_id: Optional[str] = None

    # Content
    title: str
    description: Optional[str] = None

    # music21 representation (stored as JSON via freezeThaw)
    music21_json: Optional[str] = None  # Serialized music21.stream.Stream

    # File references
    audio_url: Optional[str] = None  # S3/local storage URL
    midi_url: Optional[str] = None
    musicxml_url: Optional[str] = None

    # Metadata
    metadata: MusicalMetadata = Field(default_factory=MusicalMetadata)

    # Generation info
    prompt: Optional[str] = None  # Original text prompt
    generation_params: Optional[Dict[str, Any]] = None

    # Organization
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Versioning
    version: int = 1
    parent_id: Optional[str] = None  # For variations

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "title": "Relaxing Jazz Piano",
                "description": "A calm jazz piano piece in Bb major",
                "prompt": "Create a relaxing jazz piano piece in Bb major",
                "metadata": {
                    "key": "Bb major",
                    "tempo": 70,
                    "time_signature": "4/4",
                    "duration": 30.0,
                    "style": "jazz"
                },
                "tags": ["jazz", "piano", "relaxing"]
            }
        }
