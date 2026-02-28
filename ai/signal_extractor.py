# Why: Classifies articles into typed signals
# Deps: OpenRouter via ai.client, json
# How: LLM JSON extraction with keyword fallback

import json

from ai.client import get_ai_client, get_bulk_model

SYSTEM_PROMPT = """You are a signal classifier for a sales intelligence platform at Iren, 
an HPC data center company.

Given a news article title and optional content, classify it into exactly ONE signal type 
and extract structured data.

Signal types:
- fundraising: Company is ACTIVELY raising money (rumors, "seeking funding", "in talks", "exploring IPO")
- funding_completed: Company CLOSED a funding round (announced raise, "raised $X", "secured $X")
- hiring: Company is hiring infrastructure/GPU/ML/data center roles
- ai_initiative: Company announced AI product, model training, compute partnership, or expansion
- cloud_spend: Signals about cloud costs, cloud repatriation, infrastructure cost optimization
- outgrowing: Company outgrowing current provider, complaints about capacity, switching providers
- other: Article does not fit any of the above signal types

Respond with ONLY valid JSON:
{
    "signal_type": "one of the types above",
    "magnitude": number (dollar amount if funding, 1.0 otherwise),
    "confidence": number between 0 and 1,
    "key_facts": "1-2 sentence extraction of key facts"
}"""


def extract_signal(title: str, content: str = "", company_name: str = "") -> dict:
    """
    Classify an article and extract structured signal data.

    Returns dict with: signal_type, magnitude, confidence, key_facts
    """
    client = get_ai_client()
    if not client:
        return _fallback_extraction(title)

    user_prompt = f"Company: {company_name}\nTitle: {title}\nContent: {content[:2000]}"
    model = get_bulk_model()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.1,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return {
            "signal_type": result.get("signal_type", "other"),
            "magnitude": result.get("magnitude", 1.0),
            "confidence": result.get("confidence", 0.5),
            "key_facts": result.get("key_facts", ""),
        }
    except Exception as e:
        print(f"[signal_extractor] bulk model {model} failed: {e}")

    return _fallback_extraction(title)


def _fallback_extraction(title: str) -> dict:
    """Keyword-based fallback classification when no API key is set."""
    title_lower = title.lower()

    if any(kw in title_lower for kw in ["raising", "seeks", "exploring ipo", "fundrais", "in talks"]):
        return {"signal_type": "fundraising", "magnitude": 1.0, "confidence": 0.4, "key_facts": title}
    if any(kw in title_lower for kw in ["raised", "raises", "secured", "closes", "series", "funding round"]):
        return {"signal_type": "funding_completed", "magnitude": 1.0, "confidence": 0.4, "key_facts": title}
    if any(kw in title_lower for kw in ["hiring", "hires", "job", "recruit", "engineer"]):
        return {"signal_type": "hiring", "magnitude": 1.0, "confidence": 0.4, "key_facts": title}
    if any(kw in title_lower for kw in ["gpu", "model", "training", "ai", "infrastructure", "data center"]):
        return {"signal_type": "ai_initiative", "magnitude": 1.0, "confidence": 0.3, "key_facts": title}
    if any(kw in title_lower for kw in ["cloud cost", "repatriat", "optimize", "cloud spend"]):
        return {"signal_type": "cloud_spend", "magnitude": 1.0, "confidence": 0.3, "key_facts": title}
    if any(kw in title_lower for kw in ["outgrow", "switch", "migrat", "waitlist", "capacity"]):
        return {"signal_type": "outgrowing", "magnitude": 1.0, "confidence": 0.3, "key_facts": title}

    return {"signal_type": "other", "magnitude": 0, "confidence": 0.1, "key_facts": ""}
