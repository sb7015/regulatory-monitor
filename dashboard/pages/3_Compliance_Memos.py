"""
Page 4 — Compliance Memos: Select any regulation and read the full Claude-generated memo.
"""

import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from dashboard.utils import (
    get_regulations_with_memos,
    get_impacts_for_regulation,
    SEVERITY_COLORS,
    STATE_COLORS,
    severity_badge,
    state_badge,
)

st.set_page_config(page_title="Compliance Memos — Regulatory Monitor", page_icon="📋", layout="wide")

st.markdown("# 📋 Compliance memos")
st.markdown("AI-generated compliance memos with state-specific action items for TX and CA.")
st.markdown("")

# ── Load memos ───────────────────────────────────────────
memos = get_regulations_with_memos()

if not memos:
    st.warning("No compliance memos found.")
    st.stop()

st.markdown(f"**{len(memos)} memos available** — select one to view:")
st.markdown("")

# ── Sidebar filter ───────────────────────────────────────
with st.sidebar:
    st.markdown("### Memo filters")
    memo_state = st.radio("State", ["All", "TX", "CA", "BOTH"], horizontal=True)
    memo_severity = st.multiselect("Severity", ["critical", "high", "medium", "low"], default=["critical", "high", "medium", "low"])

# ── Filter memos ─────────────────────────────────────────
filtered = memos
if memo_state != "All":
    filtered = [m for m in filtered if m["state"] == memo_state or m["state"] == "BOTH"]
if memo_severity:
    filtered = [m for m in filtered if m["severity"] in memo_severity]

if not filtered:
    st.info("No memos match the current filters.")
    st.stop()

# ── Memo selector ────────────────────────────────────────
memo_options = {}
for m in filtered:
    date_str = m["published_date"].strftime("%Y-%m-%d") if m["published_date"] else "unknown"
    sev = m["severity"].upper() if m["severity"] else ""
    label = f"[{sev}] [{m['state']}] {date_str} — {m['title'][:80]}"
    memo_options[label] = m

selected_label = st.selectbox("Select regulation", list(memo_options.keys()))
selected = memo_options[selected_label]

st.markdown("")
st.divider()

# ── Memo header ──────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"**Severity**")
    sev_color = SEVERITY_COLORS.get(selected["severity"], "#6B7280")
    st.markdown(
        f'<span style="background:{sev_color}; color:white; padding:4px 12px; '
        f'border-radius:6px; font-size:14px; font-weight:700;">'
        f'{selected["severity"].upper()}</span>',
        unsafe_allow_html=True,
    )

with col2:
    st.markdown("**State**")
    st_color = STATE_COLORS.get(selected["state"], "#6B7280")
    st.markdown(
        f'<span style="background:{st_color}; color:white; padding:4px 12px; '
        f'border-radius:6px; font-size:14px; font-weight:700;">'
        f'{selected["state"]}</span>',
        unsafe_allow_html=True,
    )

with col3:
    st.markdown("**Source**")
    st.markdown(f"{selected['source_label']}")

with col4:
    st.markdown("**Date**")
    date_str = selected["published_date"].strftime("%Y-%m-%d") if selected["published_date"] else "unknown"
    st.markdown(f"{date_str}")

st.markdown("")

# ── Main layout: Memo + Affected policies ────────────────
col_memo, col_policies = st.columns([3, 1])

def format_memo_as_markdown(text):
    """Convert numbered section memo text into clean markdown."""
    # Convert numbered section headers (e.g. "1. REGULATION SUMMARY") to ### headers
    text = re.sub(r'^(\d+)\.\s+([A-Z][A-Z &/\-]+)$', r'### \2', text, flags=re.MULTILINE)
    # Convert ALL-CAPS standalone lines (e.g. "DEADLINE", "RECOMMENDED NEXT STEPS") to ### headers
    text = re.sub(r'^([A-Z][A-Z &/\-]{3,})$', r'### \1', text, flags=re.MULTILINE)
    return text

with col_memo:
    st.markdown("#### Compliance memo")
    memo_md = format_memo_as_markdown(selected["memo_text"])
    st.markdown(memo_md)

with col_policies:
    st.markdown("#### Affected policies")
    impacts = get_impacts_for_regulation(selected["id"])
    if not impacts.empty:
        for _, imp in impacts.iterrows():
            st_color = STATE_COLORS.get(imp["affected_state"], "#6B7280")
            st.markdown(
                f'<div style="background:#F8F9FA; border:1px solid #D1D5DB; border-radius:8px; '
                f'padding:12px; margin-bottom:8px;">'
                f'<div style="font-weight:700; font-size:14px; color:#1F2937;">{imp["policy_id"]}</div>'
                f'<div style="font-size:12px; color:#6B7280;">{imp["policy_name"]}</div>'
                f'<div style="font-size:11px; color:#9CA3AF; margin-top:4px;">Form: {imp["form_number"]}</div>'
                f'<div style="margin-top:6px;">'
                f'<span style="background:{st_color}; color:white; padding:1px 6px; '
                f'border-radius:4px; font-size:10px;">{imp["affected_state"]}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No specific policy impacts recorded.")

# ── Download memo ────────────────────────────────────────
st.markdown("")
st.download_button(
    "📥 Download memo as text",
    data=f"REGULATION: {selected['title']}\nDATE: {date_str}\nSTATE: {selected['state']}\nSEVERITY: {selected['severity']}\n\n{selected['memo_text']}",
    file_name=f"memo_{selected['id']}_{selected['state']}.txt",
    mime="text/plain",
)
