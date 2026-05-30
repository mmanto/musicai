"""REST API routes for knowledge-graph service."""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...graph import Neo4jClient, MusicOntology
from ...gnn import GraphEmbedder

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (initialized in main.py lifespan)
neo4j_client: Optional[Neo4jClient] = None
ontology: Optional[MusicOntology] = None
embedder: Optional[GraphEmbedder] = None


# Request/Response Models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str


class ConceptQuery(BaseModel):
    """Query for musical concepts."""
    concept_name: str = Field(..., description="Name of the musical concept")
    max_depth: int = Field(default=2, ge=1, le=5, description="Maximum relationship depth")


class RelationQuery(BaseModel):
    """Query for relationships between concepts."""
    from_concept: str = Field(..., description="Source concept")
    to_concept: str = Field(..., description="Target concept")
    relationship_type: Optional[str] = Field(None, description="Type of relationship")


class EmbeddingRequest(BaseModel):
    """Request for concept embedding."""
    concept_name: str = Field(..., description="Name of the concept")


class SimilarityRequest(BaseModel):
    """Request for similar concepts."""
    concept_name: str = Field(..., description="Query concept name")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results")
    metric: str = Field(default="cosine", description="Similarity metric")


class ConceptResponse(BaseModel):
    """Response with concept information."""
    name: str
    properties: Dict[str, Any]
    related: List[Dict[str, Any]] = []


class EmbeddingResponse(BaseModel):
    """Response with concept embedding."""
    concept_name: str
    embedding: List[float]
    dimension: int


# Endpoints
@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="knowledge-graph",
        version="0.1.0"
    )


@router.post("/query/concept", response_model=ConceptResponse)
async def query_concept(query: ConceptQuery) -> ConceptResponse:
    """
    Query information about a musical concept.

    Returns the concept and its related concepts up to max_depth.
    """
    if not neo4j_client or not ontology:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not initialized"
        )

    try:
        # Find the concept
        nodes = neo4j_client.search_by_concept(query.concept_name, limit=1)
        if not nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{query.concept_name}' not found"
            )

        concept = nodes[0]["n"]

        # Get related concepts
        related = ontology.query_related_concepts(
            query.concept_name,
            max_depth=query.max_depth
        )

        return ConceptResponse(
            name=concept.get("name", query.concept_name),
            properties=dict(concept),
            related=[{"concept": r["related"], "relationship": r.get("r")} for r in related]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query concept: {str(e)}"
        )


@router.post("/query/relations")
async def query_relations(query: RelationQuery) -> Dict[str, Any]:
    """
    Query relationships between two musical concepts.

    Returns the shortest path and relationship types.
    """
    if not neo4j_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not initialized"
        )

    try:
        # Find both concepts
        from_nodes = neo4j_client.search_by_concept(query.from_concept, limit=1)
        to_nodes = neo4j_client.search_by_concept(query.to_concept, limit=1)

        if not from_nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{query.from_concept}' not found"
            )
        if not to_nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{query.to_concept}' not found"
            )

        # Get node IDs (simplified - in practice use actual Neo4j IDs)
        from_id = str(from_nodes[0]["n"].id) if hasattr(from_nodes[0]["n"], "id") else "0"
        to_id = str(to_nodes[0]["n"].id) if hasattr(to_nodes[0]["n"], "id") else "1"

        # Find shortest path
        path = neo4j_client.get_shortest_path(from_id, to_id)

        return {
            "from_concept": query.from_concept,
            "to_concept": query.to_concept,
            "path": path,
            "connected": path is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying relations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query relations: {str(e)}"
        )


@router.post("/embeddings/concept", response_model=EmbeddingResponse)
async def get_concept_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """
    Get embedding vector for a musical concept.

    Returns the learned embedding from the GNN.
    """
    if not embedder or not neo4j_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedder not initialized"
        )

    try:
        # Find concept
        nodes = neo4j_client.search_by_concept(request.concept_name, limit=1)
        if not nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{request.concept_name}' not found"
            )

        # TODO: Convert graph to PyG Data and get embedding
        # For now, return placeholder
        embedding = [0.0] * 256  # Placeholder

        return EmbeddingResponse(
            concept_name=request.concept_name,
            embedding=embedding,
            dimension=len(embedding)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get embedding: {str(e)}"
        )


@router.post("/embeddings/similar")
async def find_similar_concepts(request: SimilarityRequest) -> Dict[str, Any]:
    """
    Find concepts similar to the query concept.

    Uses embedding similarity to find related concepts.
    """
    if not embedder or not neo4j_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedder not initialized"
        )

    try:
        # Find concept
        nodes = neo4j_client.search_by_concept(request.concept_name, limit=1)
        if not nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{request.concept_name}' not found"
            )

        # TODO: Get embedding and find similar
        # For now, return placeholder
        similar = []

        return {
            "query_concept": request.concept_name,
            "similar_concepts": similar,
            "top_k": request.top_k,
            "metric": request.metric
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar concepts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar concepts: {str(e)}"
        )


@router.get("/ontology/schema")
async def get_ontology_schema() -> Dict[str, Any]:
    """
    Get the music ontology schema.

    Returns node types, relationship types, and structure.
    """
    if not neo4j_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not initialized"
        )

    try:
        # Query schema information
        node_labels = neo4j_client.execute_query("CALL db.labels()")
        rel_types = neo4j_client.execute_query("CALL db.relationshipTypes()")

        return {
            "node_types": [label["label"] for label in node_labels],
            "relationship_types": [rel["relationshipType"] for rel in rel_types],
            "version": "0.1.0"
        }

    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.get("/ontology/stats")
async def get_ontology_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge graph."""
    if not neo4j_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not initialized"
        )

    try:
        # Count nodes and relationships
        node_count = neo4j_client.execute_query("MATCH (n) RETURN count(n) as count")
        rel_count = neo4j_client.execute_query("MATCH ()-[r]->() RETURN count(r) as count")

        return {
            "total_nodes": node_count[0]["count"] if node_count else 0,
            "total_relationships": rel_count[0]["count"] if rel_count else 0
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


def set_globals(
    client: Neo4jClient,
    onto: MusicOntology,
    emb: GraphEmbedder
) -> None:
    """Set global instances for use in route handlers."""
    global neo4j_client, ontology, embedder
    neo4j_client = client
    ontology = onto
    embedder = emb
