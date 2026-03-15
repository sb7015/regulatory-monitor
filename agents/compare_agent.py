"""
agents/compare_agent.py
Checks SQLite for duplicates. Returns only new items.
No Claude — pure SQL query.
"""

from datetime import datetime, timezone
from sqlalchemy import select

from models.database import get_session, Regulation
from config.constants import SOURCE_STATE_MAP, Source


def run_compare_agent(items: list[dict]) -> list[dict]:
    """Filter out items that already exist in the database. Return only new ones."""

    print(f"[COMPARE AGENT] Checking {len(items)} items against database...")

    session = get_session()
    new_items = []

    for item in items:
        existing = session.execute(
            select(Regulation).where(
                Regulation.source == item["source"],
                Regulation.source_id == item["source_id"],
            )
        ).scalar_one_or_none()

        if existing:
            continue

        # Pre-assign state for sources with known state mapping
        source_enum = Source(item["source"])
        pre_assigned_state = SOURCE_STATE_MAP.get(source_enum)
        state_value = pre_assigned_state.value if pre_assigned_state else None

        # Insert as pending
        reg = Regulation(
            source=item["source"],
            source_id=item["source_id"],
            source_url=item.get("source_url"),
            title=item["title"],
            text=item.get("text"),
            regulation_type=item.get("regulation_type"),
            agency=item.get("agency"),
            published_date=item.get("published_date"),
            state=state_value,
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(reg)
        new_items.append(reg)

    session.commit()

    print(f"[COMPARE AGENT] New items: {len(new_items)} | Skipped (duplicates): {len(items) - len(new_items)}")

    session.close()
    return new_items
