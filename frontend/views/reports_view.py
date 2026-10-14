import json
import os
import requests
import streamlit as st
from frontend.api_client import api_client, BACKEND_URL

# ── Color constants ──────────────────────────────────────────────────────────
_CYAN   = "#06B6D4"
_PURPLE = "#8B5CF6"
_GREEN  = "#10B981"
_AMBER  = "#F59E0B"
_RED    = "#EF4444"
_MUTED  = "#667085"
_BORDER = "#e4e9f0"


def render(current_project_id: int):
    # ── 1. Hero Header ────────────────────────────────────────────────────────
    st.markdown("""
<div class="hero-header-card">
  <div class="hero-title">📑 Engineering Review &amp; Compliance Reports</div>
  <div class="hero-subtitle">
    Compile auditable, multi-standard compliance reports across ISO 26262, MISRA C:2012, and ISO 21434.
    Export executive summaries, line-level findings matrices, and RAG guideline citations for internal review or formal certification bodies.
  </div>
  <div class="hero-tags">
    <span class="hero-tag cyan">📑 Formal Audit Docs</span>
    <span class="hero-tag green">🛡️ ISO 26262 Evidence</span>
    <span class="hero-tag">⚖️ MISRA C:2012 Compliance</span>
    <span class="hero-tag">🔒 Tamper-Evident</span>
    <span class="hero-tag">🏎️ Multi-Format Export</span>
  </div>
</div>
""", unsafe_allow_html=True)

    if not current_project_id:
        st.markdown("""
<div class="empty-state-card" style="padding:36px 20px;">
  <div class="empty-state-icon">📁</div>
  <div class="empty-state-title">No Active Project Selected</div>
  <div class="empty-state-sub">
    Please select or create an automotive project from the sidebar to generate compliance reports.
  </div>
</div>""", unsafe_allow_html=True)
        return

    # ── 2. Telemetry Row ───────────────────────────────────────────────────────
    findings = api_client.list_findings(project_id=current_project_id)
    total_findings = len(findings)
    high_critical = sum(1 for f in findings if f.get("severity") in ("CRITICAL", "HIGH"))
    verified_fixes = sum(1 for f in findings if f.get("status") in ("VERIFIED", "RESOLVED"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_CYAN};">
  <div class="kpi-title">Total Project Findings</div>
  <div class="kpi-value" style="color:{_CYAN};">{total_findings}</div>
  <div class="kpi-sub">Static, Security &amp; MISRA</div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {'#EF4444' if high_critical > 0 else _GREEN};">
  <div class="kpi-title">High / Critical Vulnerabilities</div>
  <div class="kpi-value" style="color:{'#EF4444' if high_critical > 0 else _GREEN};">{high_critical}</div>
  <div class="kpi-sub">Requires safety justification</div>
</div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_GREEN};">
  <div class="kpi-title">Verified Remediations</div>
  <div class="kpi-value" style="color:{_GREEN};">{verified_fixes}</div>
  <div class="kpi-sub">AI verified against spec</div>
</div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_PURPLE};">
  <div class="kpi-title">Supported Formats</div>
  <div class="kpi-value" style="color:{_PURPLE}; font-size:1.3rem;">PDF · MD · JSON · CSV</div>
  <div class="kpi-sub">Executive &amp; machine-readable</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── 3. Two Column Layout: Configuration & Output ──────────────────────────
    col_config, col_output = st.columns([1, 1.4], gap="large")

    with col_config:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">⚙️ Report Export Configuration</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Automated Compilation
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        format_info = {
            "markdown": ("📘 Markdown (.md)", "Full engineering technical dossier with embedded code snippets, diffs, and citations."),
            "pdf": ("📕 Executive PDF (.pdf)", "Formal document suitable for safety certification boards, customer delivery, and sign-off."),
            "json": ("🗄️ Structured JSON (.json)", "Machine-readable payload for CI/CD pipelines, defect trackers, and compliance automation."),
            "csv": ("📊 Spreadsheet CSV (.csv)", "Tabular findings register ideal for Excel tracking, auditor sign-offs, and triage meetings.")
        }

        rep_format = st.selectbox(
            "Select Output Format",
            options=list(format_info.keys()),
            format_func=lambda x: format_info[x][0],
            index=0
        )

        st.markdown(f"""
<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 14px; margin:8px 0 16px; font-size:0.83rem; color:#475467; line-height:1.5;">
  <b>Format Description:</b><br>{format_info[rep_format][1]}
</div>""", unsafe_allow_html=True)

        submit_gen = st.button("📄 Compile &amp; Generate Report", use_container_width=True, type="primary")

        st.markdown("""
<div style="background:#fffbeb; border:1px solid #fedf89; border-left:4px solid #f79009;
            border-radius:0 8px 8px 0; padding:12px 14px; margin-top:16px; font-size:0.82rem; color:#9a3412; line-height:1.5;">
  <b>Compliance Notice:</b> Reports are generated entirely on-premises using the local SQLite findings repository and ChromaDB RAG vector index. No proprietary engineering telemetry leaves this workstation.
</div>""", unsafe_allow_html=True)

    with col_output:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">📦 Compiled Report &amp; Artifact Download</span>
  </div>
</div>""", unsafe_allow_html=True)

        if submit_gen:
            with st.spinner(f"Compiling {rep_format.upper()} audit report with findings register and citations..."):
                res = api_client.generate_report(current_project_id, format=rep_format)

            if "error" in res:
                st.error(f"❌ Report generation failed: {res['error']}")
            else:
                fname = res.get("filename", f"report.{rep_format}")
                st.markdown(f"""
<div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:8px; padding:12px 16px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center;">
  <span style="font-weight:600; font-size:0.88rem; color:#047857;">
    ✅ Successfully Compiled: <code>{fname}</code>
  </span>
  <span style="font-size:0.75rem; background:#ffffff; border:1px solid #6ee7b7; color:#065f46; font-weight:700; padding:2px 8px; border-radius:4px;">
    {rep_format.upper()}
  </span>
</div>""", unsafe_allow_html=True)

                if rep_format == "pdf":
                    rel_url = res.get("report_url", "")
                    if rel_url.startswith("http"):
                        download_url = rel_url
                    elif rel_url.startswith("/api/v1") and BACKEND_URL.endswith("/api/v1"):
                        download_url = f"{BACKEND_URL[:-len('/api/v1')]}{rel_url}"
                    else:
                        download_url = f"{BACKEND_URL.rstrip('/')}/{rel_url.lstrip('/')}"

                    try:
                        pdf_resp = requests.get(download_url, timeout=30)
                        pdf_resp.raise_for_status()
                        st.download_button(
                            label=f"⬇️ Download {fname}",
                            data=pdf_resp.content,
                            file_name=fname,
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                    except Exception as pdf_err:
                        st.error(f"PDF download failed: {pdf_err}")
                else:
                    content_str = res.get("content", "")
                    mime_types = {
                        "markdown": "text/markdown",
                        "json": "application/json",
                        "csv": "text/csv"
                    }
                    st.download_button(
                        label=f"⬇️ Download {fname}",
                        data=content_str,
                        file_name=fname,
                        mime=mime_types.get(rep_format, "text/plain"),
                        use_container_width=True,
                        type="primary"
                    )

                    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
                    st.markdown("<div style='font-size:0.88rem; font-weight:600; color:#344054; margin-bottom:6px;'>Report Preview</div>", unsafe_allow_html=True)

                    if rep_format == "markdown":
                        st.markdown(f"""
<div style="max-height:480px; overflow-y:auto; border:1px solid {_BORDER}; border-radius:8px; padding:16px 20px; background:#ffffff;">
""", unsafe_allow_html=True)
                        st.markdown(content_str)
                        st.markdown("</div>", unsafe_allow_html=True)
                    elif rep_format == "json":
                        try:
                            st.json(json.loads(content_str))
                        except Exception:
                            st.code(content_str, language="json")
                    elif rep_format == "csv":
                        st.code(content_str, language="csv")

        else:
            st.markdown("""
<div class="empty-state-card" style="padding:48px 24px;">
  <div class="empty-state-icon">📄</div>
  <div class="empty-state-title">Ready to Compile Report</div>
  <div class="empty-state-sub">
    Select your preferred report format on the left and click <b>Compile &amp; Generate Report</b>.
    A live preview and download link will appear here.
  </div>
</div>""", unsafe_allow_html=True)

    # ── 4. Compliance Footer ──────────────────────────────────────────────────
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:#9ca3af;"
        " border-top:1px solid #e4e9f0; padding-top:14px;'>"
        "SECURECODE AI v1.0.0 &nbsp;·&nbsp; ISO 26262 &nbsp;·&nbsp; "
        "MISRA C:2012 &nbsp;·&nbsp; ISO 21434 &nbsp;·&nbsp; "
        "Automated Air-Gapped Compliance Reporting</div>",
        unsafe_allow_html=True,
    )
