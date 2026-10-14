import streamlit as st
import pandas as pd
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🕸️ Repository Dependency Graph & Architecture Analysis")
    st.markdown("Analyze module relationships, `#include` / `import` dependency trees, and detect circular dependencies.")

    if not current_project_id:
        st.warning("Please select a project first.")
        return

    cache_key = f"dep_data_{current_project_id}"
    col_hdr, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("🔄 Refresh Graph", use_container_width=True):
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()

    if cache_key not in st.session_state:
        with st.spinner("Extracting include graphs and computing cycle metrics..."):
            st.session_state[cache_key] = api_client.get_dependencies(current_project_id)

    dep_data = st.session_state[cache_key]

    if not dep_data or dep_data.get("total_nodes", 0) == 0:
        st.info("No dependency data available for this project. Ensure C/C++ or Python files are uploaded.")
        return

    # High-level stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Modules", dep_data.get("total_nodes", 0))
    c2.metric("Total Edges", dep_data.get("total_edges", 0))
    has_cycles = dep_data.get("has_cycles", False)
    c3.metric("Circular Dependencies", "DETECTED" if has_cycles else "NONE", delta_color="inverse")

    if has_cycles:
        st.error(f"⚠️ Circular dependency detected: {dep_data.get('circular_dependencies')}")
    else:
        st.success("✅ Clean architecture: No circular dependencies detected.")

    st.markdown("---")

    # Graphviz visualization
    st.markdown("### Visual Dependency Tree")
    nodes = dep_data.get("nodes", [])
    edges = dep_data.get("edges", [])

    dot_lines = ["digraph G {", '  node [shape=box, style="filled,rounded", fillcolor="#ffffff", color="#cbd5e1", fontcolor="#172033", fontname="Helvetica"];', '  edge [color="#0f766e", arrowhead=vee];', "  bgcolor=transparent;"]

    for n in nodes:
        dot_lines.append(f'  "{n["id"]}" [label="{n["label"]}"];')

    for e in edges:
        dot_lines.append(f'  "{e["source"]}" -> "{e["target"]}";')

    dot_lines.append("}")
    dot_str = "\n".join(dot_lines)

    try:
        st.graphviz_chart(dot_str)
    except Exception:
        st.info("Graphviz visual representation rendered as table below:")

    st.markdown("---")

    # Table of Edges & Nodes
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### Dependency Edges")
        if edges:
            st.dataframe(pd.DataFrame(edges), use_container_width=True)
    with col_t2:
        st.markdown("#### Module Coupling Metrics")
        if nodes:
            st.dataframe(pd.DataFrame(nodes), use_container_width=True)
