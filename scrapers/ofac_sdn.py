"""
scrapers/ofac_sdn.py
Download and parse the OFAC SDN (Specially Designated Nationals) list.

Every Securian Life policy references OFAC compliance.
We track the SDN list for additions/changes relevant to insurance.

Source: https://www.treasury.gov/ofac/downloads/sdn.csv
XML:    https://www.treasury.gov/ofac/downloads/sdn.xml
"""

import csv
import io
import requests
from datetime import datetime

from config.config import OFAC_SDN_CSV_URL
from config.constants import Source


def scrape_ofac_sdn() -> list[dict]:
    """Download OFAC SDN CSV and create a summary entry for the current list."""

    print(f"  [OFAC] Fetching SDN list from {OFAC_SDN_CSV_URL}...")

    response = requests.get(OFAC_SDN_CSV_URL, timeout=60)
    response.raise_for_status()

    # Parse CSV
    content = response.text
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    total_entries = len(rows)
    print(f"  [OFAC] SDN list contains {total_entries} entries")

    # Count entries by type
    type_counts = {}
    for row in rows:
        if len(row) >= 3:
            sdn_type = row[2].strip() if row[2] else "Unknown"
            type_counts[sdn_type] = type_counts.get(sdn_type, 0) + 1

    type_summary = ", ".join(f"{k}: {v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1])[:5])

    # Create a single summary regulation entry
    today = datetime.utcnow()

    result = {
        "source": Source.OFAC.value,
        "source_id": f"OFAC-SDN-{today.strftime('%Y%m%d')}",
        "source_url": OFAC_SDN_CSV_URL,
        "title": f"OFAC SDN List Snapshot — {total_entries} entries as of {today.strftime('%Y-%m-%d')}",
        "text": (
            f"OFAC Specially Designated Nationals list snapshot. "
            f"Total entries: {total_entries}. "
            f"Breakdown by type: {type_summary}. "
            f"All Securian Life Insurance Company policies (NAIC 93742) include OFAC compliance provisions. "
            f"Any additions or changes to the SDN list require Securian to screen policyholders and beneficiaries "
            f"against the updated list to ensure no coverage is provided to sanctioned entities or individuals."
        ),
        "regulation_type": "Sanctions",
        "agency": "U.S. Department of the Treasury — Office of Foreign Assets Control",
        "published_date": today,
    }

    print(f"  [OFAC] Snapshot created: {total_entries} entries, {len(type_counts)} types")
    return [result]


if __name__ == "__main__":
    print("[INFO] Testing OFAC scraper...")
    results = scrape_ofac_sdn()
    print(f"\n[OK] Fetched {len(results)} OFAC entries")
    for r in results:
        print(f"  {r['source_id']}")
        print(f"  {r['title']}")
        print(f"  {r['text'][:200]}...")
