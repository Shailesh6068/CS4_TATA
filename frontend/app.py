import streamlit as st
from frontend.styles import AUTOMOTIVE_THEME_CSS
from frontend.api_client import api_client
from frontend.views import (
    dashboard_view, projects_view, explorer_view, explanation_view,
    debug_view, code_review_view, security_review_view, misra_review_view,
    compiler_logs_view, ask_codebase_view, dependency_view, diff_review_view,
    findings_view, knowledge_view, reports_view, settings_view
)

st.set_page_config(
    page_title="SECURECODE AI | Automotive Review Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply CSS styling
st.markdown(AUTOMOTIVE_THEME_CSS, unsafe_allow_html=True)

# Top Air-Gapped Privacy Indicator
st.markdown("""
<div class="privacy-badge-container">
    <span class="privacy-badge-dot"></span>
    LOCAL PRIVACY ENABLED: All source code, embeddings, and Ollama LLM processing remain 100% on this machine. No cloud APIs.
</div>
""", unsafe_allow_html=True)

# Query Ollama status
ollama_stat = api_client.get_ollama_status()
is_connected = ollama_stat.get("is_connected", False)
active_model = ollama_stat.get("active_model", "Unknown")

# Sidebar
st.sidebar.markdown("""
<div class="sidebar-brand">
    <h2>SECURECODE AI</h2>
    <p>Automotive Software Engineering</p>
</div>
""", unsafe_allow_html=True)

# Ollama Status Pill
st.sidebar.markdown(f"""
<div class="ollama-status-card {'is-connected' if is_connected else 'is-disconnected'}">
    <div class="ollama-status-title">
        ● Ollama: {'CONNECTED' if is_connected else 'DISCONNECTED'}
    </div>
    <div class="ollama-status-model">
        Model: <code>{active_model}</code>
    </div>
</div>
""", unsafe_allow_html=True)

# Project Selector
projects = api_client.list_projects()
p_dict = {p["id"]: p["name"] for p in projects}

selected_pid = st.session_state.get("selected_project_id", None)
if projects:
    if selected_pid not in p_dict:
        selected_pid = projects[-1]["id"]
        st.session_state["selected_project_id"] = selected_pid

    p_names = list(p_dict.keys())
    # Prefer currently selected project or the first one available
    cur_idx = p_names.index(selected_pid) if selected_pid in p_names else 0
    selected_pid = st.sidebar.selectbox(
        "Active Workspace",
        options=p_names,
        format_func=lambda x: f"🚗 {p_dict[x]} (ID: {x})",
        index=cur_idx,
        key="active_workspace_selector"
    )
    st.session_state["selected_project_id"] = selected_pid
else:
    st.sidebar.info("No projects yet. Create one in 'Projects'.")
    selected_pid = None

st.sidebar.markdown("---")

# Navigation Menu (16 Pages)
PAGES = {
    "📊 Dashboard": dashboard_view,
    "📁 Projects": projects_view,
    "🔍 Project Explorer": explorer_view,
    "📖 Code Explanation": explanation_view,
    "🛠️ Code Debugging": debug_view,
    "📋 Code Review": code_review_view,
    "🛡️ Security Review": security_review_view,
    "⚖️ MISRA Review": misra_review_view,
    "📜 Compiler & Logs": compiler_logs_view,
    "💬 Ask Your Codebase": ask_codebase_view,
    "🕸️ Dependency Graph": dependency_view,
    "🔀 Diff Review": diff_review_view,
    "🎯 Findings": findings_view,
    "📚 Knowledge Base": knowledge_view,
    "📑 Reports": reports_view,
    "⚙️ Settings": settings_view
}

choice = st.sidebar.radio("Navigation", list(PAGES.keys()))

st.sidebar.markdown("---")
st.sidebar.caption("SECURECODE AI v1.0.0 | ISO 26262 / MISRA C:2012 / ISO 21434")

# Render selected view
view_module = PAGES[choice]
view_module.render(current_project_id=selected_pid)
