"""Neo4j client for graph database operations."""

import logging
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j database client for music knowledge graph."""

    def __init__(self):
        """Initialize Neo4j client."""
        self.settings = get_settings()
        self._driver: Optional[Driver] = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def connect(self) -> None:
        """Connect to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                self.settings.NEO4J_URI,
                auth=(self.settings.NEO4J_USER, self.settings.NEO4J_PASSWORD)
            )
            # Test connection
            with self._driver.session(database=self.settings.NEO4J_DATABASE) as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Closed Neo4j connection")

    @contextmanager
    def session(self) -> Session:
        """Context manager for Neo4j session."""
        if not self._driver:
            self.connect()
        session = self._driver.session(database=self.settings.NEO4J_DATABASE)
        try:
            yield session
        finally:
            session.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results."""
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def create_node(
        self,
        label: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a node in the graph."""
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """
        result = self.execute_query(query, {"properties": properties})
        return result[0]["n"] if result else {}

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a relationship between two nodes."""
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:{rel_type} $properties]->(b)
        RETURN r
        """
        params = {
            "from_id": from_id,
            "to_id": to_id,
            "properties": properties or {}
        }
        result = self.execute_query(query, params)
        return result[0]["r"] if result else {}

    def find_node(
        self,
        label: str,
        properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find a node by label and properties."""
        prop_conditions = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
        query = f"""
        MATCH (n:{label})
        WHERE {prop_conditions}
        RETURN n
        """
        result = self.execute_query(query, properties)
        return result[0]["n"] if result else None

    def find_relationships(
        self,
        from_label: str,
        to_label: str,
        rel_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find relationships between node types."""
        rel_pattern = f"[r:{rel_type}]" if rel_type else "[r]"
        query = f"""
        MATCH (a:{from_label})-{rel_pattern}->(b:{to_label})
        RETURN a, r, b
        """
        return self.execute_query(query)

    def get_node_neighbors(
        self,
        node_id: str,
        max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """Get neighbors of a node up to max_depth."""
        query = f"""
        MATCH path = (n)-[*1..{max_depth}]-(neighbor)
        WHERE id(n) = $node_id
        RETURN neighbor, length(path) as depth
        """
        return self.execute_query(query, {"node_id": node_id})

    def search_by_concept(
        self,
        concept_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search nodes by concept name (fuzzy matching)."""
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($concept_name)
        RETURN n
        LIMIT $limit
        """
        return self.execute_query(query, {"concept_name": concept_name, "limit": limit})

    def get_shortest_path(
        self,
        from_id: str,
        to_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find shortest path between two nodes."""
        query = """
        MATCH (start), (end)
        WHERE id(start) = $from_id AND id(end) = $to_id
        MATCH path = shortestPath((start)-[*]-(end))
        RETURN path, length(path) as distance
        """
        result = self.execute_query(query, {"from_id": from_id, "to_id": to_id})
        return result[0] if result else None

    def clear_database(self) -> None:
        """Clear all nodes and relationships (use with caution!)."""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        logger.warning("Cleared all data from Neo4j database")
