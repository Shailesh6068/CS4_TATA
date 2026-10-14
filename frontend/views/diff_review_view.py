import streamlit as st
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🔀 Git Diff & Code Change Review")
    st.markdown("Perform differential review of pull requests and commit diffs. Verify whether a proposed patch resolves an issue or introduces security regressions.")

    if not current_project_id:
        st.warning("Please select a project first.")
        return

    if st.button("Load Preset: CAN Payload Fix Patch"):
        st.session_state["diff_before"] = """void CANInterface::unpackPayloadUnsafe(const CANMessage* message, uint8_t* destinationBuffer) {
    // Insecure: no bounds check
    memcpy(destinationBuffer, message->data, message->dlc);
}"""
        st.session_state["diff_after"] = """void CANInterface::unpackPayloadUnsafe(const CANMessage* message, uint8_t* destinationBuffer) {
    // Secured with DLC length check
    if (message != nullptr && destinationBuffer != nullptr && message->dlc <= 8) {
        memcpy(destinationBuffer, message->data, message->dlc);
    }
}"""
        st.rerun()

    col_b, col_a = st.columns(2)
    with col_b:
        st.markdown("### Before Version (Original Code)")
        before_code = st.text_area("Original Code", value=st.session_state.get("diff_before", ""), height=200, placeholder="Code before change...")

    with col_a:
        st.markdown("### After Version (Revised Code)")
        after_code = st.text_area("Revised Code", value=st.session_state.get("diff_after", ""), height=200, placeholder="Code after change...")

    submit_diff = st.button("🚀 Analyze Code Change", use_container_width=True)

    if submit_diff:
        if not before_code.strip() and not after_code.strip():
            st.warning("Please provide code changes to analyze.")
        else:
            with st.spinner("Analyzing delta risks and verifying regressions..."):
                res = api_client.run_diff_review(
                    project_id=current_project_id,
                    before_code=before_code,
                    after_code=after_code,
                    file_name="CANInterface.cpp"
                )

                if "error" in res:
                    st.error(f"Diff review failed: {res['error']}")
                else:
                    verdict = res.get("introduces_security_vulnerability", "UNCERTAIN")
                    if verdict == "YES":
                        st.error(f"🚨 **VULNERABILITY INTRODUCED: YES** (Confidence: {res.get('confidence')})")
                    elif verdict == "NO":
                        st.success(f"✅ **NO NEW VULNERABILITY DETECTED** (Confidence: {res.get('confidence')})")
                    else:
                        st.warning(f"⚠️ **UNCERTAIN RISK PROFILE** (Confidence: {res.get('confidence')})")

                    st.markdown("### Detailed Engineering Diff Analysis")
                    st.markdown(res.get("detailed_analysis"))
