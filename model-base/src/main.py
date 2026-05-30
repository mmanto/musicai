"""Main entry point for the model-base service."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.rest import router as rest_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    # Startup: preload model
    from .inference import MusicGenerator
    try:
        generator = MusicGenerator()
        logger.info(f"Model loaded: {generator.model.num_parameters:,} parameters")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")

    yield

    logger.info("Shutting down model-base service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MusicAI Model Base Service",
        description="Music Transformer for music generation",
        version=settings.SERVICE_VERSION,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(rest_router, prefix="/api/v1", tags=["model-base"])

    return app


app = create_app()


def main():
    """Run the application."""
    settings = get_settings()

    uvicorn.run(
        "src.main:app",
        host=settings.REST_HOST,
        port=settings.REST_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
