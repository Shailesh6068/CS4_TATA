from backend.app.services.embedding_service import embedding_service
from backend.app.services.rag_service import rag_service

def test_local_embeddings():
    vec = embedding_service.embed_text("ECU powertrain sensor controller")
    assert len(vec) == 256
    # Vector is normalized
    import math
    norm = math.sqrt(sum(v*v for v in vec))
    assert 0.99 <= norm <= 1.01

def test_rag_ingest_and_query():
    doc_id = "test_doc_99"
    title = "Test Safety Standard"
    text = "All memory allocation inside ECU sensor loop must be static. Dynamic malloc is prohibited."
    
    chunks = rag_service.ingest_document(doc_id=doc_id, title=title, text=text, project_id=1)
    assert chunks >= 1

    citations = rag_service.query_guidelines("memory allocation malloc", project_id=1, top_k=2)
    assert len(citations) >= 1
    assert "malloc" in citations[0]["content"].lower()

    # Clean up
    rag_service.delete_document(doc_id)
