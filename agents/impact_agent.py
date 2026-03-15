"""
agents/impact_agent.py
For each relevant regulation:
  1. Search ChromaDB for matching policy documents (filtered by state)
  2. Send matches to Claude to confirm which policies are truly affected
  3. Create PolicyImpact records in SQLite

Tracks: input tokens, output tokens, cost, time.
"""

import json
import time
import chromadb
import anthropic

from config.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CHROMA_PERSIST_DIR
from config.prompts import IMPACT_AGENT_PROMPT
from config.constants import CHROMA_COLLECTION, ProcessingStatus
from models.database import PolicyImpact

INPUT_COST_PER_TOKEN = 3.0 / 1_000_000
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def search_policies(query_text: str, state: str, n_results: int = 10) -> list[dict]:
    """Search ChromaDB for matching policy chunks filtered by state."""

    collection = chroma_client.get_collection(CHROMA_COLLECTION)

    if state == "TX":
        where_filter = {"state": {"$in": ["TX", "BOTH"]}}
    elif state == "CA":
        where_filter = {"state": {"$in": ["CA", "BOTH"]}}
    else:
        where_filter = None

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
    )

    matches = []
    for i in range(len(results["ids"][0])):
        matches.append({
            "chunk_id": results["ids"][0][i],
            "document": results["documents"][0][i][:1500],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })

    return matches


def analyze_impact(reg, matched_docs: list[dict]) -> tuple[dict, dict]:
    """Send regulation + matched docs to Claude. Returns (result, usage)."""

    docs_text = ""
    for i, match in enumerate(matched_docs):
        meta = match["metadata"]
        docs_text += f"\n--- Document {i+1}: {meta.get('policy_id', '')} ({meta.get('section', '')}) ---\n"
        docs_text += f"Policy: {meta.get('policy_name', '')}\n"
        docs_text += f"Form: {meta.get('form_number', '')}\n"
        docs_text += f"State section: {meta.get('state', '')}\n"
        docs_text += f"Content:\n{match['document']}\n"

    date_str = reg.published_date.strftime("%Y-%m-%d") if reg.published_date else "unknown"

    prompt = IMPACT_AGENT_PROMPT.format(
        title=reg.title,
        date=date_str,
        source=reg.source,
        state=reg.state,
        severity=reg.severity,
        text=reg.text or "(no text)",
        matched_documents=docs_text,
    )

    start = time.time()

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    elapsed = time.time() - start

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "time_seconds": round(elapsed, 2),
    }

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw), usage


def run_impact_agent(session, regulations: list) -> dict:
    """For each relevant regulation, find affected policies and create impact records."""

    print(f"[IMPACT AGENT] Analyzing {len(regulations)} relevant regulations with {CLAUDE_MODEL}")

    total_impacts = 0
    error_count = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_time = 0.0
    total_calls = 0

    for i, reg in enumerate(regulations):
        try:
            search_query = f"{reg.title} {reg.text or ''}"[:500]
            matched_docs = search_policies(search_query, reg.state)

            if not matched_docs:
                reg.status = ProcessingStatus.IMPACT_MAPPED.value
                continue

            result, usage = analyze_impact(reg, matched_docs)

            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]
            total_time += usage["time_seconds"]
            total_calls += 1

            affected = result.get("affected_policies", [])

            for policy in affected:
                impact = PolicyImpact(
                    regulation_id=reg.id,
                    policy_id=policy.get("policy_id", ""),
                    policy_name=policy.get("policy_name", ""),
                    form_number=policy.get("form_number", ""),
                    affected_state=policy.get("affected_state", reg.state),
                    affected_clause=policy.get("affected_clause", ""),
                    impact_description=policy.get("impact_description", ""),
                )
                session.add(impact)
                total_impacts += 1

            reg.status = ProcessingStatus.IMPACT_MAPPED.value

            if (i + 1) % 10 == 0:
                session.commit()
                cost_so_far = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)
                print(
                    f"  [IMPACT] {i + 1}/{len(regulations)} | "
                    f"Impacts: {total_impacts} | "
                    f"Tokens: {total_input_tokens + total_output_tokens:,} | "
                    f"Cost: ${cost_so_far:.3f} | "
                    f"Time: {total_time:.0f}s"
                )

            time.sleep(0.5)

        except json.JSONDecodeError as e:
            print(f"  [IMPACT] JSON error on '{reg.title[:50]}...': {e}")
            reg.status = ProcessingStatus.IMPACT_MAPPED.value
            error_count += 1

        except anthropic.RateLimitError:
            print(f"  [IMPACT] Rate limited. Waiting 30 seconds...")
            time.sleep(30)

        except Exception as e:
            print(f"  [IMPACT] Error on '{reg.title[:50]}...': {e}")
            reg.status = ProcessingStatus.IMPACT_MAPPED.value
            error_count += 1

    session.commit()

    total_cost = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)

    stats = {
        "total_impacts": total_impacts,
        "errors": error_count,
        "total_calls": total_calls,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "cost_usd": round(total_cost, 4),
        "time_seconds": round(total_time, 1),
        "model": CLAUDE_MODEL,
    }

    print(f"[IMPACT AGENT] Done")
    print(f"  Impacts created: {total_impacts} | Errors: {error_count}")
    print(f"  Model: {CLAUDE_MODEL}")
    print(f"  API calls: {total_calls}")
    print(f"  Input tokens: {total_input_tokens:,}")
    print(f"  Output tokens: {total_output_tokens:,}")
    print(f"  Cost: ${total_cost:.4f}")
    print(f"  Time: {total_time:.0f}s ({total_time/60:.1f} min)")

    return stats
