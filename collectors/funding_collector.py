"""
Funding collector that detects fundraising and completed funding signals.

Two distinct signal types:
- fundraising: company is actively raising (rumors, "seeking Series X", "in talks")
- funding_completed: company closed a round (announced raise, SEC filing)

Sources: Google News RSS targeted queries, SEC filings (handled by sec_collector).
"""

from datetime import datetime, timezone
from urllib.parse import quote
import re

import feedparser
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from database.models import Company

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

FUNDRAISING_PATTERNS = [
    r"seeking\s+(series|funding|investment|capital)",
    r"in\s+talks?\s+(to|for)\s+rais",
    r"looking\s+to\s+raise",
    r"fundrais",
    r"exploring.*ipo",
    r"plans?\s+to\s+go\s+public",
    r"considering.*offering",
    r"preparing.*ipo",
    r"roadshow",
]

COMPLETED_FUNDING_PATTERNS = [
    r"raises?\s+\$[\d,.]+\s*(million|billion|m|b|mn|bn)",
    r"raised\s+\$[\d,.]+",
    r"secures?\s+\$[\d,.]+",
    r"secured\s+\$[\d,.]+",
    r"closes?\s+\$[\d,.]+.*round",
    r"closed\s+\$[\d,.]+",
    r"series\s+[a-g]\s+(round|funding)",
    r"funding\s+round",
    r"venture\s+capital",
    r"valued\s+at\s+\$[\d,.]+",
    r"debt\s+facility",
    r"credit\s+facility",
]

AMOUNT_PATTERN = re.compile(
    r"\$\s*([\d,.]+)\s*(million|billion|m|b|mn|bn|M|B|MM|BB)", re.IGNORECASE
)


class FundingCollector(BaseCollector):
    collector_name = "funding"

    def collect(self):
        """Collect funding signals for prospect companies."""
        prospects = (
            self.session.query(Company)
            .filter(Company.company_type == "prospect")
            .all()
        )

        print(f"[funding] Scanning funding news for {len(prospects)} prospects...")

        for company in prospects:
            self._search_funding_news(company)

        self.finish()

    def _search_funding_news(self, company: Company):
        """Search Google News for funding-related articles about a company."""
        queries = [
            f'"{company.name}" funding OR raise OR raised OR Series OR IPO',
            f'"{company.name}" investors OR valuation OR fundraising',
        ]

        for query in queries:
            try:
                url = GOOGLE_NEWS_RSS.format(query=quote(query))
                feed = feedparser.parse(url)

                for entry in feed.entries[:8]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    pub_date = self._parse_date(published)

                    title_lower = title.lower()
                    signal_type = self._classify_funding(title_lower)

                    if signal_type:
                        amount = self._extract_amount(title)
                        self._create_signal(
                            company_id=company.id,
                            signal_type=signal_type,
                            title=title[:500],
                            summary=f"Funding signal detected for {company.name}.",
                            source_url=link,
                            source_type="major_news",
                            magnitude=amount or 1.0,
                            is_active=(signal_type == "fundraising"),
                            detected_at=pub_date,
                        )
            except Exception as e:
                print(f"[funding] Error for {company.name}: {e}")

    def _classify_funding(self, text: str) -> str | None:
        """Classify text as fundraising, funding_completed, or None."""
        for pattern in FUNDRAISING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "fundraising"

        for pattern in COMPLETED_FUNDING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "funding_completed"

        return None

    def _extract_amount(self, text: str) -> float | None:
        """Extract a dollar amount from text, normalized to raw dollars."""
        match = AMOUNT_PATTERN.search(text)
        if not match:
            return None

        number = float(match.group(1).replace(",", ""))
        unit = match.group(2).lower()

        if unit in ("billion", "b", "bn", "bb"):
            return number * 1_000_000_000
        elif unit in ("million", "m", "mn", "mm"):
            return number * 1_000_000
        return number

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
