"""
agents/filter_agent.py
Uses Claude to classify each regulatory item:
  - Is it relevant to life insurance? (true/false)
  - Which state? (TX / CA / BOTH)
  - Severity? (critical / high / medium / low)

Tracks: input tokens, output tokens, cost, time per call.
"""

import json
import time
import anthropic

from config.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from config.prompts import FILTER_AGENT_PROMPT
from config.constants import ProcessingStatus

# Claude Sonnet 4 pricing (per token)
# https://docs.anthropic.com/en/docs/about-claude/models
INPUT_COST_PER_TOKEN = 3.0 / 1_000_000    # $3 per 1M input tokens
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000   # $15 per 1M output tokens

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def classify_regulation(source: str, title: str, date: str, text: str) -> tuple[dict, dict]:
    """Send one regulation to Claude for classification.
    Returns (parsed_result, usage_stats)."""

    prompt = FILTER_AGENT_PROMPT.format(
        source=source,
        title=title,
        date=date,
        text=text or "(no text available)",
    )

    start = time.time()

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    elapsed = time.time() - start

    raw = response.content[0].text.strip()

    # Token usage from response
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "time_seconds": round(elapsed, 2),
    }

    # Parse JSON — strip markdown fences if Claude adds them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw), usage


def run_filter_agent(session, regulations: list) -> dict:
    """Classify a list of Regulation ORM objects. Updates each record in-place."""

    print(f"[FILTER AGENT] Classifying {len(regulations)} items with {CLAUDE_MODEL}")

    relevant_count = 0
    rejected_count = 0
    error_count = 0

    total_input_tokens = 0
    total_output_tokens = 0
    total_time = 0.0
    total_calls = 0

    for i, reg in enumerate(regulations):
        try:
            date_str = reg.published_date.strftime("%Y-%m-%d") if reg.published_date else "unknown"

            result, usage = classify_regulation(
                source=reg.source,
                title=reg.title,
                date=date_str,
                text=reg.text,
            )

            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]
            total_time += usage["time_seconds"]
            total_calls += 1

            reg.relevant = result.get("relevant", False)
            reg.severity = result.get("severity", "low")
            reg.filter_reason = result.get("reason", "")

            if reg.state is None:
                reg.state = result.get("state", "BOTH")

            if reg.relevant:
                reg.status = ProcessingStatus.CLASSIFIED.value
                relevant_count += 1
            else:
                reg.status = ProcessingStatus.REJECTED.value
                rejected_count += 1

            if (i + 1) % 25 == 0:
                session.commit()
                cost_so_far = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)
                print(
                    f"  [FILTER] {i + 1}/{len(regulations)} | "
                    f"Relevant: {relevant_count} | Rejected: {rejected_count} | "
                    f"Tokens: {total_input_tokens + total_output_tokens:,} | "
                    f"Cost: ${cost_so_far:.3f} | "
                    f"Time: {total_time:.0f}s"
                )

            time.sleep(0.3)

        except json.JSONDecodeError as e:
            print(f"  [FILTER] JSON parse error on '{reg.title[:50]}...': {e}")
            reg.status = "error"
            reg.filter_reason = f"JSON parse error: {e}"
            error_count += 1

        except anthropic.RateLimitError:
            print(f"  [FILTER] Rate limited. Waiting 30 seconds...")
            time.sleep(30)
            try:
                date_str = reg.published_date.strftime("%Y-%m-%d") if reg.published_date else "unknown"
                result, usage = classify_regulation(reg.source, reg.title, date_str, reg.text)
                total_input_tokens += usage["input_tokens"]
                total_output_tokens += usage["output_tokens"]
                total_time += usage["time_seconds"]
                total_calls += 1
                reg.relevant = result.get("relevant", False)
                reg.severity = result.get("severity", "low")
                reg.filter_reason = result.get("reason", "")
                if reg.state is None:
                    reg.state = result.get("state", "BOTH")
                reg.status = ProcessingStatus.CLASSIFIED.value if reg.relevant else ProcessingStatus.REJECTED.value
                if reg.relevant:
                    relevant_count += 1
                else:
                    rejected_count += 1
            except Exception as e2:
                print(f"  [FILTER] Retry failed: {e2}")
                reg.status = "error"
                error_count += 1

        except Exception as e:
            print(f"  [FILTER] Error on '{reg.title[:50]}...': {e}")
            reg.status = "error"
            reg.filter_reason = str(e)
            error_count += 1

    session.commit()

    total_cost = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)

    stats = {
        "relevant": relevant_count,
        "rejected": rejected_count,
        "errors": error_count,
        "total_calls": total_calls,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "cost_usd": round(total_cost, 4),
        "time_seconds": round(total_time, 1),
        "model": CLAUDE_MODEL,
    }

    print(f"[FILTER AGENT] Done")
    print(f"  Relevant: {relevant_count} | Rejected: {rejected_count} | Errors: {error_count}")
    print(f"  Model: {CLAUDE_MODEL}")
    print(f"  API calls: {total_calls}")
    print(f"  Input tokens: {total_input_tokens:,}")
    print(f"  Output tokens: {total_output_tokens:,}")
    print(f"  Total tokens: {total_input_tokens + total_output_tokens:,}")
    print(f"  Cost: ${total_cost:.4f}")
    print(f"  Time: {total_time:.0f}s ({total_time/60:.1f} min)")

    return stats
