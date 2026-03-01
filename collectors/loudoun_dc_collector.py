# Why: Tracks Loudoun County data center builds via ArcGIS REST API
# Deps: BaseCollector, requests, JSON state file
# How: Diffs COM_DATA_CENTER records against last run; emits signals on new/changed

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from collectors.base import BaseCollector
from database.models import Company

LOUDOUN_BUILDOUT_URL = (
    "https://logis.loudoun.gov/gis/rest/services/Projects/BuildOut_LandUse/MapServer/0/query"
)

STATE_FILE = Path("data/loudoun_dc_state.json")

# Ordered statuses from least to most developed
STATUS_ORDER = [
    "Entitled",
    "Under Construction",
    "Built",
]

_GENERIC_TOKENS = frozenset({
    "ai", "labs", "lab", "inc", "co", "corp", "group", "technologies",
    "technology", "systems", "platform", "platforms", "cloud", "data",
    "center", "centers", "solutions", "services", "networks", "network",
    "data center", "llc", "ltd", "the",
})

AMOUNT_RE = re.compile(
    r"\$\s*([\d,.]+)\s*(billion|million|B\b|M\b|bn|mn)", re.IGNORECASE
)


def _status_rank(status: str | None) -> int:
    s = (status or "").strip()
    for i, known in enumerate(STATUS_ORDER):
        if known.lower() in s.lower():
            return i
    return -1


class LoudounDCCollector(BaseCollector):
    """
    Monitors Loudoun County's BuildOut land use dataset for data center activity.

    On each run, fetches all COM_DATA_CENTER features and compares against last
    known state. Emits signals for:
    - New data center records (newly entitled or permitted)
    - Status progression: Entitled → Under Construction → Built
    """

    collector_name = "loudoun_dc"

    def __init__(self):
        super().__init__()
        self._prev_state: dict[str, dict] = self._load_state()
        self._name_map: dict[str, Company] = {}

    def collect(self) -> None:
        companies = self.session.query(Company).all()
        self._build_name_map(companies)
        print(f"[loudoun_dc] Loaded {len(self._name_map)} name variants for {len(companies)} companies.")

        features = self._fetch_dc_features()
        if not features:
            print("[loudoun_dc] No features returned from ArcGIS API.")
            self.finish()
            return

        print(f"[loudoun_dc] Fetched {len(features)} COM_DATA_CENTER records.")

        new_state: dict[str, dict] = {}
        for feat in features:
            attrs = feat.get("attributes", {})
            obj_id = str(attrs.get("OBJECTID", ""))
            if not obj_id:
                continue

            display = attrs.get("LU_DISPLAY") or attrs.get("LU_ADDRESS") or ""
            status = attrs.get("LU_DEVELOP_STATUS") or ""
            sqft = attrs.get("LU_NON_RES_SQ_FT") or 0
            address = attrs.get("LU_ADDRESS") or ""
            bp_date = attrs.get("LU_BP_ISSUE_DATE") or ""
            year_built = attrs.get("LU_DEMOG_YEAR_BUILT") or ""

            new_state[obj_id] = {
                "display": display,
                "status": status,
                "sqft": sqft,
                "address": address,
            }

            prev = self._prev_state.get(obj_id)
            if prev is None:
                self._handle_new_record(attrs, display, status, sqft, address)
            elif self._status_progressed(prev.get("status"), status):
                self._handle_status_change(attrs, display, prev["status"], status, sqft, address)

        self._save_state(new_state)
        self.finish()

    def _build_name_map(self, companies: list[Company]) -> None:
        for c in companies:
            self._name_map[c.name.lower()] = c
            parts = c.name.lower().split()
            if parts:
                first = parts[0]
                if len(first) >= 4 and first not in _GENERIC_TOKENS:
                    self._name_map.setdefault(first, c)

    def _fetch_dc_features(self) -> list[dict]:
        """Fetch all COM_DATA_CENTER records from Loudoun County ArcGIS."""
        all_features = []
        offset = 0
        while True:
            params = {
                "where": "LU_USE = 'COM_DATA_CENTER'",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json",
                "resultRecordCount": 1000,
                "resultOffset": offset,
            }
            try:
                resp = requests.get(LOUDOUN_BUILDOUT_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[loudoun_dc] API error: {e}")
                break

            features = data.get("features", [])
            if not features:
                break
            all_features.extend(features)
            if not data.get("exceededTransferLimit"):
                break
            offset += len(features)

        return all_features

    def _handle_new_record(
        self, attrs: dict, display: str, status: str, sqft: int, address: str
    ) -> None:
        """Emit signal for a newly discovered data center record."""
        company = self._match_company(display + " " + address)

        sqft_str = f"{sqft:,} sq ft" if sqft else "unknown sq ft"
        title = f"Loudoun County: New data center {status.lower()} — {display or address}"
        summary = (
            f"New COM_DATA_CENTER record in Loudoun County (world's largest DC market). "
            f"Facility: {display or address}. Status: {status}. Size: {sqft_str}."
        )

        if company:
            self._create_signal(
                company_id=company.id,
                signal_type="outgrowing",
                title=title[:500],
                summary=summary,
                source_url="https://logis.loudoun.gov/gis/rest/services/Projects/BuildOut_LandUse/MapServer/0",
                source_type="industry_news",
                magnitude=max(1.0, (sqft or 0) / 100_000),
                is_active=True,
            )
        else:
            print(f"[loudoun_dc] New record, no company match: {display or address} ({status})")

    def _handle_status_change(
        self,
        attrs: dict,
        display: str,
        old_status: str,
        new_status: str,
        sqft: int,
        address: str,
    ) -> None:
        """Emit signal when a data center progresses in development status."""
        company = self._match_company(display + " " + address)

        sqft_str = f"{sqft:,} sq ft" if sqft else "unknown sq ft"
        title = f"Loudoun County DC expansion: {display or address} moved to {new_status}"
        summary = (
            f"Loudoun County data center progressed from '{old_status}' to '{new_status}'. "
            f"Facility: {display or address}. Size: {sqft_str}. "
            f"Loudoun holds ~25% of Americas data center capacity."
        )

        if company:
            self._create_signal(
                company_id=company.id,
                signal_type="outgrowing",
                title=title[:500],
                summary=summary,
                source_url="https://logis.loudoun.gov/gis/rest/services/Projects/BuildOut_LandUse/MapServer/0",
                source_type="industry_news",
                magnitude=max(1.5, (sqft or 0) / 100_000),
                is_active=True,
            )
        else:
            print(f"[loudoun_dc] Status change, no company match: {display or address} ({old_status} → {new_status})")

    def _status_progressed(self, old: str | None, new: str | None) -> bool:
        """Return True if status moved forward in the development pipeline."""
        return _status_rank(new) > _status_rank(old)

    def _match_company(self, text: str) -> Company | None:
        """Find the longest matching company name in the given text."""
        text_lower = text.lower()
        best: Company | None = None
        best_len = 0
        for name_variant, company in self._name_map.items():
            if name_variant in text_lower and len(name_variant) > best_len:
                best = company
                best_len = len(name_variant)
        return best

    def _load_state(self) -> dict[str, dict]:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save_state(self, state: dict[str, dict]) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))
