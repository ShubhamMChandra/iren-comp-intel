# Why: Extracts Virginia incentive recipients from VEDP COF/VJIP PDF reports
# Deps: BaseCollector, pdfplumber, requests
# How: Downloads semi-annual PDFs, parses tables, matches company names to DB

import io
import re
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import requests

from collectors.base import BaseCollector
from database.models import Company

# VEDP COF (Commonwealth's Opportunity Fund) — deal-closing grants, named companies
COF_WITHIN_URL = (
    "https://www.vedp.org/sites/default/files/incentives/"
    "COF%20Within%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf"
)
COF_POST_URL = (
    "https://www.vedp.org/sites/default/files/incentives/"
    "COF%20Post%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf"
)

# VEDP VJIP (Virginia Jobs Investment Program) — workforce training grants
VJIP_WITHIN_URL = (
    "https://www.vedp.org/sites/default/files/incentives/"
    "VJIP%20Within%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf"
)

AMOUNT_RE = re.compile(
    r"\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B\b|M\b|bn|mn)?",
    re.IGNORECASE,
)

# Data center and tech company keywords to filter COF/VJIP rows
DC_KEYWORDS = [
    "data center", "cloud", "computing", "technology", "tech", "software",
    "microsoft", "amazon", "google", "meta", "apple", "oracle", "ibm",
    "semiconductor", "chip", "AI", "machine learning", "hyperscale",
    "colocation", "server", "networking", "internet",
]

_GENERIC_TOKENS = frozenset({
    "ai", "labs", "lab", "inc", "co", "corp", "group", "technologies",
    "technology", "systems", "platform", "platforms", "cloud", "data",
    "center", "centers", "solutions", "services", "networks", "network",
    "llc", "ltd", "the",
})


def _parse_dollar(text: str | None) -> float | None:
    """Parse a dollar string into a float (in raw dollars)."""
    if not text:
        return None
    clean = str(text).replace(",", "").replace("$", "").strip()
    match = re.match(r"([\d.]+)\s*(billion|million|B|M|bn|mn)?", clean, re.IGNORECASE)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    unit = (match.group(2) or "").lower()
    if unit in ("billion", "b", "bn"):
        return number * 1_000_000_000
    elif unit in ("million", "m", "mn"):
        return number * 1_000_000
    return number if number > 1_000 else number * 1_000_000


class COFCollector(BaseCollector):
    """
    Extracts Virginia incentive package recipients from VEDP semi-annual PDF reports.

    Parses three reports:
    - COF Within Performance Period: active projects still meeting targets
    - COF Post Performance Period: completed/closed projects
    - VJIP Within Performance Period: workforce training grants

    For each row that matches a known company, emits a funding_completed signal
    with the capital investment target as magnitude. Skips rows with no DB match
    and logs unmatched company names for review.
    """

    collector_name = "cof"

    def __init__(self):
        super().__init__()
        self._name_map: dict[str, Company] = {}

    def collect(self) -> None:
        companies = self.session.query(Company).all()
        self._build_name_map(companies)
        print(f"[cof] Loaded {len(self._name_map)} name variants for {len(companies)} companies.")

        reports = [
            ("COF Within Performance", COF_WITHIN_URL, "cof_within"),
            ("COF Post Performance", COF_POST_URL, "cof_post"),
            ("VJIP Within Performance", VJIP_WITHIN_URL, "vjip_within"),
        ]

        for label, url, report_key in reports:
            print(f"[cof] Processing: {label}")
            try:
                rows = self._download_and_parse(url)
                matched, unmatched = 0, 0
                for row in rows:
                    company_name = row.get("company", "")
                    if not company_name:
                        continue
                    company = self._match_company(company_name)
                    if company:
                        self._emit_signal(company, row, label)
                        matched += 1
                    else:
                        unmatched += 1
                        if _looks_like_tech(company_name):
                            print(f"[cof] Unmatched tech company: {company_name}")
                print(f"[cof] {label}: {len(rows)} rows, {matched} matched, {unmatched} unmatched.")
            except Exception as e:
                print(f"[cof] Error processing {label}: {e}")

        self.finish()

    def _download_and_parse(self, url: str) -> list[dict]:
        """Download PDF from URL and extract tabular rows."""
        try:
            resp = requests.get(url, timeout=60, headers={"User-Agent": "IrenIntel/1.0"})
            resp.raise_for_status()
        except Exception as e:
            print(f"[cof] Download error {url}: {e}")
            return []

        rows = []
        try:
            with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if not table:
                        continue
                    for row in table[1:]:  # skip header row
                        parsed = self._parse_row(row)
                        if parsed:
                            rows.append(parsed)
        except Exception as e:
            print(f"[cof] PDF parse error: {e}")

        return rows

    def _parse_row(self, row: list) -> dict | None:
        """Extract structured data from a table row."""
        if not row or len(row) < 3:
            return None

        # Normalize cells (pdfplumber may return None for merged cells)
        cells = [str(c).strip() if c is not None else "" for c in row]

        # Skip header rows and empty rows
        first = cells[0].lower()
        if not first or first in ("project #", "project number", "company", "nan", "none"):
            return None

        # COF format: [project_num, company, locality, grant, jobs_target, capex_target, wage_target, ...]
        # VJIP format: [project_num, company, locality, grant_awarded, grant_paid, reimb_rate, jobs_new, ...]
        company = cells[1] if len(cells) > 1 else cells[0]
        if not company or company.lower() in ("none", "nan", ""):
            return None

        locality = cells[2] if len(cells) > 2 else ""
        grant_raw = cells[3] if len(cells) > 3 else ""
        capex_raw = cells[5] if len(cells) > 5 else ""

        return {
            "company": company,
            "locality": locality,
            "grant": _parse_dollar(grant_raw),
            "capex": _parse_dollar(capex_raw),
        }

    def _emit_signal(self, company: Company, row: dict, report_label: str) -> None:
        capex = row.get("capex")
        grant = row.get("grant")
        locality = row.get("locality", "Virginia")

        magnitude = max(1.0, (capex or 0) / 1_000_000_000)

        summary_parts = [
            f"Virginia incentive package detected via {report_label} report.",
            f"Locality: {locality}.",
        ]
        if grant:
            summary_parts.append(f"State grant: ${grant / 1_000_000:.1f}M.")
        if capex:
            summary_parts.append(f"Capital investment target: ${capex / 1_000_000:.0f}M.")

        title = f"{company.name} — Virginia {report_label.split()[0]} incentive package"
        if locality:
            title += f", {locality}"

        self._create_signal(
            company_id=company.id,
            signal_type="funding_completed",
            title=title[:500],
            summary=" ".join(summary_parts),
            source_url="https://www.vedp.org/incentive-performance-reports",
            source_type="major_news",
            magnitude=magnitude,
            is_active=True,
        )

    def _build_name_map(self, companies: list[Company]) -> None:
        for c in companies:
            self._name_map[c.name.lower()] = c
            parts = c.name.lower().split()
            if parts:
                first = parts[0]
                if len(first) >= 4 and first not in _GENERIC_TOKENS:
                    self._name_map.setdefault(first, c)

    def _match_company(self, company_name: str) -> Company | None:
        """Find DB company matching the report row's company name."""
        name_lower = company_name.lower()
        # First try exact prefix match on full name
        for variant, company in self._name_map.items():
            if variant in name_lower or name_lower in variant:
                return company
        return None


def _looks_like_tech(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in DC_KEYWORDS)
