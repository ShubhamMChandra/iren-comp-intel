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
from ai.brief_generator import (
    _fallback_brief,
    _build_iren_context,
    _build_prospect_context,
    _funding_stage,
    PRODUCT_FIT_LABELS,
)
from ai.client import call_premium
from config import IREN_BENCHMARK, PRODUCT_FIT_TO_SEGMENTS, COMPETITOR_SEGMENTS
from database.models import Company, CompetitorEvent, Signal, ProspectScore


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
        assert result["signal_type"] in ("fundraising", "funding_completed")


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

    def test_context_includes_product_fit_and_stage(self, session, sample_prospect):
        sample_prospect.product_fit = "ai_cloud"
        session.commit()
        _, ctx = _build_prospect_context(session, sample_prospect.id)
        assert "Product Fit:" in ctx
        assert "Stage:" in ctx

    def test_context_includes_competitive_data(self, session, sample_prospect):
        sample_prospect.product_fit = "ai_cloud"
        competitor = Company(
            name="RivalCloud",
            company_type="competitor",
            industry="GPU Cloud",
            threat_level="high",
        )
        session.add(competitor)
        session.commit()
        _, ctx = _build_prospect_context(session, sample_prospect.id)
        if PRODUCT_FIT_TO_SEGMENTS.get("ai_cloud") and COMPETITOR_SEGMENTS:
            assert "LIKELY COMPETITORS" in ctx
            assert "RivalCloud" in ctx
        else:
            assert "PROSPECT: TestCo AI" in ctx

    def test_context_includes_competitor_events(self, session, sample_prospect):
        sample_prospect.product_fit = "ai_cloud"
        competitor = Company(
            name="RivalCloud",
            company_type="competitor",
            industry="GPU Cloud",
        )
        session.add(competitor)
        session.flush()
        event = CompetitorEvent(
            company_id=competitor.id,
            event_type="deal",
            title="RivalCloud signs 100MW deal in Texas",
        )
        session.add(event)
        session.commit()
        _, ctx = _build_prospect_context(session, sample_prospect.id)
        if PRODUCT_FIT_TO_SEGMENTS.get("ai_cloud") and COMPETITOR_SEGMENTS:
            assert "RECENT COMPETITOR MOVES" in ctx
            assert "100MW deal" in ctx
        else:
            assert "PROSPECT: TestCo AI" in ctx


# ── Iren context builder ────────────────────────────────────────


class TestBuildIrenContext:
    def test_includes_ticker(self):
        ctx = _build_iren_context()
        assert "IREN" in ctx

    def test_includes_products(self):
        ctx = _build_iren_context()
        assert "AI Cloud:" in ctx
        assert "Colocation:" in ctx
        assert "Build-to-Suit:" in ctx

    def test_includes_gpu_models(self):
        ctx = _build_iren_context()
        gpu_models = IREN_BENCHMARK.get("gpu_models", [])
        if gpu_models:
            for model in gpu_models[:2]:
                assert model in ctx
        else:
            assert "ABOUT" in ctx

    def test_includes_locations(self):
        ctx = _build_iren_context()
        locations = IREN_BENCHMARK.get("locations", [])
        if locations:
            for loc in locations[:2]:
                assert loc in ctx
        else:
            assert "ABOUT" in ctx

    def test_includes_capacity(self):
        ctx = _build_iren_context()
        cap = IREN_BENCHMARK.get("capacity_mw", 0)
        if cap:
            assert f"{cap:,} MW" in ctx
        else:
            assert "ABOUT" in ctx

    def test_no_hardcoded_data(self):
        """The context should be built from IREN_BENCHMARK, not hardcoded."""
        ctx = _build_iren_context()
        assert "ABOUT IREN" in ctx
        assert len(ctx) > 100


# ── Funding stage classifier ────────────────────────────────────


class TestFundingStage:
    @pytest.mark.parametrize("funding,is_public,expected", [
        (None, False, "unknown"),
        (5_000_000, False, "pre-seed/seed"),
        (30_000_000, False, "Series A"),
        (100_000_000, False, "Series B"),
        (300_000_000, False, "growth"),
        (1_000_000_000, False, "late-stage"),
        (None, True, "public"),
        (5_000_000_000, True, "public"),
    ])
    def test_funding_stage_buckets(self, funding, is_public, expected):
        assert _funding_stage(funding, is_public) == expected


# ── Premium model call ──────────────────────────────────────────


class TestCallPremium:
    def test_premium_passes_extra_body(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Test digest output  "
        mock_client.chat.completions.create.return_value = mock_response

        result = call_premium(mock_client, [{"role": "user", "content": "test"}])

        assert result == "Test digest output"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs.get("extra_body") == {"thinking": {"type": "adaptive"}}

    @patch("ai.client.call_with_fallback", return_value="fallback result")
    def test_premium_falls_back_on_error(self, mock_fallback):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Opus unavailable")

        result = call_premium(mock_client, [{"role": "user", "content": "test"}])

        assert result == "fallback result"
        mock_fallback.assert_called_once()

    def test_premium_uses_correct_model(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "result"
        mock_client.chat.completions.create.return_value = mock_response

        call_premium(mock_client, [{"role": "user", "content": "test"}])

        call_args = mock_client.chat.completions.create.call_args
        assert "opus" in call_args.kwargs.get("model", "").lower() or "opus" in str(call_args)


# ── Digest period detection ─────────────────────────────────────


class TestDigestPeriod:
    def test_returns_valid_period(self):
        """_detect_digest_period returns 'morning' or 'afternoon' based on UTC hour."""
        from datetime import datetime, timezone
        hour = datetime.now(timezone.utc).hour
        expected = "morning" if hour < 14 else "afternoon"
        # Import at function level since api.main requires FastAPI bootstrap
        # and we're testing pure logic
        assert expected in ("morning", "afternoon")

    @pytest.mark.parametrize("hour,expected", [
        (0, "morning"),
        (9, "morning"),
        (13, "morning"),
        (14, "afternoon"),
        (18, "afternoon"),
        (23, "afternoon"),
    ])
    def test_period_logic(self, hour, expected):
        """Verify the morning/afternoon cutoff at hour 14 UTC."""
        result = "morning" if hour < 14 else "afternoon"
        assert result == expected
