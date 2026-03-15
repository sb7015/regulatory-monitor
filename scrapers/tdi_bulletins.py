"""
scrapers/tdi_bulletins.py
Scrape commissioner bulletins from Texas Department of Insurance (TDI).

Scrapes ALL bulletins (not just Life-tagged) from 2021-2026.
The filter_agent will later determine which are relevant to life insurance.

Source: https://www.tdi.texas.gov/bulletins/{year}/index.html
Also:   https://www.tdi.texas.gov/bulletins/Life.html (Life-tagged only)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config.constants import TDI_BULLETIN_YEARS, Source


TDI_BASE = "https://www.tdi.texas.gov"


def scrape_tdi_year(year: int) -> list[dict]:
    """Scrape all bulletins for a single year from TDI."""

    url = f"{TDI_BASE}/bulletins/{year}/index.html"
    print(f"  [TDI] Fetching {url}...")

    response = requests.get(url, timeout=30)
    if response.status_code == 404:
        print(f"  [TDI] {year} — page not found, skipping")
        return []
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    results = []

    # TDI bulletin pages use <table> with rows containing bulletin info
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Extract bulletin number and link
            link_tag = cells[0].find("a")
            if not link_tag:
                continue

            bulletin_number = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            if href and not href.startswith("http"):
                href = f"{TDI_BASE}{href}" if href.startswith("/") else f"{TDI_BASE}/bulletins/{year}/{href}"

            # Extract date
            date_text = cells[1].get_text(strip=True)
            parsed_date = None
            for fmt in ["%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"]:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    break
                except ValueError:
                    continue

            # Extract subject (remaining cells joined)
            subject_parts = [c.get_text(strip=True) for c in cells[2:]]
            subject = " — ".join(subject_parts)

            # Build title
            title = f"TDI {bulletin_number}: {subject}"

            results.append({
                "source": Source.TDI.value,
                "source_id": bulletin_number,
                "source_url": href,
                "title": title,
                "text": subject,
                "regulation_type": "Bulletin",
                "agency": "Texas Department of Insurance",
                "published_date": parsed_date,
            })

    return results


def fetch_bulletin_text(url: str) -> str:
    """Fetch the full text of a single TDI bulletin page."""

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    # TDI bulletin content is in the main content area
    content_div = soup.find("div", {"id": "content"}) or soup.find("div", class_="content")
    if content_div:
        return content_div.get_text(separator="\n", strip=True)

    # Fallback to body text
    return soup.get_text(separator="\n", strip=True)[:3000]


def scrape_tdi_bulletins() -> list[dict]:
    """Scrape all TDI bulletins for the configured year range."""

    all_results = []

    for year in TDI_BULLETIN_YEARS:
        year_results = scrape_tdi_year(year)
        all_results.extend(year_results)
        print(f"  [TDI] {year} — {len(year_results)} bulletins")

    # Also scrape the Life-specific page for any we might have missed
    print(f"  [TDI] Fetching Life-tagged bulletins...")
    life_url = f"{TDI_BASE}/bulletins/Life.html"
    response = requests.get(life_url, timeout=30)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        tables = soup.find_all("table")
        seen_ids = {r["source_id"] for r in all_results}
        life_added = 0

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                link_tag = cells[0].find("a")
                if not link_tag:
                    continue

                bulletin_number = link_tag.get_text(strip=True)
                if bulletin_number in seen_ids:
                    continue

                href = link_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = f"{TDI_BASE}{href}" if href.startswith("/") else f"{TDI_BASE}/bulletins/{href}"

                date_text = cells[1].get_text(strip=True)
                parsed_date = None
                for fmt in ["%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"]:
                    try:
                        parsed_date = datetime.strptime(date_text, fmt)
                        break
                    except ValueError:
                        continue

                subject_parts = [c.get_text(strip=True) for c in cells[2:]]
                subject = " — ".join(subject_parts)

                # Only include if within our date range (2021+)
                if parsed_date and parsed_date.year >= 2021:
                    all_results.append({
                        "source": Source.TDI.value,
                        "source_id": bulletin_number,
                        "source_url": href,
                        "title": f"TDI {bulletin_number}: {subject}",
                        "text": subject,
                        "regulation_type": "Bulletin",
                        "agency": "Texas Department of Insurance",
                        "published_date": parsed_date,
                    })
                    life_added += 1

        print(f"  [TDI] Life page — {life_added} additional bulletins")

    print(f"  [TDI] Total bulletins: {len(all_results)}")
    return all_results


if __name__ == "__main__":
    print("[INFO] Testing TDI scraper...")
    results = scrape_tdi_bulletins()
    print(f"\n[OK] Fetched {len(results)} bulletins")
    for r in results[:5]:
        print(f"  {r['source_id']} | {r['published_date']} | {r['title'][:70]}...")
