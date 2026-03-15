"""
Page 5 — Data Explorer: Full searchable table, funnel stats, API usage.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from dashboard.utils import (
    get_all_regulations,
    get_overview_stats,
    SOURCE_LABELS,
    SOURCE_COLORS,
    SEVERITY_ORDER,
)

st.set_page_config(page_title="Data Explorer — Regulatory Monitor", page_icon="🔍", layout="wide")

st.markdown("# 🔍 Data explorer")
st.markdown("Full transparency — search all 3,533 regulations, view classification decisions, and API usage stats.")
st.markdown("")

stats = get_overview_stats()

# ── Processing funnel ────────────────────────────────────
st.markdown("#### Processing funnel")

funnel_stages = ["Scraped", "Relevant", "Policy impacts", "Memos generated"]
funnel_values = [stats["total"], stats["relevant"], stats["impacts"], stats["memos"]]

fig_funnel = go.Figure(go.Funnel(
    y=funnel_stages,
    x=funnel_values,
    textinfo="value+percent initial",
    textfont_size=14,
    marker_color=["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B"],
    connector_line_color="#D1D5DB",
))

fig_funnel.update_layout(
    height=300,
    margin=dict(l=20, r=20, t=20, b=20),
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font_color="#374151",
)

st.plotly_chart(fig_funnel, width="stretch")

# ── Source breakdown ─────────────────────────────────────
st.markdown("#### Data by source")
col1, col2, col3, col4 = st.columns(4)

src = stats["source"]
col1.metric("Federal Register", src.get("federal_register", 0))
col2.metric("TDI (Texas)", src.get("tdi", 0))
col3.metric("CDI (California)", src.get("cdi", 0))
col4.metric("OFAC", src.get("ofac", 0))

# ── Full data table ──────────────────────────────────────
st.markdown("#### All regulations (searchable)")

search_text = st.text_input("🔍 Search by title", "")

df_all = get_all_regulations(relevant_only=False)

if not df_all.empty:
    if search_text:
        mask = df_all["title"].str.contains(search_text, case=False, na=False)
        df_all = df_all[mask]

    df_table = df_all[["published_date", "title", "source_label", "state", "severity", "status"]].copy()
    df_table.columns = ["Date", "Title", "Source", "State", "Severity", "Status"]
    df_table["Date"] = pd.to_datetime(df_table["Date"]).dt.strftime("%Y-%m-%d")
    df_table["Title"] = df_table["Title"].str[:85]

    st.markdown(f"Showing **{len(df_table):,}** regulations")

    st.dataframe(
        df_table,
        width="stretch",
        hide_index=True,
        height=600,
    )
else:
    st.info("No data found.")
