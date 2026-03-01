# Why: Catches hiring, funding, and outgrowing signals from HN
# Deps: BaseCollector, requests, Company model
# How: HN Algolia search API for company mentions in stories

import time
from datetime import datetime, timedelta, timezone

import requests

from collectors.base import BaseCollector
from database.models import Company

HIRING_KEYWORDS = ["hiring", "jobs", "who is hiring"]
FUNDING_COMPLETED_KEYWORDS = ["raised", "raises", "secured", "closed", "valued at"]
FUNDRAISING_KEYWORDS = ["seeking", "in talks", "exploring ipo", "fundrais", "looking to raise"]
OUTGROWING_KEYWORDS = ["outgrew", "switching", "migrating from", "leaving", "dropped",
                       "waitlist", "oversubscribed", "capacity"]


class HNCollector(BaseCollector):
    collector_name = "hn"

    def collect(self) -> None:
        companies = self.session.query(Company).all()
        print(f"[hn] Scanning Hacker News for {len(companies)} companies...")

        for company in companies:
            try:
                self._collect_for_company(company)
            except Exception as e:
                print(f"[hn] Error for {company.name}: {e}")
            time.sleep(1)

        self.finish()

    def _collect_for_company(self, company: Company) -> None:
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        url = "https://hn.algolia.com/api/v1/search"
        resp = requests.get(
            url,
            params={
                "query": f'"{company.name}"',
                "tags": "story",
                "numericFilters": f"created_at_i>{cutoff}",
            },
            timeout=15,
        )
        resp.raise_for_status()

        hits = resp.json().get("hits", [])
        hits.sort(key=lambda h: h.get("points", 0), reverse=True)

        for hit in hits[:5]:
            try:
                title = hit.get("title", "")
                points = hit.get("points", 0)
                num_comments = hit.get("num_comments", 0)
                object_id = hit.get("objectID", "")
                story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"

                signal_type = self._classify(title)

                self._create_signal(
                    company_id=company.id,
                    signal_type=signal_type,
                    title=f"[HN] {title[:400]}",
                    summary=f"Discussed on Hacker News ({points} points, {num_comments} comments).",
                    source_url=story_url,
                    source_type="social_media",
                    magnitude=1.0,
                )
            except Exception as e:
                print(f"[hn] Error processing story '{hit.get('title', '?')[:60]}': {e}")

    def _classify(self, title: str) -> str:
        lower = title.lower()
        if any(kw in lower for kw in HIRING_KEYWORDS):
            return "hiring"
        if any(kw in lower for kw in FUNDRAISING_KEYWORDS):
            return "fundraising"
        if any(kw in lower for kw in FUNDING_COMPLETED_KEYWORDS):
            return "funding_completed"
        if any(kw in lower for kw in OUTGROWING_KEYWORDS):
            return "outgrowing"
        return "ai_initiative"
