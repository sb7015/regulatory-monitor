"""
scripts/03_classify_history.py
One-time script: Run filter_agent + impact_agent + draft_agent on all pending regulations.

Tracks total tokens, cost, and time across all 3 agents.
Resumable — if it crashes, run again and it picks up where it left off.

Model: claude-sonnet-4-20250514 (configured in config/config.py)
Pricing: $3/1M input tokens, $15/1M output tokens

Usage:
    python -m scripts.03_classify_history
"""

from sqlalchemy import select

from models.database import init_db, get_session, Regulation
from config.config import CLAUDE_MODEL
from config.constants import ProcessingStatus
from agents.filter_agent import run_filter_agent
from agents.impact_agent import run_impact_agent
from agents.draft_agent import run_draft_agent


def run_classification():
    """Run all 3 classification agents on historical data."""

    print("=" * 70)
    print(" CLASSIFY HISTORICAL DATA")
    print(f" Model: {CLAUDE_MODEL}")
    print(f" Pricing: $3.00 / 1M input tokens | $15.00 / 1M output tokens")
    print(" Securian Life (93742) | TX + CA")
    print("=" * 70)
    print()

    init_db()
    session = get_session()

    grand_input_tokens = 0
    grand_output_tokens = 0
    grand_cost = 0.0
    grand_time = 0.0
    grand_calls = 0

    # ── Stage 1: Filter Agent ─────────────────────────────
    pending = session.execute(
        select(Regulation).where(Regulation.status == ProcessingStatus.PENDING.value)
    ).scalars().all()

    print(f"[STAGE 1/3] FILTER AGENT — {len(pending)} pending items")
    print("-" * 50)

    if pending:
        filter_result = run_filter_agent(session, pending)
        grand_input_tokens += filter_result.get("input_tokens", 0)
        grand_output_tokens += filter_result.get("output_tokens", 0)
        grand_cost += filter_result.get("cost_usd", 0)
        grand_time += filter_result.get("time_seconds", 0)
        grand_calls += filter_result.get("total_calls", 0)
    else:
        print("  No pending items. Skipping.")
        filter_result = {"relevant": 0, "rejected": 0, "errors": 0}

    print()

    # ── Stage 2: Impact Agent ─────────────────────────────
    classified = session.execute(
        select(Regulation).where(Regulation.status == ProcessingStatus.CLASSIFIED.value)
    ).scalars().all()

    print(f"[STAGE 2/3] IMPACT AGENT — {len(classified)} relevant items")
    print("-" * 50)

    if classified:
        impact_result = run_impact_agent(session, classified)
        grand_input_tokens += impact_result.get("input_tokens", 0)
        grand_output_tokens += impact_result.get("output_tokens", 0)
        grand_cost += impact_result.get("cost_usd", 0)
        grand_time += impact_result.get("time_seconds", 0)
        grand_calls += impact_result.get("total_calls", 0)
    else:
        print("  No classified items. Skipping.")
        impact_result = {"total_impacts": 0, "errors": 0}

    print()

    # ── Stage 3: Draft Agent ──────────────────────────────
    impact_mapped = session.execute(
        select(Regulation).where(Regulation.status == ProcessingStatus.IMPACT_MAPPED.value)
    ).scalars().all()

    print(f"[STAGE 3/3] DRAFT AGENT — {len(impact_mapped)} impact-mapped items")
    print("-" * 50)

    if impact_mapped:
        draft_result = run_draft_agent(session, impact_mapped)
        grand_input_tokens += draft_result.get("input_tokens", 0)
        grand_output_tokens += draft_result.get("output_tokens", 0)
        grand_cost += draft_result.get("cost_usd", 0)
        grand_time += draft_result.get("time_seconds", 0)
        grand_calls += draft_result.get("total_calls", 0)
    else:
        print("  No impact-mapped items. Skipping.")
        draft_result = {"memos_created": 0, "skipped": 0, "errors": 0}

    print()

    # ── Database Summary ──────────────────────────────────
    total = session.execute(select(Regulation)).scalars().all()
    status_counts = {}
    for reg in total:
        status_counts[reg.status] = status_counts.get(reg.status, 0) + 1

    # ── Grand Summary ─────────────────────────────────────
    print("=" * 70)
    print(" CLASSIFICATION COMPLETE")
    print("=" * 70)
    print()
    print(" AGENT RESULTS:")
    print(f"   Filter:  {filter_result.get('relevant', 0)} relevant | {filter_result.get('rejected', 0)} rejected | {filter_result.get('errors', 0)} errors")
    print(f"   Impact:  {impact_result.get('total_impacts', 0)} policy impacts | {impact_result.get('errors', 0)} errors")
    print(f"   Draft:   {draft_result.get('memos_created', 0)} memos | {draft_result.get('skipped', 0)} skipped | {draft_result.get('errors', 0)} errors")
    print()
    print(" DATABASE STATUS:")
    for status, count in sorted(status_counts.items()):
        print(f"   {status:25s} {count:>6}")
    print(f"   {'TOTAL':25s} {sum(status_counts.values()):>6}")
    print()
    print(" TOKEN USAGE & COST:")
    print(f"   Model:          {CLAUDE_MODEL}")
    print(f"   Total API calls: {grand_calls:,}")
    print(f"   Input tokens:    {grand_input_tokens:,}")
    print(f"   Output tokens:   {grand_output_tokens:,}")
    print(f"   Total tokens:    {grand_input_tokens + grand_output_tokens:,}")
    print(f"   Total cost:      ${grand_cost:.4f}")
    print(f"   Total time:      {grand_time:.0f}s ({grand_time/60:.1f} min)")
    print()
    print(" Ready for Step 8 — Streamlit dashboard")
    print()

    session.close()


if __name__ == "__main__":
    run_classification()
