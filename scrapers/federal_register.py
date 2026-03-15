"""
scrapers/federal_register.py
Fetch life insurance related documents from Federal Register API.

API docs: https://www.federalregister.gov/developers/documentation/api/v1
No API key needed. Free. Documents since 1994.

Returns list of dicts with: title, text, date, source_id, source_url, regulation_type, agency
"""

import requests
from datetime import datetime

from config.config import FR_ARTICLES_URL, FR_DATE_START, FR_DATE_END, FR_PER_PAGE
from config.constants import FR_SEARCH_TERMS, Source


def fetch_federal_register(search_term: str, page: int = 1) -> dict:
    """Fetch one page of results for a single search term."""

    params = {
        "conditions[term]": search_term,
        "conditions[publication_date][gte]": FR_DATE_START,
        "conditions[publication_date][lte]": FR_DATE_END,
        "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
        "fields[]": [
            "title",
            "abstract",
            "document_number",
            "publication_date",
            "type",
            "agencies",
            "html_url",
            "full_text_xml_url",
        ],
        "per_page": FR_PER_PAGE,
        "page": page,
        "order": "newest",
    }

    response = requests.get(FR_ARTICLES_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_fr_document(doc: dict) -> dict:
    """Parse a single Federal Register API result into our standard format."""

    agencies = doc.get("agencies", [])
    agency_names = [a.get("name", "") for a in agencies if a.get("name")]
    agency_str = "; ".join(agency_names) if agency_names else "Unknown"

    pub_date = doc.get("publication_date")
    parsed_date = None
    if pub_date:
        parsed_date = datetime.strptime(pub_date, "%Y-%m-%d")

    fr_type = doc.get("type", "")
    type_map = {
        "Rule": "Rule",
        "Proposed Rule": "Proposed Rule",
        "Notice": "Notice",
    }
    regulation_type = type_map.get(fr_type, fr_type)

    return {
        "source": Source.FEDERAL_REGISTER.value,
        "source_id": doc.get("document_number", ""),
        "source_url": doc.get("html_url", ""),
        "title": doc.get("title", ""),
        "text": doc.get("abstract", ""),
        "regulation_type": regulation_type,
        "agency": agency_str,
        "published_date": parsed_date,
    }


def scrape_federal_register() -> list[dict]:
    """Fetch all life insurance related documents from Federal Register for the 5-year period."""

    all_results = []
    seen_doc_numbers = set()

    for term in FR_SEARCH_TERMS:
        page = 1
        term_count = 0

        while True:
            print(f"  [FR] Searching '{term}' — page {page}...")
            data = fetch_federal_register(term, page)

            results = data.get("results", [])
            if not results:
                break

            for doc in results:
                doc_number = doc.get("document_number", "")
                if doc_number and doc_number not in seen_doc_numbers:
                    seen_doc_numbers.add(doc_number)
                    parsed = parse_fr_document(doc)
                    all_results.append(parsed)
                    term_count += 1

            total_pages = data.get("total_pages", 1)
            if page >= total_pages or page >= 20:
                break
            page += 1

        print(f"  [FR] '{term}' — {term_count} new documents")

    print(f"  [FR] Total unique documents: {len(all_results)}")
    return all_results


if __name__ == "__main__":
    print("[INFO] Testing Federal Register scraper...")
    results = scrape_federal_register()
    print(f"\n[OK] Fetched {len(results)} documents")
    if results:
        sample = results[0]
        print(f"  Sample: {sample['title'][:80]}...")
        print(f"  Date:   {sample['published_date']}")
        print(f"  Agency: {sample['agency']}")
        print(f"  Type:   {sample['regulation_type']}")
