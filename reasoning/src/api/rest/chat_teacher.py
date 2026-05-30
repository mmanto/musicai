"""
Chat teacher endpoint for educational musical conversations with visualization.

This endpoint provides an educational chat interface that can:
1. Answer music theory questions
2. Generate musical visualizations (scales, chords, arpeggios)
3. Provide hybrid responses (text + sheet music)
4. Track conversational context
"""

import logging
import base64
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ...learning.correction_store import (
    CorrectionStore, Correction, get_correction_store
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-teacher", tags=["chat-teacher"])

# Global instances (will be initialized in main.py)
music_analyzer = None
llm_client = None
pattern_parser = None
correction_store: Optional[CorrectionStore] = None


class ConversationMessage(BaseModel):
    """A message in the conversation history."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatTeacherRequest(BaseModel):
    """Request for chat teacher endpoint."""
    message: str = Field(..., description="User's message")
    conversation_history: List[ConversationMessage] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    session_id: Optional[str] = Field(None, description="Session ID for context tracking")
    session_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Current session context (last concepts shown)"
    )


class ConceptVisualization(BaseModel):
    """Musical concept visualization data."""
    pattern_type: str = Field(..., description="Type of pattern (scale/chord/arpeggio)")
    tonic: Optional[str] = Field(None, description="Root note")
    scale_type: Optional[str] = Field(None, description="Scale type (for scales)")
    chord_symbols: Optional[List[str]] = Field(None, description="Chord symbols (for chords)")
    direction: Optional[str] = Field(None, description="Direction (for arpeggios)")
    musicxml_b64: str = Field(..., description="MusicXML content (base64 encoded)")
    midi_b64: str = Field(..., description="MIDI content (base64 encoded)")
    description: str = Field(..., description="Human-readable description")


class ChatTeacherResponse(BaseModel):
    """Response from chat teacher."""
    type: str = Field(..., description="Response type: 'text' or 'hybrid'")
    explanation: str = Field(..., description="Educational explanation text")
    visualization: Optional[ConceptVisualization] = Field(
        None,
        description="Musical visualization (if hybrid response)"
    )
    context_update: Dict[str, Any] = Field(
        default_factory=dict,
        description="Updated session context"
    )


class CorrectionRequest(BaseModel):
    """Request to submit a correction."""
    session_id: str = Field(..., description="Session ID")
    original_response: str = Field(..., description="The original response that was incorrect")
    user_correction: str = Field(..., description="The user's correction")
    concept_type: str = Field(default="general", description="Type of concept (scale, chord, etc.)")
    concept_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details about the concept (tonic, scale_type, etc.)"
    )


class CorrectionResponse(BaseModel):
    """Response after submitting a correction."""
    success: bool
    correction_id: str
    message: str


def init_components(analyzer, llm, parser):
    """Initialize global components."""
    global music_analyzer, llm_client, pattern_parser, correction_store
    music_analyzer = analyzer
    llm_client = llm
    pattern_parser = parser
    correction_store = get_correction_store()
    logger.info("Chat teacher components initialized (with correction store)")


@router.post("", response_model=ChatTeacherResponse)
async def chat_teacher(request: ChatTeacherRequest):
    """
    Educational chat endpoint with music visualization.

    This endpoint:
    1. Analyzes the user's message to detect intent
    2. Generates educational explanations using LLM
    3. Extracts musical concepts for visualization
    4. Generates sheet music when concepts are detected
    5. Returns hybrid responses (text + visualization)

    Args:
        request: Chat request with message and history

    Returns:
        ChatTeacherResponse with explanation and optional visualization
    """
    try:
        logger.info(f"Chat teacher request: {request.message[:100]}")

        # Check if components are initialized
        if music_analyzer is None or llm_client is None or pattern_parser is None:
            raise HTTPException(
                status_code=500,
                detail="Chat teacher components not initialized"
            )

        # 1. Parse musical patterns from the message
        concepts = pattern_parser.extract_concepts_for_visualization(request.message)

        logger.info(f"Extracted {len(concepts)} concepts from message")

        # 2. Generate educational explanation with LLM
        explanation = await _generate_explanation(
            message=request.message,
            history=request.conversation_history,
            context=request.session_context,
            concepts=concepts
        )

        # 3. If concepts found, generate visualization
        visualization = None
        context_update = {}

        if concepts:
            # Take the first concept for visualization
            concept = concepts[0]
            logger.info(f"Generating visualization for concept: {concept}")

            try:
                visualization = await _generate_visualization(concept)

                # Update context
                context_update = {
                    "last_concept": {
                        "type": concept.get("type"),
                        "tonic": concept.get("tonic"),
                        "scale_type": concept.get("scale_type"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            except Exception as e:
                logger.error(f"Error generating visualization: {e}")
                # Continue without visualization if it fails

        # 4. Determine response type
        response_type = "hybrid" if visualization else "text"

        logger.info(f"Returning {response_type} response")

        return ChatTeacherResponse(
            type=response_type,
            explanation=explanation,
            visualization=visualization,
            context_update=context_update
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat teacher endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def _generate_explanation(
    message: str,
    history: List[ConversationMessage],
    context: Optional[Dict[str, Any]],
    concepts: List[Dict[str, Any]]
) -> str:
    """
    Generate educational explanation using LLM.

    Args:
        message: User's message
        history: Conversation history
        context: Session context
        concepts: Detected musical concepts

    Returns:
        Educational explanation text
    """
    try:
        # Build messages for LLM
        from ...neural.llm_client import Message

        messages = []

        # Get relevant corrections to include in context
        corrections_context = ""
        if correction_store:
            # Try to get concept-specific corrections first
            concept_type = None
            if concepts:
                concept_type = concepts[0].get("type")

            corrections_context = correction_store.format_corrections_for_prompt(
                concept_type=concept_type,
                limit=5
            )

        # System prompt
        system_prompt = f"""Eres un profesor de teoría musical experto y amigable.

Tu objetivo es enseñar conceptos musicales de forma clara, concisa y educativa.

Características de tus respuestas:
- Claras y concisas (2-4 párrafos máximo)
- Educativas y pedagógicas
- Incluyen ejemplos cuando es relevante
- Usan terminología correcta pero accesible
- En español
- Evitas ser demasiado técnico a menos que se te pida

Si el usuario pregunta sobre un concepto específico (escala, acorde, intervalo, etc.):
1. Define el concepto brevemente
2. Explica sus características principales
3. Da un ejemplo práctico si aplica
4. Menciona su uso en la música

Si el usuario pide que le muestres algo, indica que lo estás generando.
{corrections_context}"""

        messages.append(Message(role="system", content=system_prompt))

        # Add conversation history
        for msg in history[-6:]:  # Last 6 messages for context
            messages.append(Message(
                role=msg.role,
                content=msg.content
            ))

        # Add context information if available
        if context and context.get("last_concept"):
            last_concept = context["last_concept"]
            context_note = f"\n\n[Contexto: El usuario vio recientemente: {last_concept.get('type')} de {last_concept.get('tonic')} {last_concept.get('scale_type', '')}]"

            # Append context to the last user message or create new one
            if messages and messages[-1].role == "user":
                messages[-1].content += context_note
            else:
                messages.append(Message(role="system", content=context_note))

        # Add current message
        messages.append(Message(role="user", content=message))

        # Get response from LLM
        response = await llm_client.chat(messages, temperature=0.7, max_tokens=500)

        return response.content

    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        # Fallback response
        if concepts:
            concept = concepts[0]
            return f"Generando visualización para: {concept.get('type')} de {concept.get('tonic')} {concept.get('scale_type', '')}"
        return "Lo siento, hubo un error al generar la explicación. Por favor intenta de nuevo."


async def _generate_visualization(concept: Dict[str, Any]) -> ConceptVisualization:
    """
    Generate music21 visualization for a musical concept.

    Args:
        concept: Musical concept to visualize

    Returns:
        ConceptVisualization with MusicXML and MIDI data

    Raises:
        ValueError: If concept type is not supported
    """
    try:
        pattern_type = concept.get("type")

        if pattern_type == "scale":
            score = music_analyzer.create_scale(
                tonic=concept.get("tonic", "C"),
                scale_type=concept.get("scale_type", "major"),
                octaves=1,
                duration_per_note=1.0,
                tempo_bpm=120,
                clef_type=concept.get("clef", "treble")
            )

            description = f"Escala de {concept.get('tonic')} {concept.get('scale_type')}"

        elif pattern_type == "chord":
            chord_symbol = concept.get("symbol")
            if chord_symbol:
                score = music_analyzer.create_chord_progression(
                    chord_symbols=[chord_symbol],
                    duration_per_chord=2.0,
                    tempo_bpm=120,
                    clef_type=concept.get("clef", "treble")
                )
                description = f"Acorde {chord_symbol}"
            else:
                raise ValueError("Chord symbol not provided")

        elif pattern_type == "chord_progression":
            symbols = concept.get("symbols", [])
            if symbols:
                score = music_analyzer.create_chord_progression(
                    chord_symbols=symbols,
                    duration_per_chord=2.0,
                    tempo_bpm=120,
                    clef_type=concept.get("clef", "treble")
                )
                description = f"Progresión: {' - '.join(symbols)}"
            else:
                raise ValueError("Chord symbols not provided")

        elif pattern_type == "arpeggio":
            score = music_analyzer.create_arpeggio(
                tonic=concept.get("tonic", "C"),
                chord_type=concept.get("chord_type", "major"),
                direction=concept.get("direction", "ascending"),
                octaves=1,
                duration_per_note=0.5,
                tempo_bpm=120,
                clef_type=concept.get("clef", "treble")
            )

            direction_es = "ascendente" if concept.get("direction") == "ascending" else "descendente"
            description = f"Arpegio {direction_es} de {concept.get('tonic')} {concept.get('chord_type')}"

        else:
            raise ValueError(f"Unsupported concept type: {pattern_type}")

        # Convert to MusicXML and MIDI
        musicxml_str = music_analyzer.to_musicxml(score)
        midi_bytes = music_analyzer.to_midi_bytes(score)

        # Encode to base64
        musicxml_b64 = base64.b64encode(musicxml_str.encode('utf-8')).decode('utf-8')
        midi_b64 = base64.b64encode(midi_bytes).decode('utf-8')

        logger.info(f"Successfully generated visualization: {description}")

        return ConceptVisualization(
            pattern_type=pattern_type,
            tonic=concept.get("tonic"),
            scale_type=concept.get("scale_type"),
            chord_symbols=concept.get("symbols"),
            direction=concept.get("direction"),
            musicxml_b64=musicxml_b64,
            midi_b64=midi_b64,
            description=description
        )

    except Exception as e:
        logger.error(f"Error generating visualization: {e}", exc_info=True)
        raise


@router.get("/health")
async def health_check():
    """Health check endpoint for chat teacher service."""
    return {
        "status": "healthy",
        "components": {
            "music_analyzer": music_analyzer is not None,
            "llm_client": llm_client is not None,
            "pattern_parser": pattern_parser is not None,
            "correction_store": correction_store is not None
        }
    }


@router.post("/correction", response_model=CorrectionResponse)
async def submit_correction(request: CorrectionRequest):
    """
    Submit a user correction.

    This endpoint stores corrections that the system can learn from.
    Corrections are used to improve future responses.

    Args:
        request: The correction details

    Returns:
        CorrectionResponse with success status
    """
    try:
        if correction_store is None:
            raise HTTPException(
                status_code=503,
                detail="Correction store not initialized"
            )

        correction_id = str(uuid.uuid4())

        correction = Correction(
            id=correction_id,
            session_id=request.session_id,
            original_response=request.original_response,
            user_correction=request.user_correction,
            concept_type=request.concept_type,
            concept_details=request.concept_details,
            timestamp=datetime.utcnow().isoformat(),
            applied_count=0
        )

        success = correction_store.add_correction(correction)

        if success:
            logger.info(f"Stored correction {correction_id} from session {request.session_id}")
            return CorrectionResponse(
                success=True,
                correction_id=correction_id,
                message="Corrección guardada. Gracias por ayudarme a mejorar."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to store correction"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing correction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corrections")
async def get_corrections(
    session_id: Optional[str] = None,
    concept_type: Optional[str] = None,
    limit: int = 20
):
    """
    Get stored corrections.

    Args:
        session_id: Filter by session (optional)
        concept_type: Filter by concept type (optional)
        limit: Maximum number to return

    Returns:
        List of corrections
    """
    try:
        if correction_store is None:
            return {"corrections": [], "count": 0}

        if session_id:
            corrections = correction_store.get_corrections_for_session(session_id)
        elif concept_type:
            corrections = correction_store.get_corrections_for_concept(concept_type, limit)
        else:
            corrections = correction_store.get_all_corrections(limit)

        return {
            "corrections": [c.to_dict() for c in corrections],
            "count": len(corrections)
        }

    except Exception as e:
        logger.error(f"Error getting corrections: {e}")
        return {"corrections": [], "count": 0, "error": str(e)}
