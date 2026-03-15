"""
dashboard/app.py
Main Streamlit app — Executive Overview (Home Page)
Run: streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from dashboard.utils import (
    get_overview_stats,
    get_all_regulations,
    SEVERITY_COLORS,
    SEVERITY_ORDER,
    STATE_COLORS,
    SOURCE_COLORS,
    SOURCE_LABELS,
    severity_badge,
    state_badge,
)

# ── Page Config ──────────────────────────────────────────
st.set_page_config(
    page_title="Regulatory Change Monitor",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .stMetric > div { background: #F0F2F6; border: 1px solid #D1D5DB; border-radius: 10px; padding: 16px 20px; }
    .stMetric label { font-size: 13px !important; color: #6B7280 !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 32px !important; font-weight: 700 !important; color: #1F2937 !important; }
    h1 { font-size: 28px !important; }
    .severity-critical { color: #DC2626; font-weight: 700; }
    .severity-high { color: #EA580C; font-weight: 700; }
    .severity-medium { color: #3B82F6; font-weight: 700; }
    .severity-low { color: #6B7280; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/bank-building.png", width=40)
    st.markdown("### Regulatory Monitor")
    st.markdown("**Life Insurance Company**")
    st.markdown("TX + CA")
    st.divider()

    st.markdown("#### Filters")
    state_filter = st.radio("State", ["All", "TX", "CA"], horizontal=True)
    severity_filter = st.multiselect(
        "Severity",
        SEVERITY_ORDER,
        default=SEVERITY_ORDER,
    )
    source_options = list(SOURCE_LABELS.keys())
    source_filter = st.multiselect(
        "Source",
        source_options,
        default=source_options,
        format_func=lambda x: SOURCE_LABELS[x],
    )

    st.divider()
    st.markdown(
        '<p style="font-size:11px; color:#6B7280;">Data: Mar 2021 – Mar 2026<br>'
        'Model: claude-sonnet-4<br>'
        'Policies: 11 products + 7 riders</p>',
        unsafe_allow_html=True,
    )

# ── Load Data ────────────────────────────────────────────
stats = get_overview_stats()

# ── Header ───────────────────────────────────────────────
st.markdown("# 🏛️ Regulatory Change Monitor")
st.markdown("Texas & California — 5 Year Analysis")
st.markdown("")

# ── KPI Row ──────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Tracked", f"{stats['total']:,}")
col2.metric("Relevant to Life", f"{stats['relevant']:,}")
col3.metric("Policy Impacts", f"{stats['impacts']:,}")
col4.metric("Memos Generated", f"{stats['memos']:,}")
col5.metric("Policies Affected", f"{stats['policies_affected']}/18")

st.markdown("")

# ── Row 2: Severity + State ──────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Severity breakdown")

    sev_data = stats["severity"]
    colors = [SEVERITY_COLORS[s] for s in SEVERITY_ORDER]
    values = [sev_data.get(s, 0) for s in SEVERITY_ORDER]

    fig_sev = go.Figure(data=[go.Pie(
        labels=[s.upper() for s in SEVERITY_ORDER],
        values=values,
        hole=0.55,
        marker_colors=colors,
        textinfo="label+value",
        textfont_size=13,
    )])
    fig_sev.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font_color="#374151",
        showlegend=False,
    )
    st.plotly_chart(fig_sev, width="stretch")

with col_right:
    st.markdown("#### State comparison")

    state_data = stats["state"]
    states = ["TX", "CA", "BOTH"]
    state_values = [state_data.get(s, 0) for s in states]
    state_cols = [STATE_COLORS[s] for s in states]

    fig_state = go.Figure(data=[go.Bar(
        x=states,
        y=state_values,
        marker_color=state_cols,
        text=state_values,
        textposition="outside",
        textfont_size=16,
    )])
    fig_state.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=30, b=40),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font_color="#374151",
        xaxis=dict(title="", tickfont_size=14),
        yaxis=dict(title="Regulations", gridcolor="#E5E7EB"),
    )
    st.plotly_chart(fig_state, width="stretch")

# ── Row 3: Source breakdown ──────────────────────────────
st.markdown("#### Source distribution")

src_data = stats["source"]
src_labels = [SOURCE_LABELS[s] for s in src_data]
src_values = list(src_data.values())
src_colors = [SOURCE_COLORS[s] for s in src_data]

fig_src = go.Figure(data=[go.Bar(
    x=src_labels,
    y=src_values,
    marker_color=src_colors,
    text=src_values,
    textposition="outside",
    textfont_size=14,
)])
fig_src.update_layout(
    height=280,
    margin=dict(l=20, r=20, t=20, b=40),
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font_color="#374151",
    yaxis=dict(gridcolor="#E5E7EB"),
)
st.plotly_chart(fig_src, width="stretch")

# ── Row 4: Recent Critical/High ─────────────────────────
st.markdown("#### Recent critical & high severity items")

df = get_all_regulations(
    state_filter=state_filter if state_filter != "All" else None,
    severity_filter=("critical", "high"),
    source_filter=tuple(source_filter),
)

if not df.empty:
    df_display = df.head(15)[["published_date", "title", "state", "severity", "source_label"]].copy()
    df_display.columns = ["Date", "Title", "State", "Severity", "Source"]
    df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.strftime("%Y-%m-%d")
    df_display["Title"] = df_display["Title"].str[:80] + "..."

    st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        height=400,
    )
else:
    st.info("No critical/high severity items found with current filters.")

# ── Footer ───────────────────────────────────────────────
st.divider()
st.markdown(
    '<p style="font-size:11px; color:#6B7280; text-align:center;">'
    'Regulatory Change Monitor Agent — POC | '
    'Powered by Claude AI + ChromaDB | Data: Federal Register API + TDI + CDI + OFAC | '
    '5-year analysis: Mar 2021 – Mar 2026</p>',
    unsafe_allow_html=True,
)
