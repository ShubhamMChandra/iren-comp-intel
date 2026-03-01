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

CLASSIFICATION_PROMPT = """Classify this news headline about a company into exactly ONE category.
Think about what this headline MEANS for the company's need for HPC/GPU data center infrastructure.

Categories:
- fundraising: Company is ACTIVELY raising money (rumored rounds, exploring IPO, seeking investors)
- funding_completed: Company CLOSED a funding round or received investment ("raised $X", "secured $X")
- hiring: Company is hiring infrastructure/GPU/ML/data center roles, OR expanding workforce significantly
- ai_initiative: Company announced AI model training, launched AI products, signed compute partnerships, or is expanding AI/data center infrastructure
- cloud_spend: Signals about cloud costs, cloud repatriation, infrastructure cost optimization
- outgrowing: Company outgrowing current provider, complaints about capacity, switching providers, waitlist issues
- other: Article is about lawsuits, politics, opinion pieces, executive drama, or unrelated business news that has NO bearing on compute infrastructure needs

Company: {company}
Headline: {title}

Respond with ONLY a JSON object: {{"type": "one_of_the_categories", "confidence": 0.0_to_1.0}}"""


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


def _classify_with_keywords(title: str) -> str:
    """Keyword-based fallback — fast and free."""
    t = title.lower()

    not_relevant_patterns = [
        "lawsuit", "sued", "suing", "deposition", "testimony",
        "criminal", "antitrust", "regulation", "ban", "bans",
        "opinion", "editorial", "musk bashes", "controversy",
        "stock price", "analyst rating", "buy rating", "sell rating",
        "earnings call", "quarterly results",
    ]
    if any(p in t for p in not_relevant_patterns):
        return "other"

    fundraising_patterns = [
        "seeking", "in talks to raise", "exploring ipo", "fundrais",
        "plans to go public", "considering offering", "roadshow",
    ]
    if any(p in t for p in fundraising_patterns):
        return "fundraising"

    funding_patterns = [
        "raises", "raised", "secures", "secured", "closes", "closed",
        "$", "billion", "million", "funding round", "series",
        "investment from", "backed by", "led by",
    ]
    if any(p in t for p in funding_patterns):
        return "funding_completed"

    layoff_patterns = [
        "layoff", "lay off", "laid off", "lays off", "job cuts",
        "workforce reduction", "downsiz",
    ]
    if any(p in t for p in layoff_patterns):
        return "other"

    hiring_patterns = [
        "hiring", "hires", "hire", "job", "recruit", "workforce",
        "headcount", "engineer", "permanent jobs",
        "construction jobs", "sre", "mlops", "ml engineer",
    ]
    if any(p in t for p in hiring_patterns):
        return "hiring"

    cloud_patterns = [
        "cloud cost", "cloud spend", "repatri", "optimize",
        "cost reduction", "cloud bill", "egress",
    ]
    if any(p in t for p in cloud_patterns):
        return "cloud_spend"

    outgrowing_patterns = [
        "outgrow", "switch", "migrat", "waitlist", "shortage",
        "capacity constraint", "moving away from",
    ]
    if any(p in t for p in outgrowing_patterns):
        return "outgrowing"

    ai_patterns = [
        "data center", "datacenter", "gpu", "ai infrastructure",
        "model training", "ai cloud", "compute", "chip", "semiconductor",
        "nvidia", "server", "liquid cooling", "power", "megawatt",
        "gw", "mw ", "facility", "campus", "supercomputer",
        "partnership", "contract", "deal", "agreement",
        "ai model", "llm", "foundation model", "inference",
        "expansion", "build", "construction", "new site",
    ]
    if any(p in t for p in ai_patterns):
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
