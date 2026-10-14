import streamlit as st
import pandas as pd
from frontend.api_client import api_client

def render(current_project_id: int):
    st.markdown("## 📊 Automotive Engineering & Security Dashboard")
    
    # Fetch Data
    findings = api_client.list_findings(project_id=current_project_id)
    quality = api_client.get_quality_score(current_project_id) if current_project_id else {}
    files = api_client.list_project_files(current_project_id) if current_project_id else []
    
    total_loc = sum(f.get("line_count", 0) for f in files)
    open_findings = [f for f in findings if f.get("status") == "OPEN"]
    crit_count = sum(1 for f in findings if f.get("severity") == "CRITICAL")
    high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
    fixed_count = sum(1 for f in findings if f.get("status") in ("FIXED", "VERIFIED"))
    fp_count = sum(1 for f in findings if f.get("status") == "FALSE_POSITIVE")

    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Files</div>
            <div class="kpi-value">{len(files)}</div>
            <div class="kpi-sub">{total_loc} total LOC</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Quality</div>
            <div class="kpi-value" style="color: #06B6D4;">{quality.get('overall_score', 85.0)}<span style="font-size: 1rem;">/100</span></div>
            <div class="kpi-sub">Overall score</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Open</div>
            <div class="kpi-value" style="color: {'#EF4444' if len(open_findings) > 0 else '#10B981'};">{len(open_findings)}</div>
            <div class="kpi-sub">Needs human review</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Risk</div>
            <div class="kpi-value" style="color: #F97316;">{crit_count + high_count}</div>
            <div class="kpi-sub">{crit_count} Critical, {high_count} High</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Resolved</div>
            <div class="kpi-value" style="color: #10B981;">{fixed_count}</div>
            <div class="kpi-sub">{fp_count} false positives</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Multi-dimensional Quality Radar / Scores
    st.markdown("### 🎯 Engineering Quality Indicator Breakdown")
    qc1, qc2, qc3, qc4, qc5 = st.columns(5)
    qc1.metric("Security", f"{quality.get('security_score', 82.0)}/100")
    qc2.metric("Correctness", f"{quality.get('correctness_score', 78.0)}/100")
    qc3.metric("Maintainability", f"{quality.get('maintainability_score', 80.0)}/100")
    qc4.metric("Performance", f"{quality.get('performance_score', 85.0)}/100")
    qc5.metric("Readability", f"{quality.get('readability_score', 88.0)}/100")

    if quality.get("explanation"):
        st.caption(f"ℹ️ {quality.get('explanation')}")

    st.markdown("---")

    # Findings Visualizations
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("#### Findings by Severity")
        if findings:
            sev_counts = pd.Series([f.get("severity") for f in findings]).value_counts()
            st.bar_chart(sev_counts)
        else:
            st.info("No findings recorded yet. Run a review to populate metrics.")

    with col_chart2:
        st.markdown("#### Findings by Source Type (AI vs Deterministic)")
        if findings:
            src_counts = pd.Series([f.get("source_type") for f in findings]).value_counts()
            st.bar_chart(src_counts)
        else:
            st.info("No review telemetry available.")

    st.markdown("---")

    # Recent High-Priority Findings Table
    st.markdown("#### 🚨 Priority Action Items (Critical & High Severity)")
    priority_findings = [f for f in findings if f.get("severity") in ("CRITICAL", "HIGH")]
    if priority_findings:
        table_rows = []
        for f in priority_findings:
            table_rows.append({
                "ID": f.get("finding_code"),
                "Severity": f.get("severity"),
                "Source": f.get("source_type"),
                "File": f.get("file_path"),
                "Line": f.get("line_start"),
                "Issue": f.get("issue"),
                "Status": f.get("status")
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
    else:
        st.success("✅ No unmitigated Critical or High severity findings in current workspace.")
