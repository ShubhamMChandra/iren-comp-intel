# Why: Detects Virginia data center investments via VEDP press releases
# Deps: BaseCollector, feedparser, requests, BeautifulSoup
# How: Polls VEDP RSS + sitemap; extracts investment signals for matched companies

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from database.models import Company

VEDP_RSS_URL = "https://www.vedp.org/rss.xml"
VEDP_SITEMAP_URL = "https://www.vedp.org/sitemap.xml"

STATE_FILE = Path("data/vedp_seen_urls.json")

try:
    from private.collector_patterns import DC_KEYWORDS
except ImportError:
    DC_KEYWORDS = [
        "data center", "data centre", "hyperscale", "colocation",
        "megawatt", " MW ", "gigawatt",
    ]

AMOUNT_RE = re.compile(
    r"\$\s*([\d,.]+)\s*(billion|million|B\b|M\b|bn|mn)", re.IGNORECASE
)
JOBS_RE = re.compile(
    r"(?:create|creating|add|adding|support)\s+(?:more than\s+|up to\s+)?(\d[\d,]*)\s+(?:new\s+)?jobs",
    re.IGNORECASE,
)


def _is_dc_related(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in DC_KEYWORDS)


def _extract_amount(text: str) -> float | None:
    match = AMOUNT_RE.search(text)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    unit = match.group(2).lower()
    if unit in ("billion", "b", "bn"):
        return number * 1_000_000_000
    elif unit in ("million", "m", "mn"):
        return number * 1_000_000
    return number


def _extract_jobs(text: str) -> int | None:
    match = JOBS_RE.search(text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _parse_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        dt = dateparser.parse(date_str)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt or datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


class VEDPCollector(BaseCollector):
    """Collects data center investment signals from VEDP press releases."""

    collector_name = "vedp"

    def __init__(self):
        super().__init__()
        self._seen_urls: set[str] = self._load_seen_urls()
        self._name_map: dict[str, Company] = {}

    def collect(self) -> None:
        companies = self.session.query(Company).all()
        if not companies:
            print("[vedp] No companies in database.")
            self.finish()
            return

        self._build_name_map(companies)
        print(f"[vedp] Loaded {len(self._name_map)} name variants for {len(companies)} companies.")

        entries = self._fetch_rss_entries()
        print(f"[vedp] Found {len(entries)} press releases via RSS.")

        new_urls = set()
        for entry in entries:
            url = entry.get("url", "")
            if url in self._seen_urls:
                continue
            new_urls.add(url)
            self._process_entry(entry)

        if new_urls:
            self._save_seen_urls(self._seen_urls | new_urls)

        self.finish()

    def _build_name_map(self, companies: list[Company]) -> None:
        for c in companies:
            self._name_map[c.name.lower()] = c
            parts = c.name.lower().split()
            if parts:
                first = parts[0]
                if len(first) >= 4 and first not in _GENERIC_TOKENS:
                    self._name_map.setdefault(first, c)

    def _fetch_rss_entries(self) -> list[dict]:
        """Fetch press releases from VEDP RSS feed."""
        try:
            feed = self.fetch_feed(VEDP_RSS_URL)
            entries = []
            for item in feed.entries:
                link = item.get("link", "")
                if "/press-release/" not in link:
                    continue
                entries.append({
                    "title": item.get("title", ""),
                    "url": link,
                    "published": item.get("published", ""),
                    "summary": item.get("summary", "") or item.get("description", ""),
                })
            return entries
        except Exception as e:
            print(f"[vedp] RSS fetch error: {e}")
            return []

    def _process_entry(self, entry: dict) -> None:
        title = entry.get("title", "")
        url = entry.get("url", "")
        published = entry.get("published", "")
        body = entry.get("summary", "")

        full_text = f"{title} {body}"

        if not _is_dc_related(full_text):
            # Fetch full page if summary doesn't mention DC keywords
            page_text = self._fetch_page_text(url)
            if not page_text or not _is_dc_related(page_text):
                return
            full_text = f"{title} {page_text}"

        pub_date = _parse_date(published)
        investment = _extract_amount(full_text)
        jobs = _extract_jobs(full_text)

        matched_company = self._match_company(full_text)
        if not matched_company:
            print(f"[vedp] No company match for: {title[:80]}")
            return

        signal_type = "ai_initiative" if not investment else "funding_completed"
        magnitude = max(1.0, (investment or 0) / 1_000_000_000)

        summary_parts = [f"VEDP press release: Virginia data center investment detected."]
        if investment:
            summary_parts.append(f"Investment: ${investment / 1_000_000:.0f}M.")
        if jobs:
            summary_parts.append(f"Jobs: {jobs}.")

        self._create_signal(
            company_id=matched_company.id,
            signal_type=signal_type,
            title=title[:500],
            summary=" ".join(summary_parts),
            source_url=url,
            source_type="major_news",
            magnitude=magnitude,
            is_active=True,
            detected_at=pub_date,
        )

    def _match_company(self, text: str) -> Company | None:
        """Find a company whose name appears in the text."""
        text_lower = text.lower()
        best: Company | None = None
        best_len = 0
        for name_variant, company in self._name_map.items():
            if name_variant in text_lower and len(name_variant) > best_len:
                best = company
                best_len = len(name_variant)
        return best

    def _fetch_page_text(self, url: str) -> str | None:
        """Fetch press release HTML and return cleaned text."""
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "IrenIntel/1.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            return soup.get_text(separator=" ", strip=True)
        except Exception as e:
            print(f"[vedp] Page fetch error {url}: {e}")
            return None

    def _load_seen_urls(self) -> set[str]:
        if STATE_FILE.exists():
            try:
                return set(json.loads(STATE_FILE.read_text()))
            except Exception:
                pass
        return set()

    def _save_seen_urls(self, urls: set[str]) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(list(urls)))


def scrape_vedp_historical(max_pages: int = 500) -> list[dict]:
    """
    One-time scrape of all VEDP press releases via sitemap.
    Returns list of {url, lastmod} dicts for press release URLs.
    Use this manually to backfill historical data.
    """
    try:
        resp = requests.get(VEDP_SITEMAP_URL, timeout=15)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        press_releases = []
        for sitemap_elem in root.findall("s:sitemap", ns):
            loc_elem = sitemap_elem.find("s:loc", ns)
            if loc_elem is None:
                continue
            sub_url = loc_elem.text
            try:
                sub_resp = requests.get(sub_url, timeout=15)
                sub_resp.raise_for_status()
                sub_root = ElementTree.fromstring(sub_resp.content)
                for url_elem in sub_root.findall("s:url", ns):
                    url_loc = url_elem.find("s:loc", ns)
                    lastmod = url_elem.find("s:lastmod", ns)
                    if url_loc is not None and "/press-release/" in url_loc.text:
                        press_releases.append({
                            "url": url_loc.text,
                            "lastmod": lastmod.text if lastmod is not None else None,
                        })
                        if len(press_releases) >= max_pages:
                            return press_releases
            except Exception as e:
                print(f"[vedp_historical] Sub-sitemap error {sub_url}: {e}")

        return press_releases
    except Exception as e:
        print(f"[vedp_historical] Sitemap error: {e}")
        return []


_GENERIC_TOKENS = frozenset({
    "ai", "labs", "lab", "inc", "co", "corp", "group", "technologies",
    "technology", "systems", "platform", "platforms", "cloud", "data",
    "center", "centers", "solutions", "services", "networks", "network",
})
