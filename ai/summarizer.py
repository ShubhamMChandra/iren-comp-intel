# Why: Condenses articles into sales-relevant summaries
# Deps: OpenRouter via ai.client
# How: LLM prompt with extractive keyword fallback

from ai.client import get_ai_client, call_with_fallback

SYSTEM_PROMPT = """You are a sales intelligence analyst for Iren, a high-performance computing 
data center company that sells GPU cloud, colocation, and build-to-suit data center capacity.

When summarizing articles, focus on:
- What this means for compute/GPU/data center demand
- Whether this company might need HPC infrastructure
- Key numbers (funding amount, capacity, GPU count, MW)
- Competitive implications (who they're working with now)

Keep summaries to 2-3 sentences. Be direct and actionable — a salesperson will read this."""


def summarize_article(title: str, content: str, company_name: str = "") -> str:
    """Summarize an article into a sales-relevant 2-3 sentence brief."""
    client = get_ai_client()
    if not client:
        return _fallback_summary(title, content)

    user_prompt = f"Company: {company_name}\nTitle: {title}\n\nContent:\n{content[:3000]}"

    result = call_with_fallback(
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
