"""
dashboard/utils.py
Database queries and helper functions used across all dashboard pages.
"""

import pandas as pd
import streamlit as st
from sqlalchemy import select, func, text

from models.database import get_session, Regulation, PolicyImpact, Memo


# ── Severity colors ──────────────────────────────────────
SEVERITY_COLORS = {
    "critical": "#DC2626",
    "high": "#EA580C",
    "medium": "#3B82F6",
    "low": "#6B7280",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low"]

# ── State colors ─────────────────────────────────────────
STATE_COLORS = {
    "TX": "#3B82F6",
    "CA": "#8B5CF6",
    "BOTH": "#10B981",
}

# ── Source colors ────────────────────────────────────────
SOURCE_COLORS = {
    "federal_register": "#3B82F6",
    "tdi": "#10B981",
    "cdi": "#8B5CF6",
    "ofac": "#DC2626",
}

SOURCE_LABELS = {
    "federal_register": "Federal Register",
    "tdi": "TDI (Texas)",
    "cdi": "CDI (California)",
    "ofac": "OFAC",
}


@st.cache_data(ttl=300)
def get_all_regulations(state_filter=None, severity_filter=None, source_filter=None, relevant_only=True):
    """Get regulations as DataFrame with optional filters."""
    session = get_session()

    # Select only needed columns — avoids loading ORM relationships and heavy text column
    query = select(
        Regulation.id,
        Regulation.source,
        Regulation.title,
        Regulation.published_date,
        Regulation.state,
        Regulation.severity,
        Regulation.filter_reason,
        Regulation.status,
        Regulation.source_url,
        Regulation.agency,
        Regulation.regulation_type,
    )

    if relevant_only:
        query = query.where(Regulation.relevant == True)

    if state_filter and state_filter != "All":
        query = query.where(Regulation.state.in_([state_filter, "BOTH"]))

    if severity_filter:
        query = query.where(Regulation.severity.in_(severity_filter))

    if source_filter:
        query = query.where(Regulation.source.in_(source_filter))

    query = query.order_by(Regulation.published_date.desc())
    results = session.execute(query).all()

    data = []
    for r in results:
        data.append({
            "id": r.id,
            "source": r.source,
            "source_label": SOURCE_LABELS.get(r.source, r.source),
            "title": r.title,
            "published_date": r.published_date,
            "state": r.state,
            "severity": r.severity,
            "filter_reason": r.filter_reason,
            "status": r.status,
            "source_url": r.source_url,
            "agency": r.agency,
            "regulation_type": r.regulation_type,
        })

    session.close()
    return pd.DataFrame(data)


def get_impacts_for_regulation(regulation_id):
    """Get all policy impacts for a single regulation."""
    session = get_session()
    impacts = session.execute(
        select(PolicyImpact).where(PolicyImpact.regulation_id == regulation_id)
    ).scalars().all()

    data = []
    for imp in impacts:
        data.append({
            "policy_id": imp.policy_id,
            "policy_name": imp.policy_name,
            "form_number": imp.form_number,
            "affected_state": imp.affected_state,
            "affected_clause": imp.affected_clause,
            "impact_description": imp.impact_description,
        })

    session.close()
    return pd.DataFrame(data)


def get_memo_for_regulation(regulation_id):
    """Get the compliance memo for a single regulation."""
    session = get_session()
    memo = session.execute(
        select(Memo).where(Memo.regulation_id == regulation_id)
    ).scalar_one_or_none()
    session.close()

    if memo:
        return memo.memo_text
    return None


@st.cache_data(ttl=300)
def get_all_impacts():
    """Get all policy impacts as DataFrame."""
    session = get_session()
    impacts = session.execute(select(PolicyImpact)).scalars().all()

    data = []
    for imp in impacts:
        data.append({
            "regulation_id": imp.regulation_id,
            "policy_id": imp.policy_id,
            "policy_name": imp.policy_name,
            "form_number": imp.form_number,
            "affected_state": imp.affected_state,
            "affected_clause": imp.affected_clause,
            "impact_description": imp.impact_description,
        })

    session.close()
    return pd.DataFrame(data)


@st.cache_data(ttl=300)
def get_overview_stats():
    """Get summary statistics for the home page."""
    session = get_session()

    total = session.execute(select(func.count(Regulation.id))).scalar()
    relevant = session.execute(
        select(func.count(Regulation.id)).where(Regulation.relevant == True)
    ).scalar()
    rejected = session.execute(
        select(func.count(Regulation.id)).where(Regulation.status == "rejected")
    ).scalar()
    total_impacts = session.execute(select(func.count(PolicyImpact.id))).scalar()
    total_memos = session.execute(select(func.count(Memo.id))).scalar()

    # Unique policies affected
    policies_affected = session.execute(
        select(func.count(func.distinct(PolicyImpact.policy_id)))
    ).scalar()

    # By severity
    severity_counts = {}
    for sev in SEVERITY_ORDER:
        count = session.execute(
            select(func.count(Regulation.id)).where(
                Regulation.relevant == True,
                Regulation.severity == sev,
            )
        ).scalar()
        severity_counts[sev] = count

    # By state
    state_counts = {}
    for st in ["TX", "CA", "BOTH"]:
        count = session.execute(
            select(func.count(Regulation.id)).where(
                Regulation.relevant == True,
                Regulation.state == st,
            )
        ).scalar()
        state_counts[st] = count

    # By source
    source_counts = {}
    for src in SOURCE_LABELS:
        count = session.execute(
            select(func.count(Regulation.id)).where(
                Regulation.relevant == True,
                Regulation.source == src,
            )
        ).scalar()
        source_counts[src] = count

    session.close()

    return {
        "total": total,
        "relevant": relevant,
        "rejected": rejected,
        "impacts": total_impacts,
        "memos": total_memos,
        "policies_affected": policies_affected,
        "severity": severity_counts,
        "state": state_counts,
        "source": source_counts,
    }


@st.cache_data(ttl=300)
def get_regulations_with_memos():
    """Get regulations that have memos, for the memo viewer."""
    session = get_session()

    results = session.execute(
        select(Regulation).where(Regulation.status == "memo_generated").order_by(Regulation.published_date.desc())
    ).scalars().all()

    data = []
    for r in results:
        # Check if memo exists
        memo = session.execute(
            select(Memo).where(Memo.regulation_id == r.id)
        ).scalar_one_or_none()

        if memo:
            data.append({
                "id": r.id,
                "title": r.title,
                "published_date": r.published_date,
                "state": r.state,
                "severity": r.severity,
                "source": r.source,
                "source_label": SOURCE_LABELS.get(r.source, r.source),
                "memo_text": memo.memo_text,
            })

    session.close()
    return data


def severity_badge(severity):
    """Return colored HTML badge for severity."""
    color = SEVERITY_COLORS.get(severity, "#6B7280")
    return f'<span style="background:{color}; color:white; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600;">{severity.upper()}</span>'


def state_badge(state):
    """Return colored HTML badge for state."""
    color = STATE_COLORS.get(state, "#6B7280")
    return f'<span style="background:{color}; color:white; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600;">{state}</span>'
