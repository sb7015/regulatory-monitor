"""
agents/crawl_agent.py
Orchestrates all 4 data source scrapers.
No Claude — pure Python.
"""

from scrapers.federal_register import scrape_federal_register
from scrapers.tdi_bulletins import scrape_tdi_bulletins
from scrapers.cdi_bulletins import scrape_cdi_all
from scrapers.ofac_sdn import scrape_ofac_sdn


def run_crawl_agent() -> list[dict]:
    """Fetch from all 4 sources and return combined list."""

    print("[CRAWL AGENT] Starting...")
    all_items = []

    print("[CRAWL AGENT] Source 1/4: Federal Register")
    fr = scrape_federal_register()
    all_items.extend(fr)

    print("[CRAWL AGENT] Source 2/4: TDI Bulletins (Texas)")
    tdi = scrape_tdi_bulletins()
    all_items.extend(tdi)

    print("[CRAWL AGENT] Source 3/4: CDI Bulletins (California)")
    cdi = scrape_cdi_all()
    all_items.extend(cdi)

    print("[CRAWL AGENT] Source 4/4: OFAC SDN")
    ofac = scrape_ofac_sdn()
    all_items.extend(ofac)

    print(f"[CRAWL AGENT] Done — {len(all_items)} total items")
    return all_items
