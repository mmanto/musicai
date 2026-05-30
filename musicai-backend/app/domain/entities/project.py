"""Project entity - Container for musical pieces."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Project(BaseModel):
    """
    Project entity for organizing musical pieces.

    Similar to Feathrai's project model, this groups related
    musical pieces together.
    """

    id: Optional[str] = None
    user_id: str

    # Basic info
    name: str
    description: Optional[str] = None

    # Settings
    default_tempo: Optional[int] = 120
    default_key: Optional[str] = None
    default_time_signature: str = "4/4"

    # Organization
    tags: List[str] = Field(default_factory=list)
    color: Optional[str] = None  # Hex color for UI

    # Status
    is_archived: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "name": "Album Recordings 2024",
                "description": "Collection of compositions for upcoming album",
                "default_tempo": 120,
                "default_key": "C major",
                "tags": ["album", "2024"]
            }
        }
