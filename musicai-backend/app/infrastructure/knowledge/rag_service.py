"""
RAG (Retrieval-Augmented Generation) Service for music knowledge.

Three ChromaDB collections:
  - music_theory       : static knowledge base loaded from JSON
  - music_scores       : analyses of user-uploaded music files
  - chat_interactions  : past Q&A pairs, indexed for semantic retrieval
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MusicTheoryRAG:
    """
    RAG system for music knowledge.
    Provides semantic search over music theory, uploaded scores, and chat history.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or "/tmp/musicai_chromadb"

        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=self.persist_directory)

            self.collection = self.client.get_or_create_collection(
                name="music_theory",
                metadata={"description": "Music theory knowledge base"},
            )
            self.scores_collection = self.client.get_or_create_collection(
                name="music_scores",
                metadata={"description": "Uploaded score analyses"},
            )
            self.interactions_collection = self.client.get_or_create_collection(
                name="chat_interactions",
                metadata={"description": "Chat interaction history"},
            )

            logger.info(
                f"ChromaDB initialized at '{self.persist_directory}' — "
                f"theory={self.collection.count()}, "
                f"scores={self.scores_collection.count()}, "
                f"interactions={self.interactions_collection.count()}"
            )

        except ImportError:
            logger.warning("ChromaDB not installed. RAG features will be disabled.")
            self.client = None
            self.collection = None
            self.scores_collection = None
            self.interactions_collection = None
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            self.client = None
            self.collection = None
            self.scores_collection = None
            self.interactions_collection = None

    # ─── Availability ──────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return self.collection is not None

    # ─── Static knowledge base ─────────────────────────────────────────────────

    def load_knowledge_base(self, knowledge_file: str) -> None:
        if not self.is_available():
            logger.warning("RAG service not available, skipping knowledge base loading")
            return

        try:
            with open(knowledge_file, "r", encoding="utf-8") as f:
                knowledge = json.load(f)

            if self.collection.count() > 0:
                logger.info("Clearing existing music_theory knowledge base")
                self.client.delete_collection("music_theory")
                self.collection = self.client.create_collection(
                    name="music_theory",
                    metadata={"description": "Music theory knowledge base"},
                )

            documents, metadatas, ids = [], [], []

            for idx, entry in enumerate(knowledge.get("concepts", [])):
                doc_text = f"{entry['title']}\n{entry['description']}\n"
                if "examples" in entry:
                    doc_text += "\nEjemplos: " + ", ".join(entry["examples"])
                if "related_concepts" in entry:
                    doc_text += "\nRelacionado con: " + ", ".join(entry["related_concepts"])

                documents.append(doc_text)
                metadatas.append({
                    "title": entry["title"],
                    "category": entry.get("category", "general"),
                    "difficulty": entry.get("difficulty", "intermediate"),
                })
                ids.append(f"concept_{idx}")

            # Add in small batches so a single network/embedding timeout doesn't
            # abort the entire load.
            batch_size = 5
            loaded = 0
            for start in range(0, len(documents), batch_size):
                end = start + batch_size
                for attempt in range(3):
                    try:
                        self.collection.add(
                            documents=documents[start:end],
                            metadatas=metadatas[start:end],
                            ids=ids[start:end],
                        )
                        loaded += end - start
                        break
                    except Exception as batch_err:
                        if attempt == 2:
                            logger.error(f"Batch {start}:{end} failed after 3 attempts: {batch_err}")
                        else:
                            logger.warning(f"Batch {start}:{end} attempt {attempt+1} failed, retrying: {batch_err}")

            logger.info(f"Loaded {loaded}/{len(documents)} concepts into music_theory collection")

        except FileNotFoundError:
            logger.warning(f"Knowledge base file not found: {knowledge_file}")
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")

    # ─── Document CRUD (music_theory collection) ──────────────────────────────

    def list_documents(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return all documents in the music_theory collection."""
        if not self.is_available():
            return []
        try:
            count = self.collection.count()
            if count == 0:
                return []
            results = self.collection.get(
                limit=min(limit, count),
                include=["documents", "metadatas"],
            )
            formatted = []
            for i, doc_id in enumerate(results.get("ids") or []):
                formatted.append({
                    "id":       doc_id,
                    "content":  (results.get("documents") or [])[i] if results.get("documents") else "",
                    "metadata": (results.get("metadatas") or [])[i] if results.get("metadatas") else {},
                })
            return formatted
        except Exception as e:
            logger.error(f"Error listing music_theory documents: {e}")
            return []

    def add_document(
        self,
        title: str,
        content: str,
        category: str = "general",
        difficulty: str = "intermediate",
        source_type: str = "manual",
    ) -> str:
        """Add a document to the music_theory collection. Returns the document ID."""
        if not self.is_available():
            raise RuntimeError("RAG service not available")
        import uuid
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        self.collection.add(
            documents=[content],
            metadatas=[{
                "title":       title,
                "category":    category,
                "difficulty":  difficulty,
                "source_type": source_type,
                "added_at":    datetime.utcnow().isoformat(),
            }],
            ids=[doc_id],
        )
        logger.info(f"Added knowledge document '{title}' id={doc_id}")
        return doc_id

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the music_theory collection."""
        if not self.is_available():
            return False
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted knowledge document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    # ─── Score indexing ────────────────────────────────────────────────────────

    def add_score(self, score_analysis) -> None:
        """Upsert a ScoreAnalysis into the music_scores collection."""
        if not self.is_available():
            return
        try:
            doc_text = score_analysis.context_summary or score_analysis.build_summary()
            metadata = {
                "score_id":       score_analysis.score_id,
                "file_name":      score_analysis.file_name,
                "file_type":      score_analysis.file_type,
                "key":            score_analysis.key or "",
                "tempo":          score_analysis.tempo or 0,
                "time_signature": score_analysis.time_signature or "",
                "created_at":     score_analysis.created_at.isoformat(),
            }
            self.scores_collection.upsert(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[score_analysis.score_id],
            )
            logger.info(f"Upserted score '{score_analysis.file_name}' ({score_analysis.score_id}) into music_scores")
        except Exception as e:
            logger.error(f"Error adding score to RAG: {e}")

    # ─── Interaction indexing ──────────────────────────────────────────────────

    def add_interaction(
        self,
        session_id: str,
        user_msg: str,
        assistant_response: str,
        timestamp: Optional[str] = None,
    ) -> None:
        """Store a chat Q&A pair in the chat_interactions collection."""
        if not self.is_available():
            return
        try:
            ts = timestamp or datetime.utcnow().isoformat()
            raw_id = f"{session_id}::{ts}::{user_msg[:40]}"
            doc_id = "chat_" + hashlib.sha1(raw_id.encode()).hexdigest()[:16]

            doc_text = f"Usuario: {user_msg}\nAsistente: {assistant_response}"
            metadata = {
                "session_id":   session_id,
                "timestamp":    ts,
                "user_msg_len": len(user_msg),
            }
            self.interactions_collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[doc_id],
            )
            logger.info(f"Stored interaction for session '{session_id}' (id={doc_id})")
        except Exception as e:
            logger.error(f"Error adding interaction to RAG: {e}")

    # ─── Search helpers ────────────────────────────────────────────────────────

    def _format_results(self, results) -> List[Dict[str, Any]]:
        formatted = []
        if results.get("documents") and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                formatted.append({
                    "content":  results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None,
                })
        return formatted

    def search(
        self,
        query: str,
        n_results: int = 3,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search over the music_theory collection."""
        if not self.is_available():
            return []
        try:
            count = self.collection.count()
            if count == 0:
                return []
            where = {"category": category} if category else None
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
                where=where,
            )
            formatted = self._format_results(results)
            logger.info(f"Theory search: {len(formatted)} results for '{query[:50]}'")
            return formatted
        except Exception as e:
            logger.error(f"Error searching music_theory: {e}")
            return []

    def search_scores(self, query: str, n_results: int = 2) -> List[Dict[str, Any]]:
        """Semantic search over uploaded score analyses."""
        if not self.is_available():
            return []
        try:
            count = self.scores_collection.count()
            if count == 0:
                return []
            results = self.scores_collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Error searching music_scores: {e}")
            return []

    def list_scores(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return all indexed scores (used to build the available-files inventory)."""
        if not self.is_available():
            return []
        try:
            count = self.scores_collection.count()
            if count == 0:
                return []
            results = self.scores_collection.get(limit=min(limit, count))
            formatted = []
            if results.get("documents"):
                for i, doc in enumerate(results["documents"]):
                    formatted.append({
                        "content":  doc,
                        "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                    })
            return formatted
        except Exception as e:
            logger.error(f"Error listing music_scores: {e}")
            return []

    def get_score_by_id(self, score_id: str) -> Optional[str]:
        """Retrieve a score document from ChromaDB by its score_id (fallback for ephemeral ScoreStore)."""
        if not self.is_available():
            return None
        try:
            results = self.scores_collection.get(ids=[score_id])
            if results.get("documents") and results["documents"]:
                return results["documents"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching score {score_id} from ChromaDB: {e}")
            return None

    def search_interactions(
        self,
        query: str,
        n_results: int = 2,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search over past chat interactions."""
        if not self.is_available():
            return []
        try:
            count = self.interactions_collection.count()
            if count == 0:
                return []
            where = {"session_id": session_id} if session_id else None
            results = self.interactions_collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
                where=where,
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Error searching chat_interactions: {e}")
            return []

    # ─── Aggregated context for LLM prompts ───────────────────────────────────

    def get_context_for_query(
        self,
        query: str,
        n_results: int = 2,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Build a multi-section context string from all three collections.
        Existing callers that omit session_id continue to work unchanged.
        """
        parts = []

        # 1. Music theory KB
        theory = self.search(query, n_results=n_results)
        if theory:
            section = ["CONOCIMIENTO RELEVANTE DE TEORÍA MUSICAL:"]
            for i, r in enumerate(theory, 1):
                title = r["metadata"].get("title", "Concepto")
                section.append(f"\n{i}. {title}:\n{r['content']}")
            parts.append("\n".join(section))

        # 2. Uploaded scores
        scores = self.search_scores(query, n_results=1)
        if scores:
            section = ["PARTITURAS ANALIZADAS RELEVANTES:"]
            for i, r in enumerate(scores, 1):
                fname = r["metadata"].get("file_name", "Partitura")
                section.append(f"\n{i}. {fname}:\n{r['content']}")
            parts.append("\n".join(section))

        # 3. Past interactions
        interactions = self.search_interactions(query, n_results=1, session_id=session_id)
        if interactions:
            section = ["INTERACCIONES PREVIAS RELEVANTES:"]
            for i, r in enumerate(interactions, 1):
                section.append(f"\n{i}.\n{r['content']}")
            parts.append("\n".join(section))

        return "\n\n".join(parts)


# ─── Singleton ────────────────────────────────────────────────────────────────

_rag_service: Optional[MusicTheoryRAG] = None


def get_rag_service() -> MusicTheoryRAG:
    global _rag_service
    if _rag_service is None:
        from app.config import settings
        _rag_service = MusicTheoryRAG(persist_directory=settings.chroma_persist_directory)

        kb_path = Path(__file__).parent / "music_theory_kb.json"
        if kb_path.exists():
            _rag_service.load_knowledge_base(str(kb_path))

    return _rag_service
