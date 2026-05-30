"""Main entry point for the preprocessing service."""

import logging
import asyncio
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

    # Startup tasks
    # TODO: Initialize RabbitMQ connection
    # TODO: Start gRPC server in background

    yield

    # Shutdown tasks
    logger.info("Shutting down preprocessing service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MusicAI Preprocessing Service",
        description="Audio tokenization, feature extraction, and MIDI conversion",
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
    app.include_router(rest_router, prefix="/api/v1", tags=["preprocessing"])

    return app


# Create app instance
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
