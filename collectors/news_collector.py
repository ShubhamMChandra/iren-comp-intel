"""
News collector that pulls articles from RSS feeds and Google News.

For each tracked company, it:
1. Searches RSS feeds for mentions
2. Queries Google News RSS for company-specific news
3. Stores raw articles as potential signals (AI layer classifies them later)

Rate-limiting: Google News RSS blocks datacenter IPs aggressively.
We cap queries per run and sleep between requests.
"""

import time
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from config import GOOGLE_NEWS_BASE, NEWS_RSS_FEEDS
from database.models import Company, ProspectScore

# Max companies to query Google News for per run (by score rank)
_GOOGLE_NEWS_COMPANY_LIMIT = 80
# Seconds to sleep between Google News requests to avoid rate-limiting
_GOOGLE_NEWS_SLEEP = 0.5
# HTTP request timeout in seconds
_REQUEST_TIMEOUT = 8


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    """Fetch an RSS feed with a timeout so a stalled feed doesn't block collection."""
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT, headers={
            "User-Agent": "IrenIntel/1.0 (research platform)"
        })
        resp.raise_for_status()
        return feedparser.parse(resp.text)
    except Exception:
        return feedparser.FeedParserDict()


class NewsCollector(BaseCollector):
    collector_name = "news"

    def collect(self):
        """Collect news for tracked companies."""
        companies = self.session.query(Company).all()
        print(f"[news] Collecting news for {len(companies)} companies (RSS feeds first)...")
        self._collect_rss_feeds(companies)

        # For Google News: rank prospects by score and cap at limit
        top_prospects = self._top_prospects(_GOOGLE_NEWS_COMPANY_LIMIT)
        print(f"[news] Querying Google News for top {len(top_prospects)} prospects...")
        self._collect_google_news(top_prospects)
        self.finish()

    def _top_prospects(self, limit: int) -> list[Company]:
        """Return top prospects by latest score, falling back to all if no scores."""
        scored = (
            self.session.query(Company, ProspectScore.total_score)
            .join(ProspectScore, ProspectScore.company_id == Company.id)
            .filter(Company.company_type == "prospect")
            .order_by(ProspectScore.total_score.desc())
            .limit(limit)
            .all()
        )
        if scored:
            return [c for c, _ in scored]
        # Fallback: just take first N prospects
        return (
            self.session.query(Company)
            .filter(Company.company_type == "prospect")
            .limit(limit)
            .all()
        )

    def _collect_rss_feeds(self, companies: list[Company]):
        """Pull articles from industry RSS feeds and match to companies."""
        for feed_url in NEWS_RSS_FEEDS:
            try:
                feed = _fetch_feed(feed_url)
                matched = 0
                for entry in feed.entries[:30]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")

                    pub_date = self._parse_date(published)
                    text = f"{title} {summary}".lower()

                    for company in companies:
                        name_lower = company.name.lower()
                        if name_lower in text or self._fuzzy_match(name_lower, text):
                            self._create_signal(
                                company_id=company.id,
                                signal_type="ai_initiative",
                                title=title[:500],
                                summary=summary[:1000],
                                source_url=link,
                                source_type="industry_news",
                                detected_at=pub_date,
                            )
                            matched += 1
                print(f"[news] RSS {feed_url.split('/')[2]}: {len(feed.entries)} entries, {matched} matched")
            except Exception as e:
                print(f"[news] Error fetching {feed_url}: {e}")

    def _collect_google_news(self, companies: list[Company]):
        """Search Google News RSS for each company with rate limiting."""
        for i, company in enumerate(companies):
            queries = self._build_queries(company)
            company_signals = 0
            for query in queries:
                try:
                    url = GOOGLE_NEWS_BASE.format(query=quote(query))
                    feed = _fetch_feed(url)

                    for entry in feed.entries[:5]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        pub_date = self._parse_date(published)

                        sig = self._create_signal(
                            company_id=company.id,
                            signal_type="ai_initiative",
                            title=title[:500],
                            summary="",
                            source_url=link,
                            source_type="major_news",
                            detected_at=pub_date,
                        )
                        if sig:
                            company_signals += 1
                    time.sleep(_GOOGLE_NEWS_SLEEP)
                except Exception as e:
                    print(f"[news] Google News error for {company.name}: {e}")

            if company_signals > 0:
                print(f"[news] {company.name}: +{company_signals} signals ({i+1}/{len(companies)})")

    def _build_queries(self, company: Company) -> list[str]:
        """Build search queries tailored to detect relevant signals."""
        name = company.name
        return [
            f'"{name}" GPU OR "data center" OR HPC OR "compute capacity"',
            f'"{name}" fundraising OR "Series" OR funding OR IPO',
            f'"{name}" AI infrastructure OR "model training"',
            f'"{name}" "capacity constraint" OR waitlist OR outgrowing',
        ]

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
