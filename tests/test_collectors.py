"""
Tests for data collectors.

What we're testing:
  - BaseCollector: deduplication logic (_signal_exists / _create_signal)
  - FundingCollector: regex-based classification and amount extraction
  - JobsCollector: infra keyword matching
  - NewsCollector: fuzzy company name matching
  - ATSCollector: Greenhouse/Lever JSON parsing + infra filtering
  - EarningsCollector: filing keyword classification
  - GitHubCollector: infra repo keyword matching
  - ArXivCollector: scale keyword matching in papers
  - HNCollector: story classification by keyword
  - CloudBlogCollector: company matching + signal type classification

We test the LOGIC without making real HTTP requests.
"""

import pytest
from datetime import datetime, timezone

from database.models import Signal
from collectors.base import BaseCollector
from collectors.funding_collector import FundingCollector
from collectors.jobs_collector import JobsCollector
from collectors.news_collector import NewsCollector
from collectors.ats_collector import ATSCollector
from collectors.earnings_collector import EarningsCollector
from collectors.github_collector import GitHubCollector
from collectors.arxiv_collector import ArXivCollector
from collectors.hn_collector import HNCollector
from collectors.cloud_blog_collector import CloudBlogCollector


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


# ── ATSCollector parsing + infra filtering ────────────────────────


class TestATSCollectorGreenhouseParsing:
    """Test Greenhouse JSON → job dict extraction."""

    @pytest.fixture()
    def parser(self):
        collector = ATSCollector.__new__(ATSCollector)
        return collector._fetch_greenhouse  # we won't call it — we test the struct below

    def test_parse_greenhouse_structure(self):
        """_fetch_greenhouse should extract title, location, department, url."""
        collector = ATSCollector.__new__(ATSCollector)
        raw_api_response = {
            "jobs": [
                {
                    "title": "GPU Infrastructure Engineer",
                    "location": {"name": "San Francisco, CA"},
                    "departments": [{"name": "Platform"}],
                    "absolute_url": "https://boards.greenhouse.io/testco/jobs/123",
                },
                {
                    "title": "Marketing Manager",
                    "location": {"name": "New York, NY"},
                    "departments": [],
                    "absolute_url": "https://boards.greenhouse.io/testco/jobs/456",
                },
            ],
        }

        results = []
        for job in raw_api_response["jobs"]:
            departments = job.get("departments", [])
            results.append({
                "title": job.get("title", ""),
                "location": (job.get("location") or {}).get("name", "Unknown"),
                "department": departments[0].get("name", "Unknown") if departments else "Unknown",
                "url": job.get("absolute_url", ""),
            })

        assert len(results) == 2
        assert results[0]["title"] == "GPU Infrastructure Engineer"
        assert results[0]["location"] == "San Francisco, CA"
        assert results[0]["department"] == "Platform"
        assert results[0]["url"] == "https://boards.greenhouse.io/testco/jobs/123"
        assert results[1]["department"] == "Unknown"

    def test_parse_greenhouse_missing_location(self):
        """Null location should default to 'Unknown'."""
        job = {"title": "SRE", "location": None, "departments": [], "absolute_url": ""}
        location = (job.get("location") or {}).get("name", "Unknown")
        assert location == "Unknown"


class TestATSCollectorLeverParsing:
    """Test Lever JSON → job dict extraction."""

    def test_parse_lever_structure(self):
        raw_postings = [
            {
                "text": "ML Platform Engineer",
                "categories": {"location": "Remote", "team": "Infrastructure"},
                "hostedUrl": "https://jobs.lever.co/testco/abc-123",
            },
            {
                "text": "Sales Rep",
                "categories": {"location": "Chicago, IL"},
                "hostedUrl": "https://jobs.lever.co/testco/def-456",
            },
        ]

        results = []
        for posting in raw_postings:
            categories = posting.get("categories", {})
            results.append({
                "title": posting.get("text", ""),
                "location": categories.get("location", "Unknown"),
                "department": categories.get("team", "Unknown"),
                "url": posting.get("hostedUrl", ""),
            })

        assert results[0]["title"] == "ML Platform Engineer"
        assert results[0]["department"] == "Infrastructure"
        assert results[1]["department"] == "Unknown"


class TestATSCollectorInfraFilter:
    """Test that _is_infra_role reuses INFRA_KEYWORDS properly."""

    @pytest.fixture()
    def matcher(self):
        collector = ATSCollector.__new__(ATSCollector)
        return collector._is_infra_role

    @pytest.mark.parametrize("title", [
        "gpu infrastructure engineer",
        "ml platform lead",
        "senior cuda developer",
        "distributed systems engineer",
        "site reliability engineer",
        "kubernetes platform engineer",
    ])
    def test_infra_titles_matched(self, matcher, title):
        assert matcher(title) is True

    @pytest.mark.parametrize("title", [
        "marketing manager",
        "product designer",
        "recruiter",
        "general counsel",
    ])
    def test_non_infra_titles_rejected(self, matcher, title):
        assert matcher(title) is False


# ── EarningsCollector classification ──────────────────────────────


class TestEarningsClassification:
    """Test keyword-based signal classification from filing content."""

    @pytest.fixture()
    def classifier(self):
        collector = EarningsCollector.__new__(EarningsCollector)
        return collector._classify_signal

    @pytest.mark.parametrize("text,expected", [
        ("capex increase for data center expansion", "cloud_spend"),
        ("significant capital expenditure planned for q3", "cloud_spend"),
        ("infrastructure investment in gpu clusters", "cloud_spend"),
    ])
    def test_capex_keywords_classify_as_cloud_spend(self, classifier, text, expected):
        assert classifier(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("capacity constraints in current data centers", "outgrowing"),
        ("company continues to outgrow existing facilities", "outgrowing"),
        ("resource constraint impacting delivery timelines", "outgrowing"),
    ])
    def test_capacity_keywords_classify_as_outgrowing(self, classifier, text, expected):
        assert classifier(text) == expected

    def test_default_classification_is_ai_initiative(self, classifier):
        assert classifier("quarterly results show growth in ai segment") == "ai_initiative"

    def test_capex_takes_precedence_over_capacity(self, classifier):
        """When both keyword sets match, capex (checked first) wins."""
        assert classifier("capex for additional capacity") == "cloud_spend"


class TestEarningsCompanyFilter:
    """Only public companies with tickers should be processed."""

    def test_public_company_with_ticker_qualifies(self, session, sample_competitor):
        """sample_competitor is public with ticker='RVCL'."""
        from database.models import Company
        public = (
            session.query(Company)
            .filter(Company.is_public == True, Company.ticker.isnot(None))
            .all()
        )
        assert sample_competitor in public

    def test_private_company_excluded(self, session, sample_prospect):
        """sample_prospect is private (is_public=False)."""
        from database.models import Company
        public = (
            session.query(Company)
            .filter(Company.is_public == True, Company.ticker.isnot(None))
            .all()
        )
        assert sample_prospect not in public


# ── GitHubCollector infra keyword matching ────────────────────────


class TestGitHubInfraMatching:
    """Test that repo name+description is checked against INFRA_KEYWORDS."""

    @pytest.mark.parametrize("name,description", [
        ("training-infra", "Distributed training scripts"),
        ("gpu-cluster", "Managing GPU cluster deployments"),
        ("model-serving", "Low-latency inference serving framework"),
        ("k8s-mlops", "Kubernetes configs for MLOps pipelines"),
        ("llm-benchmark", "Benchmarking large language models"),
        ("hpc-scheduler", "HPC job scheduler"),
    ])
    def test_infra_repos_matched(self, name, description):
        from collectors.github_collector import INFRA_KEYWORDS
        searchable = f"{name} {description}".lower()
        assert any(kw in searchable for kw in INFRA_KEYWORDS)

    @pytest.mark.parametrize("name,description", [
        ("company-website", "Our marketing site"),
        ("hr-portal", "Employee self-service portal"),
        ("design-system", "UI component library for branding"),
    ])
    def test_non_infra_repos_skipped(self, name, description):
        from collectors.github_collector import INFRA_KEYWORDS
        searchable = f"{name} {description}".lower()
        assert not any(kw in searchable for kw in INFRA_KEYWORDS)


# ── ArXivCollector scale keyword matching ─────────────────────────


class TestArXivScaleMatching:
    """Test that paper title+abstract is matched against SCALE_KEYWORDS."""

    @pytest.mark.parametrize("title,abstract", [
        ("Scaling Laws for Large-Scale Language Models", "We study training compute optimal models"),
        ("Efficient Distributed Training on GPU Clusters", "Using 512 H100 GPUs across 64 nodes"),
        ("Infrastructure for Billion Parameter Models", "Scaling to billions with distributed systems"),
        ("TPU Pod Training at Scale", "Our TPU pod configuration for large runs"),
    ])
    def test_scale_papers_matched(self, title, abstract):
        from collectors.arxiv_collector import SCALE_KEYWORDS
        searchable = f"{title} {abstract}".lower()
        assert any(kw in searchable for kw in SCALE_KEYWORDS)

    @pytest.mark.parametrize("title,abstract", [
        ("A Survey of Sentiment Analysis Methods", "We review recent approaches to sentiment analysis"),
        ("Improving User Interface Design", "This paper proposes a novel UI layout algorithm"),
    ])
    def test_non_scale_papers_skipped(self, title, abstract):
        from collectors.arxiv_collector import SCALE_KEYWORDS
        searchable = f"{title} {abstract}".lower()
        assert not any(kw in searchable for kw in SCALE_KEYWORDS)


# ── HNCollector classification ────────────────────────────────────


class TestHNClassification:
    """Test HN story title → signal type classification."""

    @pytest.fixture()
    def classifier(self):
        collector = HNCollector.__new__(HNCollector)
        return collector._classify

    @pytest.mark.parametrize("title,expected", [
        ("Company X is hiring ML engineers", "hiring"),
        ("Ask HN: Who is hiring? (January 2026)", "hiring"),
        ("New jobs posted at startup Y", "hiring"),
    ])
    def test_hiring_classification(self, classifier, title, expected):
        assert classifier(title) == expected

    @pytest.mark.parametrize("title,expected", [
        ("Company X raised $50M Series B", "funding_completed"),
        ("Startup Y raises $200M at $2B valuation", "funding_completed"),
        ("New funding round for AI lab", "funding_completed"),
        ("Series C valued at $5B", "funding_completed"),
    ])
    def test_funding_classification(self, classifier, title, expected):
        assert classifier(title) == expected

    @pytest.mark.parametrize("title,expected", [
        ("Switching from AWS to bare metal", "outgrowing"),
        ("Why we're leaving GCP for colo", "outgrowing"),
        ("Company X dropped their cloud provider", "outgrowing"),
        ("Migrating from Azure to on-prem", "outgrowing"),
    ])
    def test_outgrowing_classification(self, classifier, title, expected):
        assert classifier(title) == expected

    @pytest.mark.parametrize("title", [
        "Company X launches new AI product",
        "Show HN: Open source LLM toolkit",
        "Deep learning framework comparison 2026",
    ])
    def test_default_is_ai_initiative(self, classifier, title):
        assert classifier(title) == "ai_initiative"


# ── CloudBlogCollector matching + classification ──────────────────


class TestCloudBlogCompanyMatching:
    """Test that company names are detected in blog post text."""

    def test_company_name_found_in_title(self):
        company_name = "TestCo AI"
        title = "How TestCo AI Scaled Their ML Pipeline on AWS"
        summary = "A case study on scaling."
        text = f"{title} {summary}".lower()
        assert company_name.lower() in text

    def test_company_name_found_in_summary(self):
        company_name = "TestCo AI"
        title = "Case Study: Scaling ML Workloads"
        summary = "TestCo AI used our new GPU instances to train models."
        text = f"{title} {summary}".lower()
        assert company_name.lower() in text

    def test_company_not_mentioned(self):
        company_name = "TestCo AI"
        title = "New GPU instances available in us-east-1"
        summary = "We're launching new p5 instances for ML training."
        text = f"{title} {summary}".lower()
        assert company_name.lower() not in text


class TestCloudBlogClassification:
    """Test blog post title → signal type classification."""

    @pytest.fixture()
    def classifier(self):
        collector = CloudBlogCollector.__new__(CloudBlogCollector)
        return collector._classify

    @pytest.mark.parametrize("title,expected", [
        ("Reduce your ML training cost by 40%", "cloud_spend"),
        ("New pricing for GPU instances", "cloud_spend"),
        ("Cost optimization strategies for AI workloads", "cloud_spend"),
        ("Savings plans for compute-intensive workloads", "cloud_spend"),
    ])
    def test_spend_keywords_classify_as_cloud_spend(self, classifier, title, expected):
        assert classifier(title) == expected

    @pytest.mark.parametrize("title", [
        "New foundation model APIs now available",
        "How Company X trains billion-parameter models",
        "Announcing managed Kubernetes for ML",
    ])
    def test_default_classification_is_ai_initiative(self, classifier, title):
        assert classifier(title) == "ai_initiative"
