"""
Page 2 — Timeline: 5-year regulatory change timeline with interactive Plotly chart.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dashboard.utils import (
    get_all_regulations,
    SEVERITY_COLORS,
    SEVERITY_ORDER,
    STATE_COLORS,
    SOURCE_LABELS,
)

st.set_page_config(page_title="Timeline — Regulatory Monitor", page_icon="📊", layout="wide")

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    state_filter = st.radio("State", ["All", "TX", "CA"], horizontal=True)
    severity_filter = st.multiselect("Severity", SEVERITY_ORDER, default=SEVERITY_ORDER)
    source_options = list(SOURCE_LABELS.keys())
    source_filter = st.multiselect("Source", source_options, default=source_options, format_func=lambda x: SOURCE_LABELS[x])
    view_mode = st.radio("Color by", ["Severity", "Source", "State"], horizontal=True)

# ── Load Data ────────────────────────────────────────────
df = get_all_regulations(
    state_filter=state_filter if state_filter != "All" else None,
    severity_filter=tuple(severity_filter),
    source_filter=tuple(source_filter),
)

st.markdown("# 📊 Regulatory Change Timeline")
st.markdown("5-year view of life insurance regulatory activity — Mar 2021 to Mar 2026")
st.markdown("")

if df.empty:
    st.warning("No regulations found with current filters.")
    st.stop()

# ── Prepare timeline data ────────────────────────────────
df["published_date"] = pd.to_datetime(df["published_date"])
df["month"] = df["published_date"].dt.strftime("%Y-%m")
df["quarter"] = df["published_date"].dt.to_period("Q").astype(str)
df["year"] = df["published_date"].dt.year

# ── Main chart ───────────────────────────────────────────
if view_mode == "Severity":
    monthly = df.groupby(["month", "severity"]).size().reset_index(name="count")
    fig = px.bar(
        monthly,
        x="month",
        y="count",
        color="severity",
        color_discrete_map=SEVERITY_COLORS,
        category_orders={"severity": SEVERITY_ORDER},
        labels={"month": "Month", "count": "Regulations", "severity": "Severity"},
    )
elif view_mode == "Source":
    monthly = df.groupby(["month", "source"]).size().reset_index(name="count")
    monthly["source_label"] = monthly["source"].map(SOURCE_LABELS)
    fig = px.bar(
        monthly,
        x="month",
        y="count",
        color="source_label",
        labels={"month": "Month", "count": "Regulations", "source_label": "Source"},
    )
else:
    monthly = df.groupby(["month", "state"]).size().reset_index(name="count")
    fig = px.bar(
        monthly,
        x="month",
        y="count",
        color="state",
        color_discrete_map=STATE_COLORS,
        labels={"month": "Month", "count": "Regulations", "state": "State"},
    )

fig.update_layout(
    height=450,
    margin=dict(l=20, r=20, t=40, b=60),
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font_color="#374151",
    xaxis=dict(tickangle=-45, dtick=3, gridcolor="#E5E7EB"),
    yaxis=dict(gridcolor="#E5E7EB"),
    barmode="stack",
    legend=dict(orientation="h", y=-0.2),
)

st.plotly_chart(fig, width="stretch")

# ── Summary stats ────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total in view", len(df))
col2.metric("Critical", len(df[df["severity"] == "critical"]))
col3.metric("High", len(df[df["severity"] == "high"]))
col4.metric("Avg/month", round(len(df) / max(df["month"].nunique(), 1), 1))

# ── Yearly breakdown ─────────────────────────────────────
st.markdown("#### Yearly breakdown")
yearly = df.groupby("year").agg(
    total=("id", "count"),
    critical=("severity", lambda x: (x == "critical").sum()),
    high=("severity", lambda x: (x == "high").sum()),
    medium=("severity", lambda x: (x == "medium").sum()),
    low=("severity", lambda x: (x == "low").sum()),
).reset_index()
yearly.columns = ["Year", "Total", "Critical", "High", "Medium", "Low"]
st.dataframe(yearly, width="stretch", hide_index=True)

# ── Detail table ─────────────────────────────────────────
st.markdown("#### All regulations")
df_table = df[["published_date", "title", "source_label", "state", "severity"]].copy()
df_table.columns = ["Date", "Title", "Source", "State", "Severity"]
df_table["Date"] = pd.to_datetime(df_table["Date"]).dt.strftime("%Y-%m-%d")
df_table["Title"] = df_table["Title"].str[:90]

st.dataframe(df_table, width="stretch", hide_index=True, height=500)
