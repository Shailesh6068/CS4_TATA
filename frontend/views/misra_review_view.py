import os
import streamlit as st
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🛡️ MISRA-Oriented Automotive C/C++ Review")
    st.markdown("AI-assisted static review against MISRA C:2012 and MISRA C++:2008 coding standards for embedded safety-critical software.")

    st.markdown("""
    <div class="disclaimer-box">
        ⚠️ <b>MANDATORY COMPLIANCE NOTICE:</b> This is an AI-assisted MISRA-oriented review. It does NOT replace qualified certified MISRA analysis toolchains (e.g., QA-C, Polyspace, PC-lint) or formal safety human engineering sign-off.
    </div>
    """, unsafe_allow_html=True)

    if not current_project_id:
        st.warning("Please select a project first.")
        return

    files = api_client.list_project_files(current_project_id) if current_project_id else []

    col_in, col_res = st.columns([1, 1])

    with col_in:
        st.markdown("### Review Scope & Rule Configuration")
        scope_choice = st.radio("Target Source", ["Custom Code Snippet", "Select Indexed File"], horizontal=True)

        target_name = "snippet.cpp"
        code_to_send = ""
        paths_to_send = None

        if scope_choice == "Custom Code Snippet":
            code_to_send = st.text_area("C/C++ Code Snippet", height=200, placeholder="Paste C/C++ code here...")
            target_name = st.text_input("File Name", value="snippet.cpp")
        else:
            if not files:
                st.info("ℹ️ No indexed files found in this workspace. Upload files in 'Projects' or switch to 'Custom Code Snippet' above.")
            else:
                file_options = {f["id"]: f["relative_path"] for f in files}
                sel_id = st.selectbox("Target File", options=list(file_options.keys()), format_func=lambda x: file_options[x])
                sel_f = next((f for f in files if f["id"] == sel_id), None)
                if sel_f:
                    target_name = sel_f["relative_path"]
                    paths_to_send = [target_name]
                    file_res = api_client.get_file_content(current_project_id, sel_id)
                    if isinstance(file_res, dict) and "content" in file_res:
                        code_to_send = file_res["content"]
                    st.code(code_to_send[:600] + ("..." if len(code_to_send) > 600 else ""), language="cpp")

        st.markdown("#### Configurable MISRA Rules")
        r_21_3 = st.checkbox("Rule 21.3 / Dir 4.12: Prohibit dynamic memory (malloc/free/new)", value=True)
        r_21_6 = st.checkbox("Rule 21.6: Prohibit unbounded string I/O (strcpy/sprintf/gets)", value=True)
        r_11_4 = st.checkbox("Rule 11.4: Prohibit incompatible pointer conversions", value=True)
        r_13_2 = st.checkbox("Rule 13.2: Disallow side-effects in expressions & assertions", value=True)
        r_9_1 = st.checkbox("Rule 9.1: Mandatory variable initialization before read", value=True)
        r_2_1 = st.checkbox("Rule 2.1: Prohibit unreachable dead code blocks", value=True)

        selected_rules = []
        if r_21_3: selected_rules.append("Rule 21.3 / Dir 4.12: Prohibit dynamic memory (malloc/free/new)")
        if r_21_6: selected_rules.append("Rule 21.6: Prohibit unbounded string I/O (strcpy/sprintf/gets)")
        if r_11_4: selected_rules.append("Rule 11.4: Prohibit incompatible pointer conversions")
        if r_13_2: selected_rules.append("Rule 13.2: Disallow side-effects in expressions & assertions")
        if r_9_1:  selected_rules.append("Rule 9.1: Mandatory variable initialization before read")
        if r_2_1:  selected_rules.append("Rule 2.1: Prohibit unreachable dead code blocks")

        submit_misra = st.button("🚀 Run MISRA-Oriented Review", use_container_width=True)

    with col_res:
        st.markdown("### MISRA Advisory Findings")
        if submit_misra:
            if not code_to_send.strip() and not paths_to_send:
                st.warning("Please provide C/C++ source code to analyze.")
            else:
                with st.spinner("Evaluating against MISRA C:2012 guidelines..."):
                    res = api_client.run_review(
                        project_id=current_project_id,
                        review_type="MISRA",
                        file_paths=paths_to_send,
                        snippet=code_to_send.strip() if code_to_send else None,
                        file_name=target_name,
                        use_rag=True,
                        enabled_rules=selected_rules
                    )

                    if "error" in res:
                        st.error(f"MISRA review failed: {res['error']}")
                    else:
                        st.info(f"Summary: {res.get('summary')}")
                        findings = [f for f in res.get("findings", []) if "MISRA" in f.get("category", "") or "MISRA" in f.get("finding_code", "")]
                        if not findings:
                            findings = res.get("findings", [])

                        st.markdown(f"#### Identified Violations ({len(findings)})")
                        if findings:
                            for f in findings:
                                with st.expander(f"[{f.get('severity')}] {f.get('finding_code')}: {f.get('issue')} (Line {f.get('line_start') or 'N/A'})"):
                                    if f.get("evidence"):
                                        st.code(f.get("evidence"), language="cpp")
                                    st.markdown(f"**Explanation:** {f.get('explanation')}")
                                    if f.get("recommendation"):
                                        st.markdown(f"**Automotive Recommendation:** {f.get('recommendation')}")
                                    if f.get("suggested_fix"):
                                        st.markdown("**Compliant Code:**")
                                        st.code(f.get("suggested_fix"), language="cpp")
                        else:
                            st.success("No MISRA violations detected. The code conforms to checked rules.")
        else:
            st.info("Select a file or paste snippet and click 'Run MISRA-Oriented Review' to examine rule compliance.")
