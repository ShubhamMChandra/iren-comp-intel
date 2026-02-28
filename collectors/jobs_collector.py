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

import feedparser

from collectors.base import BaseCollector
from database.models import Company

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
    "devops",
    "nvidia",
    "nccl",
    "infiniband",
]

GOOGLE_NEWS_JOBS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class JobsCollector(BaseCollector):
    collector_name = "jobs"

    def collect(self):
        """Collect job posting signals for prospect companies."""
        prospects = (
            self.session.query(Company)
            .filter(Company.company_type == "prospect")
            .all()
        )

        print(f"[jobs] Scanning job postings for {len(prospects)} prospects...")

        for company in prospects:
            self._search_jobs(company)

        self.finish()

    def _search_jobs(self, company: Company):
        """Search for infrastructure-related job postings at a company."""
        query = f'"{company.name}" hiring OR jobs "GPU" OR "infrastructure" OR "data center" OR "ML platform"'

        try:
            url = GOOGLE_NEWS_JOBS.format(query=quote(query))
            feed = feedparser.parse(url)

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
