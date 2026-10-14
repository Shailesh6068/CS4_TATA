import json
import streamlit as st
import pandas as pd
from frontend.api_client import api_client

# ── Color tokens ─────────────────────────────────────────────────────────────
_RED    = "#EF4444"
_AMBER  = "#F59E0B"
_CYAN   = "#06B6D4"
_PURPLE = "#8B5CF6"
_GREEN  = "#10B981"
_BLUE   = "#3B82F6"
_MUTED  = "#667085"
_BORDER = "#e4e9f0"

_SEV_BADGE = {
    "CRITICAL": ("#fef2f2", "#991b1b", "#fecaca", "🔴 CRITICAL"),
    "HIGH":     ("#fff7ed", "#c2410c", "#fed7aa", "🟠 HIGH"),
    "MEDIUM":   ("#fffbeb", "#92400e", "#fde68a", "🟡 MEDIUM"),
    "LOW":      ("#f0fdf4", "#166534", "#bbf7d0", "🟢 LOW"),
    "INFO":     ("#eff6ff", "#1e40af", "#bfdbfe", "ℹ️ INFO"),
}

_CAT_ICONS = {
    "MemorySafety": "🧠 Memory Safety",
    "ArrayBounds": "📏 Array & Bounds",
    "ResourceManagement": "📦 Resource Mgmt",
    "UnsafeFunctions": "⚠️ Unsafe Functions",
    "Correctness": "🎯 Correctness",
    "Security": "🛡️ Security / CWE",
    "AutomotiveEmbedded": "🏎️ Automotive / MISRA",
    "Performance": "⚡ Performance",
    "Maintainability": "🧹 Maintainability",
    "General": "📋 General Defect",
    "StaticAnalysis": "🔍 Static Rule"
}

def _sev_badge_html(sev: str) -> str:
    s = str(sev).upper()
    bg, fg, border, label = _SEV_BADGE.get(s, ("#f8fafc", "#475467", "#e2e8f0", s))
    return (
        f'<span style="background:{bg}; color:{fg}; border:1px solid {border};'
        f' border-radius:5px; padding:2px 8px; font-size:0.73rem; font-weight:700;">'
        f'{label}</span>'
    )

def _cat_badge_html(cat: str) -> str:
    label = _CAT_ICONS.get(cat, cat)
    return (
        f'<span style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1;'
        f' border-radius:5px; padding:2px 8px; font-size:0.73rem; font-weight:600;">'
        f'{label}</span>'
    )

# ── Sample Automotive Code Presets ───────────────────────────────────────────
PRESETS = {
    "Select a vulnerability preset...": "",
    "1. Heap Buffer Overflow (strlen allocation + strcpy)": """// ISO 26262 ASIL-B Safety Violation: Missing null terminator allocation
#include <string.h>
#include <stdlib.h>

void updateVehicleIdentifier(const char* vehicleName) {
    // Defect: strlen() does not include the null-terminator (+1)
    char* name = new char[strlen(vehicleName)];
    strcpy(name, vehicleName);
    
    // Additional logic...
    delete[] name;
}
""",
    "2. Array Out-of-Bounds & Off-by-One Loop": """// Array boundary safety violation
#include <stdint.h>

void processSensorSamples() {
    int sensorValues[10];
    
    // Defect: Off-by-one loop condition iterates 11 times on size 10
    for (int i = 0; i <= 10; i++) {
        sensorValues[i] = i * 5;
    }
    
    // Defect: Direct access at invalid index
    int lastSample = sensorValues[10];
}
""",
    "3. Mismatched Allocation/Deallocation (new[] with delete)": """// C++ Resource Management Defect: Mismatched delete
#include <stdlib.h>

class TelemetryPacket {
public:
    uint8_t* payload;
    
    TelemetryPacket(size_t size) {
        // Allocated as array
        payload = new uint8_t[size];
    }
    
    ~TelemetryPacket() {
        // Defect: Scalar delete used for array allocation new[]
        delete payload;
    }
};
""",
    "4. Unsafe Functions & Unchecked CAN Frame Unpack": """// Automotive CAN Gateway Safety Defect
#include <string.h>
#include <stdio.h>

struct CanFrame {
    uint32_t id;
    uint8_t dlc;
    uint8_t data[64];
};

void handleIncomingDiagnostic(const CanFrame* frame) {
    char diagnosticBuffer[32];
    
    // Defect: Unchecked CAN payload copy without validating DLC against buffer size
    memcpy(diagnosticBuffer, frame->data, frame->dlc);
    
    // Defect: Unsafe sprintf with unbounded formatting
    char logMsg[64];
    sprintf(logMsg, "Frame received: %s", diagnosticBuffer);
}
"""
}


def render(current_project_id: int):
    # ── 1. Hero Header ────────────────────────────────────────────────────────
    st.markdown("""
<div class="hero-header-card">
  <div class="hero-title">📋 Comprehensive Multi-Pass Code Review</div>
  <div class="hero-subtitle">
    Execute a thorough 8-pass multi-layered source code inspection fusing deterministic static analyzers,
    local Ollama reasoning, and RAG engineering guidelines. Detects actual memory corruption defects,
    array boundary violations, C/C++ resource leaks, dangerous functions, logic bugs, and MISRA/ISO 26262 compliance issues.
  </div>
  <div class="hero-tags">
    <span class="hero-tag red">🧠 Memory Safety</span>
    <span class="hero-tag cyan">📏 Array Bounds &amp; Loops</span>
    <span class="hero-tag">📦 Resource Ownership</span>
    <span class="hero-tag">⚠️ Unsafe APIs</span>
    <span class="hero-tag">🎯 Logic Correctness</span>
    <span class="hero-tag green">🛡️ CWE &amp; Security</span>
    <span class="hero-tag">⚖️ MISRA C:2012 / C++:2008</span>
    <span class="hero-tag">🏎️ ISO 26262 Part 6</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 2. Two-Column Layout (Input Config & Execution) ─────────────────────────
    col_input, col_output = st.columns([1, 1.25], gap="large")

    files = api_client.list_project_files(current_project_id) if current_project_id else []

    with col_input:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">🎯 Review Scope &amp; Target Code</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Line-by-Line Inspection
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        scope_choice = st.radio("Review Target Mode", ["Custom Code Snippet", "Indexed Project File"], horizontal=True)

        target_name = "snippet.cpp"
        code_to_send = ""
        paths_to_send = None

        if scope_choice == "Custom Code Snippet":
            # Quick preset selector
            selected_preset = st.selectbox(
                "⚡ Quick Load Automotive Defect Test Cases",
                options=list(PRESETS.keys()),
                index=0
            )
            default_snippet = PRESETS[selected_preset] if selected_preset != "Select a vulnerability preset..." else ""

            code_to_send = st.text_area(
                "Source Code (C, C++, or Python)",
                value=default_snippet,
                height=280,
                placeholder="// Paste automotive C/C++ or systems code here...\nvoid updateVehicle() {\n    ...\n}"
            )
            target_name = st.text_input("File Name & Extension", value="ecu_control.cpp")

        else:
            if not files:
                st.info("ℹ️ No indexed files found in active workspace. Create a project and upload files in 'Projects' or choose 'Custom Code Snippet' above.")
            else:
                file_options = {f["id"]: f["relative_path"] for f in files}
                sel_id = st.selectbox("Select Project File", options=list(file_options.keys()), format_func=lambda x: f"📄 {file_options[x]}")
                sel_f = next((f for f in files if f["id"] == sel_id), None)
                if sel_f:
                    target_name = sel_f["relative_path"]
                    paths_to_send = [target_name]
                    file_res = api_client.get_file_content(current_project_id, sel_id)
                    if isinstance(file_res, dict) and "content" in file_res:
                        code_to_send = file_res["content"]
                    st.code(code_to_send[:500] + ("\n... [truncated for preview]" if len(code_to_send) > 500 else ""), language="cpp")

        use_rag = st.checkbox("Augment with Internal Engineering Guidelines (RAG)", value=True, help="Retrieves relevant clauses from approved ISO 26262/MISRA guidelines in ChromaDB.")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        submit_review = st.button("🚀 Execute Multi-Pass Code Review", use_container_width=True, type="primary")

        # Multi-pass protocol info
        st.markdown(f"""
<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px 16px; margin-top:16px; font-size:0.8rem; color:#475467; line-height:1.6;">
  <b>Active Analysis Protocol (8 Passes):</b><br>
  1. Syntax &amp; Type Signatures &nbsp;|&nbsp; 2. Memory &amp; Pointer Safety<br>
  3. Array Bounds &amp; Loops &nbsp;|&nbsp; 4. Resource Allocation &amp; RAII<br>
  5. Unsafe Functions &amp; Formats &nbsp;|&nbsp; 6. Logic &amp; Correctness<br>
  7. MISRA / ISO 26262 / Security &nbsp;|&nbsp; 8. Performance &amp; Maintainability
</div>""", unsafe_allow_html=True)

    with col_output:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:16px;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">📊 Multi-Layered Review Findings</span>
  </div>
</div>""", unsafe_allow_html=True)

        if submit_review:
            if not code_to_send.strip() and not paths_to_send:
                st.warning("⚠️ Please provide or select code to review.")
            else:
                with st.spinner("Executing 8-Pass analysis: static analyzers + ChromaDB RAG + local Ollama..."):
                    res = api_client.run_review(
                        project_id=current_project_id or 1,
                        review_type="GENERAL",
                        file_paths=paths_to_send,
                        snippet=code_to_send.strip() if code_to_send else None,
                        file_name=target_name,
                        use_rag=use_rag
                    )

                if "error" in res:
                    st.error(f"❌ Review failed: {res['error']}")
                else:
                    overall_risk = res.get("overall_risk", "LOW")
                    score = res.get("score", 100.0)
                    sec_score = res.get("security_score", 100.0)
                    corr_score = res.get("correctness_score", 100.0)
                    maint_score = res.get("maintainability_score", 100.0)
                    findings = res.get("findings", [])

                    # Store in session state for filtering
                    st.session_state["last_review_res"] = res

        # Display results from current or previous run
        res = st.session_state.get("last_review_res")
        if res:
            overall_risk = res.get("overall_risk", "LOW")
            score = res.get("score", 100.0)
            sec_score = res.get("security_score", 100.0)
            corr_score = res.get("correctness_score", 100.0)
            maint_score = res.get("maintainability_score", 100.0)
            findings = res.get("findings", [])

            crit_count = sum(1 for f in findings if f.get("severity") == "CRITICAL")
            high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
            med_count  = sum(1 for f in findings if f.get("severity") == "MEDIUM")
            low_count  = sum(1 for f in findings if f.get("severity") in ("LOW", "INFO"))

            # Risk color
            risk_color = _RED if overall_risk in ("CRITICAL", "HIGH") else (_AMBER if overall_risk == "MEDIUM" else _GREEN)

            # Telemetry Cards Row
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {risk_color};">
  <div class="kpi-title">Overall Risk</div>
  <div class="kpi-value" style="color:{risk_color}; font-size:1.25rem;">{overall_risk}</div>
  <div class="kpi-sub">Composite Safety Risk</div>
</div>""", unsafe_allow_html=True)
            with k2:
                st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_CYAN};">
  <div class="kpi-title">Quality Score</div>
  <div class="kpi-value" style="color:{_CYAN};">{score} / 100</div>
  <div class="kpi-sub">Deduction-weighted</div>
</div>""", unsafe_allow_html=True)
            with k3:
                st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_PURPLE};">
  <div class="kpi-title">Total Findings</div>
  <div class="kpi-value" style="color:{_PURPLE};">{len(findings)}</div>
  <div class="kpi-sub">{crit_count} Critical · {high_count} High</div>
</div>""", unsafe_allow_html=True)
            with k4:
                st.markdown(f"""
<div class="kpi-card" style="border-left:5px solid {_GREEN};">
  <div class="kpi-title">Coverage</div>
  <div class="kpi-value" style="color:{_GREEN}; font-size:1.2rem;">8 Passes</div>
  <div class="kpi-sub">Multi-Layered Fusion</div>
</div>""", unsafe_allow_html=True)

            # Sub-score pill strip
            st.markdown(f"""
<div style="background:#ffffff; border:1px solid {_BORDER}; border-radius:8px; padding:10px 16px; margin:14px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; font-size:0.8rem;">
  <div><b>Sub-Scores:</b></div>
  <div style="color:{_RED if sec_score < 70 else _GREEN}; font-weight:600;">🛡️ Security: {sec_score}/100</div>
  <div style="color:{_AMBER if corr_score < 70 else _GREEN}; font-weight:600;">🎯 Correctness: {corr_score}/100</div>
  <div style="color:{_CYAN if maint_score < 70 else _GREEN}; font-weight:600;">🧹 Maintainability: {maint_score}/100</div>
</div>""", unsafe_allow_html=True)

            # Executive Summary Box
            st.markdown(f"""
<div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid {_CYAN}; border-radius:0 8px 8px 0; padding:14px 18px; margin-bottom:16px;">
  <div style="font-weight:700; color:#1e293b; font-size:0.9rem; margin-bottom:4px;">Executive Summary</div>
  <div style="font-size:0.85rem; color:#475467; line-height:1.5;">{res.get('summary')}</div>
</div>""", unsafe_allow_html=True)

            # Filter Tabs
            if findings:
                st.markdown("<div style='font-size:0.9rem; font-weight:700; color:#172033; margin:16px 0 8px;'>Identified Code Defects &amp; Citations:</div>", unsafe_allow_html=True)

                filter_options = ["All"]
                if crit_count > 0:
                    filter_options.append(f"Critical ({crit_count})")
                if high_count > 0:
                    filter_options.append(f"High ({high_count})")
                if med_count > 0:
                    filter_options.append(f"Medium ({med_count})")
                if low_count > 0:
                    filter_options.append(f"Low ({low_count})")

                selected_filter = st.radio("Filter Severity:", filter_options, horizontal=True, label_visibility="collapsed")

                displayed_findings = []
                for f in findings:
                    sev = f.get("severity", "MEDIUM")
                    if selected_filter == "All":
                        displayed_findings.append(f)
                    elif selected_filter.startswith("Critical") and sev == "CRITICAL":
                        displayed_findings.append(f)
                    elif selected_filter.startswith("High") and sev == "HIGH":
                        displayed_findings.append(f)
                    elif selected_filter.startswith("Medium") and sev == "MEDIUM":
                        displayed_findings.append(f)
                    elif selected_filter.startswith("Low") and sev in ("LOW", "INFO"):
                        displayed_findings.append(f)

                # Render each finding card
                for idx, f in enumerate(displayed_findings, start=1):
                    sev = f.get("severity", "MEDIUM")
                    cat = f.get("category", "General")
                    line_start = f.get("line_start")
                    line_str = f"Line {line_start}" if line_start else "Line N/A"
                    sev_badge = _sev_badge_html(sev)
                    cat_badge = _cat_badge_html(cat)
                    src_type = f.get("source_type", "COMBINED")

                    # Border color based on severity
                    b_color = _RED if sev == "CRITICAL" else (_AMBER if sev == "HIGH" else _CYAN)

                    with st.expander(f"[{sev}] {f.get('finding_code')}: {f.get('issue')} ({line_str})", expanded=(idx <= 3)):
                        # Header badges
                        st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:6px;">
  <div style="display:flex; gap:6px; align-items:center;">
    {sev_badge} {cat_badge}
    <span style="background:#f1f5f9; color:#475467; border:1px solid #e2e8f0; border-radius:5px; padding:2px 8px; font-size:0.72rem; font-weight:600;">
      📍 {line_str}
    </span>
  </div>
  <span style="font-size:0.72rem; color:{_MUTED}; background:#f8fafc; border:1px solid #e2e8f0; padding:2px 8px; border-radius:4px;">
    Engine: {src_type} · Conf: {f.get('confidence', 'HIGH')}
  </span>
</div>""", unsafe_allow_html=True)

                        # Problematic code snippet
                        if f.get("evidence"):
                            st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#64748b; margin-bottom:2px;'>PROBLEM CODE:</div>", unsafe_allow_html=True)
                            st.code(f.get("evidence"), language="cpp")

                        # Root cause and explanation
                        expl_text = f.get("explanation", "")
                        st.markdown(f"""
<div style="background:#ffffff; border:1px solid {_BORDER}; border-radius:6px; padding:12px 14px; margin:8px 0; font-size:0.85rem; color:#334155; line-height:1.6;">
  <b>Analysis &amp; Root Cause:</b><br>{expl_text}
</div>""", unsafe_allow_html=True)

                        # Recommendation
                        if f.get("recommendation"):
                            st.markdown(f"""
<div style="font-size:0.83rem; color:#0f766e; background:#f0fdfa; border:1px solid #99f6e4; border-radius:6px; padding:8px 12px; margin-bottom:8px;">
  <b>💡 Recommendation:</b> {f.get('recommendation')}
</div>""", unsafe_allow_html=True)

                        # Suggested Fix / Corrected Code
                        if f.get("suggested_fix"):
                            st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#0f766e; margin-bottom:2px;'>CORRECTED CODE:</div>", unsafe_allow_html=True)
                            st.code(f.get("suggested_fix"), language="cpp")

                # Export buttons
                st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
                rep_md = f"# Comprehensive Code Review Report: {target_name}\n\n"
                rep_md += f"**Overall Risk:** {overall_risk} | **Quality Score:** {score}/100\n\n"
                rep_md += f"### Executive Summary\n{res.get('summary')}\n\n"
                rep_md += f"### Detailed Findings ({len(findings)})\n"
                for idx, f in enumerate(findings, 1):
                    rep_md += f"#### {idx}. [{f.get('severity')}] {f.get('finding_code')}: {f.get('issue')} (Line {f.get('line_start') or 'N/A'})\n"
                    rep_md += f"- **Category:** {f.get('category')} | **Source:** {f.get('source_type')}\n"
                    if f.get('evidence'):
                        rep_md += f"```cpp\n{f.get('evidence')}\n```\n"
                    rep_md += f"**Explanation:**\n{f.get('explanation')}\n\n"
                    if f.get('recommendation'):
                        rep_md += f"**Recommendation:** {f.get('recommendation')}\n\n"
                    if f.get('suggested_fix'):
                        rep_md += f"**Corrected Code:**\n```cpp\n{f.get('suggested_fix')}\n```\n\n"

                st.download_button(
                    label="⬇️ Download Full Audit Report (.md)",
                    data=rep_md,
                    file_name=f"review_{target_name.replace('/', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            else:
                st.markdown("""
<div class="empty-state-card" style="padding:36px 20px;">
  <div class="empty-state-icon">✅</div>
  <div class="empty-state-title">No Defects Detected</div>
  <div class="empty-state-sub">
    The reviewed source code is well-structured and conforms to safety and quality standards across all 8 inspection passes.
  </div>
</div>""", unsafe_allow_html=True)

        else:
            st.markdown("""
<div class="empty-state-card" style="padding:48px 24px;">
  <div class="empty-state-icon">🔬</div>
  <div class="empty-state-title">Ready to Execute Code Review</div>
  <div class="empty-state-sub">
    Paste a C/C++ or Python code snippet, select one of the automotive defect test cases,
    or choose an indexed workspace file on the left and click <b>Execute Multi-Pass Code Review</b>.
  </div>
</div>""", unsafe_allow_html=True)

    # ── 3. Compliance Footer ──────────────────────────────────────────────────
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:#9ca3af;"
        " border-top:1px solid #e4e9f0; padding-top:14px;'>"
        "SECURECODE AI v1.0.0 &nbsp;·&nbsp; ISO 26262 Part 6 &nbsp;·&nbsp; "
        "MISRA C:2012 / C++:2008 &nbsp;·&nbsp; CERT C/C++ &nbsp;·&nbsp; "
        "100% Local Air-Gapped Analysis</div>",
        unsafe_allow_html=True,
    )
