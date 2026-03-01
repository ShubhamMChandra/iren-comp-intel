"""
Job posting collector that detects infrastructure hiring signals.

Searches for GPU, ML infrastructure, data center, and platform engineering
roles at tracked prospect companies. Each relevant posting contributes to
the hiring score.

Uses Google search via RSS to find job postings on common ATS platforms
(Greenhouse, Lever, Workday, LinkedIn).
"""

from datetime import datetime, timezone
from urllib.parse import quote

import time

import feedparser
import requests

from collectors.base import BaseCollector
from database.models import Company, ProspectScore

_REQUEST_TIMEOUT = 8
_SLEEP_BETWEEN = 0.4
_COMPANY_LIMIT = 80


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT, headers={
            "User-Agent": "IrenIntel/1.0 (research platform)"
        })
        resp.raise_for_status()
        return feedparser.parse(resp.text)
    except Exception:
        return feedparser.FeedParserDict()

INFRA_KEYWORDS = [
    "gpu",
    "cuda",
    "ml infrastructure",
    "machine learning infrastructure",
    "ai infrastructure",
    "data center",
    "datacenter",
    "hpc",
    "high performance computing",
    "platform engineer",
    "infrastructure engineer",
    "cloud infrastructure",
    "compute",
    "kubernetes",
    "gpu cluster",
    "distributed systems",
    "ml platform",
    "training infrastructure",
    "inference infrastructure",
    "site reliability",
    "sre",
    "devops",
    "mlops",
    "ml engineer",
    "machine learning engineer",
    "research scientist",
    "research engineer",
    "applied scientist",
    "nvidia",
    "nccl",
    "infiniband",
]

GOOGLE_NEWS_JOBS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class JobsCollector(BaseCollector):
    collector_name = "jobs"

    def collect(self):
        """Collect job posting signals for top prospects by score."""
        # Prioritise scored prospects so we focus budget on likely buyers
        scored = (
            self.session.query(Company, ProspectScore.total_score)
            .join(ProspectScore, ProspectScore.company_id == Company.id)
            .filter(Company.company_type == "prospect")
            .order_by(ProspectScore.total_score.desc())
            .limit(_COMPANY_LIMIT)
            .all()
        )
        prospects = [c for c, _ in scored] if scored else (
            self.session.query(Company)
            .filter(Company.company_type == "prospect")
            .limit(_COMPANY_LIMIT)
            .all()
        )

        print(f"[jobs] Scanning job postings for {len(prospects)} prospects...")

        for company in prospects:
            self._search_jobs(company)
            time.sleep(_SLEEP_BETWEEN)

        self.finish()

    def _search_jobs(self, company: Company):
        """Search for infrastructure-related job postings at a company."""
        query = f'"{company.name}" hiring OR jobs "GPU" OR "infrastructure" OR "data center" OR "ML engineer" OR "SRE" OR "MLOps"'

        try:
            url = GOOGLE_NEWS_JOBS.format(query=quote(query))
            feed = _fetch_feed(url)

            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                title_lower = title.lower()

                if self._is_infra_role(title_lower):
                    self._create_signal(
                        company_id=company.id,
                        signal_type="hiring",
                        title=f"[Hiring] {title[:480]}",
                        summary=f"Infrastructure/GPU-related job posting detected for {company.name}.",
                        source_url=link,
                        source_type="industry_news",
                        magnitude=1.0,
                    )
        except Exception as e:
            print(f"[jobs] Error searching jobs for {company.name}: {e}")

    def _is_infra_role(self, title_lower: str) -> bool:
        """Check if a job title contains infrastructure-related keywords."""
        return any(kw in title_lower for kw in INFRA_KEYWORDS)
