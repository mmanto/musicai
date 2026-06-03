"""
Score Upload API Routes.

Handles uploading music files (MusicXML or MIDI exported from GP via AlphaTab),
running music21 analysis, and linking scores to chat sessions.
"""

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.models.score_store import ScoreAnalysis, score_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/music/score", tags=["score"])


def get_music21():
    from app.main import music21_service
    return music21_service


# ── DTOs ────────────────────────────────────────────────────────────────────────

class LinkSessionRequest(BaseModel):
    session_id: str
    score_id: str


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _parse_json_field(raw: Optional[str], label: str) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        logger.warning(f"Could not parse {label}: {raw[:100]}")
        return []


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    summary="Upload and analyse a music score",
    description=(
        "Accepts a MusicXML file or a MIDI file (exported from Guitar Pro via AlphaTab). "
        "Runs music21 analysis and stores the result in the in-memory ScoreStore. "
        "Returns 200 with full analysis or 206 if only metadata is available."
    ),
)
async def upload_score(
    file: UploadFile = File(..., description="MusicXML (.xml/.musicxml) or MIDI (.mid) file"),
    file_name: str = Form(..., description="Original display name (e.g. 'song.gp5')"),
    file_type: str = Form(..., description="'xml' or 'gp'"),
    tracks_json: Optional[str] = Form(None, description="JSON array of track objects (GP only)"),
    sections_json: Optional[str] = Form(None, description="JSON array of section objects (GP only)"),
    music21=Depends(get_music21),
):
    score_id = f"score_{uuid.uuid4().hex[:12]}"
    content = await file.read()
    fname_lower = (file.filename or "").lower()

    tracks = _parse_json_field(tracks_json, "tracks_json")
    sections = _parse_json_field(sections_json, "sections_json")

    # ── Attempt music21 analysis ──────────────────────────────────────────────
    analysis: dict = {}
    score_meta: dict = {}
    stream_obj = None
    parse_ok = False

    GP_EXTENSIONS = (".gp", ".gp3", ".gp4", ".gp5", ".gpx")

    try:
        if fname_lower.endswith((".mid", ".midi")):
            stream_obj = music21.from_midi_bytes(bytes(content))
        elif fname_lower.endswith((".xml", ".musicxml")) or file_type == "xml":
            stream_obj = music21.from_musicxml(content.decode("utf-8", errors="replace"))
        elif fname_lower.endswith(GP_EXTENSIONS):
            ext = "." + fname_lower.rsplit(".", 1)[-1]
            stream_obj = music21.from_gp_bytes(bytes(content), file_ext=ext)
        elif file_type == "gp":
            stream_obj = music21.from_midi_bytes(bytes(content))
        else:
            try:
                stream_obj = music21.from_midi_bytes(bytes(content))
            except Exception:
                stream_obj = music21.from_musicxml(content.decode("utf-8", errors="replace"))

        analysis = music21.analyze(stream_obj)
        score_meta = music21.extract_score_metadata(stream_obj)
        parse_ok = True
        logger.info(f"music21 analysis succeeded for {file_name}: {list(analysis.keys())} meta={list(score_meta.keys())}")

    except Exception as exc:
        # If MIDI parse failed for a GP file, retry with native GP parser
        if file_type == "gp" and not parse_ok:
            try:
                ext_guess = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ".gp5"
                if ext_guess not in GP_EXTENSIONS:
                    ext_guess = ".gp5"
                stream_obj = music21.from_gp_bytes(bytes(content), file_ext=ext_guess)
                analysis = music21.analyze(stream_obj)
                score_meta = music21.extract_score_metadata(stream_obj)
                parse_ok = True
                logger.info(f"GP native parse succeeded on retry for {file_name}")
            except Exception as gp_exc:
                logger.warning(f"GP native parse also failed for {file_name}: {gp_exc}")
        else:
            logger.warning(f"music21 analysis failed for {file_name}: {exc}")

    # ── Build ScoreAnalysis ───────────────────────────────────────────────────
    score = ScoreAnalysis(
        score_id=score_id,
        file_name=file_name,
        file_type=file_type,
        key=analysis.get("key"),
        tempo=analysis.get("tempo"),
        time_signature=analysis.get("time_signature"),
        note_count=analysis.get("note_count"),
        chords=analysis.get("chords", []),
        pitch_range=analysis.get("pitch_range"),
        title=score_meta.get("title"),
        composer=score_meta.get("composer"),
        instruments=score_meta.get("instruments", []),
        measure_count=score_meta.get("measure_count"),
        tracks=tracks,
        sections=sections,
    )
    score_store.save(score)

    # Index in RAG so future chats can retrieve this score semantically
    try:
        from app.infrastructure.knowledge.rag_service import get_rag_service
        get_rag_service().add_score(score)
    except Exception as rag_err:
        logger.warning(f"RAG indexing failed for score {score_id} (non-fatal): {rag_err}")

    logger.info(f"Stored score {score_id} for '{file_name}' (parse_ok={parse_ok})")

    response_body = {
        "score_id": score_id,
        "analysis": analysis,
        "context_summary": score.context_summary,
    }

    status_code = 200 if parse_ok else 206
    return JSONResponse(content=response_body, status_code=status_code)


@router.get(
    "/{score_id}",
    summary="Get stored score analysis",
    description="Returns the stored ScoreAnalysis. Useful for validating the score is still in memory after a backend restart.",
)
async def get_score(score_id: str):
    score = score_store.get(score_id)
    if not score:
        raise HTTPException(status_code=404, detail=f"Score '{score_id}' not found")
    return {
        "score_id": score.score_id,
        "file_name": score.file_name,
        "file_type": score.file_type,
        "key": score.key,
        "tempo": score.tempo,
        "time_signature": score.time_signature,
        "note_count": score.note_count,
        "chords": score.chords,
        "pitch_range": score.pitch_range,
        "tracks": score.tracks,
        "sections": score.sections,
        "context_summary": score.context_summary,
    }


@router.post(
    "/link-session",
    summary="Link a score to a chat session",
    description="Associates a score_id with a session_id so the chat endpoint can look up score context using only the session_id.",
)
async def link_session(request: LinkSessionRequest):
    ok = score_store.link_to_session(request.session_id, request.score_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Score '{request.score_id}' not found")
    logger.info(f"Linked score {request.score_id} to session {request.session_id}")
    return {"ok": True}
