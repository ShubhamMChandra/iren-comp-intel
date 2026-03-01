"""
SEC EDGAR collector for public company filings.

Monitors:
- 8-K: material events (partnerships, expansions, leadership changes)
- 10-K/10-Q: quarterly/annual reports (financials, capacity data)
- S-1/S-1A: IPO filings (strong fundraising signal)
- SC 13D: major stake acquisitions

The SEC EDGAR API is free and requires only a User-Agent header.
"""

from datetime import datetime, timedelta, timezone

import requests
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from config import SEC_EDGAR_USER_AGENT
from database.models import Company

EDGAR_SUBMISSIONS_URL = "https://efts.sec.gov/LATEST/search-index?q={query}&dateRange=custom&startdt={start}&enddt={end}&forms={forms}"
EDGAR_COMPANY_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FULLTEXT_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{query}%22&forms=8-K,S-1,10-K&dateRange=custom&startdt={start}&enddt={end}"

FILING_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{company}%22&forms={forms}&dateRange=custom&startdt={start}&enddt={end}"

EDGAR_SEARCH_API = "https://efts.sec.gov/LATEST/search-index"

FUNDRAISING_FORMS = ["S-1", "S-1/A", "F-1", "F-1/A"]
MATERIAL_EVENT_FORMS = ["8-K", "8-K/A"]
FINANCIAL_FORMS = ["10-K", "10-Q"]


class SECCollector(BaseCollector):
    collector_name = "sec"

    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": SEC_EDGAR_USER_AGENT,
            "Accept": "application/json",
        }

    def collect(self):
        """Collect SEC filing signals for public companies."""
        public_companies = (
            self.session.query(Company)
            .filter(Company.is_public == True, Company.ticker.isnot(None))
            .all()
        )

        print(f"[sec] Checking SEC filings for {len(public_companies)} public companies...")

        for company in public_companies:
            if company.sec_cik:
                self._collect_by_cik(company)
            else:
                self._collect_by_name_search(company)

        self.finish()

    def _collect_by_cik(self, company: Company):
        """Fetch recent filings for a company with a known CIK number."""
        try:
            cik_padded = company.sec_cik.zfill(10)
            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            descriptions = recent.get("primaryDocDescription", [])
            accessions = recent.get("accessionNumber", [])

            for i, form in enumerate(forms[:20]):
                self._process_filing(
                    company=company,
                    form_type=form,
                    filing_date=dates[i] if i < len(dates) else "",
                    description=descriptions[i] if i < len(descriptions) else "",
                    accession=accessions[i] if i < len(accessions) else "",
                )
        except Exception as e:
            print(f"[sec] Error fetching CIK data for {company.name}: {e}")

    def _collect_by_name_search(self, company: Company):
        """Search EDGAR full-text search for a company by name."""
        try:
            params = {
                "q": f'"{company.name}"',
                "dateRange": "custom",
                "startdt": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                "enddt": datetime.now().strftime("%Y-%m-%d"),
                "forms": "8-K,S-1,10-K,10-Q",
            }
            url = "https://efts.sec.gov/LATEST/search-index"
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)

            if resp.status_code != 200:
                return

            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])

            for hit in hits[:10]:
                source = hit.get("_source", {})
                form_type = source.get("form_type", "")
                filing_date = source.get("file_date", "")
                description = source.get("display_names", [""])[0] if source.get("display_names") else ""

                self._process_filing(
                    company=company,
                    form_type=form_type,
                    filing_date=filing_date,
                    description=description,
                    accession="",
                )
        except Exception as e:
            print(f"[sec] Error searching for {company.name}: {e}")

    def _process_filing(
        self,
        company: Company,
        form_type: str,
        filing_date: str,
        description: str,
        accession: str,
    ):
        """Classify a filing and create the appropriate signal."""
        filing_dt = self._parse_date(filing_date)

        if form_type in FUNDRAISING_FORMS:
            signal_type = "fundraising"
            title = f"[SEC {form_type}] {company.name} filed {form_type} — potential IPO/public offering"
        elif form_type in MATERIAL_EVENT_FORMS:
            signal_type = "ai_initiative"  # AI layer will reclassify from 8-K content
            title = f"[SEC 8-K] {company.name} material event: {description[:200]}"
        elif form_type in FINANCIAL_FORMS:
            signal_type = "funding_completed"
            title = f"[SEC {form_type}] {company.name} filed {form_type} — quarterly/annual financials"
        else:
            return

        sec_url = ""
        if accession:
            clean_accession = accession.replace("-", "")
            sec_url = f"https://www.sec.gov/Archives/edgar/data/{company.sec_cik or ''}/{clean_accession}/{accession}-index.htm"

        self._create_signal(
            company_id=company.id,
            signal_type=signal_type,
            title=title,
            summary=description[:1000],
            source_url=sec_url,
            source_type="sec_filing",
            magnitude=1.0,
            detected_at=filing_dt,
        )

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
