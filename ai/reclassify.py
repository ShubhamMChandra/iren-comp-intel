"""
Signal reclassification pipeline.

Takes all signals currently typed as 'ai_initiative' (the default bucket from
the news collector) and reclassifies them using AI + keyword fallback.

Also marks irrelevant signals (celebrity gossip, lawsuits, etc.) as 'other'
so they don't pollute scoring.

Usage:
    python -m ai.reclassify           # reclassify all mistyped signals
    python -m ai.reclassify --dry-run # preview without saving
"""

import json
import sys
import time

from database.db import get_session, init_db
from database.models import Company, Signal
from ai.client import get_ai_client, get_model, get_fallback_model

try:
    from private.prompts import CLASSIFICATION_PROMPT
except ImportError:
    CLASSIFICATION_PROMPT = (
        "Classify this news headline into one category: fundraising, funding_completed, "
        "hiring, ai_initiative, cloud_spend, outgrowing, other.\n\n"
        "Company: {company}\nHeadline: {title}\n\n"
        'Respond with ONLY a JSON object: {{"type": "category", "confidence": 0.0_to_1.0}}'
    )


def _classify_with_ai(client, model: str, company_name: str, title: str) -> dict | None:
    prompt = CLASSIFICATION_PROMPT.format(company=company_name, title=title)
    for m in [model, get_fallback_model()]:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.1,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            if m == model:
                print(f"  {model} failed ({e}), trying fallback...")
            else:
                print(f"  Fallback also failed: {e}")
    return None


try:
    from private.collector_patterns import (
        RECLASSIFY_NOT_RELEVANT,
        RECLASSIFY_FUNDRAISING,
        RECLASSIFY_FUNDING,
        RECLASSIFY_LAYOFFS,
        RECLASSIFY_HIRING,
        RECLASSIFY_CLOUD,
        RECLASSIFY_OUTGROWING,
        RECLASSIFY_AI,
    )
except ImportError:
    RECLASSIFY_NOT_RELEVANT = ["lawsuit", "sued", "opinion", "editorial"]
    RECLASSIFY_FUNDRAISING = ["seeking", "fundrais", "exploring ipo"]
    RECLASSIFY_FUNDING = ["raises", "raised", "secured", "series"]
    RECLASSIFY_LAYOFFS = ["layoff", "laid off", "job cuts"]
    RECLASSIFY_HIRING = ["hiring", "hires", "recruit", "engineer"]
    RECLASSIFY_CLOUD = ["cloud cost", "cloud spend", "repatri"]
    RECLASSIFY_OUTGROWING = ["outgrow", "switch", "migrat"]
    RECLASSIFY_AI = ["data center", "gpu", "ai infrastructure", "compute"]


def _classify_with_keywords(title: str) -> str:
    """Keyword-based fallback — fast and free."""
    t = title.lower()

    if any(p in t for p in RECLASSIFY_NOT_RELEVANT):
        return "other"
    if any(p in t for p in RECLASSIFY_FUNDRAISING):
        return "fundraising"
    if any(p in t for p in RECLASSIFY_FUNDING):
        return "funding_completed"
    if any(p in t for p in RECLASSIFY_LAYOFFS):
        return "other"
    if any(p in t for p in RECLASSIFY_HIRING):
        return "hiring"
    if any(p in t for p in RECLASSIFY_CLOUD):
        return "cloud_spend"
    if any(p in t for p in RECLASSIFY_OUTGROWING):
        return "outgrowing"
    if any(p in t for p in RECLASSIFY_AI):
        return "ai_initiative"

    return "other"


def reclassify_signals(dry_run: bool = False, use_ai: bool = True):
    """Reclassify all signals that were dumped into the default ai_initiative bucket."""
    init_db()
    session = get_session()

    mistyped = (
        session.query(Signal)
        .filter(Signal.signal_type == "ai_initiative")
        .all()
    )

    print(f"Found {len(mistyped)} signals to reclassify")

    companies = {c.id: c.name for c in session.query(Company).all()}
    client = get_ai_client() if use_ai else None
    model = get_model()

    if client:
        print(f"Using AI model: {model} via OpenRouter")
    else:
        print("No API key — using keyword classification only")

    stats: dict[str, int] = {}
    errors = 0

    for i, signal in enumerate(mistyped):
        company_name = companies.get(signal.company_id, "Unknown")

        if client:
            result = _classify_with_ai(client, model, company_name, signal.title)
            if result and result.get("type") in [
                "fundraising", "funding_completed", "hiring",
                "ai_initiative", "cloud_spend", "outgrowing", "other",
            ]:
                new_type = result["type"]
            else:
                new_type = _classify_with_keywords(signal.title)
                errors += 1
        else:
            new_type = _classify_with_keywords(signal.title)

        stats[new_type] = stats.get(new_type, 0) + 1

        if new_type != signal.signal_type:
            if not dry_run:
                signal.signal_type = new_type

        if (i + 1) % 25 == 0:
            print(f"  Processed {i + 1}/{len(mistyped)}...")
            if not dry_run:
                session.commit()

            # Rate limiting for AI calls
            if client:
                time.sleep(0.3)

    if not dry_run:
        session.commit()

    print(f"\nReclassification complete {'(DRY RUN)' if dry_run else ''}")
    print(f"AI errors (fell back to keywords): {errors}")
    print("\nResults:")
    for sig_type, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {sig_type}: {count}")

    session.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    no_ai = "--no-ai" in sys.argv
    reclassify_signals(dry_run=dry, use_ai=not no_ai)
