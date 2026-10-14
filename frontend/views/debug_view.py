import streamlit as st
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 🛠️ Code Debugging & Root Cause Assistant")
    st.markdown("Analyze compiler errors, runtime crashes, and stack traces against local source code to pinpoint root causes and verified fixes.")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Load Preset: Null Pointer Dereference"):
            st.session_state["dbg_src"] = """int16_t SensorManager::readUnverifiedSensor() {
    // Pointer is accessed directly without checking m_unverifiedSensor != nullptr
    return m_unverifiedSensor->last_reading;
}"""
            st.session_state["dbg_err"] = "src/SensorManager.cpp:33:12: error: dereference of possibly-null pointer 'm_unverifiedSensor' [-Werror=null-dereference]"
            st.session_state["dbg_desc"] = "Engine ECU crashes with Segmentation Fault when reading backup coolant sensor during cranking."
            st.rerun()

    with col_btn2:
        if st.button("Load Preset: Unchecked CAN DLC Buffer Issue"):
            st.session_state["dbg_src"] = """void CANInterface::unpackPayloadUnsafe(const CANMessage* message, uint8_t* destinationBuffer) {
    // Length is directly copied without validating message->dlc <= 8 or destination capacity
    memcpy(destinationBuffer, message->data, message->dlc);
}"""
            st.session_state["dbg_err"] = "Runtime memory corruption detected when processing extended frame CAN ID 0x7E0."
            st.session_state["dbg_desc"] = "Stack corruption observed when receiving CAN payloads with DLC > 8 in test harness."
            st.rerun()

    col_in, col_out = st.columns([1, 1])

    with col_in:
        st.markdown("### Debug Evidence Inputs")
        
        # Quick Load from Active Project Files
        proj_files = api_client.list_project_files(current_project_id) if current_project_id else []
        if proj_files:
            file_opts = {f["id"]: f["file_name"] for f in proj_files}
            col_f1, col_f2 = st.columns([3, 1])
            with col_f1:
                sel_f = st.selectbox("📂 Load Code from Project File:", options=list(file_opts.keys()), format_func=lambda x: file_opts[x], key="dbg_file_sel")
            with col_f2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("📥 Load", key="btn_load_dbg_file", use_container_width=True):
                    c_res = api_client.get_file_content(current_project_id, sel_f)
                    if isinstance(c_res, dict) and "content" in c_res:
                        st.session_state["dbg_src"] = c_res["content"]
                        st.session_state["dbg_desc"] = f"Analyzing {file_opts[sel_f]} for runtime faults."
                        st.rerun()

        src_val = st.session_state.get("dbg_src", "")
        source_code = st.text_area("Source Code", value=src_val, height=200, placeholder="Paste affected function or code...")

        err_val = st.session_state.get("dbg_err", "")
        compiler_err = st.text_area("Compiler Error / Warning", value=err_val, height=100, placeholder="e.g. main.cpp:42:10: error: ...")

        desc_val = st.session_state.get("dbg_desc", "")
        user_desc = st.text_area("User Problem Description", value=desc_val, height=80, placeholder="Describe observed runtime failure symptoms...")

        runtime_err = st.text_input("Runtime Error / Exception (Optional)", placeholder="e.g. SIGSEGV / MemManage Fault")
        stack_trace = st.text_area("Stack Trace (Optional)", height=80, placeholder="Call stack frames...")

        submit_debug = st.button("🔍 Analyze Root Cause & Fix", use_container_width=True)

    with col_out:
        st.markdown("### Root Cause Analysis & Fix")
        if submit_debug:
            if not source_code.strip() and not compiler_err.strip() and not user_desc.strip():
                st.warning("Please provide code, compiler error, or problem description.")
            else:
                with st.spinner("Synthesizing deterministic diagnostics and local Ollama root-cause analysis..."):
                    res = api_client.debug_analyze(
                        project_id=current_project_id or 1,
                        source_code=source_code,
                        compiler_error=compiler_err,
                        runtime_error=runtime_err,
                        stack_trace=stack_trace,
                        user_description=user_desc
                    )

                    if "error" in res:
                        st.error(f"Debug analysis failed: {res['error']}")
                    else:
                        st.success(f"**Fault:** {res.get('error_summary')}")
                        st.markdown(f"**Severity:** `{res.get('severity')}` | **Confidence:** `{res.get('confidence')}`")
                        
                        st.markdown("#### 🔬 Likely Root Cause")
                        st.info(res.get("likely_root_cause"))

                        if res.get("affected_line"):
                            st.markdown(f"**Affected Line:** `{res.get('affected_line')}`")
                        if res.get("evidence"):
                            st.markdown(f"**Evidence:** `{res.get('evidence')}`")

                        st.markdown("#### 💡 Explanation")
                        st.write(res.get("explanation"))

                        st.markdown("#### 🔧 Suggested Remediation & Corrected Code")
                        st.write(res.get("suggested_fix"))

                        if res.get("corrected_code"):
                            st.code(res.get("corrected_code"), language="cpp")

                        st.caption(f"⚠️ **Limitations:** {res.get('limitations', 'AI analysis requires human engineer review.')}")
        else:
            st.info("Input error symptoms and click 'Analyze Root Cause & Fix'.")
