"""
scrapers/cdi_bulletins.py
Scrape bulletins from California Department of Insurance (CDI).

Scrapes ALL bulletins from 2021-2026.
The filter_agent will later determine which are relevant to life insurance.

Source: https://www.insurance.ca.gov/0250-insurers/0300-insurers/0200-bulletins/bulletin-notices-commiss-opinion/bulletins.cfm
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config.constants import CDI_BULLETIN_YEARS, Source


CDI_BASE = "https://www.insurance.ca.gov"
CDI_BULLETINS_URL = f"{CDI_BASE}/0250-insurers/0300-insurers/0200-bulletins/bulletin-notices-commiss-opinion/bulletins.cfm"


def scrape_cdi_bulletins_page() -> list[dict]:
    """Scrape the main CDI bulletins page which lists all bulletins by year."""

    print(f"  [CDI] Fetching {CDI_BULLETINS_URL}...")
    response = requests.get(CDI_BULLETINS_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    results = []

    # CDI bulletins are listed as links with format "Bulletin YYYY-NN: Subject"
    # They appear in <li> or <p> tags within the main content area
    content = soup.find("div", {"id": "mainContent"}) or soup.find("div", class_="content") or soup

    all_links = content.find_all("a")

    for link in all_links:
        text = link.get_text(strip=True)
        href = link.get("href", "")

        # Match pattern: "Bulletin YYYY-NN" or "Bulletin YYYY-NN (Amended)"
        match = re.match(r"Bulletin\s+(\d{4})-(\d+)(?:\s*\(.*?\))?\s*[:\-]?\s*(.*)", text, re.IGNORECASE)
        if not match:
            continue

        year = int(match.group(1))
        number = match.group(2)
        subject = match.group(3).strip()

        # Only include years in our range
        if year < min(CDI_BULLETIN_YEARS) or year > max(CDI_BULLETIN_YEARS):
            continue

        bulletin_id = f"Bulletin {year}-{number}"

        # Build full URL
        if href and not href.startswith("http"):
            href = f"{CDI_BASE}{href}" if href.startswith("/") else f"{CDI_BASE}/{href}"

        results.append({
            "source": Source.CDI.value,
            "source_id": bulletin_id,
            "source_url": href,
            "title": f"CDI {bulletin_id}: {subject}",
            "text": subject,
            "regulation_type": "Bulletin",
            "agency": "California Department of Insurance",
            "published_date": datetime(year, 1, 1),  # exact date parsed below if available
        })

    return results


def scrape_cdi_notices() -> list[dict]:
    """Scrape CDI licensing/industry notices that affect life insurance."""

    notices_url = f"{CDI_BASE}/0200-industry/0120-notices/"
    print(f"  [CDI] Fetching notices from {notices_url}...")

    response = requests.get(notices_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    results = []

    content = soup.find("div", {"id": "mainContent"}) or soup.find("div", class_="content") or soup
    all_links = content.find_all("a")

    for link in all_links:
        text = link.get_text(strip=True)
        href = link.get("href", "")

        # Look for notices mentioning life insurance, annuity, or related terms
        lower_text = text.lower()
        life_keywords = ["life insurance", "annuity", "life agent", "variable life", "suitability", "sb 263"]
        if not any(kw in lower_text for kw in life_keywords):
            continue

        if href and not href.startswith("http"):
            href = f"{CDI_BASE}{href}" if href.startswith("/") else f"{CDI_BASE}/{href}"

        # Try to extract year from text or URL
        year_match = re.search(r"20(2[1-6])", text + href)
        pub_year = int(f"20{year_match.group(1)}") if year_match else 2025

        if pub_year < min(CDI_BULLETIN_YEARS):
            continue

        notice_id = f"CDI-Notice-{pub_year}-{len(results)+1}"

        results.append({
            "source": Source.CDI.value,
            "source_id": notice_id,
            "source_url": href,
            "title": f"CDI Notice: {text[:150]}",
            "text": text,
            "regulation_type": "Notice",
            "agency": "California Department of Insurance",
            "published_date": datetime(pub_year, 1, 1),
        })

    return results


def scrape_cdi_all() -> list[dict]:
    """Scrape all CDI bulletins and relevant notices."""

    bulletins = scrape_cdi_bulletins_page()
    print(f"  [CDI] Bulletins: {len(bulletins)}")

    notices = scrape_cdi_notices()
    print(f"  [CDI] Life-related notices: {len(notices)}")

    all_results = bulletins + notices

    # Deduplicate by source_id
    seen = set()
    deduped = []
    for r in all_results:
        if r["source_id"] not in seen:
            seen.add(r["source_id"])
            deduped.append(r)

    print(f"  [CDI] Total unique items: {len(deduped)}")
    return deduped


if __name__ == "__main__":
    print("[INFO] Testing CDI scraper...")
    results = scrape_cdi_all()
    print(f"\n[OK] Fetched {len(results)} items")
    for r in results[:5]:
        print(f"  {r['source_id']} | {r['title'][:70]}...")
