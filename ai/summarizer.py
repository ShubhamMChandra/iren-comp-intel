# Why: Condenses articles into sales-relevant summaries
# Deps: OpenRouter via ai.client
# How: LLM prompt with extractive keyword fallback

from ai.client import call_bulk, get_ai_client

try:
    from private.prompts import SUMMARIZER_PROMPT as SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = (
        "You are a sales intelligence analyst. Summarize articles focusing on "
        "compute infrastructure demand signals. Keep to 2-3 sentences."
    )


def summarize_article(title: str, content: str, company_name: str = "") -> str:
    """Summarize an article into a sales-relevant 2-3 sentence brief."""
    client = get_ai_client()
    if not client:
        return _fallback_summary(title, content)

    user_prompt = f"Company: {company_name}\nTitle: {title}\n\nContent:\n{content[:3000]}"

    result = call_bulk(
        client,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=200,
        temperature=0.3,
    )
    return result or _fallback_summary(title, content)


def _fallback_summary(title: str, content: str) -> str:
    """Simple extractive fallback when no API key is set."""
    if content:
        sentences = content.replace("\n", " ").split(". ")
        return ". ".join(sentences[:2]).strip() + "."
    return title
