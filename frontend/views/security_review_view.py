import os
import streamlit as st
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🛡️ Security-Focused Vulnerability Review")
    st.markdown("Automotive & embedded cyber-security analysis targeting buffer overflows, memory corruption, credential leaks, and unchecked I/O.")

    files = api_client.list_project_files(current_project_id) if current_project_id else []

    col_in, col_res = st.columns([1, 1])

    with col_in:
        st.markdown("### Security Review Scope")
        scope_choice = st.radio("Target Selection", ["Direct Snippet", "Indexed Project File"], horizontal=True)

        target_name = "snippet.cpp"
        code_to_send = ""
        paths_to_send = None

        if scope_choice == "Direct Snippet":
            code_to_send = st.text_area("Source Code", height=250, placeholder="Paste C/C++ or Python code to audit...")
            target_name = st.text_input("Filename", value="snippet.cpp")
        else:
            if not files:
                st.info("ℹ️ No indexed files found in this workspace. Upload files in 'Projects' or switch to 'Direct Snippet' above.")
            else:
                file_options = {f["id"]: f["relative_path"] for f in files}
                sel_id = st.selectbox("Select File", options=list(file_options.keys()), format_func=lambda x: file_options[x])
                sel_f = next((f for f in files if f["id"] == sel_id), None)
                if sel_f:
                    target_name = sel_f["relative_path"]
                    paths_to_send = [target_name]
                    file_res = api_client.get_file_content(current_project_id, sel_id)
                    if isinstance(file_res, dict) and "content" in file_res:
                        code_to_send = file_res["content"]
                    st.code(code_to_send[:600] + ("..." if len(code_to_send) > 600 else ""), language="cpp")

        use_rag = st.checkbox("Retrieve ISO 21434 / AUTOSAR Guidelines (RAG)", value=True)
        submit_sec = st.button("🚨 Run Security Review", use_container_width=True)

    with col_res:
        st.markdown("### Vulnerability Findings")
        if submit_sec:
            if not code_to_send.strip() and not paths_to_send:
                st.warning("Please provide code to review.")
            else:
                with st.spinner("Analyzing against CWE Top 25 and automotive threat vectors..."):
                    res = api_client.run_review(
                        project_id=current_project_id or 1,
                        review_type="SECURITY",
                        file_paths=paths_to_send,
                        snippet=code_to_send.strip() if code_to_send else None,
                        file_name=target_name,
                        use_rag=use_rag
                    )

                    if "error" in res:
                        st.error(f"Security review failed: {res['error']}")
                    else:
                        st.markdown(f"""
                        <div class="kpi-card" style="border-left: 5px solid {'#EF4444' if res.get('overall_risk') in ('CRITICAL', 'HIGH') else '#10B981'};">
                            <div class="kpi-title">Security Risk Status</div>
                            <div class="kpi-value">{res.get('overall_risk')}</div>
                            <div class="kpi-sub">Security Score: {res.get('security_score')}/100</div>
                        </div>
                        """, unsafe_allow_html=True)

                        st.write(res.get("summary"))

                        findings = res.get("findings", [])
                        st.markdown(f"#### Detected Security Vulnerabilities ({len(findings)})")
                        if findings:
                            for f in findings:
                                sev = f.get('severity', 'MEDIUM')
                                badge_class = f"badge-{sev.lower()}"
                                st.markdown(f"""
                                <div style="background:#ffffff; padding:12px; border-radius:8px; margin-bottom:10px; border:1px solid #e4e9f0; box-shadow:0 2px 8px rgba(23,32,51,0.05);">
                                    <span class="{badge_class}">{sev}</span>
                                    <strong style="margin-left: 8px;">{f.get('finding_code')}: {f.get('issue')}</strong>
                                    <div style="font-size:0.8rem; color:#667085; margin-top:4px;">File: {f.get('file_path')} | Line: {f.get('line_start') or 'N/A'} | Source: {f.get('source_type')}</div>
                                </div>
                                """, unsafe_allow_html=True)

                                with st.expander("Inspect Evidence & Suggested Fix"):
                                    if f.get("evidence"):
                                        st.code(f.get("evidence"), language="cpp")
                                    st.markdown(f"**Explanation:** {f.get('explanation')}")
                                    st.markdown(f"**Remediation:** {f.get('recommendation')}")
                                    if f.get("suggested_fix"):
                                        st.code(f.get("suggested_fix"), language="cpp")
                        else:
                            st.success("No security vulnerabilities detected within analyzed scope.")
        else:
            st.info("Select a file or paste snippet and click 'Run Security Review'.")
