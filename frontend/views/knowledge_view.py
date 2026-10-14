import os
import streamlit as st
import pandas as pd
from frontend.api_client import api_client

# ── Color constants ──────────────────────────────────────────────────────────
_GREEN  = "#10B981"
_CYAN   = "#06B6D4"
_PURPLE = "#8B5CF6"
_AMBER  = "#F59E0B"
_RED    = "#EF4444"
_MUTED  = "#667085"
_BORDER = "#e4e9f0"

_TYPE_TAGS = {
    "GUIDELINE":     ("#f0fdfa", "#0f766e", "#99f6e4", "📘 Guideline"),
    "STANDARD":      ("#eff6ff", "#1d4ed8", "#bfdbfe", "🛡️ Standard"),
    "SPECIFICATION": ("#f5f3ff", "#6d28d9", "#ddd6fe", "📐 Specification"),
    "MISRA_RULES":   ("#fffbeb", "#92400e", "#fde68a", "⚖️ MISRA Rules"),
}

def _doc_type_badge(doc_type: str) -> str:
    bg, fg, border, label = _TYPE_TAGS.get(
        doc_type.upper(), ("#f8fafc", "#475467", "#e2e8f0", doc_type)
    )
    return (
        f'<span style="background:{bg}; color:{fg}; border:1px solid {border};'
        f' border-radius:5px; padding:2px 8px; font-size:0.73rem; font-weight:600;">'
        f'{label}</span>'
    )


def render(current_project_id: int):
    # ── 1. Hero Header ────────────────────────────────────────────────────────
    st.markdown("""
<div class="hero-header-card">
  <div class="hero-title">📚 Approved Guidelines &amp; RAG Knowledge Base</div>
  <div class="hero-subtitle">
    Ingest automotive engineering standards, MISRA C/C++ compliance rules, ISO 26262/21434 safety manuals,
    and ECU specifications into ChromaDB vector memory. AI code reviews and explanations ground their findings
    with verifiable, tamper-evident citations directly from these documents.
  </div>
  <div class="hero-tags">
    <span class="hero-tag green">🔒 Air-Gapped ChromaDB</span>
    <span class="hero-tag cyan">🧠 Local Embeddings</span>
    <span class="hero-tag">🛡️ ISO 26262 Part 6</span>
    <span class="hero-tag">⚖️ MISRA C:2012</span>
    <span class="hero-tag">🏎️ RAG Grounding Engine</span>
    <span class="hero-tag">⚡ Zero Cloud Egress</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 2. Fetch documents & Telemetry ─────────────────────────────────────────
    docs = api_client.list_knowledge()
    total_docs = len(docs)
    total_chunks = sum(d.get("chunk_count", 0) for d in docs)
    unique_types = len(set(d.get("document_type", "") for d in docs))

    # ── 3. KPI Telemetry Row ───────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_CYAN};">
  <div class="kpi-title">Ingested Documents</div>
  <div class="kpi-value" style="color:{_CYAN};">{total_docs}</div>
  <div class="kpi-sub">Approved engineering standards</div>
</div>""", unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_PURPLE};">
  <div class="kpi-title">Indexed Vector Chunks</div>
  <div class="kpi-value" style="color:{_PURPLE};">{total_chunks}</div>
  <div class="kpi-sub">600-token sliding windows in ChromaDB</div>
</div>""", unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_GREEN};">
  <div class="kpi-title">Standards Categories</div>
  <div class="kpi-value" style="color:{_GREEN};">{unique_types}</div>
  <div class="kpi-sub">Guidelines · Standards · MISRA · Specs</div>
</div>""", unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_AMBER};">
  <div class="kpi-title">RAG Vector Store</div>
  <div class="kpi-value" style="color:{_AMBER}; font-size:1.35rem;">ChromaDB</div>
  <div class="kpi-sub">Local persistent · Top-K = 4</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # ── 4. Main Two-Column Layout ──────────────────────────────────────────────
    col_upload, col_library = st.columns([1.05, 0.95], gap="large")

    # ── Left Column: Upload & Ingest ──────────────────────────────────────────
    with col_upload:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">📤 Ingest Engineering Specification</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Auto-Chunked &amp; Vectorized
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        with st.form("upload_kb_form", clear_on_submit=False):
            doc_title = st.text_input(
                "Document Title",
                placeholder="e.g., ISO 26262-6 Software Unit Safety Specification",
                help="Descriptive title used in RAG citation references"
            )

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                doc_type = st.selectbox(
                    "Standard Category",
                    ["GUIDELINE", "STANDARD", "SPECIFICATION", "MISRA_RULES"],
                    format_func=lambda x: {
                        "GUIDELINE": "📘 Guideline (Safety / Quality)",
                        "STANDARD": "🛡️ Standard (ISO / SAE)",
                        "SPECIFICATION": "📐 Specification (ECU HW/SW)",
                        "MISRA_RULES": "⚖️ MISRA Rules (C:2012 / C++:2023)"
                    }.get(x, x)
                )
            with col_t2:
                doc_ver = st.text_input("Version / Release", value="2026.1")

            owner = st.text_input("Owner / Approver", value="Automotive Safety Lead")

            doc_file = st.file_uploader(
                "Upload Source Document (.md, .txt, .pdf)",
                type=["md", "txt", "pdf"],
                help="Plain text, Markdown, or PDF documents are parsed and vectorized locally."
            )

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            submit_kb = st.form_submit_button(
                "🚀 Ingest into ChromaDB Vector Store",
                use_container_width=True,
                type="primary"
            )

            if submit_kb:
                if not doc_title.strip():
                    st.warning("⚠️ Please provide a Document Title.")
                elif not doc_file:
                    st.warning("⚠️ Please select a file to upload.")
                else:
                    with st.spinner("Tokenizing document and generating embeddings for ChromaDB..."):
                        res = api_client.upload_knowledge(
                            title=doc_title.strip(),
                            doc_type=doc_type,
                            version=doc_ver.strip(),
                            file_tuple=(doc_file.name, doc_file.getvalue(), doc_file.type or "application/octet-stream"),
                            project_id=current_project_id
                        )
                        if "document_id" in res:
                            st.success(f"✅ {res.get('message', 'Document ingested successfully!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ Ingestion failed: {res.get('error', 'Unknown error')}")

        # Quick preset load
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">⚡ Quick-Load Automotive Test Guidelines</span>
  </div>
</div>""", unsafe_allow_html=True)

        spec_path = os.path.abspath("sample_project/Vehicle_ECU/docs/ECU_Software_Spec.md")
        spec_exists = os.path.exists(spec_path)

        st.markdown(f"""
<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 16px; margin-bottom:12px; font-size:0.83rem; color:#475467;">
  <b>Included Test Asset:</b> <code>sample_project/Vehicle_ECU/docs/ECU_Software_Spec.md</code><br>
  Contains ISO 26262 ASIL-D safety requirements, watchdog timings, MISRA C:2012 deviations,
  and CAN bus error thresholds.
</div>""", unsafe_allow_html=True)

        if st.button("🏎️ Ingest Sample 'ECU Software Safety & Coding Guidelines'", use_container_width=True):
            if spec_exists:
                with st.spinner("Ingesting ECU Software Safety Specification..."):
                    with open(spec_path, "rb") as sf:
                        contents = sf.read()
                    res = api_client.upload_knowledge(
                        title="Automotive ECU Software Safety & Coding Guidelines",
                        doc_type="GUIDELINE",
                        version="2026.1",
                        file_tuple=("ECU_Software_Spec.md", contents, "text/markdown"),
                        project_id=current_project_id
                    )
                    if "document_id" in res:
                        st.success("✅ Sample guidelines ingested into local RAG knowledge base!")
                        st.rerun()
                    else:
                        st.error(f"❌ Ingestion failed: {res.get('error', 'Unknown error')}")
            else:
                st.error(f"Sample spec file not found at `{spec_path}`")

    # ── Right Column: Ingested Standards Library ──────────────────────────────
    with col_library:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">📑 Ingested Standards Library</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Active RAG Sources
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        if docs:
            # Summary Table
            table_rows = []
            for d in docs:
                table_rows.append({
                    "ID": d.get("id"),
                    "Title": d.get("title"),
                    "Type": d.get("document_type"),
                    "Ver": d.get("version"),
                    "Chunks": d.get("chunk_count", 0),
                    "Status": "Approved" if d.get("is_approved") else "Pending",
                })
            st.dataframe(
                pd.DataFrame(table_rows),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            # Details cards for each doc
            st.markdown("<div style='font-size:0.85rem; font-weight:600; color:#344054; margin-bottom:8px;'>Document Details</div>", unsafe_allow_html=True)
            for d in docs:
                badge_html = _doc_type_badge(d.get("document_type", "GUIDELINE"))
                st.markdown(f"""
<div style="background:#ffffff; border:1px solid {_BORDER}; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
  <div>
    <div style="font-weight:600; font-size:0.88rem; color:#172033; display:flex; align-items:center; gap:8px;">
      {d.get('title')} {badge_html}
    </div>
    <div style="font-size:0.75rem; color:{_MUTED}; margin-top:3px;">
      v{d.get('version')} · {d.get('chunk_count', 0)} vector chunks · Owner: {d.get('owner', 'Safety Team')}
    </div>
  </div>
  <span style="background:#ecfdf5; color:#047857; border:1px solid #a7f3d0; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:600;">
    ✅ Approved
  </span>
</div>""", unsafe_allow_html=True)

            # Delete section
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.85rem; font-weight:600; color:#b42318;'>Manage / Delete Standard</div>", unsafe_allow_html=True)
            
            doc_options = {d["id"]: f"ID {d['id']}: {d.get('title')} (v{d.get('version')})" for d in docs}
            del_id = st.selectbox(
                "Select Guideline to Remove",
                options=list(doc_options.keys()),
                format_func=lambda x: doc_options.get(x, str(x)),
                label_visibility="collapsed"
            )

            if st.button("🗑️ Delete Selected Document & Purge Embeddings", type="secondary", use_container_width=True):
                res = api_client.delete_knowledge(del_id)
                if isinstance(res, dict) and "error" in res:
                    st.error(f"Failed to delete: {res['error']}")
                else:
                    st.success(f"✅ Document {del_id} and associated vector embeddings removed.")
                    st.rerun()

        else:
            st.markdown("""
<div class="empty-state-card" style="padding:36px 20px;">
  <div class="empty-state-icon">📚</div>
  <div class="empty-state-title">No Knowledge Documents Ingested Yet</div>
  <div class="empty-state-sub">
    Upload an automotive safety standard, MISRA ruleset, or click the Quick-Load button
    on the left to ingest the sample ECU Software Safety Specification.
  </div>
</div>""", unsafe_allow_html=True)

    # ── 5. Interactive RAG Query & Citation Simulator ──────────────────────────
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">🔍 RAG Retrieval Simulator &amp; Citation Inspector</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      ChromaDB Semantic Query
    </span>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.85rem; color:#475467; margin-bottom:12px;'>"
        "Test how the local vector database matches engineering queries against ingested standards. "
        "During automated reviews, these exact chunks are retrieved and provided to the LLM as grounding context."
        "</div>",
        unsafe_allow_html=True
    )

    preset_queries = [
        "What is the watchdog timeout policy for ECU recovery?",
        "What are the safety requirements for pointer validation?",
        "MISRA rule regarding dynamic memory allocation in safety critical code",
        "CAN bus baud rate and error passive handling specifications"
    ]

    selected_query_chip = st.radio(
        "Example Automotive Queries:",
        preset_queries,
        horizontal=True,
        index=0
    )

    col_q1, col_q2 = st.columns([4, 1])
    with col_q1:
        test_query = st.text_input(
            "Semantic Query Text",
            value=selected_query_chip,
            placeholder="Type a technical question or requirement to retrieve citations...",
            label_visibility="collapsed"
        )
    with col_q2:
        top_k = st.number_input("Top K", min_value=1, max_value=8, value=3, label_visibility="collapsed")

    if st.button("🔎 Search Vector Memory", use_container_width=True, type="primary"):
        if not test_query.strip():
            st.warning("Please enter a query.")
        else:
            with st.spinner("Computing query embeddings & searching ChromaDB..."):
                res = api_client.query_knowledge(
                    query=test_query.strip(),
                    project_id=current_project_id,
                    top_k=top_k
                )

            citations = res.get("citations", []) if isinstance(res, dict) else []
            if citations:
                st.markdown(f"<div style='font-weight:600; font-size:0.9rem; color:#0f766e; margin:14px 0 10px;'>🎯 Retrieved {len(citations)} Relevant Citation(s):</div>", unsafe_allow_html=True)
                for idx, c in enumerate(citations, 1):
                    sim = c.get("similarity", 0.0)
                    sim_pct = int(sim * 100) if sim > 0 else 0
                    doc_t = c.get("doc_type", "GUIDELINE")
                    badge = _doc_type_badge(doc_t)

                    st.markdown(f"""
<div class="analysis-section" style="border-left-color:{_CYAN}; margin-bottom:12px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
    <span style="font-weight:700; color:#172033; font-size:0.92rem;">
      Citation #{idx}: {c.get('title')} ({c.get('section')})
    </span>
    <div style="display:flex; align-items:center; gap:8px;">
      {badge}
      <span style="background:#ecfeff; color:#0e7490; border:1px solid #a5f3fc; border-radius:5px; padding:2px 8px; font-size:0.75rem; font-weight:700;">
        {sim_pct}% Relevance
      </span>
    </div>
  </div>
  <div style="font-size:0.85rem; color:#334155; line-height:1.6; background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 14px; font-family:monospace; white-space:pre-wrap;">
{c.get('content', '')}
  </div>
</div>""", unsafe_allow_html=True)
            else:
                if total_docs == 0:
                    st.info("ℹ️ No citations found because no documents are ingested yet. Ingest a document above.")
                else:
                    st.warning("⚠️ No matching chunks found for this query in the vector database.")

    # ── 6. Compliance Footer ──────────────────────────────────────────────────
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:#9ca3af;"
        " border-top:1px solid #e4e9f0; padding-top:14px;'>"
        "SECURECODE AI v1.0.0 &nbsp;·&nbsp; ISO 26262 &nbsp;·&nbsp; "
        "MISRA C:2012 &nbsp;·&nbsp; ISO 21434 &nbsp;·&nbsp; "
        "100% Local RAG Embeddings &amp; Vector Store</div>",
        unsafe_allow_html=True,
    )
