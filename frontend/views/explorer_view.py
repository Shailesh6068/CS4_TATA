import os
import streamlit as st
import pandas as pd
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🔍 Workspace Project Explorer")
    st.markdown("Browse indexed repository files, review source code, and inspect extracted AST/C++ symbols.")

    if not current_project_id:
        st.warning("Please select a project first.")
        return

    files = api_client.list_project_files(current_project_id)
    if not files:
        st.info("No files found in this project. Upload files in the 'Projects' page.")
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Files Index")
        file_map = {f["id"]: f["relative_path"] for f in files}
        selected_file_id = st.radio(
            "Select File",
            options=list(file_map.keys()),
            format_func=lambda x: f"📄 {file_map[x]}"
        )

        selected_file = next((f for f in files if f["id"] == selected_file_id), None)
        if selected_file:
            st.markdown("#### File Metadata")
            st.markdown(f"- **Language:** `{selected_file.get('language')}`")
            st.markdown(f"- **Lines of Code:** `{selected_file.get('line_count')}`")
            st.markdown(f"- **Size:** `{selected_file.get('size_bytes')} bytes`")
            st.markdown(f"- **Extension:** `{selected_file.get('extension')}`")

            symbols = selected_file.get("symbols", [])
            st.markdown(f"#### Extracted Symbols ({len(symbols)})")
            if symbols:
                sym_rows = []
                for s in symbols:
                    sym_rows.append({
                        "Symbol": s.get("symbol_name"),
                        "Type": s.get("symbol_type"),
                        "Line": s.get("line_start")
                    })
                st.dataframe(pd.DataFrame(sym_rows), use_container_width=True)

    with col2:
        if selected_file:
            st.markdown(f"### Source: `{selected_file.get('relative_path')}`")
            # Fetch file content via API first, fallback to disk
            code_text = ""
            file_res = api_client.get_file_content(current_project_id, selected_file["id"])
            if isinstance(file_res, dict) and "content" in file_res:
                code_text = file_res["content"]
            else:
                proj_data = api_client.get_project(current_project_id)
                repo_path = proj_data.get("repo_path", "")
                full_path = os.path.join(repo_path, selected_file.get("relative_path"))
                if os.path.exists(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            code_text = f.read()
                    except Exception as e:
                        code_text = f"// Error reading file: {e}"
                else:
                    code_text = "// File content could not be loaded."

            lang = selected_file.get("language", "cpp")
            st.code(code_text, language=lang, line_numbers=True)
