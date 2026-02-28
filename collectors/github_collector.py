# Why: Detects AI/infra scaling via GitHub org activity
# Deps: BaseCollector, requests, Company model
# How: GitHub REST API for recent repo pushes and infra keywords

import time
from datetime import datetime, timedelta, timezone

import requests
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from config import GITHUB_TOKEN
from database.models import Company

INFRA_KEYWORDS = [
    "training", "inference", "gpu", "cluster", "mlops", "distributed",
    "llm", "model", "serving", "deploy", "kubernetes", "infrastructure",
    "hpc", "cuda", "nccl",
]


class GitHubCollector(BaseCollector):
    collector_name = "github"

    def __init__(self):
        super().__init__()
        self.headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    def collect(self) -> None:
        companies = (
            self.session.query(Company)
            .filter(Company.github_org.isnot(None))
            .all()
        )
        print(f"[github] Scanning {len(companies)} companies with GitHub orgs...")

        for company in companies:
            try:
                self._collect_for_company(company)
            except Exception as e:
                print(f"[github] Error for {company.name}: {e}")
            time.sleep(2)

        self.finish()

    def _collect_for_company(self, company: Company) -> None:
        url = f"https://api.github.com/orgs/{company.github_org}/repos"
        resp = requests.get(
            url,
            headers=self.headers,
            params={"sort": "pushed", "per_page": 10},
            timeout=15,
        )
        resp.raise_for_status()

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        for repo in resp.json():
            try:
                name = repo.get("name", "")
                description = repo.get("description") or ""
                pushed_at_str = repo.get("pushed_at", "")
                searchable = f"{name} {description}".lower()

                if not any(kw in searchable for kw in INFRA_KEYWORDS):
                    continue

                pushed_at = self._parse_gh_date(pushed_at_str)
                if pushed_at < cutoff:
                    continue

                stars = repo.get("stargazers_count", 0)
                self._create_signal(
                    company_id=company.id,
                    signal_type="ai_initiative",
                    title=f"[GitHub] {company.name}/{name}: {description[:200]}",
                    summary=f"Active infrastructure repo at {company.name}. {stars} stars, last pushed {pushed_at_str}.",
                    source_url=repo.get("html_url", ""),
                    source_type="blog",
                    magnitude=1.0,
                )
            except Exception as e:
                print(f"[github] Error processing repo {repo.get('name', '?')}: {e}")

    def _parse_gh_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            dt = dateparser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=timezone.utc)
