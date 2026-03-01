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
    r"pre.?seed",
    r"seed\s+round",
    r"bridge\s+(round|funding|loan)",
    r"growth\s+round",
    r"extension\s+round",
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
                feed = self.fetch_feed(url)

                for entry in feed.entries[:8]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    pub_date = self._parse_date(published)

                    title_lower = title.lower()
                    signal_type = self._classify_funding(title_lower)

                    if signal_type and self._company_is_recipient(company.name, title):
                        amount = self._extract_amount(title)
                        self._create_signal(
                            company_id=company.id,
                            signal_type=signal_type,
                            title=title[:500],
                            summary=f"Funding signal detected for {company.name}.",
                            source_url=link,
                            source_type="major_news",
                            magnitude=amount or 1.0,
                            is_active=True,
                            detected_at=pub_date,
                        )
            except Exception as e:
                print(f"[funding] Error for {company.name}: {e}")

    # Generic suffixes that aren't distinctive enough to match on their own
    _GENERIC_TOKENS = frozenset({
        "ai", "labs", "lab", "inc", "co", "corp", "group", "technologies",
        "technology", "systems", "platform", "platforms", "cloud", "data",
    })

    def _name_tokens(self, company_name: str) -> list[str]:
        """
        Return name variants to search for in a headline:
        always the full name, plus the first token when it's distinctive (>=4 chars
        and not a generic suffix). E.g. 'Mistral AI' → ['mistral ai', 'mistral'].
        """
        name_lower = company_name.lower()
        tokens = [name_lower]
        first = name_lower.split()[0]
        if len(first) >= 4 and first not in self._GENERIC_TOKENS:
            tokens.append(first)
        return tokens

    def _company_is_recipient(self, company_name: str, title: str) -> bool:
        """
        Return True only when the prospect is the entity receiving funding,
        not merely an investor, bystander, or comparison reference.

        Two checks:
        1. Investor-role patterns: "Led by X", "Backed by X", "X Ventures", etc.
        2. Subject-position check: when funding keywords are present, the company
           must appear in the first half of the title (the grammatical subject) or
           in possessive form — not just as a trailing mention.
        """
        name_lower = company_name.lower()
        title_lower = title.lower()
        name_variants = self._name_tokens(company_name)

        # At least one name variant must appear in the title
        if not any(v in title_lower for v in name_variants):
            return False

        # Explicit investor-role patterns (check all name variants)
        investor_templates = [
            "led by {n}",
            "backed by {n}",
            "from {n}",
            "{n} ventures",
            "{n} capital",
            "{n} invest",
            "investment from {n}",
            "funding from {n}",
        ]
        for variant in name_variants:
            for tmpl in investor_templates:
                if re.search(tmpl.format(n=re.escape(variant)), title_lower):
                    return False

        # Subject-position check: when the title contains a funding action keyword,
        # the company must appear in the first half of the title or as a possessive.
        # This catches bystander/beneficiary mentions like:
        #   "OpenAI raises $110B ... should benefit Microsoft, Oracle"
        #   "AI race: OpenAI raises $110B ... to match Scale AI"
        funding_action_re = re.compile(
            r"\b(raises?|raised|secures?|secured|closes?|closed|funding round|series [a-g])\b",
            re.IGNORECASE,
        )
        if funding_action_re.search(title):
            words = title.split()
            subject_window = " ".join(words[: max(4, len(words) // 2 + 1)]).lower()
            in_subject = any(v in subject_window for v in name_variants)
            in_possessive = any(
                f"{v}\u2019s" in title_lower or f"{v}'s" in title_lower
                for v in name_variants
            )
            if not in_subject and not in_possessive:
                return False

        return True

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
