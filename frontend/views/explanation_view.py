import streamlit as st
from frontend.api_client import api_client

# ── colour palette ─────────────────────────────────────────────────────────
_TEAL   = "#0f766e"
_MUTED  = "#667085"
_BORDER = "#e4e9f0"


def _mode_card(label: str, icon: str, desc: str, selected: bool) -> str:
    """Render a styled mode-selection card as HTML."""
    if selected:
        card_style = (
            "border-color:#0f766e; background:#f0fdfa;"
            " box-shadow:0 0 0 2px rgba(15,118,110,0.18);"
        )
        check = "✓ "
    else:
        card_style = "border-color:#e4e9f0; background:#ffffff;"
        check = ""
    return (
        f'<div style="border:1.5px solid; border-radius:10px; padding:12px 14px;'
        f' transition:all 0.2s; margin-bottom:8px; {card_style}">'
        f'  <div style="font-size:0.95rem; font-weight:700; color:#172033;">'
        f'{icon} {check}{label}</div>'
        f'  <div style="font-size:0.78rem; color:#667085; margin-top:3px; line-height:1.4;">'
        f'{desc}</div>'
        f"</div>"
    )


def render(current_project_id: int):

    # ── hero header ────────────────────────────────────────────────────────
    st.markdown("""
<div class="hero-header-card">
  <div class="hero-title">📖 Automotive Code Explanation Assistant</div>
  <div class="hero-subtitle">
    Reverse-engineer and decode embedded C/C++ or Python source files, functions,
    and control logic — using local Ollama inference with zero cloud exposure.
  </div>
  <div class="hero-tags">
    <span class="hero-tag cyan">⚙️ C / C++</span>
    <span class="hero-tag cyan">🐍 Python</span>
    <span class="hero-tag green">🛡️ ISO 26262 Aware</span>
    <span class="hero-tag">🔁 Reverse Engineering</span>
    <span class="hero-tag">🔒 100% Local</span>
  </div>
</div>
""", unsafe_allow_html=True)

    files = api_client.list_project_files(current_project_id) if current_project_id else []

    col_input, col_out = st.columns([1, 1], gap="large")

    # ══════════════════════════════════════════════════════════════════════
    # LEFT PANEL — Input Configuration
    # ══════════════════════════════════════════════════════════════════════
    with col_input:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:0;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">⚡ Source Input</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Step 1 of 2
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        input_choice = st.radio(
            "Input Source",
            ["Paste Custom Snippet", "Select Indexed File"],
            horizontal=True,
            label_visibility="collapsed",
        )

        target_code  = ""
        target_name  = "snippet.cpp"

        if input_choice == "Paste Custom Snippet":
            st.markdown(
                "<div style='font-size:0.8rem; font-weight:600; color:#344054;"
                " margin:6px 0 6px; text-transform:uppercase; letter-spacing:0.04em;'>"
                "📄 Source Code Snippet</div>",
                unsafe_allow_html=True,
            )
            target_code = st.text_area(
                "Source Code Snippet",
                height=260,
                placeholder=(
                    "// Paste C/C++ or Python code here...\n"
                    "// e.g. ECU CAN frame handler, state machine, AUTOSAR SWC"
                ),
                label_visibility="collapsed",
            )
            st.markdown(
                "<div style='font-size:0.8rem; font-weight:600; color:#344054;"
                " margin:10px 0 6px; text-transform:uppercase; letter-spacing:0.04em;'>"
                "🏷️ File Name</div>",
                unsafe_allow_html=True,
            )
            target_name = st.text_input(
                "File Name", value="snippet.cpp", label_visibility="collapsed"
            )
            if target_code.strip():
                n_lines = len(target_code.splitlines())
                n_chars = len(target_code)
                st.markdown(
                    f"<div style='font-size:0.75rem; color:{_MUTED}; margin-top:4px;'>"
                    f"📏 <b>{n_lines}</b> lines &nbsp;|&nbsp; <b>{n_chars:,}</b> chars</div>",
                    unsafe_allow_html=True,
                )
        else:
            if not files:
                st.markdown("""
<div class="empty-state-card" style="padding:28px 20px; margin-top:8px;">
  <div class="empty-state-icon">📁</div>
  <div class="empty-state-title">No Indexed Files Found</div>
  <div class="empty-state-sub">
    Upload source files in <b>Projects</b> first, or switch to
    <b>Paste Custom Snippet</b> above.
  </div>
</div>""", unsafe_allow_html=True)
            else:
                file_options = {f["id"]: f["relative_path"] for f in files}
                st.markdown(
                    "<div style='font-size:0.8rem; font-weight:600; color:#344054;"
                    " margin:4px 0 6px; text-transform:uppercase; letter-spacing:0.04em;'>"
                    "📂 Select Indexed File</div>",
                    unsafe_allow_html=True,
                )
                sel_id = st.selectbox(
                    "Select File",
                    options=list(file_options.keys()),
                    format_func=lambda x: file_options[x],
                    label_visibility="collapsed",
                )
                sel_f = next((f for f in files if f["id"] == sel_id), None)
                if sel_f:
                    target_name = sel_f["relative_path"]
                    file_res    = api_client.get_file_content(current_project_id, sel_id)
                    if isinstance(file_res, dict) and "content" in file_res:
                        target_code = file_res["content"]

                    ext      = target_name.rsplit(".", 1)[-1].upper() if "." in target_name else "TXT"
                    lang_map = {"CPP": "cpp", "C": "c", "PY": "python", "H": "cpp", "HPP": "cpp"}
                    lang     = lang_map.get(ext, "text")
                    n_lines  = len(target_code.splitlines())

                    st.markdown(
                        f"<div style='display:flex; gap:8px; margin:8px 0 6px; flex-wrap:wrap;'>"
                        f"<span style='background:#f1f5f9; border:1px solid #e4e9f0; border-radius:6px;"
                        f" padding:3px 9px; font-size:0.75rem; font-weight:600; color:#344054;'>"
                        f"📄 {ext}</span>"
                        f"<span style='background:#f1f5f9; border:1px solid #e4e9f0; border-radius:6px;"
                        f" padding:3px 9px; font-size:0.75rem; color:{_MUTED};'>"
                        f"📏 {n_lines} lines</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.code(
                        target_code[:700] + ("\n… (preview truncated)" if len(target_code) > 700 else ""),
                        language=lang,
                    )

        st.divider()

        # ── Step 2 – Explanation Level ──────────────────────────────────────
        st.markdown("""
<div style="font-size:0.8rem; font-weight:600; color:#344054; margin-bottom:10px;
            text-transform:uppercase; letter-spacing:0.04em;">
  🎛️ Step 2 — Explanation Level
</div>""", unsafe_allow_html=True)

        mode = st.radio(
            "Explanation Level",
            ["TECHNICAL", "SIMPLE"],
            horizontal=False,
            label_visibility="collapsed",
        )

        st.markdown(
            _mode_card(
                "TECHNICAL", "🔧",
                "Deep-dive for embedded/automotive engineers — architecture, data flows, MISRA risks, assembly mapping.",
                mode == "TECHNICAL",
            )
            + _mode_card(
                "SIMPLE", "📊",
                "Executive summary for project managers or non-technical stakeholders — plain language, high-level purpose.",
                mode == "SIMPLE",
            ),
            unsafe_allow_html=True,
        )

        # ── Target symbol (optional) ────────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.8rem; font-weight:600; color:#344054; margin:14px 0 6px;"
            " text-transform:uppercase; letter-spacing:0.04em;'>🔍 Target Symbol "
            "<span style='font-weight:400; color:#667085; text-transform:none; letter-spacing:0;'>"
            "(optional)</span></div>",
            unsafe_allow_html=True,
        )
        target_symbol = st.text_input(
            "Target Symbol",
            placeholder="e.g. calculateEngineState(), CANHandler, CRC_Check",
            label_visibility="collapsed",
            help="Narrow the explanation to a specific function, class, or macro.",
        )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        submit_explain = st.button(
            "🚀  Generate Explanation",
            use_container_width=True,
            type="primary",
        )

    # ══════════════════════════════════════════════════════════════════════
    # RIGHT PANEL — Output
    # ══════════════════════════════════════════════════════════════════════
    with col_out:
        st.markdown("""
<div class="panel-card" style="padding:0; margin-bottom:0;">
  <div class="panel-header" style="padding:16px 20px 14px;">
    <span class="panel-title">📋 Engineering Explanation</span>
    <span style="font-size:0.75rem; color:#667085; font-weight:500; background:#f1f5f9;
                 padding:3px 10px; border-radius:20px; border:1px solid #e4e9f0;">
      Local Ollama · Air-Gapped
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        if submit_explain:
            if not target_code.strip():
                st.markdown("""
<div class="risk-callout-card">
  <div class="risk-callout-title">⚠️ No Source Code Provided</div>
  <div class="risk-callout-content">
    Paste a code snippet or select an indexed project file before generating an explanation.
  </div>
</div>""", unsafe_allow_html=True)
            else:
                with st.spinner("🔍 Reverse-engineering architecture, control flow, and risks with local Ollama…"):
                    res = api_client.run_code_explanation(
                        project_id=current_project_id or 1,
                        file_path=target_name,
                        snippet=target_code,
                        mode=mode,
                        symbol=target_symbol or None,
                    )

                if "error" in res:
                    st.markdown(
                        f'<div class="risk-callout-card">'
                        f'<div class="risk-callout-title">❌ Explanation Failed</div>'
                        f'<div class="risk-callout-content">{res["error"]}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    # metadata strip
                    sym_label   = f" → <code>{target_symbol}</code>" if target_symbol else ""
                    mode_color  = _TEAL if mode == "TECHNICAL" else "#7c3aed"
                    mode_icon   = "🔧" if mode == "TECHNICAL" else "📊"
                    st.markdown(
                        f"<div style='display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px;'>"
                        f"<span style='background:#f0fdfa; border:1px solid #a7f3d0; border-radius:6px;"
                        f" padding:3px 10px; font-size:0.75rem; font-weight:600; color:#047857;'>"
                        f"✅ Analysis Complete</span>"
                        f"<span style='background:#f8fafc; border:1px solid #e4e9f0; border-radius:6px;"
                        f" padding:3px 10px; font-size:0.75rem; color:{_MUTED};'>"
                        f"📄 {target_name}{sym_label}</span>"
                        f"<span style='background:#f8fafc; border:1px solid #e4e9f0; border-radius:6px;"
                        f" padding:3px 10px; font-size:0.75rem; font-weight:600; color:{mode_color};'>"
                        f"{mode_icon} {mode}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    explanation = res.get("formatted_explanation", "")
                    if explanation:
                        # scrollable output container
                        st.markdown(
                            f"<div style='background:#ffffff; border:1px solid {_BORDER};"
                            f" border-radius:10px; padding:18px 20px; max-height:560px;"
                            f" overflow-y:auto; box-shadow:0 2px 10px rgba(23,32,51,0.05);'>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(explanation)
                        st.markdown("</div>", unsafe_allow_html=True)

                        # action row
                        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                        dl_col, cp_col = st.columns([1, 1])
                        with dl_col:
                            st.download_button(
                                "⬇️ Download (.md)",
                                data=explanation,
                                file_name=f"explanation_{target_name.replace('/', '_')}.md",
                                mime="text/markdown",
                                use_container_width=True,
                            )
                        with cp_col:
                            if st.button("📋 Copy to Clipboard", use_container_width=True):
                                st.session_state["_clipboard_exp"] = explanation
                                st.toast("✅ Copied to clipboard!", icon="📋")

                        # disclaimer
                        st.markdown(
                            "<div class='disclaimer-box' style='margin-top:14px;'>"
                            "⚠️ <b>Engineering Notice:</b> This is an AI-assisted reverse-engineering "
                            "summary. Always validate architectural interpretations against original design "
                            "documentation and certified review toolchains before release.</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.warning("⚠️ No explanation was generated. Try a different model or code snippet.")

        else:
            # rich empty state
            st.markdown("""
<div class="empty-state-card" style="padding:52px 28px; margin-top:4px;">
  <div class="empty-state-icon">🔬</div>
  <div class="empty-state-title">Ready to Analyze</div>
  <div class="empty-state-sub">
    Paste a source snippet or select an indexed project file,
    configure the explanation level, then click
    <b>Generate Explanation</b> to reverse-engineer the code.
  </div>
  <div style="margin-top:20px; display:flex; justify-content:center; gap:10px; flex-wrap:wrap;">
    <span style="background:#f0fdfa; border:1px solid #a7f3d0; border-radius:6px;
                 padding:4px 12px; font-size:0.75rem; font-weight:600; color:#047857;">
      ⚙️ C / C++ ECU code
    </span>
    <span style="background:#f0fdfa; border:1px solid #a7f3d0; border-radius:6px;
                 padding:4px 12px; font-size:0.75rem; font-weight:600; color:#047857;">
      🐍 Python modules
    </span>
    <span style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px;
                 padding:4px 12px; font-size:0.75rem; font-weight:600; color:#1d4ed8;">
      🔁 State machines
    </span>
    <span style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px;
                 padding:4px 12px; font-size:0.75rem; font-weight:600; color:#1d4ed8;">
      📡 CAN handlers
    </span>
  </div>
</div>""", unsafe_allow_html=True)
