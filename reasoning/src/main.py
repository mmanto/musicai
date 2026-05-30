"""Main entry point for reasoning service."""

import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.rest import router, init_components
from .api.rest.chat_teacher import router as chat_teacher_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting reasoning service...")

    settings = get_settings()

    # Initialize API components
    init_components()

    logger.info(f"Reasoning service started on port {settings.REST_PORT}")

    yield

    # Shutdown
    logger.info("Shutting down reasoning service...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app
    """
    settings = get_settings()

    app = FastAPI(
        title="MusicAI Reasoning Service",
        description="Hybrid symbolic and neural reasoning for music analysis",
        version=settings.SERVICE_VERSION,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router)
    app.include_router(chat_teacher_router, prefix="/api/v1")

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "status": "running",
            "docs": "/docs"
        }

    return app


def main():
    """Run the service."""
    settings = get_settings()

    app = create_app()

    uvicorn.run(
        app,
        host=settings.REST_HOST,
        port=settings.REST_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
