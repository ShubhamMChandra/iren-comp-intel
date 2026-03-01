# Why: Monitors SEC EDGAR Atom feeds for competitor filings
# Deps: BaseCollector, feedparser, CompetitorEvent, SEC config
# How: Per-CIK Atom feed, classifies 8-K/10-K/S-1, creates events

from datetime import datetime, timezone

import feedparser
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from config import SEC_EDGAR_USER_AGENT
from database.models import Company, CompetitorEvent

EDGAR_ATOM_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcompany&CIK={cik}&type=&dateb=&owner=include"
    "&count=20&search_text=&action=getcompany&output=atom"
)

TICKER_TO_CIK: dict[str, str] = {
    "CRWV": "0001916902",
    "EQIX": "0001101239",
    "DLR": "0001365135",
    "APLD": "0001144879",
    "HUT": "0001964789",
    "CORZ": "0001839341",
    "CIFR": "0001819974",
    "WULF": "0001838293",
    "RIOT": "0001167419",
    "CLSK": "0001799448",
    "HIVE": "0001770141",
    "BTBT": "0001710350",
    "SLNH": "0001822492",
    "NBIS": "0001974789",
}

FORM_TYPES = {
    "8-K": "Material event (deal, exec change, restructuring)",
    "8-K/A": "Amended material event",
    "10-K": "Annual report — financials, capacity, strategy",
    "10-Q": "Quarterly report — financials update",
    "S-1": "IPO / public offering filing",
    "S-1/A": "Amended IPO filing",
    "SC 13D": "Major stake acquisition (>5%)",
}


def _classify_filing(form_type: str) -> str:
    form = form_type.upper().strip()
    if form in ("8-K", "8-K/A"):
        return "deal"
    if form in ("10-K", "10-Q"):
        return "expansion"
    if form in ("S-1", "S-1/A", "F-1"):
        return "deal"
    if "13D" in form:
        return "deal"
    return "expansion"


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


class EdgarRSSCollector(BaseCollector):
    collector_name = "edgar_rss"

    def __init__(self):
        super().__init__()
        self.events_created = 0

    def collect(self) -> None:
        competitors = (
            self.session.query(Company)
            .filter(
                Company.company_type == "competitor",
                Company.is_public == True,
                Company.ticker.isnot(None),
            )
            .all()
        )
        if not competitors:
            print("[edgar_rss] No public competitors in database.")
            self.finish()
            return

        print(f"[edgar_rss] Checking EDGAR Atom feeds for {len(competitors)} public competitors...")

        for company in competitors:
            try:
                self._fetch_filings(company)
            except Exception as e:
                print(f"  [{company.name}] error: {e}")

        self.finish()

    def _fetch_filings(self, company: Company) -> None:
        cik = TICKER_TO_CIK.get(company.ticker)
        if not cik:
            if company.sec_cik:
                cik = company.sec_cik.zfill(10)
            else:
                return

        url = EDGAR_ATOM_URL.format(cik=cik)
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": SEC_EDGAR_USER_AGENT},
        )

        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            updated = entry.get("updated", entry.get("published", ""))
            summary = entry.get("summary", "")

            form_type = title.split(" - ")[0].strip() if " - " in title else title.strip()
            if form_type not in FORM_TYPES:
                continue

            event_title = f"[SEC {form_type}] {company.name}: {FORM_TYPES[form_type]}"
            if self._event_exists(company.id, event_title):
                continue

            event = CompetitorEvent(
                company_id=company.id,
                event_type=_classify_filing(form_type),
                title=event_title[:500],
                description=summary[:500].strip() if summary else "",
                source_url=link[:1000] if link else "",
                detected_at=_parse_date(updated),
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
        print(f"[{self.collector_name}] Created {self.events_created} competitor events, {self.signals_created} signals.")
        self.session.close()
