# Why: Detects competitor interest spikes via Google Trends
# Deps: BaseCollector, pytrends, CompetitorEvent model
# How: Queries weekly interest, flags >50% week-over-week spikes

from datetime import datetime, timezone

from collectors.base import BaseCollector
from database.models import Company, CompetitorEvent

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

SPIKE_THRESHOLD = 50  # % week-over-week increase to flag


class TrendsCollector(BaseCollector):
    collector_name = "trends"

    def __init__(self):
        super().__init__()
        self.events_created = 0

    def collect(self) -> None:
        if TrendReq is None:
            print("[trends] pytrends not installed (`pip install pytrends`), skipping.")
            self.finish()
            return

        competitors = (
            self.session.query(Company)
            .filter(Company.company_type == "competitor")
            .all()
        )
        if not competitors:
            print("[trends] No competitors in database.")
            self.finish()
            return

        print(f"[trends] Checking Google Trends for {len(competitors)} competitors...")

        batches = [competitors[i:i + 5] for i in range(0, len(competitors), 5)]

        for batch in batches:
            try:
                self._check_batch(batch)
            except Exception as e:
                names = ", ".join(c.name for c in batch)
                print(f"  [trends] Error for batch [{names}]: {e}")

        self.finish()

    def _check_batch(self, companies: list[Company]) -> None:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

        kw_list = [c.name for c in companies]
        pytrends.build_payload(kw_list, timeframe="now 7-d")

        try:
            df = pytrends.interest_over_time()
        except Exception:
            return

        if df.empty:
            return

        for company in companies:
            if company.name not in df.columns:
                continue

            series = df[company.name]
            if len(series) < 2:
                continue

            recent = series.iloc[-1]
            previous = series.iloc[-2]

            if previous == 0:
                if recent > 20:
                    pct_change = 100.0
                else:
                    continue
            else:
                pct_change = ((recent - previous) / previous) * 100

            if pct_change >= SPIKE_THRESHOLD:
                event_title = f"Google Trends spike: {company.name} interest +{pct_change:.0f}% week-over-week"

                if self._event_exists(company.id, event_title):
                    continue

                event = CompetitorEvent(
                    company_id=company.id,
                    event_type="deal",
                    title=event_title[:500],
                    description=f"Search interest jumped from {previous} to {recent} (index). Something newsworthy may have happened.",
                    source_url=f"https://trends.google.com/trends/explore?q={company.name.replace(' ', '%20')}",
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
        print(f"[{self.collector_name}] Created {self.events_created} competitor events, {self.signals_created} signals.")
        self.session.close()
