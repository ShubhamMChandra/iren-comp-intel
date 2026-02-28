"""
Tests for database models — creation, relationships, and constraints.

What we're testing:
  - Can we create each model and read its fields back?
  - Do relationships (Company -> Signals, Scores, Events) work?
  - Does the unique constraint on Company.name prevent duplicates?
  - Do default values (timestamps, booleans) get set correctly?
"""

import pytest
from datetime import datetime, timezone

from database.models import Company, Signal, ProspectScore, CompetitorEvent


# ── Company creation ──────────────────────────────────────────────


class TestCompanyModel:
    def test_create_prospect(self, sample_prospect):
        """A prospect should have company_type='prospect' and no competitor fields."""
        assert sample_prospect.id is not None
        assert sample_prospect.name == "TestCo AI"
        assert sample_prospect.company_type == "prospect"
        assert sample_prospect.capacity_mw is None  # prospect-only: no MW
        assert sample_prospect.gpu_count is None

    def test_create_competitor(self, sample_competitor):
        """A competitor should have capacity_mw, gpu_count, and ticker set."""
        assert sample_competitor.company_type == "competitor"
        assert sample_competitor.capacity_mw == 500
        assert sample_competitor.gpu_count == 50000
        assert sample_competitor.ticker == "RVCL"

    def test_default_timestamps(self, sample_prospect):
        """created_at and updated_at should be auto-populated."""
        assert sample_prospect.created_at is not None
        assert sample_prospect.updated_at is not None

    def test_unique_name_constraint(self, session, sample_prospect):
        """Adding two companies with the same name should fail."""
        duplicate = Company(
            name="TestCo AI",  # same name as sample_prospect
            company_type="prospect",
        )
        session.add(duplicate)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

    def test_repr(self, sample_prospect):
        assert "TestCo AI" in repr(sample_prospect)
        assert "prospect" in repr(sample_prospect)


# ── Relationships ─────────────────────────────────────────────────


class TestRelationships:
    def test_company_signals_relationship(self, session, sample_prospect, sample_signals):
        """company.signals should return all signals linked to that company."""
        session.refresh(sample_prospect)
        assert len(sample_prospect.signals) == 5
        assert all(s.company_id == sample_prospect.id for s in sample_prospect.signals)

    def test_signal_back_populates_company(self, sample_signals):
        """signal.company should return the parent Company object."""
        for signal in sample_signals:
            assert signal.company is not None
            assert signal.company.name == "TestCo AI"

    def test_prospect_score_relationship(self, session, sample_prospect):
        """Scores should link back to the company."""
        score = ProspectScore(
            company_id=sample_prospect.id,
            total_score=42.5,
            hiring_score=15.0,
        )
        session.add(score)
        session.commit()

        session.refresh(sample_prospect)
        assert len(sample_prospect.scores) == 1
        assert sample_prospect.scores[0].total_score == 42.5

    def test_competitor_event_relationship(self, session, sample_competitor):
        """Events should link back to the competitor company."""
        event = CompetitorEvent(
            company_id=sample_competitor.id,
            event_type="deal",
            title="RivalCloud signs $500M contract with BigCorp",
        )
        session.add(event)
        session.commit()

        session.refresh(sample_competitor)
        assert len(sample_competitor.competitor_events) == 1
        assert "BigCorp" in sample_competitor.competitor_events[0].title

    def test_cascade_delete(self, session, sample_prospect, sample_signals):
        """Deleting a company should also delete its signals (cascade)."""
        session.delete(sample_prospect)
        session.commit()

        remaining = session.query(Signal).filter(
            Signal.company_id == sample_prospect.id
        ).count()
        assert remaining == 0


# ── Signal model ──────────────────────────────────────────────────


class TestSignalModel:
    def test_signal_defaults(self, session, sample_prospect):
        """Signals should get sensible defaults for optional fields."""
        signal = Signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="Test signal",
        )
        session.add(signal)
        session.commit()

        assert signal.magnitude == 1.0
        assert signal.is_active is True
        assert signal.source_type == "industry_news"
        assert signal.detected_at is not None

    def test_signal_repr(self, sample_signals):
        sig = sample_signals[0]
        assert "fundraising" in repr(sig)
