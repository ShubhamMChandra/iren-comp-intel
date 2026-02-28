"""
Shared test fixtures.

Key concept: A "fixture" is pytest's way of providing reusable setup/teardown
to tests.  When a test function has a parameter named `session` or `sample_company`,
pytest looks here, runs the matching fixture, and passes the result in.

We use an IN-MEMORY SQLite database so tests are fast, isolated, and never
touch your real data/iren_intel.db file.
"""

import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Company, Signal, ProspectScore, CompetitorEvent


@pytest.fixture()
def engine():
    """Create a fresh in-memory SQLite database for each test."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    """Provide a DB session that rolls back after every test (clean slate)."""
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture()
def sample_prospect(session):
    """Insert and return a single prospect company."""
    company = Company(
        name="TestCo AI",
        company_type="prospect",
        industry="AI Research",
        website="https://testco.ai",
        description="A test AI company.",
        hq_location="San Francisco, CA",
        employee_count=500,
        is_public=False,
        total_funding=100_000_000,
    )
    session.add(company)
    session.commit()
    return company


@pytest.fixture()
def sample_competitor(session):
    """Insert and return a single competitor company."""
    company = Company(
        name="RivalCloud",
        company_type="competitor",
        industry="GPU Cloud",
        website="https://rivalcloud.com",
        description="A competing GPU cloud provider.",
        hq_location="Austin, TX",
        is_public=True,
        ticker="RVCL",
        capacity_mw=500,
        gpu_count=50000,
    )
    session.add(company)
    session.commit()
    return company


@pytest.fixture()
def sample_signals(session, sample_prospect):
    """Insert a handful of signals for the sample prospect and return them."""
    now = datetime.now(timezone.utc)
    signals = [
        Signal(
            company_id=sample_prospect.id,
            signal_type="fundraising",
            title="TestCo AI reportedly seeking $200M Series C",
            source_type="major_news",
            magnitude=200_000_000,
            detected_at=now - timedelta(days=5),
        ),
        Signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="[Hiring] GPU Infrastructure Engineer at TestCo AI",
            source_type="industry_news",
            magnitude=1.0,
            detected_at=now - timedelta(days=10),
        ),
        Signal(
            company_id=sample_prospect.id,
            signal_type="ai_initiative",
            title="TestCo AI launches new foundation model training cluster",
            source_type="major_news",
            magnitude=1.0,
            detected_at=now - timedelta(days=3),
        ),
        Signal(
            company_id=sample_prospect.id,
            signal_type="funding_completed",
            title="TestCo AI raises $100M in Series B",
            source_type="major_news",
            magnitude=100_000_000,
            detected_at=now - timedelta(days=60),
        ),
        Signal(
            company_id=sample_prospect.id,
            signal_type="hiring",
            title="[Hiring] ML Platform Lead at TestCo AI",
            source_type="industry_news",
            magnitude=1.0,
            detected_at=now - timedelta(days=2),
        ),
    ]
    session.add_all(signals)
    session.commit()
    return signals
