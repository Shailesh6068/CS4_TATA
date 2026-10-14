import streamlit as st
import pandas as pd
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🔍 Finding Management & Human Verification")
    st.markdown("Track, confirm, assign, and verify identified findings. Apply human sign-off on AI-assisted alerts.")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        f_sev = st.selectbox("Filter by Severity", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
    with col_f2:
        f_cat = st.selectbox("Filter by Category", ["ALL", "Security", "MISRA", "Bug", "Performance", "Style"])
    with col_f3:
        f_stat = st.selectbox("Filter by Status", ["ALL", "OPEN", "CONFIRMED", "FALSE_POSITIVE", "IN_PROGRESS", "FIXED", "VERIFIED", "REJECTED"])

    findings = api_client.list_findings(
        project_id=current_project_id,
        severity=f_sev if f_sev != "ALL" else None,
        category=f_cat if f_cat != "ALL" else None,
        status=f_stat if f_stat != "ALL" else None
    )

    st.markdown(f"**Total Matching Findings:** `{len(findings)}`")

    if not findings:
        st.info("No findings match the selected filters.")
        return

    # Expandable details per finding
    for f in findings:
        fid = f.get("id")
        f_code = f.get("finding_code")
        f_issue = f.get("issue")
        f_sev_val = f.get("severity", "MEDIUM")
        f_status_val = f.get("status", "OPEN")

        with st.expander(f"[{f_sev_val}] {f_code}: {f_issue} — Current Status: {f_status_val}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**File:** `{f.get('file_path')}`")
            c2.markdown(f"**Line:** `{f.get('line_start') or 'N/A'}`")
            c3.markdown(f"**Source:** `{f.get('source_type')}`")
            c4.markdown(f"**Confidence:** `{f.get('confidence')}`")

            if f.get("evidence"):
                st.markdown("**Evidence Code Snippet:**")
                st.code(f.get("evidence"), language="cpp")

            st.markdown(f"**Explanation:** {f.get('explanation')}")
            if f.get("recommendation"):
                st.markdown(f"**Recommendation:** {f.get('recommendation')}")
            if f.get("suggested_fix"):
                st.markdown("**Suggested Fix:**")
                st.code(f.get("suggested_fix"), language="cpp")

            st.markdown("---")
            st.markdown("#### 👤 Human Engineer Review Actions")
            col_act1, col_act2 = st.columns([1, 2])

            with col_act1:
                new_status = st.selectbox(
                    "Update Status",
                    ["OPEN", "CONFIRMED", "FALSE_POSITIVE", "IN_PROGRESS", "FIXED", "VERIFIED", "REJECTED"],
                    index=["OPEN", "CONFIRMED", "FALSE_POSITIVE", "IN_PROGRESS", "FIXED", "VERIFIED", "REJECTED"].index(f_status_val),
                    key=f"status_select_{fid}"
                )
                comment_text = st.text_input("Reviewer Comment / Rationale", key=f"comment_{fid}")
                if st.button("Apply Status Update", key=f"btn_update_{fid}"):
                    api_client.update_finding(fid, status=new_status, comment=comment_text or None)
                    st.success("Finding updated successfully!")
                    st.rerun()

            with col_act2:
                st.markdown("##### 🔬 Automated Fix Verification")
                test_code = st.text_area(
                    "Paste Applied Fix to Verify",
                    value=f.get("suggested_fix") or "",
                    height=100,
                    key=f"verify_code_{fid}"
                )
                if st.button("Verify Applied Fix", key=f"btn_verify_{fid}"):
                    with st.spinner("Re-analyzing fix against static rules & LLM verifier..."):
                        v_res = api_client.verify_finding(fid, test_code)
                        if v_res.get("verification_passed"):
                            st.success(f"✅ VERIFICATION PASSED: Status upgraded to VERIFIED! {v_res.get('explanation')}")
                            st.rerun()
                        else:
                            st.error(f"❌ VERIFICATION FAILED: Issue still detected. {v_res.get('explanation')}")
