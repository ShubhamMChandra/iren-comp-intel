# Why: Discovers competitor events from press release wires
# Deps: BaseCollector, feedparser, CompetitorEvent model
# How: Parses GlobeNewsWire/PRNewswire RSS, matches competitor names

from datetime import datetime, timezone

import feedparser
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from database.models import Company, CompetitorEvent

PRESS_RELEASE_FEEDS = [
    "https://www.globenewswire.com/RssFeed/subjectcode/25-Data Center/feedTitle/GlobeNewswire%20-%20Data%20Center",
    "https://www.globenewswire.com/RssFeed/subjectcode/04-Artificial Intelligence/feedTitle/GlobeNewswire%20-%20AI",
    "https://www.globenewswire.com/RssFeed/subjectcode/26-Energy/feedTitle/GlobeNewswire%20-%20Energy",
    "https://www.prnewswire.com/rss/technology-latest-news/technology-latest-news-list.rss",
    "https://www.prnewswire.com/rss/energy-latest-news/energy-latest-news-list.rss",
]

EVENT_KEYWORDS: dict[str, list[str]] = {
    "deal": ["contract", "deal", "partnership", "agreement", "signed", "customer", "lease", "colocation"],
    "expansion": ["expansion", "facility", "campus", "construction", "MW", "GW", "build", "site", "groundbreaking"],
    "pricing": ["pricing", "price", "cost", "rate", "revenue", "financial results", "earnings"],
    "talent": ["hire", "hired", "CEO", "CTO", "appoint", "executive", "officer", "board"],
}


def _classify_event(title: str, body: str) -> str:
    text = (title + " " + body).lower()
    best, best_count = "deal", 0
    for event_type, keywords in EVENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in text)
        if hits > best_count:
            best, best_count = event_type, hits
    return best


def _parse_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        dt = dateparser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


class PressReleaseCollector(BaseCollector):
    collector_name = "press_releases"

    def __init__(self):
        super().__init__()
        self.events_created = 0

    def collect(self) -> None:
        competitors = (
            self.session.query(Company)
            .filter(Company.company_type == "competitor")
            .all()
        )
        if not competitors:
            print("[press_releases] No competitors in database.")
            self.finish()
            return

        name_to_company = {}
        for c in competitors:
            name_to_company[c.name.lower()] = c
            for token in c.name.lower().split():
                if len(token) > 3:
                    name_to_company.setdefault(token, c)

        print(f"[press_releases] Scanning {len(PRESS_RELEASE_FEEDS)} RSS feeds for {len(competitors)} competitors...")

        for feed_url in PRESS_RELEASE_FEEDS:
            try:
                feed = self.fetch_feed(feed_url)
                for entry in feed.entries[:50]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    text = f"{title} {summary}".lower()

                    for comp_name, company in name_to_company.items():
                        if comp_name in text:
                            if self._event_exists(company.id, title):
                                break
                            event_type = _classify_event(title, summary)
                            event = CompetitorEvent(
                                company_id=company.id,
                                event_type=event_type,
                                title=title[:500],
                                description=summary[:500].strip(),
                                source_url=link[:1000] if link else "",
                                detected_at=_parse_date(published),
                            )
                            self.session.add(event)
                            self.events_created += 1
                            break
            except Exception as e:
                print(f"[press_releases] Error fetching {feed_url}: {e}")

        self.finish()

    def _event_exists(self, company_id: int, title: str) -> bool:
        return (
            self.session.query(CompetitorEvent)
            .filter(
                CompetitorEvent.company_id == company_id,
                CompetitorEvent.title == title,
            )
            .first()
            is not None
        )

    def finish(self) -> None:
        self.session.commit()
        print(f"[{self.collector_name}] Created {self.events_created} competitor events, {self.signals_created} signals.")
        self.session.close()
