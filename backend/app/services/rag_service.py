import os
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.app.config import settings
from backend.app.services.embedding_service import embedding_service

class RAGService:
    """
    Local RAG Knowledge Engine backed by persistent ChromaDB.
    Maintains collections for internal coding standards, MISRA guidelines,
    and project codebase chunks.
    """
    def __init__(self):
        persist_path = os.path.abspath(settings.CHROMA_PERSIST_DIR)
        os.makedirs(persist_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_path)
        self.guidelines_col = self.client.get_or_create_collection(
            name="securecode_guidelines",
            metadata={"description": "Approved internal engineering and MISRA guidelines"}
        )
        self.codebase_col = self.client.get_or_create_collection(
            name="project_codebase",
            metadata={"description": "Project source code index for semantic search"}
        )

    def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
        """Splits document or code into overlapping sliding chunks."""
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += (chunk_size - overlap)
            if start >= text_len:
                break
        return chunks if chunks else [text]

    def ingest_document(
        self,
        doc_id: str,
        title: str,
        text: str,
        project_id: Optional[int] = None,
        doc_type: str = "GUIDELINE",
        section: str = "General"
    ) -> int:
        """Chunks document text, generates embeddings, and persists in ChromaDB."""
        chunks = self._chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            return 0

        embeddings = embedding_service.embed_batch(chunks)
        ids = [f"doc_{doc_id}_{idx}" for idx in range(len(chunks))]
        metadatas = [
            {
                "doc_id": str(doc_id),
                "title": title,
                "project_id": str(project_id or 0),
                "doc_type": doc_type,
                "section": section,
                "chunk_index": idx
            }
            for idx in range(len(chunks))
        ]

        self.guidelines_col.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        return len(chunks)

    def query_guidelines(
        self,
        query_text: str,
        project_id: Optional[int] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Queries the guideline knowledge base for relevant standard excerpts."""
        if self.guidelines_col.count() == 0:
            return []

        query_emb = embedding_service.embed_text(query_text)
        results = self.guidelines_col.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, self.guidelines_col.count()),
            include=["documents", "metadatas", "distances"]
        )

        citations = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

            for doc_text, meta, dist in zip(docs, metas, distances):
                # Filter by project if specified and non-zero
                p_id = meta.get("project_id", "0")
                if project_id and p_id not in ("0", str(project_id)):
                    continue
                citations.append({
                    "title": meta.get("title", "Internal Coding Standard"),
                    "section": meta.get("section", "Standard"),
                    "doc_type": meta.get("doc_type", "GUIDELINE"),
                    "content": doc_text,
                    "similarity": round(max(0.0, 1.0 - dist), 3)
                })
        return citations

    def index_code_file(self, project_id: int, file_path: str, code_content: str):
        """Indexes source file snippets for semantic codebase question answering."""
        chunks = self._chunk_text(code_content, chunk_size=500, overlap=80)
        if not chunks:
            return

        embeddings = embedding_service.embed_batch(chunks)
        file_hash = abs(hash(file_path)) % 1000000
        ids = [f"code_{project_id}_{file_hash}_{idx}" for idx in range(len(chunks))]
        metadatas = [
            {
                "project_id": str(project_id),
                "file_path": file_path,
                "chunk_index": idx
            }
            for idx in range(len(chunks))
        ]

        self.codebase_col.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

    def query_codebase(self, project_id: int, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Semantic search across project code chunks."""
        if self.codebase_col.count() == 0:
            return []

        query_emb = embedding_service.embed_text(query_text)
        results = self.codebase_col.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, self.codebase_col.count()),
            where={"project_id": str(project_id)} if project_id else None,
            include=["documents", "metadatas", "distances"]
        )

        matches = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

            for doc_text, meta, dist in zip(docs, metas, distances):
                matches.append({
                    "file_path": meta.get("file_path", "unknown"),
                    "relevant_code": doc_text,
                    "similarity_score": round(max(0.0, 1.0 - dist), 3)
                })
        return matches

    def delete_document(self, doc_id: str):
        """Removes all chunks associated with a document ID."""
        try:
            self.guidelines_col.delete(where={"doc_id": str(doc_id)})
        except Exception:
            pass

rag_service = RAGService()
