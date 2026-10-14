from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.db_models import FileSymbol, ProjectFile
from backend.app.schemas.api_schemas import (
    SemanticSearchRequest, SemanticSearchResponse,
    SemanticSearchResultItem, SymbolSearchRequest, FileSymbolResponse
)
from backend.app.services.rag_service import rag_service
from backend.app.services.ollama_service import ollama_service

router = APIRouter(prefix="", tags=["Search"])

@router.post("/search/code", response_model=SemanticSearchResponse)
def semantic_code_search(req: SemanticSearchRequest):
    matches = rag_service.query_codebase(project_id=req.project_id, query_text=req.query, top_k=req.top_k)
    items: List[SemanticSearchResultItem] = []

    for m in matches:
        # Generate short explanation using Ollama
        prompt = f"Query: {req.query}\nCode Snippet:\n{m['relevant_code'][:400]}\nProvide a one-sentence explanation of how this code relates to the query:"
        try:
            explanation = ollama_service.generate(prompt=prompt, system_prompt="Be concise and technical.")
        except Exception:
            explanation = "Matching code block retrieved from semantic vector index."

        items.append(SemanticSearchResultItem(
            file_path=m["file_path"],
            relevant_code=m["relevant_code"],
            explanation=explanation,
            similarity_score=m["similarity_score"]
        ))

    return SemanticSearchResponse(query=req.query, results=items)

@router.post("/search/symbols", response_model=List[FileSymbolResponse])
def search_code_symbols(req: SymbolSearchRequest, db: Session = Depends(get_db)):
    query = db.query(FileSymbol).join(ProjectFile).filter(
        ProjectFile.project_id == req.project_id,
        FileSymbol.symbol_name.ilike(f"%{req.symbol_name}%")
    )
    if req.symbol_type:
        query = query.filter(FileSymbol.symbol_type == req.symbol_type.upper())

    symbols = query.all()
    return symbols
