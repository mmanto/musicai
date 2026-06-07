"""
Knowledge base management routes.
CRUD API for the music_theory ChromaDB collection.
"""
import io
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

SUPPORTED_EXTENSIONS = {"txt", "md", "pdf"}


# ── DTOs ──────────────────────────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = "general"
    difficulty: str = "intermediate"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_text(content_bytes: bytes, ext: str) -> str:
    if ext in ("txt", "md"):
        return content_bytes.decode("utf-8", errors="replace")
    if ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            pages = [p.extract_text() for p in reader.pages if p.extract_text()]
            return "\n\n".join(pages)
        except ImportError:
            raise HTTPException(
                status_code=400,
                detail="PDF parsing requires 'pypdf'. Add it to requirements.txt."
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing PDF: {e}")
    raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents():
    from app.infrastructure.knowledge.rag_service import get_rag_service
    rag = get_rag_service()
    docs = rag.list_documents()
    result = []
    for d in docs:
        meta = d.get("metadata", {})
        result.append({
            "id":              d["id"],
            "title":           meta.get("title", d["id"]),
            "category":        meta.get("category", "general"),
            "difficulty":      meta.get("difficulty", "intermediate"),
            "source_type":     meta.get("source_type", "kb"),
            "added_at":        meta.get("added_at"),
            "content_preview": (d.get("content") or "")[:300],
        })
    return {"documents": result, "total": len(result)}


@router.post("/documents")
async def add_document(data: DocumentCreate):
    from app.infrastructure.knowledge.rag_service import get_rag_service
    rag = get_rag_service()
    try:
        doc_id = rag.add_document(
            title=data.title,
            content=data.content,
            category=data.category,
            difficulty=data.difficulty,
            source_type="manual",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"doc_id": doc_id, "status": "added"}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: str = Form("general"),
    difficulty: str = Form("intermediate"),
):
    from app.infrastructure.knowledge.rag_service import get_rag_service
    rag = get_rag_service()

    fname = file.filename or "documento"
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo no soportado: .{ext}. Use: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    content_bytes = await file.read()
    text = _extract_text(content_bytes, ext)

    if not text.strip():
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del archivo.")

    doc_title = (title or "").strip() or fname.rsplit(".", 1)[0]
    try:
        doc_id = rag.add_document(
            title=doc_title,
            content=text,
            category=category,
            difficulty=difficulty,
            source_type=f"upload:{ext}",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"doc_id": doc_id, "status": "uploaded", "chars": len(text), "title": doc_title}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    from app.infrastructure.knowledge.rag_service import get_rag_service
    rag = get_rag_service()
    ok = rag.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return {"status": "deleted", "doc_id": doc_id}
