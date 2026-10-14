import streamlit as st
import pandas as pd
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 📜 Compiler Diagnostics & Runtime Log Analyzer")
    st.markdown("Parse GCC, Clang, and MSVC build logs and diagnose automotive ECU runtime traces and DTC fault events.")

    tab_comp, tab_log = st.tabs(["Compiler Diagnostics (Build Logs)", "Automotive ECU Runtime Logs"])

    with tab_comp:
        st.markdown("### Compiler Warning & Error Analysis")
        if st.button("Load Preset: GCC / Clang ECU Build Log"):
            st.session_state["comp_log_input"] = """src/CANInterface.cpp:24:14: warning: conversion from 'void*' to 'uint8_t*' in dynamic allocation [-Wconversion]
src/CANInterface.cpp:30:26: warning: cast from 'uint8_t*' to 'uint32_t*' increases required alignment of target type [-Wcast-align]
src/CANInterface.cpp:37:19: warning: expression with side effects in assertion [-Wunused-value]
src/SensorManager.cpp:27:9: warning: 'strcpy' is deprecated: This function or variable may be unsafe [-Wdeprecated-declarations]
src/SensorManager.cpp:33:12: error: dereference of possibly-null pointer 'm_unverifiedSensor' [-Werror=null-dereference]
src/EngineController.cpp:58:12: warning: variable 'uninit_var' may be used uninitialized [-Wmaybe-uninitialized]
src/EngineController.cpp:63:5: warning: statement will never be executed [-Wunreachable-code]"""
            st.rerun()

        raw_log = st.text_area(
            "Compiler Log Content",
            value=st.session_state.get("comp_log_input", ""),
            height=200,
            placeholder="Paste GCC, Clang, or MSVC build output..."
        )

        if st.button("🔍 Parse & Analyze Compiler Log", use_container_width=True) and raw_log.strip():
            with st.spinner("Parsing compiler output tokens..."):
                res = api_client.debug_analyze(
                    project_id=current_project_id or 1,
                    compiler_error=raw_log,
                    user_description="Analyze all compiler errors and warnings in build log."
                )
                if "error" in res:
                    st.error(f"Analysis failed: {res['error']}")
                else:
                    st.success(f"**Diagnosis:** {res.get('error_summary')}")
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Severity:** `{res.get('severity')}`")
                    c2.markdown(f"**Confidence:** `{res.get('confidence')}`")

                    st.markdown("#### Root Cause Breakdown")
                    st.info(res.get("likely_root_cause"))

                    st.markdown("#### Suggested Compiler Remediation")
                    st.write(res.get("suggested_fix"))
                    if res.get("corrected_code"):
                        st.code(res.get("corrected_code"), language="cpp")

    with tab_log:
        st.markdown("### ECU Runtime & Crash Log Analysis")
        if st.button("Load Preset: ECU Powertrain Runtime Log"):
            st.session_state["ecu_log_input"] = """[2026-10-07 10:14:01.120] [INFO] ECU Boot sequence initialized. Firmware: v2.4.1-RC3
[2026-10-07 10:14:01.155] [INFO] CANInterface initialized at 500kbps (ISO 11898-2).
[2026-10-07 10:14:01.200] [INFO] SensorManager initialized: Coolant=85C, Throttle=25%.
[2026-10-07 10:14:02.050] [WARN] CAN Busload warning: arbitration load at 78.4%.
[2026-10-07 10:14:02.500] [ERROR] DTC U0100: Lost Communication with ECM/PCM module.
[2026-10-07 10:14:02.505] [ERROR] DTC U0100: Retrying transmission on CAN channel 0...
[2026-10-07 10:14:03.100] [CRITICAL] Sensor acquisition timeout on channel 2. Attempting fail-safe recovery.
[2026-10-07 10:14:03.105] [ERROR] DTC P0117: Engine Coolant Temperature Sensor 1 Circuit Low.
[2026-10-07 10:14:04.200] [WARN] Throttle sensor jitter exceeds 5% tolerance window.
[2026-10-07 10:14:05.000] [ERROR] DTC U0100: Lost Communication with ECM/PCM module."""
            st.rerun()

        raw_ecu_log = st.text_area(
            "ECU Log Content",
            value=st.session_state.get("ecu_log_input", ""),
            height=200,
            placeholder="Paste ECU diagnostic log, serial terminal trace, or crash dump..."
        )

        log_type = st.selectbox("Log Type", ["ECU", "RUNTIME", "CRASH", "BUILD"])

        if st.button("📊 Analyze ECU Log Sequence", use_container_width=True) and raw_ecu_log.strip():
            with st.spinner("Extracting timeline, DTC fault events, and repeated sequences..."):
                res = api_client.analyze_logs(
                    project_id=current_project_id or 1,
                    log_content=raw_ecu_log,
                    log_type=log_type
                )

                if "error" in res:
                    st.error(f"Log analysis failed: {res['error']}")
                else:
                    st.success(res.get("error_summary"))

                    timeline = res.get("timeline", [])
                    if timeline:
                        st.markdown("#### Chronological Event Timeline")
                        st.dataframe(pd.DataFrame(timeline), use_container_width=True)

                    repeated = res.get("repeated_errors", [])
                    if repeated:
                        st.markdown("#### Repeated Faults & DTCs")
                        st.dataframe(pd.DataFrame(repeated), use_container_width=True)

                    st.markdown("#### Root Cause Assessment")
                    st.info(res.get("possible_root_cause"))

                    recs = res.get("recommendations", [])
                    if recs:
                        st.markdown("#### Engineering Recommendations")
                        for r in recs:
                            st.markdown(f"- {r}")
