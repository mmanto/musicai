"""
Conversation context models for maintaining musical dialogue state.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MusicalConcept(BaseModel):
    """Represents a musical concept shown to the user."""
    concept_type: str = Field(..., description="Type: scale, chord, arpeggio, progression")
    tonic: Optional[str] = Field(None, description="Root note (C, D, E, etc.)")
    scale_type: Optional[str] = Field(None, description="Scale type: major, minor, pentatonic_major, etc.")
    chord_type: Optional[str] = Field(None, description="Chord type: major, minor, dim, aug, etc.")
    chord_symbols: Optional[List[str]] = Field(None, description="List of chord symbols for progressions")
    octaves: Optional[int] = Field(None, description="Number of octaves")
    direction: Optional[str] = Field(None, description="Direction: ascending, descending, both")
    clef: Optional[str] = Field(None, description="Clef: treble or bass")
    visualization_id: Optional[str] = Field(None, description="piece_id of generated visualization")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    description: str = Field(..., description="Human-readable description (e.g., 'escala pentatónica de la menor')")

    def to_natural_language(self) -> str:
        """Convert concept to natural language for LLM context."""
        if self.concept_type == "scale":
            scale_name = self.scale_type.replace("_", " ")
            return f"escala {scale_name} de {self.tonic}"
        elif self.concept_type == "chord":
            return f"acorde {self.chord_type} de {self.tonic}"
        elif self.concept_type == "arpeggio":
            return f"arpegio {self.chord_type} de {self.tonic}"
        elif self.concept_type == "progression":
            chords_str = ", ".join(self.chord_symbols or [])
            return f"progresión de acordes: {chords_str}"
        return self.description


class UserKnowledgeProfile(BaseModel):
    """Tracks user's apparent knowledge level and learning history."""
    inferred_level: str = Field(default="beginner", description="beginner, intermediate, advanced")
    concepts_explained: List[str] = Field(default_factory=list, description="Concepts already explained")
    common_errors: List[str] = Field(default_factory=list, description="Common mistakes made by user")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ConversationContext(BaseModel):
    """
    Maintains structured context of musical conversation.
    Tracks what was shown/discussed to handle references like "esa escala".
    """
    session_id: str = Field(..., description="Unique session identifier")

    # Last concepts shown
    last_scale: Optional[MusicalConcept] = Field(None, description="Last scale visualization")
    last_chord: Optional[MusicalConcept] = Field(None, description="Last chord visualization")
    last_arpeggio: Optional[MusicalConcept] = Field(None, description="Last arpeggio visualization")
    last_progression: Optional[MusicalConcept] = Field(None, description="Last chord progression")

    # General history
    concept_history: List[MusicalConcept] = Field(default_factory=list, description="All concepts shown (max 20)")

    # User profile
    user_profile: UserKnowledgeProfile = Field(default_factory=UserKnowledgeProfile)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)

    def add_concept(self, concept: MusicalConcept) -> None:
        """Add a concept to context, updating appropriate fields."""
        # Update specific last_X field
        if concept.concept_type == "scale":
            self.last_scale = concept
        elif concept.concept_type == "chord":
            self.last_chord = concept
        elif concept.concept_type == "arpeggio":
            self.last_arpeggio = concept
        elif concept.concept_type == "progression":
            self.last_progression = concept

        # Add to history (keep last 20)
        self.concept_history.append(concept)
        if len(self.concept_history) > 20:
            self.concept_history = self.concept_history[-20:]

        self.last_interaction = datetime.utcnow()

    def get_last_concept(self) -> Optional[MusicalConcept]:
        """Get the most recently shown concept regardless of type."""
        candidates = [
            self.last_scale,
            self.last_chord,
            self.last_arpeggio,
            self.last_progression
        ]
        candidates = [c for c in candidates if c is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.timestamp)

    def get_context_summary(self) -> str:
        """
        Generate a summary of current context for LLM.
        Used to provide context about what was previously shown.
        """
        summary_parts = []

        last = self.get_last_concept()
        if last:
            summary_parts.append(f"Última visualización mostrada: {last.to_natural_language()}")

        if self.last_scale:
            summary_parts.append(f"Última escala: {self.last_scale.to_natural_language()}")

        if self.last_chord:
            summary_parts.append(f"Último acorde: {self.last_chord.to_natural_language()}")

        if self.concept_history:
            recent_concepts = [c.to_natural_language() for c in self.concept_history[-3:]]
            summary_parts.append(f"Conceptos recientes: {', '.join(recent_concepts)}")

        if self.user_profile.concepts_explained:
            explained = ", ".join(self.user_profile.concepts_explained[-5:])
            summary_parts.append(f"Conceptos ya explicados: {explained}")

        return "\n".join(summary_parts) if summary_parts else "No hay contexto previo."

    def mark_concept_explained(self, concept_name: str) -> None:
        """Mark a concept as having been explained to the user."""
        if concept_name not in self.user_profile.concepts_explained:
            self.user_profile.concepts_explained.append(concept_name)
        self.user_profile.last_updated = datetime.utcnow()

    def record_user_error(self, error_description: str) -> None:
        """Record a common error made by the user for learning adaptation."""
        self.user_profile.common_errors.append(error_description)
        if len(self.user_profile.common_errors) > 10:
            self.user_profile.common_errors = self.user_profile.common_errors[-10:]
        self.user_profile.last_updated = datetime.utcnow()


class ContextStore:
    """
    Simple in-memory store for conversation contexts.
    In production, this should be backed by Redis or a database.
    """
    def __init__(self):
        self._store: Dict[str, ConversationContext] = {}

    def get_or_create(self, session_id: str) -> ConversationContext:
        """Get existing context or create new one."""
        if session_id not in self._store:
            self._store[session_id] = ConversationContext(session_id=session_id)
        return self._store[session_id]

    def save(self, context: ConversationContext) -> None:
        """Save context (for in-memory, this is a no-op, but useful for DB implementations)."""
        self._store[context.session_id] = context

    def clear(self, session_id: str) -> None:
        """Clear context for a session."""
        if session_id in self._store:
            del self._store[session_id]


# Global context store instance
context_store = ContextStore()
