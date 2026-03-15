"""
Page 3 — Impact Matrix: Which of the 18 policies are most affected?
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dashboard.utils import (
    get_all_impacts,
    get_all_regulations,
    get_impacts_for_regulation,
    SEVERITY_COLORS,
    STATE_COLORS,
)

st.set_page_config(page_title="Impact Matrix — Regulatory Monitor", page_icon="🎯", layout="wide")

st.markdown("# 🎯 Policy Impact Matrix")
st.markdown("Which policies face the most regulatory compliance pressure?")
st.markdown("")

# ── Load Data ────────────────────────────────────────────
impacts_df = get_all_impacts()
regs_df = get_all_regulations()

if impacts_df.empty:
    st.warning("No policy impacts found.")
    st.stop()

# ── Top affected policies (bar chart) ────────────────────
st.markdown("#### Most affected policies")

policy_counts = impacts_df.groupby(["policy_id", "policy_name"]).size().reset_index(name="impact_count")
policy_counts = policy_counts.sort_values("impact_count", ascending=True)
policy_counts["label"] = policy_counts["policy_id"] + " — " + policy_counts["policy_name"]

fig_bar = go.Figure(data=[go.Bar(
    y=policy_counts["label"],
    x=policy_counts["impact_count"],
    orientation="h",
    marker_color="#3B82F6",
    text=policy_counts["impact_count"],
    textposition="outside",
    textfont_size=13,
)])

fig_bar.update_layout(
    height=max(400, len(policy_counts) * 35),
    margin=dict(l=20, r=40, t=20, b=20),
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font_color="#374151",
    xaxis=dict(title="Number of regulatory impacts", gridcolor="#E5E7EB"),
    yaxis=dict(title=""),
)

st.plotly_chart(fig_bar, width="stretch")

# ── State split ──────────────────────────────────────────
st.markdown("#### TX vs CA impact comparison")

col_tx, col_ca = st.columns(2)

with col_tx:
    st.markdown("**Texas (TX)**")
    tx_impacts = impacts_df[impacts_df["affected_state"].isin(["TX", "BOTH"])]
    tx_counts = tx_impacts.groupby("policy_id").size().reset_index(name="count").sort_values("count", ascending=False)
    if not tx_counts.empty:
        fig_tx = go.Figure(data=[go.Bar(
            x=tx_counts["policy_id"],
            y=tx_counts["count"],
            marker_color="#3B82F6",
            text=tx_counts["count"],
            textposition="outside",
        )])
        fig_tx.update_layout(
            height=280,
            margin=dict(l=20, r=20, t=20, b=40),
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            font_color="#374151",
            yaxis=dict(gridcolor="#E5E7EB"),
        )
        st.plotly_chart(fig_tx, width="stretch")
    else:
        st.info("No TX impacts.")

with col_ca:
    st.markdown("**California (CA)**")
    ca_impacts = impacts_df[impacts_df["affected_state"].isin(["CA", "BOTH"])]
    ca_counts = ca_impacts.groupby("policy_id").size().reset_index(name="count").sort_values("count", ascending=False)
    if not ca_counts.empty:
        fig_ca = go.Figure(data=[go.Bar(
            x=ca_counts["policy_id"],
            y=ca_counts["count"],
            marker_color="#8B5CF6",
            text=ca_counts["count"],
            textposition="outside",
        )])
        fig_ca.update_layout(
            height=280,
            margin=dict(l=20, r=20, t=20, b=40),
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            font_color="#374151",
            yaxis=dict(gridcolor="#E5E7EB"),
        )
        st.plotly_chart(fig_ca, width="stretch")
    else:
        st.info("No CA impacts.")

# ── Heatmap: Policy × Regulation ─────────────────────────
st.markdown("#### Impact heatmap — policies × time")

# Merge impacts with regulation dates
merged = impacts_df.merge(
    regs_df[["id", "published_date", "severity"]],
    left_on="regulation_id",
    right_on="id",
    how="left",
)
merged["published_date"] = pd.to_datetime(merged["published_date"])
merged["quarter"] = merged["published_date"].dt.to_period("Q").astype(str)

heatmap_data = merged.groupby(["policy_id", "quarter"]).size().reset_index(name="count")
heatmap_pivot = heatmap_data.pivot(index="policy_id", columns="quarter", values="count").fillna(0)

if not heatmap_pivot.empty:
    fig_heat = px.imshow(
        heatmap_pivot.values,
        labels=dict(x="Quarter", y="Policy", color="Impacts"),
        x=list(heatmap_pivot.columns),
        y=list(heatmap_pivot.index),
        color_continuous_scale="Blues",
        aspect="auto",
    )
    fig_heat.update_layout(
        height=max(350, len(heatmap_pivot) * 30),
        margin=dict(l=20, r=20, t=20, b=60),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font_color="#374151",
        xaxis=dict(tickangle=-45),
    )
    st.plotly_chart(fig_heat, width="stretch")

# ── Policy detail expander ───────────────────────────────
st.markdown("#### Policy details")
st.markdown("Expand any policy to see all regulations that affect it.")

unique_policies = impacts_df.groupby(["policy_id", "policy_name"]).size().reset_index(name="count")
unique_policies = unique_policies.sort_values("count", ascending=False)

for _, row in unique_policies.iterrows():
    with st.expander(f"**{row['policy_id']}** — {row['policy_name']} ({row['count']} impacts)"):
        policy_impacts = impacts_df[impacts_df["policy_id"] == row["policy_id"]]
        display_df = policy_impacts[["affected_state", "affected_clause", "impact_description"]].copy()
        display_df.columns = ["State", "Clause", "Impact"]
        st.dataframe(display_df, width="stretch", hide_index=True)
