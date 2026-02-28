# Why: Direct job postings from ATS for hiring signals
# Deps: BaseCollector, requests, Company model
# How: Greenhouse/Lever public JSON APIs filtered by infra keywords

import time

import requests

from collectors.base import BaseCollector
from collectors.jobs_collector import INFRA_KEYWORDS
from database.models import Company


GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
LEVER_API = "https://api.lever.co/v0/postings/{slug}?mode=json"


class ATSCollector(BaseCollector):
    collector_name = "ats"

    def collect(self) -> None:
        """Collect hiring signals from Greenhouse and Lever job boards."""
        companies = (
            self.session.query(Company)
            .filter(Company.ats_board.isnot(None))
            .all()
        )

        print(f"[ats] Scanning ATS boards for {len(companies)} companies...")

        for company in companies:
            try:
                self._collect_company(company)
            except Exception as e:
                print(f"[ats] Error processing {company.name}: {e}")
            time.sleep(1)

        self.finish()

    def _collect_company(self, company: Company) -> None:
        """Fetch and filter job postings for a single company."""
        parts = company.ats_board.split(":", 1)
        if len(parts) != 2:
            print(f"[ats] Invalid ats_board format for {company.name}: {company.ats_board}")
            return

        platform, slug = parts

        if platform == "greenhouse":
            jobs = self._fetch_greenhouse(slug)
        elif platform == "lever":
            jobs = self._fetch_lever(slug)
        else:
            print(f"[ats] Unknown ATS platform '{platform}' for {company.name}")
            return

        for job in jobs:
            title_lower = job["title"].lower()
            if self._is_infra_role(title_lower):
                self._create_signal(
                    company_id=company.id,
                    signal_type="hiring",
                    title=f"[Hiring] {job['title']}"[:480],
                    summary=f"{job['department']} role in {job['location']} at {company.name}. Direct from {platform} job board.",
                    source_url=job["url"],
                    source_type="industry_news",
                    magnitude=1.0,
                )

    def _fetch_greenhouse(self, slug: str) -> list[dict]:
        """Fetch job listings from Greenhouse public API."""
        resp = requests.get(GREENHOUSE_API.format(slug=slug), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for job in data.get("jobs", []):
            departments = job.get("departments", [])
            results.append({
                "title": job.get("title", ""),
                "location": (job.get("location") or {}).get("name", "Unknown"),
                "department": departments[0].get("name", "Unknown") if departments else "Unknown",
                "url": job.get("absolute_url", ""),
            })
        return results

    def _fetch_lever(self, slug: str) -> list[dict]:
        """Fetch job listings from Lever public API."""
        resp = requests.get(LEVER_API.format(slug=slug), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for posting in data:
            categories = posting.get("categories", {})
            results.append({
                "title": posting.get("text", ""),
                "location": categories.get("location", "Unknown"),
                "department": categories.get("team", "Unknown"),
                "url": posting.get("hostedUrl", ""),
            })
        return results

    def _is_infra_role(self, title_lower: str) -> bool:
        """Check if a job title matches infrastructure keywords."""
        return any(kw in title_lower for kw in INFRA_KEYWORDS)
