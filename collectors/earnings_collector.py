# Why: Detects AI infrastructure signals from earnings filings
# Deps: BaseCollector, requests, Company model, SEC config
# How: EDGAR full-text search for AI/compute keywords in 8-K/10-K/10-Q

import time
from datetime import datetime, timedelta, timezone

import requests

from collectors.base import BaseCollector
from config import SEC_EDGAR_USER_AGENT
from database.models import Company

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EARNINGS_FORMS = "8-K,10-K,10-Q"
AI_COMPUTE_QUERY = '("{company}" AND ("artificial intelligence" OR "GPU" OR "compute infrastructure" OR "data center" OR "machine learning"))'

CAPEX_KEYWORDS = ["capex", "capital expenditure", "infrastructure investment",
                   "cloud spend", "cloud cost", "compute cost",
                   "gpu spend", "ai infrastructure spend"]
CAPACITY_KEYWORDS = ["capacity constraint", "outgrow", "capacity limit",
                     "oversubscribed", "waitlist", "resource constraint"]


class EarningsCollector(BaseCollector):
    collector_name = "earnings"

    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": SEC_EDGAR_USER_AGENT,
            "Accept": "application/json",
        }

    def collect(self) -> None:
        """Collect AI/compute signals from SEC earnings filings."""
        public_companies = (
            self.session.query(Company)
            .filter(Company.is_public == True, Company.ticker.isnot(None))
            .all()
        )

        print(f"[earnings] Searching earnings filings for {len(public_companies)} public companies...")

        for company in public_companies:
            try:
                self._search_filings(company)
            except Exception as e:
                print(f"[earnings] Error processing {company.name}: {e}")
            time.sleep(1)

        self.finish()

    def _search_filings(self, company: Company) -> None:
        """Search EDGAR full-text for AI/compute keywords in a company's filings."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        query = AI_COMPUTE_QUERY.replace("{company}", company.name)

        params = {
            "q": query,
            "forms": EARNINGS_FORMS,
            "dateRange": "custom",
            "startdt": start_date.strftime("%Y-%m-%d"),
            "enddt": end_date.strftime("%Y-%m-%d"),
        }

        resp = requests.get(EDGAR_SEARCH_URL, params=params, headers=self.headers, timeout=15)
        if resp.status_code != 200:
            print(f"[earnings] Non-200 response for {company.name}: {resp.status_code}")
            return

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        for hit in hits[:10]:
            self._process_hit(company, hit)

    def _process_hit(self, company: Company, hit: dict) -> None:
        """Classify and store a single EDGAR search hit."""
        source = hit.get("_source", {})
        form_type = source.get("form_type", "")
        file_date = source.get("file_date", "")
        file_description = source.get("file_description", "") or ""
        display_names = source.get("display_names", [])
        filing_desc = display_names[0] if display_names else form_type

        content_lower = (file_description + " " + filing_desc).lower()
        signal_type = self._classify_signal(content_lower)

        excerpt = file_description[:200] if file_description else filing_desc[:200]

        file_num = source.get("file_num", "")
        accession = source.get("accession_no", "")
        sec_url = ""
        if accession:
            clean = accession.replace("-", "")
            cik = source.get("entity_id", "")
            sec_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{clean}/{accession}-index.htm"

        self._create_signal(
            company_id=company.id,
            signal_type=signal_type,
            title=f"[Earnings] {company.name}: {filing_desc}"[:480],
            summary=excerpt,
            source_url=sec_url,
            source_type="sec_filing",
            magnitude=1.0,
        )

    def _classify_signal(self, content_lower: str) -> str:
        """Classify the signal type based on filing content keywords."""
        if any(kw in content_lower for kw in CAPEX_KEYWORDS):
            return "cloud_spend"
        if any(kw in content_lower for kw in CAPACITY_KEYWORDS):
            return "outgrowing"
        return "ai_initiative"
