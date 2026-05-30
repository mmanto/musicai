"""
RAG (Retrieval-Augmented Generation) Service for music theory knowledge.

Uses ChromaDB for vector storage and semantic search.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MusicTheoryRAG:
    """
    RAG system for music theory knowledge.
    Provides semantic search over music theory concepts.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize RAG service with ChromaDB.

        Args:
            persist_directory: Directory to persist the vector database
        """
        self.persist_directory = persist_directory or "/tmp/musicai_chromadb"

        try:
            import chromadb
            from chromadb.config import Settings

            # Initialize ChromaDB client
            self.client = chromadb.Client(Settings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            ))

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="music_theory",
                metadata={"description": "Music theory knowledge base"}
            )

            logger.info(f"ChromaDB initialized with {self.collection.count()} documents")

        except ImportError:
            logger.warning("ChromaDB not installed. RAG features will be disabled.")
            self.client = None
            self.collection = None
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            self.client = None
            self.collection = None

    def is_available(self) -> bool:
        """Check if RAG service is available."""
        return self.collection is not None

    def load_knowledge_base(self, knowledge_file: str) -> None:
        """
        Load knowledge base from JSON file.

        Args:
            knowledge_file: Path to JSON file with music theory knowledge
        """
        if not self.is_available():
            logger.warning("RAG service not available, skipping knowledge base loading")
            return

        try:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                knowledge = json.load(f)

            # Clear existing collection
            if self.collection.count() > 0:
                logger.info("Clearing existing knowledge base")
                # ChromaDB doesn't have a clear method, so we recreate the collection
                self.client.delete_collection("music_theory")
                self.collection = self.client.create_collection(
                    name="music_theory",
                    metadata={"description": "Music theory knowledge base"}
                )

            # Add documents to collection
            documents = []
            metadatas = []
            ids = []

            for idx, entry in enumerate(knowledge.get("concepts", [])):
                # Create searchable text from concept
                doc_text = f"{entry['title']}\n{entry['description']}\n"
                if 'examples' in entry:
                    doc_text += "\nEjemplos: " + ", ".join(entry['examples'])
                if 'related_concepts' in entry:
                    doc_text += "\nRelacionado con: " + ", ".join(entry['related_concepts'])

                documents.append(doc_text)
                metadatas.append({
                    "title": entry['title'],
                    "category": entry.get('category', 'general'),
                    "difficulty": entry.get('difficulty', 'intermediate')
                })
                ids.append(f"concept_{idx}")

            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Loaded {len(documents)} concepts into knowledge base")

        except FileNotFoundError:
            logger.warning(f"Knowledge base file not found: {knowledge_file}")
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")

    def search(
        self,
        query: str,
        n_results: int = 3,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant music theory concepts.

        Args:
            query: Search query
            n_results: Number of results to return
            category: Optional category filter (scales, chords, harmony, etc.)

        Returns:
            List of relevant concepts with metadata
        """
        if not self.is_available():
            logger.warning("RAG service not available")
            return []

        try:
            # Build where clause for filtering
            where = None
            if category:
                where = {"category": category}

            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })

            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    def get_context_for_query(
        self,
        query: str,
        n_results: int = 2
    ) -> str:
        """
        Get formatted context string for a query.
        Used to augment LLM prompts with relevant knowledge.

        Args:
            query: Search query
            n_results: Number of results to include

        Returns:
            Formatted context string
        """
        results = self.search(query, n_results=n_results)

        if not results:
            return ""

        context_parts = ["CONOCIMIENTO RELEVANTE DE TEORÍA MUSICAL:"]
        for i, result in enumerate(results, 1):
            title = result['metadata'].get('title', 'Concepto')
            content = result['content']
            context_parts.append(f"\n{i}. {title}:\n{content}")

        return "\n".join(context_parts)

    def add_user_interaction(
        self,
        user_query: str,
        concept: str,
        was_helpful: bool = True
    ) -> None:
        """
        Add user interaction to improve future searches.

        Args:
            user_query: User's question
            concept: Concept that was relevant
            was_helpful: Whether the concept was helpful
        """
        # This could be expanded to learn from user interactions
        # For now, just log it
        logger.info(f"User interaction logged: query='{user_query[:50]}', concept='{concept}', helpful={was_helpful}")


# Global instance
_rag_service: Optional[MusicTheoryRAG] = None


def get_rag_service() -> MusicTheoryRAG:
    """Get or create the global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = MusicTheoryRAG()

        # Load knowledge base if it exists
        kb_path = Path(__file__).parent / "music_theory_kb.json"
        if kb_path.exists():
            _rag_service.load_knowledge_base(str(kb_path))

    return _rag_service
