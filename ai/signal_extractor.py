# Why: Classifies articles into typed signals
# Deps: OpenRouter via ai.client, json
# How: LLM JSON extraction with keyword fallback

import json

from ai.client import get_ai_client, get_bulk_model

try:
    from private.prompts import SIGNAL_EXTRACTOR_PROMPT as SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = (
        "You are a signal classifier for a sales intelligence platform.\n\n"
        "Classify articles into one signal type and extract structured data.\n"
        "Signal types: fundraising, funding_completed, hiring, ai_initiative, "
        "cloud_spend, outgrowing, other.\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"signal_type": "...", "magnitude": number, "confidence": 0-1, "key_facts": "..."}'
    )


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


try:
    from private.collector_patterns import FALLBACK_EXTRACTION_KEYWORDS as _FALLBACK_KW
except ImportError:
    _FALLBACK_KW = {
        "fundraising": ["raising", "fundrais", "seed round"],
        "funding_completed": ["raised", "raises", "secured", "series"],
        "hiring": ["hiring", "hires", "job", "recruit"],
        "ai_initiative": ["gpu", "ai", "infrastructure", "data center"],
        "cloud_spend": ["cloud cost", "cloud spend", "egress"],
        "outgrowing": ["outgrow", "switch", "migrat"],
    }

_CONFIDENCE = {"fundraising": 0.4, "funding_completed": 0.4, "hiring": 0.4,
               "ai_initiative": 0.3, "cloud_spend": 0.3, "outgrowing": 0.3}


def _fallback_extraction(title: str) -> dict:
    """Keyword-based fallback classification when no API key is set."""
    title_lower = title.lower()

    for sig_type, keywords in _FALLBACK_KW.items():
        if any(kw in title_lower for kw in keywords):
            return {
                "signal_type": sig_type,
                "magnitude": 1.0,
                "confidence": _CONFIDENCE.get(sig_type, 0.3),
                "key_facts": title,
            }

    return {"signal_type": "other", "magnitude": 0, "confidence": 0.1, "key_facts": ""}
