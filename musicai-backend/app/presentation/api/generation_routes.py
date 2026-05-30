"""
Music Generation API Routes.

Handles music generation requests and job status tracking.
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.application.dtos import (
    MusicGenerationRequest,
    MusicGenerationResponse,
    JobStatusResponse,
    ErrorResponse,
    ChatRequest,
    ChatResponse,
    PatternData,
    ComparisonRequest,
    ComparisonResponse,
    ProcessRequest,
    ProcessResponse,
    ProcessPatternData,
)

from app.domain.models.conversation_context import (
    context_store,
    MusicalConcept,
    ConversationContext
)
from app.domain.services.music_validator import music_validator
from app.domain.services.comparison_service import comparison_service
from app.domain.services.intent_analyzer import intent_analyzer, IntentType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/music", tags=["generation"])

# In-memory job storage (will be replaced by Redis/database)
jobs_storage: Dict[str, dict] = {}


def get_services():
    """Dependency to get AI services (will be properly injected later)."""
    from app.main import music21_service, musicgen_service, ollama_service
    return {
        "music21": music21_service,
        "musicgen": musicgen_service,
        "ollama": ollama_service,
    }


@router.post(
    "/generate",
    response_model=MusicGenerationResponse,
    summary="Generate music from text prompt",
    description="Create a new music generation job. Returns a job ID for tracking progress."
)
async def generate_music(
    prompt: str = Form(..., description="Text description of the music to generate"),
    duration: int = Form(default=30, description="Duration in seconds (5-60)"),
    temperature: float = Form(default=1.0, description="Sampling temperature (0.1-2.0)"),
    guidance_scale: float = Form(default=3.0, description="Guidance scale (1.0-15.0)"),
    title: Optional[str] = Form(None, description="Title for the piece"),
    melody_file: Optional[UploadFile] = File(None, description="Optional melody reference file"),
    services: dict = Depends(get_services)
):
    """
    Generate music from a text prompt.

    This endpoint creates a background job for music generation.
    Use the returned job_id to check status and retrieve results.
    """
    try:
        # Validate parameters
        if not prompt or len(prompt.strip()) == 0:
            raise HTTPException(status_code=422, detail="Prompt cannot be empty")
        if len(prompt) > 500:
            raise HTTPException(status_code=422, detail="Prompt too long (max 500 characters)")
        if duration < 5 or duration > 60:
            raise HTTPException(status_code=422, detail="Duration must be between 5 and 60 seconds")
        if temperature < 0.1 or temperature > 2.0:
            raise HTTPException(status_code=422, detail="Temperature must be between 0.1 and 2.0")
        if guidance_scale < 1.0 or guidance_scale > 15.0:
            raise HTTPException(status_code=422, detail="Guidance scale must be between 1.0 and 15.0")

        # Create request object for internal use
        request = MusicGenerationRequest(
            prompt=prompt,
            duration=duration,
            temperature=temperature,
            guidance_scale=guidance_scale,
            title=title
        )

        # Generate unique job ID
        job_id = f"gen_{uuid.uuid4().hex[:12]}"

        logger.info(f"Creating music generation job {job_id}: {request.prompt[:50]}...")

        # Store job in memory (simplified for POC)
        jobs_storage[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "message": "Job created, waiting to start",
            "request": request.dict(),
            "created_at": datetime.utcnow().isoformat(),
            "piece_id": None,
            "error": None,
        }

        # TODO: In production, this would be sent to Celery queue
        # For now, we'll process synchronously (not ideal but works for POC)

        # Start processing (this should be async/background)
        try:
            # Update status
            jobs_storage[job_id]["status"] = "processing"
            jobs_storage[job_id]["progress"] = 10
            jobs_storage[job_id]["message"] = "Enhancing prompt with AI..."

            # Step 1: Enhance prompt with Ollama
            if services["ollama"]:
                try:
                    enhanced = services["ollama"].enhance_music_prompt(request.prompt)
                    generation_prompt = enhanced.get("enhanced_prompt", request.prompt)
                    logger.info(f"Enhanced prompt: {generation_prompt[:100]}...")
                except Exception as e:
                    logger.warning(f"Prompt enhancement failed: {e}, using original")
                    generation_prompt = request.prompt
            else:
                generation_prompt = request.prompt

            jobs_storage[job_id]["progress"] = 30
            jobs_storage[job_id]["message"] = "Generating audio..."

            # Step 2: Generate audio with MusicGen
            if not services["musicgen"]:
                raise HTTPException(status_code=503, detail="MusicGen service not available")

            audio_array, sample_rate = services["musicgen"].generate_from_text(
                prompt=generation_prompt,
                duration=request.duration,
                temperature=request.temperature,
                guidance_scale=request.guidance_scale,
            )

            jobs_storage[job_id]["progress"] = 70
            jobs_storage[job_id]["message"] = "Saving audio file..."

            # Step 3: Save audio
            piece_id = f"piece_{uuid.uuid4().hex[:12]}"
            audio_filename = f"{piece_id}.wav"
            audio_path = f"storage/{audio_filename}"

            services["musicgen"].save_audio(audio_array, audio_path, sample_rate)

            jobs_storage[job_id]["progress"] = 90
            jobs_storage[job_id]["message"] = "Finalizing..."

            # Step 4: Create piece metadata (simplified)
            # In production, this would create a database record

            jobs_storage[job_id]["status"] = "completed"
            jobs_storage[job_id]["progress"] = 100
            jobs_storage[job_id]["message"] = "Generation completed successfully"
            jobs_storage[job_id]["piece_id"] = piece_id
            jobs_storage[job_id]["audio_url"] = f"/api/v1/music/download/{piece_id}/audio"
            jobs_storage[job_id]["completed_at"] = datetime.utcnow().isoformat()

            logger.info(f"Job {job_id} completed successfully: {piece_id}")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            jobs_storage[job_id]["status"] = "failed"
            jobs_storage[job_id]["message"] = "Generation failed"
            jobs_storage[job_id]["error"] = str(e)

        return MusicGenerationResponse(
            job_id=job_id,
            status=jobs_storage[job_id]["status"],
            message="Music generation job created successfully"
        )

    except Exception as e:
        logger.error(f"Error creating generation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Check job status",
    description="Get the current status of a music generation job."
)
async def get_job_status(job_id: str):
    """
    Check the status of a music generation job.

    Returns progress, status, and download URLs when completed.
    """
    try:
        if job_id not in jobs_storage:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        job = jobs_storage[job_id]

        return JobStatusResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            message=job["message"],
            piece_id=job.get("piece_id"),
            audio_url=job.get("audio_url"),
            midi_url=job.get("midi_url"),
            musicxml_url=job.get("musicxml_url"),
            error=job.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/jobs",
    summary="List all jobs",
    description="Get a list of all generation jobs (for debugging/admin)."
)
async def list_jobs():
    """List all generation jobs."""
    return {
        "jobs": list(jobs_storage.values()),
        "total": len(jobs_storage)
    }


@router.delete(
    "/jobs/{job_id}",
    summary="Delete a job",
    description="Remove a job from storage."
)
async def delete_job(job_id: str):
    """Delete a job."""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    del jobs_storage[job_id]
    return {"message": f"Job {job_id} deleted successfully"}


@router.post(
    "/pattern",
    response_model=MusicGenerationResponse,
    summary="Generate musical pattern (scales, chords, arpeggios)",
    description="Create precise musical patterns using music21. For exact musical theory."
)
async def generate_pattern(
    pattern_type: str = Form(..., description="Type: 'scale', 'chord', 'arpeggio'"),
    tonic: str = Form(default='C', description="Root note (C, D, F#, Bb, etc.)"),
    scale_type: Optional[str] = Form(None, description="Scale type: major, minor, harmonic minor, etc."),
    chord_symbols: Optional[str] = Form(None, description="Comma-separated chords (e.g., 'C,Am,F,G')"),
    chord_type: Optional[str] = Form(None, description="Chord type: major, minor, 7, etc."),
    octaves: int = Form(default=1, description="Number of octaves"),
    tempo: int = Form(default=120, description="Tempo in BPM"),
    duration: float = Form(default=1.0, description="Duration per note in beats"),
    clef: str = Form(default='treble', description="Clef: treble, bass, alto, tenor"),
    title: Optional[str] = Form(None, description="Title for the piece"),
    services: dict = Depends(get_services)
):
    """
    Generate exact musical patterns using music21.

    Use this for:
    - Scales (major, minor, modes, pentatonic, etc.)
    - Chord progressions
    - Arpeggios

    Returns MIDI, MusicXML, ABC, and synthesized audio.
    """
    try:
        import uuid
        from pathlib import Path

        job_id = f"pat_{uuid.uuid4().hex[:12]}"
        piece_id = f"piece_{uuid.uuid4().hex[:12]}"

        logger.info(f"Creating pattern job {job_id}: {pattern_type} in {tonic}")
        logger.info(f"DEBUG - Received scale_type: '{scale_type}' (type: {type(scale_type)})")

        # Create the musical pattern using music21
        music21_service = services["music21"]

        if pattern_type == "scale":
            scale_name = scale_type or "major"
            score = music21_service.create_scale(
                tonic=tonic,
                scale_type=scale_name,
                octaves=octaves,
                duration_per_note=duration,
                tempo_bpm=tempo,
                clef_type=clef
            )
            description = f"{tonic} {scale_name} scale"

        elif pattern_type == "chord":
            if not chord_symbols:
                raise HTTPException(status_code=400, detail="chord_symbols required for chord progression")
            chords = [c.strip() for c in chord_symbols.split(',')]
            score = music21_service.create_chord_progression(
                chord_symbols=chords,
                duration_per_chord=duration * 4,
                tempo_bpm=tempo,
                clef_type=clef
            )
            description = f"Chord progression: {', '.join(chords)}"

        elif pattern_type == "arpeggio":
            chord_name = chord_type or "major"
            score = music21_service.create_arpeggio(
                root=tonic,
                chord_type=chord_name,
                octaves=octaves,
                direction="ascending",
                duration_per_note=duration / 2,
                tempo_bpm=tempo
            )
            description = f"{tonic} {chord_name} arpeggio"

        else:
            raise HTTPException(status_code=400, detail=f"Unknown pattern type: {pattern_type}")

        # Set metadata
        if title:
            score = music21_service.set_metadata(score, title=title)

        # Save as MIDI
        storage_path = Path("storage")
        storage_path.mkdir(parents=True, exist_ok=True)

        midi_path = storage_path / f"{piece_id}.mid"
        score.write('midi', fp=str(midi_path))
        logger.info(f"Saved MIDI to {midi_path}")

        # Save as MusicXML
        musicxml_path = storage_path / f"{piece_id}.musicxml"
        score.write('musicxml', fp=str(musicxml_path))
        logger.info(f"Saved MusicXML to {musicxml_path}")

        # Save as ABC
        abc_path = storage_path / f"{piece_id}.abc"
        score.write('abc', fp=str(abc_path))
        logger.info(f"Saved ABC to {abc_path}")

        # Convert MIDI to audio using a simple synthesizer
        try:
            import subprocess
            audio_path = storage_path / f"{piece_id}.wav"

            # Use FluidSynth (correct syntax for version 2.x)
            try:
                result = subprocess.run(
                    ["fluidsynth", "-ni", "-F", str(audio_path), "-r", "44100",
                     "/usr/share/sounds/sf2/FluidR3_GM.sf2", str(midi_path)],
                    capture_output=True,
                    timeout=30
                )
                if result.returncode == 0 and audio_path.exists():
                    logger.info(f"Synthesized audio with FluidSynth: {audio_path}")
                else:
                    raise Exception(f"FluidSynth failed: {result.stderr.decode()[:200]}")
            except Exception as e:
                # Fallback: try timidity
                logger.warning(f"FluidSynth failed: {e}, trying timidity")
                result = subprocess.run(
                    ["timidity", str(midi_path), "-Ow", "-o", str(audio_path)],
                    capture_output=True,
                    timeout=30
                )
                if result.returncode == 0 and audio_path.exists():
                    logger.info(f"Synthesized audio with timidity: {audio_path}")
                else:
                    logger.warning("No MIDI synthesizer available, audio not generated")
                    audio_path = None

        except Exception as e:
            logger.warning(f"Could not synthesize audio: {e}")
            audio_path = None

        # Create response
        response_data = {
            "job_id": job_id,
            "status": "completed",
            "piece_id": piece_id,
            "description": description,
            "midi_url": f"/api/v1/music/download/{piece_id}/midi",
            "musicxml_url": f"/api/v1/music/download/{piece_id}/musicxml",
            "abc_url": f"/api/v1/music/download/{piece_id}/abc",
        }

        if audio_path and audio_path.exists():
            response_data["audio_url"] = f"/api/v1/music/download/{piece_id}/audio"

        # Store job info
        jobs_storage[job_id] = {
            **response_data,
            "created_at": datetime.utcnow().isoformat(),
            "message": "Pattern generated successfully",
            "progress": 100,
            "error": None,
        }

        # NEW: Save generated concept to context
        session_id = 'default_session'  # TODO: Get from request when frontend sends it
        context: ConversationContext = context_store.get_or_create(session_id)

        concept_to_save = MusicalConcept(
            concept_type=pattern_type,
            tonic=tonic,
            scale_type=scale_type if pattern_type == 'scale' else None,
            chord_type=chord_type if pattern_type == 'chord' or pattern_type == 'arpeggio' else None,
            chord_symbols=chord_symbols.split(',') if pattern_type == 'chord' and chord_symbols else None,
            octaves=octaves,
            clef=clef,
            visualization_id=piece_id,
            description=description
        )
        context.add_concept(concept_to_save)
        context_store.save(context)

        logger.info(f"Saved pattern to context: {description}")
        logger.info(f"Job {job_id} completed: {description}")

        return MusicGenerationResponse(
            job_id=job_id,
            status="completed",
            message=f"Pattern generated successfully: {description}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating pattern: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-score")
async def update_score(
    piece_id: str = Form(..., description="ID of the piece to update"),
    musicxml_file: UploadFile = File(..., description="Updated MusicXML file"),
    services: dict = Depends(get_services)
):
    """
    Update an existing musical piece with edited MusicXML notation

    This endpoint allows updating the MusicXML file for an existing piece.
    It will regenerate the MIDI and audio files from the new MusicXML.
    """
    try:
        logger.info(f"Updating score for piece: {piece_id}")

        # Get the storage service
        storage_service: StorageService = services['storage']

        # Verify the piece exists
        piece_dir = storage_service.storage_path / piece_id
        if not piece_dir.exists():
            raise HTTPException(status_code=404, detail=f"Piece {piece_id} not found")

        # Read the uploaded MusicXML file
        musicxml_content = await musicxml_file.read()

        # Save the new MusicXML file
        musicxml_path = piece_dir / "score.musicxml"
        with open(musicxml_path, 'wb') as f:
            f.write(musicxml_content)

        logger.info(f"Updated MusicXML saved at: {musicxml_path}")

        # TODO: Optionally regenerate MIDI and audio from the updated MusicXML
        # For now, we just update the MusicXML file

        # Return the updated URL
        musicxml_url = f"/api/v1/music/download/{piece_id}/musicxml"

        return {
            "success": True,
            "piece_id": piece_id,
            "musicxml_url": musicxml_url,
            "message": "Score updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with music theory teacher",
    description="Conversational endpoint that provides explanations and generates visualizations"
)
async def chat_endpoint(
    request: ChatRequest,
    services: dict = Depends(get_services)
):
    """
    Hybrid chat endpoint that:
    1. Answers music theory questions with text
    2. Automatically generates visual examples when mentioned
    3. Routes to appropriate generation method
    4. Maintains conversation context and validates user statements
    """
    try:
        ollama = services["ollama"]
        music21 = services["music21"]

        logger.info(f"Chat request: {request.message[:50]}...")

        # NEW: Get or create conversation context (use session_id from frontend or generate one)
        session_id = request.session_id if request.session_id else 'default_session'
        context: ConversationContext = context_store.get_or_create(session_id)
        context_summary = context.get_context_summary()

        logger.info(f"Using session_id: {session_id}")

        # NEW: Check if user is making a contextual reference or validation question
        has_contextual_reference = ollama.detect_contextual_reference(request.message)
        is_validation = ollama.is_validation_question(request.message)

        logger.info(f"Contextual reference: {has_contextual_reference}, Validation: {is_validation}")

        # NEW: If validation question with context, use the validator
        if is_validation and context.get_last_concept():
            last_concept = context.get_last_concept()

            # Try validator first for precise validation
            is_valid, explanation, correction_data = music_validator.validate_scale_statement(
                request.message,
                last_concept
            )

            if explanation != "No pude interpretar tu afirmación. ¿Puedes reformularla?":
                # Validator succeeded
                logger.info(f"Validator result: valid={is_valid}")

                # Generate response with validator explanation
                response_text = explanation

                # Mark concept as explained
                if last_concept.concept_type == "scale":
                    context.mark_concept_explained(f"escala {last_concept.scale_type}")

                # Save context
                context_store.save(context)

                return ChatResponse(
                    type="text",
                    content=response_text,
                    patterns=[]
                )

        # Step 1: Classify intent (but only for ambiguous cases)
        intent = ollama.classify_intent(request.message)
        logger.info(f"Intent classified as: {intent}")

        # Step 2: Handle based on intent
        if intent == 'pattern_request':
            # Direct pattern request - route to existing pattern endpoint
            # This should be handled by frontend's fast detection
            # But if it gets here, we still handle it
            logger.info("Pattern request routed through chat - redirecting")
            return ChatResponse(
                type="pattern_redirect",
                content="Por favor usa la generación directa de patrones para solicitudes específicas.",
                patterns=[]
            )

        elif intent == 'creative_generation':
            # Creative generation - route to MusicGen
            logger.info("Creative generation requested")
            return ChatResponse(
                type="creative_redirect",
                content="Esta es una solicitud creativa. Procesando con el generador de música...",
                patterns=[]
            )

        elif intent == 'general_chat':
            # Simple conversation
            response_text = ollama.chat(
                message=request.message,
                conversation_history=request.conversation_history
            )
            return ChatResponse(
                type="text",
                content=response_text,
                patterns=[]
            )

        else:  # theory_question
            # Step 3: Generate educational response with context
            response_text = ollama.chat_music_teacher(
                message=request.message,
                conversation_history=request.conversation_history,
                context_summary=context_summary if context_summary != "No hay contexto previo." else None
            )

            # Step 4: Extract music concepts for visualization from the USER's original message
            # Pass is_user_message=True to indicate this is the user's request, not the response
            concepts = ollama.extract_music_concepts(request.message, is_user_message=True)

            if not concepts:
                # No visualization needed - pure text response
                return ChatResponse(
                    type="text",
                    content=response_text,
                    patterns=[]
                )

            # Step 5: Generate patterns for each concept
            patterns_to_generate = []

            for concept in concepts:
                try:
                    pattern_data = PatternData(
                        pattern_type=concept.get('type', 'scale'),
                        tonic=concept.get('tonic'),
                        scale_type=concept.get('scale_type'),
                        chord_type=concept.get('chord_type'),
                        octaves=1,
                        tempo=120,
                        duration=1.0
                    )
                    patterns_to_generate.append(pattern_data)
                except Exception as e:
                    logger.warning(f"Could not create pattern from concept: {e}")
                    continue

            if not patterns_to_generate:
                # Concepts found but couldn't generate patterns
                return ChatResponse(
                    type="text",
                    content=response_text,
                    patterns=[]
                )

            # Step 6: Generate first pattern synchronously for job_id
            first_pattern = patterns_to_generate[0]

            try:
                # Create score based on pattern type
                if first_pattern.pattern_type == 'scale':
                    score = music21.create_scale(
                        tonic=first_pattern.tonic or 'C',
                        scale_type=first_pattern.scale_type or 'major',
                        octaves=first_pattern.octaves,
                        duration_per_note=first_pattern.duration,
                        tempo_bpm=first_pattern.tempo
                    )
                elif first_pattern.pattern_type == 'chord':
                    score = music21.create_chord_progression(
                        chord_symbols=first_pattern.chord_symbols or ['C'],
                        duration_per_chord=first_pattern.duration * 4,
                        tempo_bpm=first_pattern.tempo
                    )
                elif first_pattern.pattern_type == 'arpeggio':
                    score = music21.create_arpeggio(
                        root=first_pattern.tonic or 'C',
                        chord_type=first_pattern.chord_type or 'major',
                        octaves=first_pattern.octaves,
                        duration_per_note=first_pattern.duration,
                        tempo_bpm=first_pattern.tempo
                    )
                else:
                    raise ValueError(f"Unknown pattern type: {first_pattern.pattern_type}")

                # Generate job ID and save files
                job_id = f"chat_{uuid.uuid4().hex[:12]}"
                piece_id = f"piece_{uuid.uuid4().hex}"

                # Save files (similar to pattern endpoint)
                import tempfile
                import os
                from pathlib import Path

                # Create temp directory for this piece
                temp_dir = Path(tempfile.gettempdir()) / "musicai" / piece_id
                temp_dir.mkdir(parents=True, exist_ok=True)

                # Save MIDI
                midi_path = temp_dir / f"{piece_id}.mid"
                midi_bytes = music21.to_midi_bytes(score)
                with open(midi_path, 'wb') as f:
                    f.write(midi_bytes)

                # Save MusicXML
                musicxml_path = temp_dir / f"{piece_id}.musicxml"
                musicxml_str = music21.to_musicxml(score)
                with open(musicxml_path, 'w') as f:
                    f.write(musicxml_str)

                # Synthesize audio
                from app.infrastructure.synthesizers.fluidsynth_synthesizer import FluidSynthSynthesizer
                audio_path = temp_dir / f"{piece_id}.wav"

                try:
                    synthesizer = FluidSynthSynthesizer()
                    synthesizer.synthesize(str(midi_path), str(audio_path))
                except Exception as synth_error:
                    logger.warning(f"FluidSynth failed, trying timidity: {synth_error}")
                    import subprocess
                    subprocess.run([
                        'timidity', str(midi_path),
                        '-Ow', '-o', str(audio_path)
                    ], check=True, capture_output=True)

                # Store job info
                jobs_storage[job_id] = {
                    "job_id": job_id,
                    "piece_id": piece_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "Pattern generated successfully",
                    "audio_url": f"/api/v1/music/download/{piece_id}/audio",
                    "midi_url": f"/api/v1/music/download/{piece_id}/midi",
                    "musicxml_url": f"/api/v1/music/download/{piece_id}/musicxml",
                    "created_at": datetime.now().isoformat(),
                    "file_paths": {
                        "audio": str(audio_path),
                        "midi": str(midi_path),
                        "musicxml": str(musicxml_path),
                    }
                }

                # NEW: Save generated concept to context
                concept_to_save = MusicalConcept(
                    concept_type=first_pattern.pattern_type,
                    tonic=first_pattern.tonic,
                    scale_type=first_pattern.scale_type if first_pattern.pattern_type == 'scale' else None,
                    chord_type=first_pattern.chord_type if first_pattern.pattern_type == 'chord' else None,
                    chord_symbols=first_pattern.chord_symbols if first_pattern.pattern_type == 'progression' else None,
                    octaves=first_pattern.octaves,
                    clef=getattr(first_pattern, 'clef', 'treble'),
                    visualization_id=piece_id,
                    description=concepts[0].get('description', f"{first_pattern.pattern_type} generado")
                )
                context.add_concept(concept_to_save)
                context_store.save(context)

                logger.info(f"Saved concept to context: {concept_to_save.description}")

                # Return hybrid response
                return ChatResponse(
                    type="hybrid",
                    content=response_text,
                    job_id=job_id,
                    patterns=patterns_to_generate
                )

            except Exception as gen_error:
                logger.error(f"Error generating pattern: {gen_error}", exc_info=True)
                # Fall back to text-only response
                return ChatResponse(
                    type="text",
                    content=response_text,
                    patterns=[]
                )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat/stream",
    summary="Chat with music theory teacher (streaming)",
    description="Streaming endpoint that returns tokens as they're generated, with optional pattern visualization"
)
async def chat_stream_endpoint(
    request: ChatRequest,
    services: dict = Depends(get_services)
):
    """
    Streaming chat endpoint that yields tokens as they're generated.
    Uses Server-Sent Events (SSE) format.

    For theory questions about specific musical concepts (scales, chords, etc.),
    it also generates a pattern visualization that's sent before the text stream.
    """
    import asyncio
    import threading
    import tempfile
    from pathlib import Path

    music21 = services["music21"]

    # Check if the question mentions specific musical concepts that should be visualized
    pattern_info = None
    lower_message = request.message.lower()

    # Detect if we should generate a visual pattern along with the explanation
    # This happens when asking about specific scales/chords
    import re

    # Pattern 1: note + scale type (e.g., "do mayor", "la menor pentatonica")
    note_scale_pattern = r'\b(do|re|mi|fa|sol|la|si)(#|b)?\s*(mayor|menor|pentat[oó]nica|arm[oó]nica|mel[oó]dica)'

    # Pattern 2: "escala de [note]" or "escala [type] de [note]" (e.g., "escala de do", "escala mayor de do")
    escala_de_pattern = r'escala\s+(?:[\w\sáéíóú]+\s+)?(?:de\s+)?(do|re|mi|fa|sol|la|si)(#|b)?(?:\s+(mayor|menor|pentat[oó]nica|arm[oó]nica|mel[oó]dica))?'

    # Pattern 3: "escala [type]" without note - use C as default (e.g., "escala mayor", "escala pentatonica")
    escala_type_pattern = r'escala\s+(mayor|menor|pentat[oó]nica|arm[oó]nica|mel[oó]dica)'

    note_match = re.search(note_scale_pattern, lower_message)
    escala_de_match = re.search(escala_de_pattern, lower_message)
    escala_type_match = re.search(escala_type_pattern, lower_message)

    has_specific_pattern = note_match is not None or escala_de_match is not None or escala_type_match is not None

    logger.info(f"Pattern detection: message='{lower_message[:50]}', note_match={note_match}, escala_de_match={escala_de_match}, escala_type_match={escala_type_match}")

    if has_specific_pattern:
        logger.info(f"Detected specific musical concept in question: note={note_match.group() if note_match else None}, escala_de={escala_de_match.group() if escala_de_match else None}, escala_type={escala_type_match.group() if escala_type_match else None}")
        # Use intent analyzer to extract pattern data
        from app.domain.services.intent_analyzer import intent_analyzer

        # Clean message to extract just the pattern part
        # e.g., "que se entiende por escala de do mayor?" -> "escala de do mayor"
        clean_message = lower_message
        # Remove question words
        for phrase in ['que se entiende por', 'qué se entiende por', 'que es', 'qué es',
                       'como funciona', 'cómo funciona', 'explica', 'explicame', 'explícame',
                       'dime sobre', 'háblame de', 'hablame de', '?']:
            clean_message = clean_message.replace(phrase, '')
        clean_message = clean_message.strip()

        logger.info(f"Cleaned message for pattern extraction: '{clean_message}'")

        # Directly call pattern detection method instead of full analyze
        pattern_data = intent_analyzer._detect_pattern(clean_message)

        # If intent analyzer didn't find it, try direct extraction from regex matches
        if not pattern_data:
            from app.application.dtos import ProcessPatternData

            # Map Spanish notes to English
            note_map = {'do': 'C', 're': 'D', 'mi': 'E', 'fa': 'F', 'sol': 'G', 'la': 'A', 'si': 'B'}
            scale_map = {
                'mayor': 'major', 'menor': 'minor',
                'pentatonica': 'pentatonic minor', 'pentatónica': 'pentatonic minor',
                'armonica': 'harmonic minor', 'armónica': 'harmonic minor',
                'melodica': 'melodic minor', 'melódica': 'melodic minor'
            }

            tonic = 'C'  # default
            scale_type = 'major'  # default

            # Extract from regex matches
            if note_match:
                note_es = note_match.group(1)
                tonic = note_map.get(note_es, 'C')
                if note_match.group(3):
                    scale_type = scale_map.get(note_match.group(3).replace('ó', 'o').replace('í', 'i'), 'major')
            elif escala_de_match:
                note_es = escala_de_match.group(1)
                tonic = note_map.get(note_es, 'C')
                if escala_de_match.group(3):
                    scale_type = scale_map.get(escala_de_match.group(3).replace('ó', 'o').replace('í', 'i'), 'major')
            elif escala_type_match:
                scale_type = scale_map.get(escala_type_match.group(1).replace('ó', 'o').replace('í', 'i'), 'major')

            pattern_data = ProcessPatternData(
                pattern_type='scale',
                tonic=tonic,
                scale_type=scale_type,
                chord_type=None,
                chord_symbols=None,
                octaves=1,
                tempo=120,
                duration=1.0,
                clef='treble'
            )
            logger.info(f"Created pattern data from regex: tonic={tonic}, scale_type={scale_type}")

        if pattern_data:
            logger.info(f"Pattern data extracted: type={pattern_data.pattern_type}, tonic={pattern_data.tonic}, scale={pattern_data.scale_type}")
            try:
                # Generate the pattern
                piece_id = f"piece_{uuid.uuid4().hex[:12]}"

                if pattern_data.pattern_type == 'scale':
                    score = music21.create_scale(
                        tonic=pattern_data.tonic or 'C',
                        scale_type=pattern_data.scale_type or 'major',
                        octaves=pattern_data.octaves,
                        duration_per_note=pattern_data.duration,
                        tempo_bpm=pattern_data.tempo
                    )
                elif pattern_data.pattern_type == 'chord':
                    chords = (pattern_data.chord_symbols or 'C').split(',')
                    score = music21.create_chord_progression(
                        chord_symbols=chords,
                        duration_per_chord=pattern_data.duration * 4,
                        tempo_bpm=pattern_data.tempo
                    )
                else:
                    score = None

                if score:
                    # Save files
                    temp_dir = Path(tempfile.gettempdir()) / "musicai" / piece_id
                    temp_dir.mkdir(parents=True, exist_ok=True)

                    midi_path = temp_dir / f"{piece_id}.mid"
                    musicxml_path = temp_dir / f"{piece_id}.musicxml"
                    audio_path = temp_dir / f"{piece_id}.wav"

                    midi_bytes = music21.to_midi_bytes(score)
                    with open(midi_path, 'wb') as f:
                        f.write(midi_bytes)

                    musicxml_str = music21.to_musicxml(score)
                    with open(musicxml_path, 'w') as f:
                        f.write(musicxml_str)

                    # Synthesize audio
                    try:
                        from app.infrastructure.synthesizers.fluidsynth_synthesizer import FluidSynthSynthesizer
                        synthesizer = FluidSynthSynthesizer()
                        synthesizer.synthesize(str(midi_path), str(audio_path))
                        audio_url = f"/api/v1/music/download/{piece_id}/audio"
                    except Exception as synth_error:
                        logger.warning(f"Audio synthesis failed: {synth_error}")
                        audio_url = None

                    # Store job info
                    job_id = f"stream_{uuid.uuid4().hex[:12]}"
                    jobs_storage[job_id] = {
                        "job_id": job_id,
                        "piece_id": piece_id,
                        "status": "completed",
                        "progress": 100,
                        "message": "Pattern generated for theory explanation",
                        "audio_url": audio_url,
                        "midi_url": f"/api/v1/music/download/{piece_id}/midi",
                        "musicxml_url": f"/api/v1/music/download/{piece_id}/musicxml",
                        "created_at": datetime.now().isoformat(),
                        "file_paths": {
                            "audio": str(audio_path) if audio_url else None,
                            "midi": str(midi_path),
                            "musicxml": str(musicxml_path),
                        }
                    }

                    pattern_info = {
                        "job_id": job_id,
                        "piece_id": piece_id,
                        "midi_url": f"/api/v1/music/download/{piece_id}/midi",
                        "musicxml_url": f"/api/v1/music/download/{piece_id}/musicxml",
                        "audio_url": audio_url,
                    }

                    logger.info(f"Generated pattern for theory question: {piece_id}")

            except Exception as e:
                logger.warning(f"Could not generate pattern for theory question: {e}")

    # Use asyncio.Queue for better async integration
    token_queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def run_ollama_stream():
        """Run the synchronous Ollama stream in a thread."""
        try:
            ollama = services["ollama"]

            session_id = request.session_id if request.session_id else 'default_session'
            context: ConversationContext = context_store.get_or_create(session_id)
            context_summary = context.get_context_summary()

            for token in ollama.chat_music_teacher_stream(
                message=request.message,
                conversation_history=request.conversation_history,
                context_summary=context_summary if context_summary != "No hay contexto previo." else None
            ):
                # Use thread-safe way to put into asyncio queue
                loop.call_soon_threadsafe(token_queue.put_nowait, ('token', token))

            loop.call_soon_threadsafe(token_queue.put_nowait, ('done', None))

        except Exception as e:
            logger.error(f"Error in streaming chat: {e}", exc_info=True)
            loop.call_soon_threadsafe(token_queue.put_nowait, ('error', str(e)))

    async def generate():
        logger.info(f"Streaming chat request: {request.message[:50]}...")

        # If we have pattern info, send it first so frontend can start loading
        if pattern_info:
            yield f"data: {json.dumps({'pattern': pattern_info})}\n\n"

        # Start the Ollama stream in a background thread
        thread = threading.Thread(target=run_ollama_stream)
        thread.start()

        full_response = ""

        # Read from async queue
        while True:
            try:
                msg_type, data = await asyncio.wait_for(token_queue.get(), timeout=60.0)

                if msg_type == 'token':
                    full_response += data
                    yield f"data: {json.dumps({'token': data})}\n\n"
                elif msg_type == 'done':
                    yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"
                    logger.info("Streaming chat completed")
                    break
                elif msg_type == 'error':
                    yield f"data: {json.dumps({'error': data})}\n\n"
                    break

            except asyncio.TimeoutError:
                logger.warning("Streaming timeout")
                yield f"data: {json.dumps({'error': 'Timeout waiting for response'})}\n\n"
                break

        thread.join(timeout=1.0)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post(
    "/process",
    response_model=ProcessResponse,
    summary="Unified message processing endpoint",
    description="Analyzes user input and returns intent with extracted parameters. Use this to determine how to route messages."
)
async def process_message(
    request: ProcessRequest,
    services: dict = Depends(get_services)
):
    """
    Unified endpoint for processing user messages.

    This endpoint centralizes all input analysis logic:
    1. Detects if user is requesting a pattern (scale, chord, arpeggio)
    2. Detects theory questions
    3. Detects validation questions
    4. Detects creative generation requests
    5. Returns intent and extracted parameters

    The frontend can use this to determine which endpoint to call next:
    - pattern intent: call /pattern endpoint with returned pattern_data
    - theory/validation/chat intent: call /chat/stream endpoint
    - creative intent: call /generate endpoint
    """
    try:
        logger.info(f"Process request: {request.message[:50]}...")

        # Get context for better analysis
        session_id = request.session_id or 'default_session'
        context: ConversationContext = context_store.get_or_create(session_id)

        # Build context dict for analyzer
        analyzer_context = {
            'session_id': session_id,
            'last_concept': context.get_last_concept().to_dict() if context.get_last_concept() else None,
            'conversation_history': request.conversation_history,
        }

        # Analyze the message
        result = intent_analyzer.analyze(request.message, analyzer_context)

        logger.info(f"Intent detected: {result.intent.value} (confidence: {result.confidence})")

        # Build response
        pattern_data = None
        if result.pattern_data:
            pattern_data = ProcessPatternData(
                pattern_type=result.pattern_data.pattern_type,
                tonic=result.pattern_data.tonic,
                scale_type=result.pattern_data.scale_type,
                chord_type=result.pattern_data.chord_type,
                chord_symbols=result.pattern_data.chord_symbols,
                octaves=result.pattern_data.octaves,
                tempo=result.pattern_data.tempo,
                duration=result.pattern_data.duration,
                clef=result.pattern_data.clef,
            )

        return ProcessResponse(
            intent=result.intent.value,
            should_stream=result.should_stream,
            pattern_data=pattern_data,
            confidence=result.confidence,
            detected_keywords=result.detected_keywords,
        )

    except Exception as e:
        logger.error(f"Error in process endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare two musical concepts side by side",
    description="Generate visual and educational comparison between two scales, chords, or arpeggios"
)
async def compare_concepts(
    request: ComparisonRequest,
    services: dict = Depends(get_services)
):
    """
    Compare two musical concepts side by side.

    Generates:
    - Two separate visualizations
    - List of differences
    - Educational explanation
    """
    try:
        music21_service = services["music21"]
        ollama_service = services["ollama"]

        logger.info(f"Comparison request: {request.concept1.pattern_type} vs {request.concept2.pattern_type}")

        # Validate that both concepts are the same type
        if request.concept1.pattern_type != request.concept2.pattern_type:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot compare different types: {request.concept1.pattern_type} vs {request.concept2.pattern_type}"
            )

        # Generate both concepts
        concept1_dict = request.concept1.model_dump()
        concept2_dict = request.concept2.model_dump()

        # Use comparison service to analyze differences
        differences, explanation = comparison_service.compare_concepts(
            concept1_dict,
            concept2_dict
        )

        # Generate visualizations for both concepts
        import tempfile
        from pathlib import Path

        job_id = f"cmp_{uuid.uuid4().hex[:12]}"
        piece1_id = f"piece_{uuid.uuid4().hex[:12]}"
        piece2_id = f"piece_{uuid.uuid4().hex[:12]}"

        # Generate first concept
        if request.concept1.pattern_type == 'scale':
            score1 = music21_service.create_scale(
                tonic=request.concept1.tonic or 'C',
                scale_type=request.concept1.scale_type or 'major',
                octaves=request.concept1.octaves,
                duration_per_note=request.concept1.duration,
                tempo_bpm=request.concept1.tempo
            )
        elif request.concept1.pattern_type == 'chord':
            score1 = music21_service.create_chord_progression(
                chord_symbols=request.concept1.chord_symbols or ['C'],
                duration_per_chord=request.concept1.duration * 4,
                tempo_bpm=request.concept1.tempo
            )
        elif request.concept1.pattern_type == 'arpeggio':
            score1 = music21_service.create_arpeggio(
                root=request.concept1.tonic or 'C',
                chord_type=request.concept1.chord_type or 'major',
                octaves=request.concept1.octaves,
                duration_per_note=request.concept1.duration,
                tempo_bpm=request.concept1.tempo
            )

        # Generate second concept
        if request.concept2.pattern_type == 'scale':
            score2 = music21_service.create_scale(
                tonic=request.concept2.tonic or 'C',
                scale_type=request.concept2.scale_type or 'major',
                octaves=request.concept2.octaves,
                duration_per_note=request.concept2.duration,
                tempo_bpm=request.concept2.tempo
            )
        elif request.concept2.pattern_type == 'chord':
            score2 = music21_service.create_chord_progression(
                chord_symbols=request.concept2.chord_symbols or ['C'],
                duration_per_chord=request.concept2.duration * 4,
                tempo_bpm=request.concept2.tempo
            )
        elif request.concept2.pattern_type == 'arpeggio':
            score2 = music21_service.create_arpeggio(
                root=request.concept2.tonic or 'C',
                chord_type=request.concept2.chord_type or 'major',
                octaves=request.concept2.octaves,
                duration_per_note=request.concept2.duration,
                tempo_bpm=request.concept2.tempo
            )

        # Save files for both concepts
        temp_dir1 = Path(tempfile.gettempdir()) / "musicai" / piece1_id
        temp_dir1.mkdir(parents=True, exist_ok=True)

        temp_dir2 = Path(tempfile.gettempdir()) / "musicai" / piece2_id
        temp_dir2.mkdir(parents=True, exist_ok=True)

        # Save concept 1
        midi1_path = temp_dir1 / f"{piece1_id}.mid"
        musicxml1_path = temp_dir1 / f"{piece1_id}.musicxml"
        audio1_path = temp_dir1 / f"{piece1_id}.wav"

        midi1_bytes = music21_service.to_midi_bytes(score1)
        with open(midi1_path, 'wb') as f:
            f.write(midi1_bytes)

        musicxml1_str = music21_service.to_musicxml(score1)
        with open(musicxml1_path, 'w') as f:
            f.write(musicxml1_str)

        # Save concept 2
        midi2_path = temp_dir2 / f"{piece2_id}.mid"
        musicxml2_path = temp_dir2 / f"{piece2_id}.musicxml"
        audio2_path = temp_dir2 / f"{piece2_id}.wav"

        midi2_bytes = music21_service.to_midi_bytes(score2)
        with open(midi2_path, 'wb') as f:
            f.write(midi2_bytes)

        musicxml2_str = music21_service.to_musicxml(score2)
        with open(musicxml2_path, 'w') as f:
            f.write(musicxml2_str)

        # Synthesize audio for both
        from app.infrastructure.synthesizers.fluidsynth_synthesizer import FluidSynthSynthesizer

        audio1_url = None
        audio2_url = None

        try:
            synthesizer = FluidSynthSynthesizer()
            synthesizer.synthesize(str(midi1_path), str(audio1_path))
            audio1_url = f"/api/v1/music/download/{piece1_id}/audio"
        except Exception as e:
            logger.warning(f"Could not synthesize audio for concept 1: {e}")

        try:
            synthesizer = FluidSynthSynthesizer()
            synthesizer.synthesize(str(midi2_path), str(audio2_path))
            audio2_url = f"/api/v1/music/download/{piece2_id}/audio"
        except Exception as e:
            logger.warning(f"Could not synthesize audio for concept 2: {e}")

        # Store job info for both pieces
        jobs_storage[f"{job_id}_1"] = {
            "job_id": f"{job_id}_1",
            "piece_id": piece1_id,
            "status": "completed",
            "progress": 100,
            "message": "Concept 1 generated",
            "audio_url": audio1_url,
            "midi_url": f"/api/v1/music/download/{piece1_id}/midi",
            "musicxml_url": f"/api/v1/music/download/{piece1_id}/musicxml",
            "created_at": datetime.now().isoformat(),
            "file_paths": {
                "audio": str(audio1_path) if audio1_url else None,
                "midi": str(midi1_path),
                "musicxml": str(musicxml1_path),
            }
        }

        jobs_storage[f"{job_id}_2"] = {
            "job_id": f"{job_id}_2",
            "piece_id": piece2_id,
            "status": "completed",
            "progress": 100,
            "message": "Concept 2 generated",
            "audio_url": audio2_url,
            "midi_url": f"/api/v1/music/download/{piece2_id}/midi",
            "musicxml_url": f"/api/v1/music/download/{piece2_id}/musicxml",
            "created_at": datetime.now().isoformat(),
            "file_paths": {
                "audio": str(audio2_path) if audio2_url else None,
                "midi": str(midi2_path),
                "musicxml": str(musicxml2_path),
            }
        }

        # Save comparison to context if session_id provided
        if request.session_id:
            context = context_store.get_or_create(request.session_id)

            # Save both concepts
            for idx, (concept_data, piece_id) in enumerate([(concept1_dict, piece1_id), (concept2_dict, piece2_id)], 1):
                concept_to_save = MusicalConcept(
                    concept_type=concept_data['pattern_type'],
                    tonic=concept_data.get('tonic'),
                    scale_type=concept_data.get('scale_type'),
                    chord_type=concept_data.get('chord_type'),
                    octaves=concept_data.get('octaves', 1),
                    visualization_id=piece_id,
                    description=f"Concepto {idx} de comparación"
                )
                context.add_concept(concept_to_save)

            context_store.save(context)

        logger.info(f"Comparison completed: {job_id}")

        return ComparisonResponse(
            job_id=job_id,
            concept1_piece_id=piece1_id,
            concept2_piece_id=piece2_id,
            differences=differences,
            explanation=explanation,
            concept1_musicxml_url=f"/api/v1/music/download/{piece1_id}/musicxml",
            concept2_musicxml_url=f"/api/v1/music/download/{piece2_id}/musicxml",
            concept1_audio_url=audio1_url,
            concept2_audio_url=audio2_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in comparison endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
