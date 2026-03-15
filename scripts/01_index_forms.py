"""
scripts/01_index_forms.py
One-time script: Read 18 Securian Life policy .txt files and index them into ChromaDB.

Each file is split into 3 chunks:
  - GENERAL: everything before the TX/CA compliance sections
  - TX: the TEXAS (TX) COMPLIANCE section only
  - CA: the CALIFORNIA (CA) COMPLIANCE section only

This separation ensures impact_agent can search TX-only or CA-only sections.

Usage:
    python -m scripts.01_index_forms
"""

import chromadb
from pathlib import Path

from config.config import POLICY_FORMS_DIR, CHROMA_PERSIST_DIR
from config.constants import POLICY_FILES, CHROMA_COLLECTION


TX_MARKER = "TEXAS (TX) COMPLIANCE"
CA_MARKER = "CALIFORNIA (CA) COMPLIANCE"
SEPARATOR = "========================================"


def split_policy_file(text: str) -> dict:
    """Split a policy file into general, TX, and CA sections."""

    tx_start = text.find(TX_MARKER)
    ca_start = text.find(CA_MARKER)

    if tx_start == -1 or ca_start == -1:
        raise ValueError(f"Policy file missing TX or CA compliance section markers.")

    # Find the separator line before TX section
    tx_sep_start = text.rfind(SEPARATOR, 0, tx_start)
    if tx_sep_start == -1:
        tx_sep_start = tx_start

    # Find the separator line before CA section
    ca_sep_start = text.rfind(SEPARATOR, tx_start + len(TX_MARKER), ca_start)
    if ca_sep_start == -1:
        ca_sep_start = ca_start

    general = text[:tx_sep_start].strip()
    tx_section = text[tx_sep_start:ca_sep_start].strip()
    ca_section = text[ca_sep_start:].strip()

    return {
        "general": general,
        "tx": tx_section,
        "ca": ca_section,
    }


def extract_policy_id(filename: str) -> str:
    """Extract P01, P02, R01, etc. from filename."""
    return filename.split("_")[0]


def extract_metadata(text: str, filename: str) -> dict:
    """Extract key metadata from the general section."""
    meta = {
        "filename": filename,
        "policy_id": extract_policy_id(filename),
    }

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("POLICY:") or line.startswith("RIDER:"):
            meta["policy_name"] = line.split(":", 1)[1].strip()
        elif line.startswith("FORM NUMBER:"):
            meta["form_number"] = line.split(":", 1)[1].strip()
        elif line.startswith("PRODUCT TYPE:"):
            meta["product_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("FILED YEAR:"):
            meta["filed_year"] = line.split(":", 1)[1].strip()
        elif line.startswith("STATUS:"):
            meta["status"] = line.split(":", 1)[1].strip()

    return meta


def index_policies():
    """Read all 18 policy files and index into ChromaDB."""

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Delete collection if it exists (clean rebuild)
    existing = [c.name for c in client.list_collections()]
    if CHROMA_COLLECTION in existing:
        client.delete_collection(CHROMA_COLLECTION)
        print(f"[INFO] Deleted existing collection '{CHROMA_COLLECTION}'")

    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"description": "Securian Life Insurance Company (93742) — TX + CA policy documents"},
    )

    total_chunks = 0

    for filename in POLICY_FILES:
        filepath = POLICY_FORMS_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Policy file not found: {filepath}")

        text = filepath.read_text(encoding="utf-8")
        sections = split_policy_file(text)
        meta = extract_metadata(sections["general"], filename)
        policy_id = meta["policy_id"]

        # Index 3 chunks per policy: general, TX, CA
        chunk_ids = []
        chunk_texts = []
        chunk_metas = []

        # Chunk 1: General (product info, features, charges)
        chunk_ids.append(f"{policy_id}_GENERAL")
        chunk_texts.append(sections["general"])
        chunk_metas.append({
            "policy_id": policy_id,
            "policy_name": meta.get("policy_name", ""),
            "form_number": meta.get("form_number", ""),
            "section": "GENERAL",
            "state": "BOTH",
            "filename": filename,
        })

        # Chunk 2: Texas compliance section
        chunk_ids.append(f"{policy_id}_TX")
        chunk_texts.append(sections["tx"])
        chunk_metas.append({
            "policy_id": policy_id,
            "policy_name": meta.get("policy_name", ""),
            "form_number": meta.get("form_number", ""),
            "section": "TX_COMPLIANCE",
            "state": "TX",
            "filename": filename,
        })

        # Chunk 3: California compliance section
        chunk_ids.append(f"{policy_id}_CA")
        chunk_texts.append(sections["ca"])
        chunk_metas.append({
            "policy_id": policy_id,
            "policy_name": meta.get("policy_name", ""),
            "form_number": meta.get("form_number", ""),
            "section": "CA_COMPLIANCE",
            "state": "CA",
            "filename": filename,
        })

        collection.add(
            ids=chunk_ids,
            documents=chunk_texts,
            metadatas=chunk_metas,
        )

        total_chunks += 3
        print(f"  [OK] {policy_id} — {meta.get('policy_name', filename)} — 3 chunks (GENERAL + TX + CA)")

    # Verify
    count = collection.count()
    print()
    print(f"[OK] ChromaDB indexed: {count} chunks from {len(POLICY_FILES)} policy files")
    print(f"     Collection: {CHROMA_COLLECTION}")
    print(f"     Storage: {CHROMA_PERSIST_DIR}")

    # Quick search test
    print()
    print("[TEST] Searching 'nonforfeiture' with state=TX filter...")
    results = collection.query(
        query_texts=["nonforfeiture requirements"],
        n_results=3,
        where={"state": "TX"},
    )
    for i, doc_id in enumerate(results["ids"][0]):
        print(f"  Match {i+1}: {doc_id} — {results['metadatas'][0][i]['policy_name']}")

    print()
    print("[TEST] Searching 'domestic partner coverage' with state=CA filter...")
    results = collection.query(
        query_texts=["domestic partner coverage required"],
        n_results=3,
        where={"state": "CA"},
    )
    for i, doc_id in enumerate(results["ids"][0]):
        print(f"  Match {i+1}: {doc_id} — {results['metadatas'][0][i]['policy_name']}")


if __name__ == "__main__":
    index_policies()