import streamlit as st
import pandas as pd
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 💬 Ask Your Codebase & Symbol Search")
    st.markdown("Perform natural language semantic queries across your repository, or perform exact symbol lookups.")

    if not current_project_id:
        st.warning("Please select a project first.")
        return

    tab_semantic, tab_symbol = st.tabs(["Semantic Search (Natural Language)", "Exact Symbol Search"])

    with tab_semantic:
        st.markdown("### Natural Language Codebase Search")
        st.caption("Examples: 'Where is memory allocated?', 'Which function handles sensor input?', 'Where is the diagnostic key defined?'")

        col_q1, col_q2, col_q3 = st.columns(3)
        if col_q1.button("Where is memory allocated?"):
            st.session_state["aq_query"] = "Where is memory allocated?"
            st.rerun()
        if col_q2.button("Which function handles sensor input?"):
            st.session_state["aq_query"] = "Which function handles sensor input?"
            st.rerun()
        if col_q3.button("Where is the diagnostic key defined?"):
            st.session_state["aq_query"] = "Where is the diagnostic key defined?"
            st.rerun()

        if "aq_query" not in st.session_state:
            st.session_state["aq_query"] = ""

        query = st.text_input(
            "Ask a question about the repository",
            placeholder="e.g. Which function handles sensor input?",
            key="aq_query"
        )

        if st.button("🔍 Search Codebase", use_container_width=True):
            if not query.strip():
                st.warning("Please enter a search query first.")
            else:
                with st.spinner("Embedding query and querying ChromaDB vector index..."):
                    res = api_client.semantic_search(current_project_id, query, top_k=4)
                    if "error" in res:
                        st.error(f"Search failed: {res['error']}")
                    else:
                        results = res.get("results", [])
                        st.markdown(f"**Found {len(results)} relevant code locations:**")
                        if results:
                            for r in results:
                                with st.expander(f"📍 {r.get('file_path')} (Similarity: {r.get('similarity_score')})"):
                                    st.markdown(f"**Explanation:** {r.get('explanation')}")
                                    st.code(r.get("relevant_code"), language="cpp")
                        else:
                            st.info("No matching code blocks found in project vector index.")

    with tab_symbol:
        st.markdown("### Exact Symbol Lookup")
        sym_name = st.text_input("Symbol Name", placeholder="e.g. EngineController, unpackPayloadUnsafe, SensorDevice")
        sym_type = st.selectbox("Symbol Type (Optional Filter)", ["ALL", "FUNCTION", "CLASS", "STRUCT", "MACRO", "INCLUDE"])

        if st.button("🔎 Search Symbol", use_container_width=True):
            if not sym_name.strip():
                st.warning("Please enter a symbol name to search.")
            else:
                res_sym = api_client.symbol_search(
                    current_project_id,
                    sym_name,
                    symbol_type=sym_type if sym_type != "ALL" else None
                )
                if res_sym:
                    st.markdown(f"**Found {len(res_sym)} symbol definitions:**")
                    st.dataframe(pd.DataFrame(res_sym), use_container_width=True)
                else:
                    st.info(f"No symbols matching '{sym_name}' found in project index.")
