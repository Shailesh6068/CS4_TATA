import os
import streamlit as st
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 📁 Project Workspaces & File Ingestion")
    st.markdown("Manage automotive software engineering workspaces, ingest repositories, and index source code.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Create New Engineering Project")
        with st.form("create_project_form"):
            p_name = st.text_input("Project Name", placeholder="e.g., Vehicle ECU Controller")
            p_desc = st.text_area("Description", placeholder="e.g., Automotive powertrain controller with CAN and sensors")
            submit_create = st.form_submit_button("Create Project", use_container_width=True)

            if submit_create and p_name.strip():
                res = api_client.create_project(p_name.strip(), p_desc.strip())
                if "id" in res:
                    st.success(f"Project '{p_name}' created successfully! (ID: {res['id']})")
                    st.session_state["selected_project_id"] = res["id"]
                    st.rerun()
                else:
                    st.error(f"Failed to create project: {res.get('error', 'Unknown')}")

    with col2:
        st.markdown("### Quick Start: Sample Automotive Project")
        st.info("Load the industry-standard educational sample: **Vehicle ECU Controller** with realistic CAN interface, sensor routines, and intentional educational test cases.")
        if st.button("🚀 Ingest Sample 'Vehicle ECU Controller'", use_container_width=True):
            sample_dir = os.path.abspath("sample_project/Vehicle_ECU")
            if not os.path.exists(sample_dir):
                st.error(f"Sample project directory not found: `{sample_dir}`. Ensure the repository is checked out correctly.")
            else:
                # 1. Check if 'Vehicle ECU Controller' already exists with files to avoid creating duplicate projects
                projs = api_client.list_projects()
                existing_sample = next((p for p in projs if p["name"] == "Vehicle ECU Controller"), None)
                if existing_sample:
                    pid = existing_sample["id"]
                    existing_files = api_client.list_project_files(pid)
                    if existing_files:
                        st.session_state["selected_project_id"] = pid
                        st.success(f"✅ 'Vehicle ECU Controller' (ID: {pid}) is already loaded with {len(existing_files)} files and is now your Active Workspace!")
                        st.rerun()
                else:
                    proj = api_client.create_project("Vehicle ECU Controller", "Powertrain Engine Controller and CAN Gateway")
                    pid = proj.get("id")

                if pid:
                    # 2. Ingest sample files from disk
                    files_to_upload = []
                    for root, _, f_names in os.walk(sample_dir):
                        for fn in f_names:
                            fp = os.path.join(root, fn)
                            with open(fp, "rb") as f_obj:
                                files_to_upload.append(("files", (fn, f_obj.read(), "application/octet-stream")))

                    if files_to_upload:
                        up_res = api_client.upload_files(pid, files_to_upload)
                        st.success(f"✅ Sample Project active! Loaded {len(files_to_upload)} files.")
                        st.session_state["selected_project_id"] = pid
                        st.rerun()
                    else:
                        st.warning("Sample directory found but contains no files.")
                else:
                    st.error("Failed to create or find sample project.")

    st.markdown("---")

    # Display Current Active Workspace Banner
    projects = api_client.list_projects()
    if not projects:
        st.warning("No projects exist. Please create one above first.")
        return

    p_options = {p["id"]: f"{p['name']} (ID: {p['id']})" for p in projects}
    current_files = api_client.list_project_files(current_project_id) if current_project_id in p_options else []
    active_name = p_options.get(current_project_id, "None")
    
    st.info(f"📍 **Currently Active Workspace:** `{active_name}` — **{len(current_files)} files indexed**")

    # Upload Files & Switch Workspace
    st.markdown("### 🗂️ Manage & Ingest Files into Selected Project")
    col_sel, col_btn = st.columns([3, 2])
    with col_sel:
        selected_p = st.selectbox(
            "Select Project",
            options=list(p_options.keys()),
            format_func=lambda x: p_options[x],
            index=list(p_options.keys()).index(current_project_id) if current_project_id in p_options else 0,
            key="target_project_select"
        )
    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("👉 Set as Active Workspace", use_container_width=True):
            st.session_state["selected_project_id"] = selected_p
            st.success(f"Switched Active Workspace to: {p_options[selected_p]}")
            st.rerun()

    uploaded_files = st.file_uploader(
        "Upload C/C++, Header, Python files or ZIP Archive into selected project",
        accept_multiple_files=True,
        type=["c", "cpp", "h", "hpp", "py", "zip", "txt", "log", "md"]
    )

    if st.button("📥 Ingest Uploaded Files", use_container_width=True) and uploaded_files:
        payload = []
        for uf in uploaded_files:
            payload.append(("files", (uf.name, uf.getvalue(), uf.type or "application/octet-stream")))
        with st.spinner("Ingesting, safely validating, and indexing symbols into ChromaDB..."):
            res = api_client.upload_files(selected_p, payload)
            if "files" in res:
                st.session_state["selected_project_id"] = selected_p
                st.success(f"Successfully processed {len(res['files'])} files into workspace!")
                st.rerun()
            else:
                st.error(f"Error: {res.get('error', 'Upload failed')}")
