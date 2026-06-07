"""
MusicAI Backend - FastAPI Application.

Main entry point for the MusicAI backend server.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global services (will be initialized on startup)
music21_service = None
musicgen_service = None
audio_to_midi_service = None
ollama_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting MusicAI backend...")

    # Initialize services
    global music21_service, musicgen_service, audio_to_midi_service, ollama_service

    from app.infrastructure.ai import (
        Music21Service,
        OllamaService
    )

    try:
        # Initialize music21 service (lightweight)
        music21_service = Music21Service()
        logger.info("✓ Music21 service initialized")

        # Initialize Ollama service
        ollama_service = OllamaService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )
        logger.info("✓ Ollama service initialized")

        logger.info("🎵 All services initialized successfully!")

    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down MusicAI backend...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered music generation and analysis platform",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "music21": music21_service is not None,
            "musicgen": musicgen_service is not None,
            "audio_to_midi": audio_to_midi_service is not None,
            "ollama": ollama_service is not None,
        }
    }


# Import and include routers
from app.presentation.api import generation_routes, analysis_routes, score_routes, knowledge_routes

app.include_router(generation_routes.router, prefix=settings.api_v1_prefix)
app.include_router(analysis_routes.router, prefix=settings.api_v1_prefix)
app.include_router(score_routes.router, prefix=settings.api_v1_prefix)
app.include_router(knowledge_routes.router, prefix=settings.api_v1_prefix)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
