# Why: Web-search competitive event discovery for competitors
# Deps: BaseCollector, duckduckgo_search, CompetitorEvent, signal_extractor
# How: Searches news per competitor, classifies events, creates CompetitorEvent rows

import json
from datetime import datetime, timezone

from collectors.base import BaseCollector
from database.models import Company, CompetitorEvent

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from private.collector_patterns import SEARCH_TEMPLATES, EVENT_KEYWORDS
except ImportError:
    SEARCH_TEMPLATES = [
        '"{name}" data center expansion OR deal OR contract',
        '"{name}" pricing OR cost',
        '"{name}" partnership OR customer win',
    ]
    EVENT_KEYWORDS: dict[str, list[str]] = {
        "deal": ["contract", "deal", "partnership", "agreement"],
        "expansion": ["expansion", "facility", "campus", "construction"],
        "pricing": ["pricing", "price", "cost", "rate"],
        "talent": ["hire", "hired", "CEO", "CTO", "appoint"],
    }


def _classify_event(title: str, body: str) -> str:
    text = (title + " " + body).lower()
    best, best_count = "deal", 0
    for event_type, keywords in EVENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in text)
        if hits > best_count:
            best, best_count = event_type, hits
    return best


class CompetitiveIntelCollector(BaseCollector):
    collector_name = "competitive_intel"

    def __init__(self):
        super().__init__()
        self.events_created = 0

    def collect(self) -> None:
        if DDGS is None:
            print("[competitive_intel] duckduckgo-search not installed, skipping.")
            self.finish()
            return

        competitors = (
            self.session.query(Company)
            .filter(Company.company_type == "competitor")
            .all()
        )

        if not competitors:
            print("[competitive_intel] No competitors in database.")
            self.finish()
            return

        print(f"[competitive_intel] Scanning {len(competitors)} competitors...")

        for company in competitors:
            try:
                self._search_company(company)
            except Exception as e:
                print(f"  [{company.name}] error: {e}")

        self.finish()

    def _search_company(self, company: Company) -> None:
        ddgs = DDGS()

        for template in SEARCH_TEMPLATES:
            query = template.format(name=company.name)
            try:
                results = list(ddgs.text(query, max_results=3))
            except Exception:
                continue

            for item in results:
                if isinstance(item, dict):
                    title = item.get("title", "")
                    body = item.get("body", "")
                    url = item.get("href", "")
                else:
                    title = getattr(item, "title", "")
                    body = getattr(item, "body", "")
                    url = getattr(item, "href", "")

                if not title:
                    continue

                if self._event_exists(company.id, title):
                    continue

                event_type = _classify_event(title, body)
                desc = body[:500].strip() if body else ""

                event = CompetitorEvent(
                    company_id=company.id,
                    event_type=event_type,
                    title=title[:500],
                    description=desc,
                    source_url=url[:1000] if url else "",
                    detected_at=datetime.now(timezone.utc),
                )
                self.session.add(event)
                self.events_created += 1

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
        msg = f"[{self.collector_name}] Created {self.events_created} competitor events, {self.signals_created} signals."
        if self.semantic_dupes_caught > 0:
            msg += f" ({self.semantic_dupes_caught} semantic duplicates filtered)"
        print(msg)
        self.session.close()
