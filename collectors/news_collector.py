"""
News collector that pulls articles from RSS feeds and Google News.

For each tracked company, it:
1. Searches RSS feeds for mentions
2. Queries Google News RSS for company-specific news
3. Stores raw articles as potential signals (AI layer classifies them later)
"""

from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from config import GOOGLE_NEWS_BASE, NEWS_RSS_FEEDS
from database.models import Company


class NewsCollector(BaseCollector):
    collector_name = "news"

    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "IrenIntel/1.0 (research platform)"
        }

    def collect(self):
        """Collect news for all tracked companies."""
        companies = self.session.query(Company).all()

        print(f"[news] Collecting news for {len(companies)} companies...")
        self._collect_rss_feeds(companies)
        self._collect_google_news(companies)
        self.finish()

    def _collect_rss_feeds(self, companies: list[Company]):
        """Pull articles from industry RSS feeds and match to companies."""
        for feed_url in NEWS_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:30]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")

                    pub_date = self._parse_date(published)
                    text = f"{title} {summary}".lower()

                    for company in companies:
                        name_lower = company.name.lower()
                        # Match on company name appearing in title or summary
                        if name_lower in text or self._fuzzy_match(name_lower, text):
                            self._create_signal(
                                company_id=company.id,
                                signal_type="ai_initiative",  # default — AI layer reclassifies
                                title=title[:500],
                                summary=summary[:1000],
                                source_url=link,
                                source_type="industry_news",
                                detected_at=pub_date,
                            )
            except Exception as e:
                print(f"[news] Error fetching {feed_url}: {e}")

    def _collect_google_news(self, companies: list[Company]):
        """Search Google News RSS for each company."""
        for company in companies:
            queries = self._build_queries(company)
            for query in queries:
                try:
                    url = GOOGLE_NEWS_BASE.format(query=quote(query))
                    feed = feedparser.parse(url)

                    for entry in feed.entries[:5]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        pub_date = self._parse_date(published)

                        self._create_signal(
                            company_id=company.id,
                            signal_type="ai_initiative",  # default — AI reclassifies
                            title=title[:500],
                            summary="",
                            source_url=link,
                            source_type="major_news",
                            detected_at=pub_date,
                        )
                except Exception as e:
                    print(f"[news] Google News error for {company.name}: {e}")

    def _build_queries(self, company: Company) -> list[str]:
        """Build search queries tailored to detect relevant signals."""
        name = company.name
        base_queries = [
            f'"{name}" GPU OR "data center" OR HPC OR "compute capacity"',
            f'"{name}" fundraising OR "Series" OR funding OR IPO',
            f'"{name}" AI infrastructure OR "model training"',
            f'"{name}" "capacity constraint" OR waitlist OR "switching provider" OR outgrowing',
        ]
        if company.company_type == "competitor":
            base_queries.append(f'"{name}" expansion OR "new facility" OR contract OR deal')
        return base_queries

    def _fuzzy_match(self, company_name: str, text: str) -> bool:
        """Basic fuzzy matching for company name variants."""
        variants = {
            "openai": ["open ai"],
            "meta platforms": ["meta", "facebook"],
            "google cloud": ["gcp", "google cloud platform"],
            "amazon web services": ["aws", "amazon cloud"],
            "coreweave": ["core weave"],
            "ai21 labs": ["ai21"],
            "weights & biases": ["wandb", "weights and biases"],
            "hugging face": ["huggingface"],
        }
        for variant in variants.get(company_name, []):
            if variant in text:
                return True
        return False

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            dt = dateparser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)
