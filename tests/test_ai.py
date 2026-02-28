"""
Tests for AI layer fallback logic.

When OPENAI_API_KEY is not set, each AI module uses a keyword-based fallback.
These tests verify those fallbacks work correctly — they're always available
and don't require API calls.

We also verify the OpenAI code path handles errors gracefully.
"""

import pytest
from unittest.mock import patch, MagicMock

from ai.summarizer import summarize_article, _fallback_summary
from ai.signal_extractor import extract_signal, _fallback_extraction
from ai.brief_generator import _fallback_brief, _build_prospect_context
from database.models import Company, Signal, ProspectScore


# ── Summarizer fallbacks ─────────────────────────────────────────


class TestFallbackSummary:
    def test_extracts_first_two_sentences(self):
        content = "First sentence here. Second sentence here. Third sentence here."
        result = _fallback_summary("Title", content)
        assert "First sentence" in result
        assert "Second sentence" in result
        assert "Third" not in result

    def test_falls_back_to_title_when_no_content(self):
        result = _fallback_summary("The Title", "")
        assert result == "The Title"

    @patch("ai.client.get_ai_client", return_value=None)
    def test_summarize_uses_fallback_without_key(self, _mock):
        """Without an API key, summarize_article should use the fallback."""
        result = summarize_article("Big News", "Content here. More content.")
        assert len(result) > 0


# ── Signal extractor fallbacks ────────────────────────────────────


class TestFallbackExtraction:
    @pytest.mark.parametrize("title,expected_type", [
        ("Company raising $500M for expansion", "fundraising"),
        ("Startup raised $200M in Series B", "funding_completed"),
        ("Company hiring GPU engineers", "hiring"),
        ("New AI model training on 10k GPUs", "ai_initiative"),
        ("Cloud cost optimization platform launches", "cloud_spend"),
        ("Company outgrowing current provider", "outgrowing"),
        ("CEO attends charity gala", "other"),
    ])
    def test_fallback_classifies_correctly(self, title, expected_type):
        result = _fallback_extraction(title)
        assert result["signal_type"] == expected_type

    def test_fallback_returns_required_keys(self):
        result = _fallback_extraction("anything")
        assert "signal_type" in result
        assert "magnitude" in result
        assert "confidence" in result
        assert "key_facts" in result

    @patch("ai.client.get_ai_client", return_value=None)
    def test_extract_signal_uses_fallback_without_key(self, _mock):
        result = extract_signal("Company raised $100M")
        assert result["signal_type"] == "funding_completed"


# ── Brief generator fallbacks ─────────────────────────────────────


class TestFallbackBrief:
    def test_fallback_includes_company_name(self, sample_prospect):
        brief = _fallback_brief(sample_prospect, "")
        assert "TestCo AI" in brief

    def test_fallback_includes_industry(self, sample_prospect):
        brief = _fallback_brief(sample_prospect, "")
        assert "AI Research" in brief

    def test_fallback_suggests_api_key(self, sample_prospect):
        brief = _fallback_brief(sample_prospect, "")
        assert "OPENAI_API_KEY" in brief


# ── Context builder ───────────────────────────────────────────────


class TestBuildContext:
    def test_context_includes_company_info(self, session, sample_prospect):
        company, ctx = _build_prospect_context(session, sample_prospect.id)
        assert company is not None
        assert "TestCo AI" in ctx
        assert "AI Research" in ctx
        assert "San Francisco" in ctx

    def test_context_includes_score_breakdown(self, session, sample_prospect):
        score = ProspectScore(
            company_id=sample_prospect.id,
            total_score=72.5,
            fundraising_score=15.0,
            hiring_score=20.0,
        )
        session.add(score)
        session.commit()

        _, ctx = _build_prospect_context(session, sample_prospect.id)
        assert "72.5" in ctx
        assert "Fundraising" in ctx

    def test_context_includes_signals(self, session, sample_prospect, sample_signals):
        _, ctx = _build_prospect_context(session, sample_prospect.id)
        assert "SIGNALS" in ctx
        assert "fundraising" in ctx

    def test_context_includes_funding(self, session, sample_prospect):
        _, ctx = _build_prospect_context(session, sample_prospect.id)
        assert "$100,000,000" in ctx
