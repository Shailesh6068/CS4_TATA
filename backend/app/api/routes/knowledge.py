import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.db_models import Document, DocumentChunk
from backend.app.schemas.api_schemas import (
    DocumentResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    KnowledgeCitationItem
)
from backend.app.security.sanitizer import validate_safe_filename
from backend.app.services.rag_service import rag_service
from backend.app.utils.audit_logger import log_audit_event

router = APIRouter(prefix="", tags=["Knowledge Base"])

@router.post("/knowledge/upload")
async def upload_knowledge_document(
    title: str = Form(...),
    document_type: str = Form("GUIDELINE"),
    version: str = Form("1.0"),
    project_id: Optional[int] = Form(None),
    owner: str = Form("Automotive Lead"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    filename = validate_safe_filename(file.filename or "guideline.txt")
    contents = await file.read()
    
    # Text extraction
    text_content = ""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        try:
            import pypdfium2
            pdf = pypdfium2.PdfDocument(contents)
            for page in pdf:
                text_page = page.get_textpage()
                text_content += text_page.get_text_range() + "\n"
        except Exception:
            text_content = contents.decode("utf-8", errors="ignore")
    else:
        text_content = contents.decode("utf-8", errors="ignore")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="Document contains no readable text content.")

    # Compute the final save path BEFORE creating the DB record
    # so the file_path column is correct from the first commit.
    save_path = os.path.join(settings.UPLOAD_DIR, f"doc_{filename}")

    doc = Document(
        project_id=project_id,
        title=title,
        version=version,
        document_type=document_type,
        file_path=save_path,
        is_enabled=True,
        is_approved=True,
        owner=owner
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Write file to disk AFTER successful DB commit (prevents orphan files on DB failure)
    with open(save_path, "wb") as f:
        f.write(contents)

    # Ingest into ChromaDB
    chunks_created = rag_service.ingest_document(
        doc_id=str(doc.id),
        title=title,
        text=text_content,
        project_id=project_id,
        doc_type=document_type
    )

    # Persist DocumentChunks in SQLite relational store
    doc_chunks = rag_service._chunk_text(text_content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    for idx, c_text in enumerate(doc_chunks):
        c_record = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=c_text,
            embedding_id=f"doc_{doc.id}_{idx}"
        )
        db.add(c_record)
    db.commit()

    log_audit_event(db, "KNOWLEDGE_INGESTED", project_id=project_id, target_id=str(doc.id), details={"title": title, "chunks": chunks_created})
    return {"message": f"Successfully ingested guideline '{title}'. Generated {chunks_created} vector chunks.", "document_id": doc.id}

@router.get("/knowledge", response_model=List[DocumentResponse])
def list_knowledge_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).options(joinedload(Document.chunks)).all()
    resp = []
    for d in docs:
        c_count = len(d.chunks)
        if c_count == 0 and rag_service.guidelines_col.count() > 0:
            try:
                chroma_match = rag_service.guidelines_col.get(where={"doc_id": str(d.id)})
                c_count = len(chroma_match.get("ids", []))
            except Exception:
                c_count = 0

        resp.append(DocumentResponse(
            id=d.id,
            project_id=d.project_id,
            title=d.title,
            version=d.version,
            document_type=d.document_type,
            file_path=d.file_path,
            is_enabled=d.is_enabled,
            is_approved=d.is_approved,
            owner=d.owner,
            chunk_count=c_count,
            created_at=d.created_at
        ))
    return resp

@router.delete("/knowledge/{document_id}")
def delete_knowledge_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    rag_service.delete_document(str(doc.id))
    db.delete(doc)
    db.commit()

    log_audit_event(db, "KNOWLEDGE_DELETED", target_id=str(document_id))
    return {"message": f"Document {document_id} and associated vector embeddings removed."}

@router.post("/knowledge/query", response_model=KnowledgeQueryResponse)
def query_knowledge_base(req: KnowledgeQueryRequest):
    citations_raw = rag_service.query_guidelines(
        query_text=req.query,
        project_id=req.project_id,
        top_k=req.top_k
    )
    items = [
        KnowledgeCitationItem(
            title=c.get("title", "Guideline"),
            section=c.get("section", "Standard"),
            doc_type=c.get("doc_type", "GUIDELINE"),
            content=c.get("content", ""),
            similarity=float(c.get("similarity", 0.0))
        )
        for c in citations_raw
    ]
    return KnowledgeQueryResponse(query=req.query, citations=items)

