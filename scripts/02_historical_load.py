"""
scripts/02_historical_load.py
One-time script: Run all 4 scrapers and load results into SQLite regulations table.

This is the 5-year historical data seed. Compare_agent logic built in —
if a record with the same source + source_id already exists, it is skipped.

Usage:
    python -m scripts.02_historical_load
"""

from datetime import datetime
from sqlalchemy import select

from models.database import init_db, get_session, Regulation
from scrapers.federal_register import scrape_federal_register
from scrapers.tdi_bulletins import scrape_tdi_bulletins
from scrapers.cdi_bulletins import scrape_cdi_all
from scrapers.ofac_sdn import scrape_ofac_sdn
from config.constants import SOURCE_STATE_MAP, Source, State


def load_items(session, items: list[dict], source_name: str) -> dict:
    """Load a list of scraped items into the regulations table. Skip duplicates."""

    inserted = 0
    skipped = 0

    for item in items:
        # Check if already exists
        existing = session.execute(
            select(Regulation).where(
                Regulation.source == item["source"],
                Regulation.source_id == item["source_id"],
            )
        ).scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        # Pre-assign state for TDI/CDI/OFAC (known from source)
        source_enum = Source(item["source"])
        pre_assigned_state = SOURCE_STATE_MAP.get(source_enum)
        state_value = pre_assigned_state.value if pre_assigned_state else None

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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(reg)
        inserted += 1

    session.commit()
    return {"inserted": inserted, "skipped": skipped}


def run_historical_load():
    """Run all 4 scrapers and load into database."""

    print("=" * 60)
    print(" HISTORICAL DATA LOAD — 5 Year Seed")
    print(" Securian Life (93742) | TX + CA | Mar 2021 – Mar 2026")
    print("=" * 60)
    print()

    # Initialize database
    init_db()
    session = get_session()

    total_inserted = 0
    total_skipped = 0

    # ── Source 1: Federal Register ─────────────────────────
    print("[1/4] FEDERAL REGISTER")
    print("-" * 40)
    fr_items = scrape_federal_register()
    fr_result = load_items(session, fr_items, "Federal Register")
    total_inserted += fr_result["inserted"]
    total_skipped += fr_result["skipped"]
    print(f"  → Inserted: {fr_result['inserted']} | Skipped: {fr_result['skipped']}")
    print()

    # ── Source 2: TDI (Texas) ──────────────────────────────
    print("[2/4] TDI BULLETINS (Texas)")
    print("-" * 40)
    tdi_items = scrape_tdi_bulletins()
    tdi_result = load_items(session, tdi_items, "TDI")
    total_inserted += tdi_result["inserted"]
    total_skipped += tdi_result["skipped"]
    print(f"  → Inserted: {tdi_result['inserted']} | Skipped: {tdi_result['skipped']}")
    print()

    # ── Source 3: CDI (California) ─────────────────────────
    print("[3/4] CDI BULLETINS (California)")
    print("-" * 40)
    cdi_items = scrape_cdi_all()
    cdi_result = load_items(session, cdi_items, "CDI")
    total_inserted += cdi_result["inserted"]
    total_skipped += cdi_result["skipped"]
    print(f"  → Inserted: {cdi_result['inserted']} | Skipped: {cdi_result['skipped']}")
    print()

    # ── Source 4: OFAC SDN ─────────────────────────────────
    print("[4/4] OFAC SDN LIST")
    print("-" * 40)
    ofac_items = scrape_ofac_sdn()
    ofac_result = load_items(session, ofac_items, "OFAC")
    total_inserted += ofac_result["inserted"]
    total_skipped += ofac_result["skipped"]
    print(f"  → Inserted: {ofac_result['inserted']} | Skipped: {ofac_result['skipped']}")
    print()

    # ── Summary ────────────────────────────────────────────
    # Count by source in DB
    all_regs = session.execute(select(Regulation)).scalars().all()
    source_counts = {}
    for reg in all_regs:
        source_counts[reg.source] = source_counts.get(reg.source, 0) + 1

    print("=" * 60)
    print(" LOAD COMPLETE")
    print("=" * 60)
    print()
    print(f"  Total inserted this run:  {total_inserted}")
    print(f"  Total skipped (dupes):    {total_skipped}")
    print()
    print("  Database contents:")
    for src, count in sorted(source_counts.items()):
        print(f"    {src:25s} {count:>6} records")
    print(f"    {'TOTAL':25s} {sum(source_counts.values()):>6} records")
    print()
    print(f"  All records status: pending (ready for Step 7 — classify)")
    print()

    session.close()


if __name__ == "__main__":
    run_historical_load()