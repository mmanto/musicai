#!/usr/bin/env python3
"""Script to initialize the music ontology in Neo4j."""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Neo4jClient, MusicOntology
from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Initialize the music ontology."""
    logger.info("Starting ontology initialization...")

    settings = get_settings()
    logger.info(f"Connecting to Neo4j at {settings.NEO4J_URI}")

    # Create Neo4j client
    client = Neo4jClient()

    try:
        # Connect to Neo4j
        client.connect()
        logger.info("Connected to Neo4j successfully")

        # Check if database is empty
        result = client.execute_query("MATCH (n) RETURN count(n) as count")
        node_count = result[0]["count"] if result else 0

        if node_count > 0:
            response = input(
                f"\nDatabase contains {node_count} nodes. "
                "Do you want to clear it and reinitialize? (yes/no): "
            )
            if response.lower() in ["yes", "y"]:
                logger.warning("Clearing existing database...")
                client.clear_database()
            else:
                logger.info("Keeping existing data")

        # Initialize ontology
        ontology = MusicOntology(client)
        ontology.initialize()

        # Verify initialization
        result = client.execute_query("MATCH (n) RETURN count(n) as count")
        final_count = result[0]["count"] if result else 0
        logger.info(f"Ontology initialized with {final_count} nodes")

        # Show statistics by type
        logger.info("\nNode counts by type:")
        labels = client.execute_query("CALL db.labels()")
        for label_row in labels:
            label = label_row["label"]
            count_result = client.execute_query(
                f"MATCH (n:{label}) RETURN count(n) as count"
            )
            count = count_result[0]["count"] if count_result else 0
            logger.info(f"  {label}: {count}")

        logger.info("\nOntology initialization complete!")

    except Exception as e:
        logger.error(f"Failed to initialize ontology: {e}")
        raise

    finally:
        client.close()


if __name__ == "__main__":
    main()
