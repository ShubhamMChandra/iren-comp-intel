"""
Tests for data collectors.

What we're testing:
  - BaseCollector: deduplication logic (_signal_exists / _create_signal)
  - FundingCollector: regex-based classification and amount extraction
  - JobsCollector: infra keyword matching
  - NewsCollector: fuzzy company name matching

We test the LOGIC without making real HTTP requests.
"""

import pytest
from datetime import datetime, timezone

from database.models import Signal
from collectors.base import BaseCollector
from collectors.funding_collector import FundingCollector
from collectors.jobs_collector import JobsCollector
from collectors.news_collector import NewsCollector


# ── BaseCollector dedup ───────────────────────────────────────────


class TestBaseCollectorDedup:
    """The base collector should prevent duplicate signals."""

    def test_create_signal_first_time(self, session, sample_prospect):
        """First signal with a given title should be created."""
        collector = BaseCollector.__new__(BaseCollector)
        collector.session = session
        collector.signals_created = 0

        result = collector._create_signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="Unique job posting",
        )
        session.commit()

        assert result is not None
        assert collector.signals_created == 1

    def test_duplicate_signal_blocked(self, session, sample_prospect):
        """Same title + company should return None (no duplicate)."""
        collector = BaseCollector.__new__(BaseCollector)
        collector.session = session
        collector.signals_created = 0

        collector._create_signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="Duplicate posting",
        )
        session.commit()

        result = collector._create_signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="Duplicate posting",
        )
        assert result is None
        assert collector.signals_created == 1  # only counted once

    def test_same_title_different_company_allowed(self, session, sample_prospect, sample_competitor):
        """Same title for different companies should both be created."""
        collector = BaseCollector.__new__(BaseCollector)
        collector.session = session
        collector.signals_created = 0

        r1 = collector._create_signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="GPU engineer needed",
        )
        r2 = collector._create_signal(
            company_id=sample_competitor.id,
            signal_type="hiring",
            title="GPU engineer needed",
        )
        session.commit()

        assert r1 is not None
        assert r2 is not None
        assert collector.signals_created == 2


# ── FundingCollector classification ───────────────────────────────


class TestFundingClassification:
    """Test the regex-based funding signal classifier."""

    @pytest.fixture()
    def classifier(self):
        """Get just the classification method without full collector init."""
        collector = FundingCollector.__new__(FundingCollector)
        return collector._classify_funding

    # Fundraising (actively raising)
    @pytest.mark.parametrize("text,expected", [
        ("company seeking series c funding", "fundraising"),
        ("startup in talks to raise $500m", "fundraising"),
        ("company looking to raise new round", "fundraising"),
        ("exploring ipo options for 2026", "fundraising"),
        ("preparing for ipo roadshow", "fundraising"),
    ])
    def test_fundraising_patterns(self, classifier, text, expected):
        assert classifier(text) == expected

    # Funding completed
    @pytest.mark.parametrize("text,expected", [
        ("startup raises $200 million in series b", "funding_completed"),
        ("company secured $1.5 billion in new funding", "funding_completed"),
        ("ai lab closes $500m series d round", "funding_completed"),
        ("valued at $10 billion after latest round", "funding_completed"),
        ("announces new debt facility for expansion", "funding_completed"),
    ])
    def test_completed_funding_patterns(self, classifier, text, expected):
        assert classifier(text) == expected

    # Not relevant
    @pytest.mark.parametrize("text", [
        "company releases new product update",
        "ceo speaks at conference",
        "quarterly earnings beat expectations",
    ])
    def test_not_funding_returns_none(self, classifier, text):
        assert classifier(text) is None


class TestAmountExtraction:
    """Test dollar amount extraction from headlines."""

    @pytest.fixture()
    def extractor(self):
        collector = FundingCollector.__new__(FundingCollector)
        return collector._extract_amount

    @pytest.mark.parametrize("text,expected", [
        ("raises $200 million", 200_000_000),
        ("secured $1.5 billion", 1_500_000_000),
        ("$50M seed round", 50_000_000),
        ("closes $3B mega-round", 3_000_000_000),
        ("$750mn facility", 750_000_000),
    ])
    def test_extracts_amounts(self, extractor, text, expected):
        result = extractor(text)
        assert result == expected

    def test_no_amount_returns_none(self, extractor):
        assert extractor("company announces new partnership") is None


# ── JobsCollector keyword matching ────────────────────────────────


class TestJobsKeywordMatching:
    """Test infra keyword matching for job titles."""

    @pytest.fixture()
    def matcher(self):
        collector = JobsCollector.__new__(JobsCollector)
        return collector._is_infra_role

    @pytest.mark.parametrize("title", [
        "senior gpu infrastructure engineer",
        "ml platform lead",
        "data center operations manager",
        "kubernetes cluster administrator",
        "distributed systems engineer",
        "site reliability engineer - hpc",
        "cuda performance engineer",
        "nvidia gpu cluster architect",
    ])
    def test_infra_roles_matched(self, matcher, title):
        assert matcher(title) is True

    @pytest.mark.parametrize("title", [
        "marketing manager",
        "senior accountant",
        "product designer",
        "hr business partner",
        "legal counsel",
    ])
    def test_non_infra_roles_rejected(self, matcher, title):
        assert matcher(title) is False


# ── NewsCollector fuzzy matching ──────────────────────────────────


class TestNewsFuzzyMatch:
    """Test company name variant matching."""

    @pytest.fixture()
    def matcher(self):
        collector = NewsCollector.__new__(NewsCollector)
        return collector._fuzzy_match

    @pytest.mark.parametrize("company,text", [
        ("openai", "open ai releases gpt-5"),
        ("meta platforms", "meta announces new ai model"),
        ("meta platforms", "facebook rebrands ai division"),
        ("amazon web services", "aws launches new gpu instances"),
        ("google cloud", "gcp expands ai offerings"),
        ("weights & biases", "wandb raises series c"),
        ("hugging face", "huggingface open-sources new model"),
    ])
    def test_fuzzy_matches(self, matcher, company, text):
        assert matcher(company, text) is True

    def test_no_match_for_unknown_company(self, matcher):
        assert matcher("some random company", "article about anything") is False
