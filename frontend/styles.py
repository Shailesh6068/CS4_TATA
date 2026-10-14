"""Shared light-theme styling for the SecureCode AI Streamlit interface."""

AUTOMOTIVE_THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

code, pre {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace !important;
}

[data-testid="stAppViewContainer"] {
    background: #f8fafc;
    color: #172033;
}

[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 1440px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stHeader"] {
    background: rgba(248, 250, 252, 0.94);
}

[data-testid="stSidebar"] {
    background: #f1f5f9;
    border-right: 1px solid #e4e9f0;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: #344054;
}

h1, h2, h3, h4 {
    color: #172033;
    letter-spacing: -0.02em;
}

hr {
    border-color: #e4e9f0;
}

/* Privacy Indicator Banner */
.privacy-badge-container {
    display: flex;
    align-items: center;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-radius: 10px;
    padding: 10px 16px;
    margin: 4px 0 24px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #047857;
}

.privacy-badge-dot {
    height: 10px;
    width: 10px;
    background-color: #10B981;
    border-radius: 50%;
    display: inline-block;
    margin-right: 10px;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

.sidebar-brand {
    text-align: center;
    margin: 4px 0 20px;
}

.sidebar-brand h2 {
    color: #0f766e;
    margin: 0;
    font-size: 1.35rem;
    letter-spacing: -0.03em;
}

.sidebar-brand p {
    color: #667085;
    font-size: 0.75rem;
    margin: 2px 0 0;
}

.ollama-status-card {
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 16px;
    border: 1px solid #e4e9f0;
    background: #f8fafc;
    font-size: 0.8rem;
}

.ollama-status-card.is-connected {
    background: #ecfdf5;
    border-color: #a7f3d0;
}

.ollama-status-card.is-disconnected {
    background: #fff5f5;
    border-color: #fecdca;
}

.ollama-status-title {
    color: #047857;
    font-weight: 700;
}

.is-disconnected .ollama-status-title {
    color: #b42318;
}

.ollama-status-model {
    color: #667085;
    font-size: 0.75rem;
    margin-top: 3px;
}

/* Metrics Cards */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e4e9f0;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(23, 32, 51, 0.05);
    min-height: 108px;
}

.kpi-title {
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    color: #667085;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
    white-space: nowrap;
}

.kpi-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: #172033;
}

.kpi-sub {
    font-size: 0.75rem;
    color: #667085;
    margin-top: 4px;
    line-height: 1.35;
}

/* Severity Badges */
.badge-critical {
    background-color: #EF4444;
    color: white;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.75rem;
}
.badge-high {
    background-color: #F97316;
    color: white;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.75rem;
}
.badge-medium {
    background-color: #EAB308;
    color: #1E293B;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.75rem;
}
.badge-low {
    background-color: #3B82F6;
    color: white;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.75rem;
}

/* Disclaimer Callout */
.disclaimer-box {
    background: #fffaeb;
    border: 1px solid #fedf89;
    border-left: 4px solid #f79009;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 16px 0;
    font-size: 0.85rem;
    color: #9a3412;
}

/* Modern Hero Header */
.hero-header-card {
    background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
    border: 1px solid #bae6fd;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(23, 32, 51, 0.08);
    position: relative;
    overflow: hidden;
}

.hero-header-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #06B6D4 0%, #3B82F6 50%, #8B5CF6 100%);
}

.hero-title {
    font-size: 1.65rem;
    font-weight: 700;
    color: #172033;
    margin: 0 0 6px 0;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 12px;
}

.hero-subtitle {
    color: #475467;
    font-size: 0.9rem;
    margin: 0;
    line-height: 1.5;
}

.hero-tags {
    display: flex;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
}

.hero-tag {
    background: #ffffff;
    border: 1px solid #d0d5dd;
    color: #475467;
    font-size: 0.75rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.hero-tag.cyan {
    border-color: rgba(6, 182, 212, 0.4);
    color: #38BDF8;
    background: #ecfeff;
}

.hero-tag.green {
    border-color: rgba(16, 185, 129, 0.4);
    color: #34D399;
    background: #ecfdf5;
}

/* Panel Containers */
.panel-card {
    background: #ffffff;
    border: 1px solid #e4e9f0;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(23, 32, 51, 0.06);
}

.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e4e9f0;
}

.panel-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #172033;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Explanation Output Section Cards */
.analysis-section {
    background: #ffffff;
    border: 1px solid #e4e9f0;
    border-left: 4px solid #06B6D4;
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 14px;
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.analysis-section:hover {
    border-color: #38BDF8;
    background: #131D31;
}

.analysis-section.purple {
    border-left-color: #A855F7;
}

.analysis-section.blue {
    border-left-color: #3B82F6;
}

.analysis-section.emerald {
    border-left-color: #10B981;
}

.analysis-section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #344054;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.analysis-section-content {
    color: #475467;
    font-size: 0.9rem;
    line-height: 1.6;
}

/* Critical Risk Card */
.risk-callout-card {
    background: #fff5f5;
    border: 1px solid #fecdca;
    border-left: 5px solid #EF4444;
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 14px;
}

.risk-callout-title {
    color: #b42318;
    font-size: 0.95rem;
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.risk-callout-content {
    color: #912018;
    font-size: 0.9rem;
    line-height: 1.6;
}

/* Empty State Card */
.empty-state-card {
    background: #ffffff;
    border: 2px dashed #d0d5dd;
    border-radius: 12px;
    padding: 48px 24px;
    text-align: center;
    color: #667085;
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 14px;
    opacity: 0.7;
}

.empty-state-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #475467;
    margin-bottom: 6px;
}

.empty-state-sub {
    font-size: 0.85rem;
    color: #667085;
    max-width: 420px;
    margin: 0 auto;
    line-height: 1.5;
}

/* Streamlit Button Overrides */
div.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    border: 1px solid #cbd5e1 !important;
}

div.stButton > button[kind="primary"] {
    background: #0f766e !important;
    border-color: #0f766e !important;
    color: #ffffff !important;
}

div.stButton > button:hover {
    border-color: #0f766e !important;
    color: #0f766e !important;
    box-shadow: 0 4px 12px rgba(15, 118, 110, 0.16) !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
textarea {
    border-color: #d0d5dd !important;
    background: #ffffff !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
textarea:focus {
    border-color: #0f766e !important;
    box-shadow: 0 0 0 1px #0f766e !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #e4e9f0;
    border-radius: 10px;
    overflow: hidden;
}

@media (max-width: 768px) {
    .privacy-badge-container {
        align-items: flex-start;
        font-size: 0.78rem;
    }

    .kpi-card {
        min-height: auto;
    }
}
</style>
"""
