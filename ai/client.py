"""
Shared AI client configured for OpenRouter.
OpenRouter is OpenAI-compatible — same client, different base_url.

Primary model: Kimi K2
Fallback model: Gemini 2.0 Flash
"""

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

FALLBACK_MODEL = "google/gemini-2.0-flash-001"


def get_ai_client() -> OpenAI | None:
    """Return a configured OpenAI client pointing at OpenRouter, or None if no key."""
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key:
        return None

    if OPENROUTER_API_KEY:
        return OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )

    return OpenAI(api_key=OPENAI_API_KEY)


def get_model() -> str:
    return OPENAI_MODEL


def get_fallback_model() -> str:
    return FALLBACK_MODEL


def call_with_fallback(
    client: OpenAI,
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.4,
) -> str | None:
    """Try primary model (Kimi K2), fall back to Gemini Flash on failure."""
    primary = get_model()
    fallback = get_fallback_model()

    for model in [primary, fallback]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if model == primary:
                print(f"[ai] {primary} failed ({e}), falling back to {fallback}")
            else:
                print(f"[ai] {fallback} also failed: {e}")

    return None
