"""Main entry point for the knowledge-graph service."""

import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.rest import router as rest_router
from .api.rest.routes import set_globals
from .graph import Neo4jClient, MusicOntology
from .gnn import GraphEmbedder

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

    # Initialize Neo4j client
    neo4j_client = Neo4jClient()
    try:
        neo4j_client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.warning("Service will start but Neo4j operations will fail")

    # Initialize ontology
    ontology = MusicOntology(neo4j_client)

    # Initialize GNN embedder (if available)
    from .gnn import GraphEmbedder, TORCH_AVAILABLE
    if TORCH_AVAILABLE and GraphEmbedder:
        embedder = GraphEmbedder()
        logger.info("GNN embedder initialized")
    else:
        embedder = None
        logger.warning("PyTorch not available - GNN features disabled")

    # Set global instances for routes
    set_globals(neo4j_client, ontology, embedder)

    # TODO: Initialize RabbitMQ connection
    # TODO: Start gRPC server in background

    logger.info("Knowledge graph service started successfully")

    yield

    # Shutdown tasks
    logger.info("Shutting down knowledge-graph service")
    neo4j_client.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MusicAI Knowledge Graph Service",
        description="Musical knowledge ontology and graph neural networks",
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
    app.include_router(rest_router, prefix="/api/v1", tags=["knowledge-graph"])

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
