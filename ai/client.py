"""
Shared AI client configured for OpenRouter.
OpenRouter is OpenAI-compatible — same client, different base_url.

Two-tier model strategy:
  Bulk tier  — Gemini 2.5 Flash (collection/enrichment pipelines)
  Analysis   — Kimi K2 (user-facing briefs, emails, battle cards)
  Fallback   — Gemini Flash (if analysis model fails)
"""

from openai import OpenAI

from config import (
    AI_MODEL_ANALYSIS,
    AI_MODEL_BULK,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)

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


def get_bulk_model() -> str:
    return AI_MODEL_BULK


def get_analysis_model() -> str:
    return AI_MODEL_ANALYSIS


def call_bulk(
    client: OpenAI,
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> str | None:
    """Use bulk model (Gemini Flash) for collection tasks. Returns None on failure — never escalates to K2."""
    model = get_bulk_model()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ai] bulk model {model} failed: {e}")
        return None


def call_with_fallback(
    client: OpenAI,
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.4,
) -> str | None:
    """Try analysis model (Kimi K2), fall back to Gemini Flash on failure."""
    primary = get_analysis_model()
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
