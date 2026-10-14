import streamlit as st
import pandas as pd
from frontend.api_client import api_client
from backend.app.config import settings as _cfg

# ── helpers ────────────────────────────────────────────────────────────────
_GREEN  = "#10B981"
_RED    = "#EF4444"
_CYAN   = "#06B6D4"
_PURPLE = "#8B5CF6"
_AMBER  = "#F59E0B"
_MUTED  = "#667085"
_BORDER = "#e4e9f0"

_ACTION_COLOR = {
    "PROJECT_CREATED": ("#f0fdfa", "#047857", "#a7f3d0"),
    "FILES_UPLOADED":  ("#eff6ff", "#1d4ed8", "#bfdbfe"),
    "KNOWLEDGE_INGESTED": ("#f5f3ff", "#6d28d9", "#ddd6fe"),
    "KNOWLEDGE_DELETED":  ("#fff5f5", "#b91c1c", "#fecaca"),
    "REPORT_GENERATED":   ("#fffbeb", "#92400e", "#fde68a"),
    "FINDING_UPDATED":    ("#fff7ed", "#c2410c", "#fed7aa"),
    "FIX_VERIFIED":       ("#f0fdf4", "#166534", "#bbf7d0"),
    "REVIEW_COMPLETED":   ("#eff6ff", "#1e40af", "#bfdbfe"),
    "SECURITY_REVIEW_COMPLETED": ("#fef2f2", "#991b1b", "#fecaca"),
    "MISRA_REVIEW_COMPLETED":    ("#fffbeb", "#78350f", "#fde68a"),
}

def _action_badge(action: str) -> str:
    bg, fg, border = _ACTION_COLOR.get(action.upper(), ("#f1f5f9", "#344054", "#e4e9f0"))
    label = action.replace("_", " ").title()
    return (
        f'<span style="background:{bg}; color:{fg}; border:1px solid {border};'
        f' border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:600;">'
        f'{label}</span>'
    )

def render(current_project_id: int):

    # ── hero header ────────────────────────────────────────────────────────
    st.markdown("""
<div class="hero-header-card">
  <div class="hero-title">⚙️ System Settings &amp; Environment Telemetry</div>
  <div class="hero-subtitle">
    Monitor local inference layers, manage Ollama model selection, inspect system
    configuration, and review the tamper-evident engineering audit trail.
  </div>
  <div class="hero-tags">
    <span class="hero-tag green">🔒 Air-Gapped</span>
    <span class="hero-tag cyan">🧠 Local Ollama</span>
    <span class="hero-tag cyan">🗄️ ChromaDB</span>
    <span class="hero-tag">📋 Audit Trail</span>
    <span class="hero-tag">ISO 26262 · MISRA C:2012 · ISO 21434</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── fetch status ───────────────────────────────────────────────────────
    stat    = api_client.get_ollama_status()
    is_conn = stat.get("is_connected", False)
    gpu     = stat.get("gpu_accelerated", False)
    version = stat.get("version") or "—"
    active  = stat.get("active_model", _cfg.OLLAMA_MODEL)
    models  = stat.get("available_models", [])

    # ── status KPI row ─────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    conn_color  = _GREEN if is_conn else _RED
    conn_label  = "CONNECTED" if is_conn else "OFFLINE"
    conn_icon   = "🟢" if is_conn else "🔴"
    conn_sub    = stat.get("base_url", "http://127.0.0.1:11434")

    gpu_color   = _GREEN if gpu else _AMBER
    gpu_label   = "GPU · CUDA" if gpu else "CPU Only"
    gpu_icon    = "⚡" if gpu else "🖥️"

    with c1:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {conn_color};">
  <div class="kpi-title">Ollama LLM Provider</div>
  <div class="kpi-value" style="color:{conn_color}; font-size:1.3rem;">
    {conn_icon} {conn_label}
  </div>
  <div class="kpi-sub" style="word-break:break-all;">{conn_sub}</div>
  <div class="kpi-sub" style="margin-top:4px;">v{version}</div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_CYAN};">
  <div class="kpi-title">Active LLM Model</div>
  <div class="kpi-value" style="color:{_CYAN}; font-size:1.3rem;">{active}</div>
  <div class="kpi-sub">{len(models)} model(s) installed locally</div>
</div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {gpu_color};">
  <div class="kpi-title">Inference Accelerator</div>
  <div class="kpi-value" style="color:{gpu_color}; font-size:1.3rem;">{gpu_icon} {gpu_label}</div>
  <div class="kpi-sub">{"NVIDIA CUDA detected" if gpu else "No GPU detected — CPU mode"}</div>
</div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_PURPLE};">
  <div class="kpi-title">Vector Database</div>
  <div class="kpi-value" style="color:{_PURPLE}; font-size:1.3rem;">🗄️ ChromaDB</div>
  <div class="kpi-sub">Local embeddings · Persistent</div>
  <div class="kpi-sub" style="margin-top:4px; font-size:0.7rem; word-break:break-all;">
    {_cfg.CHROMA_PERSIST_DIR.split("\\")[-2]}/chroma
  </div>
</div>""", unsafe_allow_html=True)

    # ── offline warning + quick-start ──────────────────────────────────────
    if stat.get("backend_offline"):
        st.markdown(f"""
<div style="background:#fffbeb; border:1px solid #fedf89; border-left:5px solid {_AMBER};
            border-radius:10px; padding:16px 20px; margin:14px 0;">
  <div style="font-size:0.95rem; font-weight:700; color:#92400e; margin-bottom:6px;">
    ⚠️ FastAPI Backend API (port 8000) is Offline
  </div>
  <div style="font-size:0.84rem; color:#78350f; line-height:1.6;">
    The dashboard connected directly to Ollama. To enable automated code reviews, file ingestion, and database audit logs, start the backend in a terminal:<br>
    <code style="background:#fef3c7; padding:2px 8px; border-radius:4px; font-weight:600; display:inline-block; margin-top:4px;">
      .\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --port 8000
    </code>
  </div>
</div>""", unsafe_allow_html=True)
    elif not is_conn:
        st.markdown(f"""
<div style="background:#fff5f5; border:1px solid #fecaca; border-left:5px solid {_RED};
            border-radius:10px; padding:18px 22px; margin:16px 0;">
  <div style="font-size:1rem; font-weight:700; color:#991b1b; margin-bottom:10px;">
    ⚠️ Ollama is not running — local LLM inference is unavailable
  </div>
  <div style="font-size:0.85rem; color:#7f1d1d; line-height:1.7;">
    <b>Quick-start steps:</b><br>
    &nbsp;&nbsp;1. Open a new terminal / PowerShell window<br>
    &nbsp;&nbsp;2. Run: <code style="background:#fee2e2; padding:1px 6px; border-radius:4px;">ollama serve</code><br>
    &nbsp;&nbsp;3. Reload this page — status will update automatically<br><br>
    <b>Models already installed:</b>
    <code style="background:#fee2e2; padding:1px 6px; border-radius:4px;">llama3.2:3b</code>&nbsp;
    <code style="background:#fee2e2; padding:1px 6px; border-radius:4px;">qwen3:4b</code>
    &nbsp; (detected via <code>ollama list</code> — no pull needed)
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # MODEL SWITCHER + SYSTEM INFO  (two columns)
    # ══════════════════════════════════════════════════════════════════════
    left_col, right_col = st.columns([1.1, 0.9], gap="large")

    with left_col:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:0;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">🧠 Dynamic Model Selection</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Persists across sessions
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        if models:
            curr_active = stat.get("active_model", "")

            # model chips
            chip_html = "<div style='display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 14px;'>"
            for m in models:
                is_active = (m == curr_active)
                bg = "#f0fdfa" if is_active else "#f8fafc"
                border = "#0f766e" if is_active else "#e4e9f0"
                fg = "#0f766e" if is_active else "#475467"
                check = "✓ " if is_active else ""
                size_hint = "2.0 GB" if "3b" in m else ("2.5 GB" if "4b" in m else "~")
                chip_html += (
                    f'<div style="background:{bg}; border:1.5px solid {border}; border-radius:8px;'
                    f' padding:8px 14px; font-size:0.8rem; font-weight:600; color:{fg};">'
                    f'{check}🤖 {m}<br>'
                    f'<span style="font-size:0.7rem; font-weight:400; color:{_MUTED};">'
                    f'{size_hint} · Local</span></div>'
                )
            chip_html += "</div>"
            st.markdown(chip_html, unsafe_allow_html=True)

            sel_model = st.selectbox(
                "Select Model to Activate",
                options=models,
                index=models.index(curr_active) if curr_active in models else 0,
                label_visibility="collapsed",
            )

            if st.button("⚡ Switch Active Model", use_container_width=True, type="primary"):
                res = api_client.switch_ollama_model(sel_model)
                if isinstance(res, dict) and "error" in res:
                    st.error(f"Failed: {res['error']}")
                else:
                    st.success(f"✅ Switched to **{sel_model}** — active for all inference operations.")
                    st.rerun()
        else:
            st.markdown(f"""
<div style="background:#fffbeb; border:1px solid #fde68a; border-left:4px solid {_AMBER};
            border-radius:8px; padding:16px 18px; margin:8px 0;">
  <div style="font-weight:700; color:#92400e; margin-bottom:8px;">
    📦 No Installed Models Detected
  </div>
  <div style="font-size:0.85rem; color:#78350f; line-height:1.7;">
    Pull a model to get started:<br>
    <code style="background:#fef3c7; padding:2px 8px; border-radius:4px;">
      ollama pull llama3.2:3b
    </code><br>
    <code style="background:#fef3c7; padding:2px 8px; border-radius:4px; margin-top:4px; display:inline-block;">
      ollama pull qwen3:4b
    </code>
  </div>
</div>""", unsafe_allow_html=True)

    with right_col:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:0;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">🖥️ System Configuration</span>
  </div>
</div>""", unsafe_allow_html=True)

        rows = [
            ("API Prefix",      _cfg.API_PREFIX),
            ("Ollama URL",      _cfg.OLLAMA_BASE_URL),
            ("Default Model",   _cfg.OLLAMA_MODEL),
            ("Timeout",         f"{_cfg.OLLAMA_TIMEOUT_SECONDS}s"),
            ("Max Upload",      f"{_cfg.MAX_UPLOAD_SIZE_MB} MB"),
            ("Chunk Size",      f"{_cfg.CHUNK_SIZE} tokens"),
            ("Chunk Overlap",   f"{_cfg.CHUNK_OVERLAP} tokens"),
            ("RAG Top-K",       str(_cfg.TOP_K_RETRIEVAL)),
            ("Privacy Mode",    "✅ Enforced" if _cfg.ENABLE_LOCAL_PRIVACY_ENFORCEMENT else "⚠️ Disabled"),
        ]
        for label, value in rows:
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center;"
                f" padding:7px 0; border-bottom:1px solid {_BORDER}; font-size:0.82rem;'>"
                f"<span style='color:{_MUTED}; font-weight:500;'>{label}</span>"
                f"<span style='color:#172033; font-weight:600; font-family:monospace;"
                f" background:#f8fafc; padding:2px 8px; border-radius:5px;"
                f" border:1px solid {_BORDER}; font-size:0.78rem;'>{value}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════════════════════════════════
    # AUDIT TRAIL
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:0;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">📋 Relational Audit Trail</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Tamper-Evident · Auto-Redacted
    </span>
  </div>
</div>""", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.82rem; color:#667085; margin:4px 0 12px;'>"
        "Chronological record of all reviews, file uploads, knowledge ingestion, "
        "findings updates, and report generation. Sensitive fields are auto-redacted.</div>",
        unsafe_allow_html=True,
    )

    audit_logs = api_client.get_audit_logs(current_project_id)
    if audit_logs:
        # show last 50 in a styled table
        df = pd.DataFrame(audit_logs)
        # reorder columns for readability
        preferred = ["id", "action", "user", "target_type", "target_id", "details", "timestamp"]
        df = df[[c for c in preferred if c in df.columns]]
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # coloured action summary chips
        st.markdown("<div style='margin-top:14px; font-size:0.8rem; font-weight:600;"
                    " color:#344054; margin-bottom:8px;'>Action Summary</div>",
                    unsafe_allow_html=True)
        action_counts: dict = {}
        for entry in audit_logs:
            a = entry.get("action", "UNKNOWN")
            action_counts[a] = action_counts.get(a, 0) + 1

        chips = "".join(
            f'<span style="display:inline-flex; align-items:center; gap:5px; margin:3px;">'
            + _action_badge(action)
            + f'<span style="font-size:0.75rem; color:{_MUTED}; font-weight:600;">×{cnt}</span></span>'
            for action, cnt in sorted(action_counts.items(), key=lambda x: -x[1])
        )
        st.markdown(f"<div style='display:flex; flex-wrap:wrap; gap:4px;'>{chips}</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="empty-state-card" style="padding:36px 24px;">
  <div class="empty-state-icon">📋</div>
  <div class="empty-state-title">No Audit Events Yet</div>
  <div class="empty-state-sub">
    Events are recorded automatically when you upload files, run reviews,
    ingest knowledge documents, or update findings.
  </div>
</div>""", unsafe_allow_html=True)

    # ── footer compliance strip ────────────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:#9ca3af;"
        " border-top:1px solid #e4e9f0; padding-top:14px;'>"
        "SECURECODE AI v1.0.0 &nbsp;·&nbsp; ISO 26262 &nbsp;·&nbsp; "
        "MISRA C:2012 &nbsp;·&nbsp; ISO 21434 &nbsp;·&nbsp; "
        "100% Local Processing — No Cloud APIs</div>",
        unsafe_allow_html=True,
    )

