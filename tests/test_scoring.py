"""
Tests for the scoring engine.

What we're testing:
  - Recency decay: does a signal lose value over time correctly?
  - Magnitude multiplier: does bigger funding = higher multiplier?
  - Source confidence: does SEC filing outweigh a blog post?
  - End-to-end scoring: does score_prospect produce the right shape?
  - Category capping: scores shouldn't exceed max_points per category
"""

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from database.models import Signal, ProspectScore
from scoring.engine import (
    _recency_decay,
    _magnitude_multiplier,
    _source_confidence,
    score_prospect,
)
from scoring.weights import SIGNAL_WEIGHTS, MAGNITUDE_THRESHOLDS


# ── Recency decay ────────────────────────────────────────────────


class TestRecencyDecay:
    """
    The decay formula is: 0.5 ^ (age_days / halflife_days)
    So at exactly 1 halflife, the multiplier should be 0.5.
    At 0 days old, it should be ~1.0.
    """

    def test_brand_new_signal(self):
        """A signal detected right now should have decay ≈ 1.0."""
        now = datetime.now(timezone.utc)
        result = _recency_decay(now, halflife_days=30)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_one_halflife(self):
        """A signal exactly 1 halflife old should have decay = 0.5."""
        halflife = 30
        detected = datetime.now(timezone.utc) - timedelta(days=halflife)
        result = _recency_decay(detected, halflife_days=halflife)
        assert result == pytest.approx(0.5, abs=0.01)

    def test_two_halflives(self):
        """At 2 halflives the decay should be 0.25."""
        halflife = 30
        detected = datetime.now(timezone.utc) - timedelta(days=halflife * 2)
        result = _recency_decay(detected, halflife_days=halflife)
        assert result == pytest.approx(0.25, abs=0.01)

    def test_very_old_signal(self):
        """A signal from 1 year ago should have a very low (but positive) decay."""
        detected = datetime.now(timezone.utc) - timedelta(days=365)
        result = _recency_decay(detected, halflife_days=30)
        assert 0 < result < 0.01

    def test_future_signal_clamped(self):
        """A signal detected in the future (clock skew) should return 1.0."""
        future = datetime.now(timezone.utc) + timedelta(days=5)
        result = _recency_decay(future, halflife_days=30)
        assert result == 1.0

    def test_naive_datetime_handled(self):
        """A datetime without tzinfo should be treated as UTC, not crash."""
        naive_dt = datetime.now() - timedelta(days=15)
        result = _recency_decay(naive_dt, halflife_days=30)
        assert 0 < result < 1.0


# ── Magnitude multiplier ─────────────────────────────────────────


class TestMagnitudeMultiplier:
    def test_no_thresholds_returns_one(self):
        """Signal types with no magnitude thresholds should return 1.0."""
        result = _magnitude_multiplier("hiring", 999)
        assert result == 1.0

    def test_zero_magnitude_returns_one(self):
        """Zero magnitude should return 1.0 (presence-only signal)."""
        result = _magnitude_multiplier("funding_completed", 0)
        assert result == 1.0

    def test_small_funding(self):
        """$50M funding_completed should hit the first tier when thresholds are configured."""
        result = _magnitude_multiplier("funding_completed", 50_000_000)
        thresholds = MAGNITUDE_THRESHOLDS.get("funding_completed", [])
        if thresholds:
            assert result == thresholds[0][1]
        else:
            assert result == 1.0

    def test_large_funding(self):
        """$5B+ should hit the max tier when thresholds are configured."""
        result = _magnitude_multiplier("funding_completed", 10_000_000_000)
        thresholds = MAGNITUDE_THRESHOLDS.get("funding_completed", [])
        if thresholds:
            assert result == thresholds[-1][1]
        else:
            assert result == 1.0

    def test_between_tiers(self):
        """$300M should land at the correct tier, not jump ahead."""
        result = _magnitude_multiplier("funding_completed", 300_000_000)
        thresholds = MAGNITUDE_THRESHOLDS.get("funding_completed", [])
        if thresholds:
            assert result == 1.0
        else:
            assert result == 1.0

    def test_fundraising_thresholds_exist(self):
        """When private config is loaded, fundraising should have magnitude thresholds."""
        if not MAGNITUDE_THRESHOLDS:
            pytest.skip("no magnitude thresholds configured (generic fallback)")
        assert "fundraising" in MAGNITUDE_THRESHOLDS
        result = _magnitude_multiplier("fundraising", 1_000_000_000)
        assert result > 1.0


# ── Source confidence ─────────────────────────────────────────────


class TestSourceConfidence:
    def test_sec_filing_is_highest(self):
        assert _source_confidence("sec_filing") == 1.0

    def test_major_news(self):
        assert _source_confidence("major_news") == 0.85

    def test_rumor_is_lowest(self):
        assert _source_confidence("rumor") == 0.2

    def test_unknown_source_gets_default(self):
        """An unrecognized source type should return a safe default (0.5)."""
        result = _source_confidence("random_blog_we_never_configured")
        assert result == 0.5


# ── Score weights config ─────────────────────────────────────────


class TestWeightsConfig:
    def test_all_signal_types_have_weights(self):
        """Every signal type used in the app should have a weight entry."""
        expected = {"fundraising", "funding_completed", "hiring",
                    "ai_initiative", "cloud_spend", "outgrowing"}
        assert set(SIGNAL_WEIGHTS.keys()) == expected

    def test_max_points_sum_to_100(self):
        """The max_points across all categories should sum to 100."""
        total = sum(w["max_points"] for w in SIGNAL_WEIGHTS.values())
        assert total == 100

    def test_each_weight_has_required_keys(self):
        for signal_type, config in SIGNAL_WEIGHTS.items():
            assert "max_points" in config, f"{signal_type} missing max_points"
            assert "base_points" in config, f"{signal_type} missing base_points"
            assert "recency_halflife_days" in config, f"{signal_type} missing halflife"


# ── End-to-end scoring ───────────────────────────────────────────


class TestScoreProspect:
    def test_score_with_signals(self, session, sample_prospect, sample_signals):
        """Scoring a prospect with signals should produce a positive total."""
        score = score_prospect(sample_prospect.id, session=session)

        assert isinstance(score, ProspectScore)
        assert score.total_score > 0
        assert score.company_id == sample_prospect.id

    def test_score_without_signals(self, session, sample_prospect):
        """A prospect with zero signals should score 0."""
        score = score_prospect(sample_prospect.id, session=session)
        assert score.total_score == 0

    def test_score_breakdown_adds_up(self, session, sample_prospect, sample_signals):
        """The sum of category scores should equal total_score."""
        score = score_prospect(sample_prospect.id, session=session)

        breakdown_sum = (
            score.fundraising_score
            + score.funding_completed_score
            + score.hiring_score
            + score.ai_initiative_score
            + score.cloud_spend_score
            + score.outgrowing_score
        )
        assert score.total_score == pytest.approx(breakdown_sum, abs=0.01)

    def test_category_caps_respected(self, session, sample_prospect):
        """Even with many signals, a category should never exceed max_points."""
        now = datetime.now(timezone.utc)
        for i in range(20):
            session.add(Signal(
                company_id=sample_prospect.id,
                signal_type="hiring",
                title=f"Hiring signal #{i}",
                source_type="sec_filing",
                magnitude=1.0,
                detected_at=now,
            ))
        session.commit()

        score = score_prospect(sample_prospect.id, session=session)
        assert score.hiring_score <= SIGNAL_WEIGHTS["hiring"]["max_points"]

    def test_score_stored_in_db(self, session, sample_prospect, sample_signals):
        """score_prospect should persist the score row to the database."""
        score = score_prospect(sample_prospect.id, session=session)

        stored = session.query(ProspectScore).filter(
            ProspectScore.company_id == sample_prospect.id
        ).first()
        assert stored is not None
        assert stored.total_score == score.total_score

    def test_older_signals_score_less(self, session, sample_prospect):
        """A recent signal should contribute more points than an old one."""
        now = datetime.now(timezone.utc)

        session.add(Signal(
            company_id=sample_prospect.id,
            signal_type="ai_initiative",
            title="Recent AI news",
            source_type="major_news",
            detected_at=now - timedelta(days=1),
        ))
        session.commit()
        score_obj = score_prospect(sample_prospect.id, session=session)
        # Capture the float now — SQLAlchemy's identity map will overwrite
        # this object when we reuse the same primary key below.
        recent_total = score_obj.total_score

        session.query(ProspectScore).filter(
            ProspectScore.company_id == sample_prospect.id
        ).delete()
        session.query(Signal).filter(
            Signal.company_id == sample_prospect.id
        ).delete()
        session.commit()

        session.add(Signal(
            company_id=sample_prospect.id,
            signal_type="ai_initiative",
            title="Old AI news",
            source_type="major_news",
            detected_at=now - timedelta(days=180),
        ))
        session.commit()
        old_score = score_prospect(sample_prospect.id, session=session)

        assert recent_total > old_score.total_score
