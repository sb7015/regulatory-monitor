"""
agents/draft_agent.py
For each impact-mapped regulation, Claude writes a structured compliance memo.
Tracks: input tokens, output tokens, cost, time.
"""

import time
import anthropic

from config.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from config.prompts import DRAFT_AGENT_PROMPT
from config.constants import ProcessingStatus
from models.database import Memo

INPUT_COST_PER_TOKEN = 3.0 / 1_000_000
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_memo(reg, impacts: list) -> tuple[str, dict]:
    """Generate a compliance memo. Returns (memo_text, usage)."""

    policies_text = ""
    for imp in impacts:
        policies_text += f"- {imp.policy_id}: {imp.policy_name} (Form: {imp.form_number})\n"
        policies_text += f"  State: {imp.affected_state} | Clause: {imp.affected_clause}\n"
        policies_text += f"  Impact: {imp.impact_description}\n\n"

    date_str = reg.published_date.strftime("%Y-%m-%d") if reg.published_date else "unknown"

    prompt = DRAFT_AGENT_PROMPT.format(
        title=reg.title,
        date=date_str,
        source=reg.source,
        state=reg.state,
        severity=reg.severity,
        text=reg.text or "(no text available)",
        affected_policies=policies_text,
    )

    start = time.time()

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    elapsed = time.time() - start

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "time_seconds": round(elapsed, 2),
    }

    return response.content[0].text.strip(), usage


def run_draft_agent(session, regulations: list) -> dict:
    """Generate compliance memos for all impact-mapped regulations."""

    print(f"[DRAFT AGENT] Generating memos for {len(regulations)} regulations with {CLAUDE_MODEL}")

    memos_created = 0
    skipped_no_impacts = 0
    error_count = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_time = 0.0
    total_calls = 0

    for i, reg in enumerate(regulations):
        try:
            impacts = reg.impacts

            if not impacts:
                skipped_no_impacts += 1
                reg.status = ProcessingStatus.MEMO_GENERATED.value
                continue

            memo_text, usage = generate_memo(reg, impacts)

            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]
            total_time += usage["time_seconds"]
            total_calls += 1

            memo = Memo(
                regulation_id=reg.id,
                memo_text=memo_text,
            )
            session.add(memo)
            reg.status = ProcessingStatus.MEMO_GENERATED.value
            memos_created += 1

            if (i + 1) % 10 == 0:
                session.commit()
                cost_so_far = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)
                print(
                    f"  [DRAFT] {i + 1}/{len(regulations)} | "
                    f"Memos: {memos_created} | "
                    f"Tokens: {total_input_tokens + total_output_tokens:,} | "
                    f"Cost: ${cost_so_far:.3f} | "
                    f"Time: {total_time:.0f}s"
                )

            time.sleep(0.5)

        except anthropic.RateLimitError:
            print(f"  [DRAFT] Rate limited. Waiting 30 seconds...")
            time.sleep(30)

        except Exception as e:
            print(f"  [DRAFT] Error on '{reg.title[:50]}...': {e}")
            reg.status = ProcessingStatus.MEMO_GENERATED.value
            error_count += 1

    session.commit()

    total_cost = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)

    stats = {
        "memos_created": memos_created,
        "skipped": skipped_no_impacts,
        "errors": error_count,
        "total_calls": total_calls,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "cost_usd": round(total_cost, 4),
        "time_seconds": round(total_time, 1),
        "model": CLAUDE_MODEL,
    }

    print(f"[DRAFT AGENT] Done")
    print(f"  Memos: {memos_created} | Skipped: {skipped_no_impacts} | Errors: {error_count}")
    print(f"  Model: {CLAUDE_MODEL}")
    print(f"  API calls: {total_calls}")
    print(f"  Input tokens: {total_input_tokens:,}")
    print(f"  Output tokens: {total_output_tokens:,}")
    print(f"  Cost: ${total_cost:.4f}")
    print(f"  Time: {total_time:.0f}s ({total_time/60:.1f} min)")

    return stats
