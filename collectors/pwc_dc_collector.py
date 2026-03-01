# Why: Tracks Prince William County data center buildings and projects
# Deps: BaseCollector, requests, JSON state file
# How: Diffs PWC FeatureServer layers against last run; emits signals on new/changed

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from collectors.base import BaseCollector
from database.models import Company

# PWC "Data Centers for Build-Out" FeatureServer (discovered from Experience Builder app)
# App: https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040
PWC_FEATURE_BASE = (
    "https://services2.arcgis.com/0Q7l03Ls62VG0fy4/arcgis/rest/services"
    "/Data_Centers_for_Build_Out/FeatureServer"
)
PWC_BUILDINGS_URL = f"{PWC_FEATURE_BASE}/2/query"
PWC_PROJECTS_URL = f"{PWC_FEATURE_BASE}/3/query"

# Reference only — DC Opportunity Zone polygons (static zone boundaries)
PWC_DC_ZONE_URL = (
    "https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData/MapServer/57/query"
)

STATE_FILE = Path("data/pwc_dc_state.json")

_GENERIC_TOKENS = frozenset({
    "ai", "labs", "lab", "inc", "co", "corp", "group", "technologies",
    "technology", "systems", "platform", "platforms", "cloud", "data",
    "center", "centers", "solutions", "services", "networks", "network",
    "llc", "ltd", "the", "azure", "aws",
})

BUILDING_STATUS_ORDER = ["Planned", "Approved", "Under Construction", "Operational"]
PROJECT_STATUS_ORDER = ["Planned", "Approved", "Under Construction", "Operational", "Built"]


def _status_rank(status: str | None, order: list[str]) -> int:
    s = (status or "").strip().lower()
    for i, known in enumerate(order):
        if known.lower() in s:
            return i
    return -1


class PWCDCCollector(BaseCollector):
    """
    Monitors Prince William County's data center buildings and campus projects.

    Tracks two layers from the PWC 'Build-Out Analysis - Data Centers' service:
    - DataCenterBuildings (173 named buildings with MW, GFA, occupancy date)
    - DataCenterProjects (49 campus-level projects with planned GFA, status)

    Emits outgrowing signals for new records and status progressions.
    """

    collector_name = "pwc_dc"

    def __init__(self):
        super().__init__()
        self._prev_state: dict = self._load_state()
        self._name_map: dict[str, Company] = {}

    def collect(self) -> None:
        companies = self.session.query(Company).all()
        self._build_name_map(companies)
        print(f"[pwc_dc] Loaded {len(self._name_map)} name variants for {len(companies)} companies.")

        buildings = self._fetch_all(PWC_BUILDINGS_URL)
        projects = self._fetch_all(PWC_PROJECTS_URL)
        print(f"[pwc_dc] Fetched {len(buildings)} buildings, {len(projects)} projects.")

        new_state: dict = {
            "buildings": {},
            "projects": {},
        }

        for feat in buildings:
            attrs = feat.get("attributes", {})
            obj_id = str(attrs.get("OBJECTID_1") or attrs.get("OBJECTID", ""))
            if not obj_id:
                continue
            name = attrs.get("BuildingName") or attrs.get("Address") or ""
            status = attrs.get("BuildingStatus") or ""
            gfa = attrs.get("GFA") or 0
            mw = attrs.get("MW") or 0

            new_state["buildings"][obj_id] = {"name": name, "status": status, "gfa": gfa}
            prev = self._prev_state.get("buildings", {}).get(obj_id)

            if prev is None:
                self._handle_new_building(name, status, gfa, mw)
            elif self._progressed(prev.get("status"), status, BUILDING_STATUS_ORDER):
                self._handle_building_change(name, prev["status"], status, gfa, mw)

        for feat in projects:
            attrs = feat.get("attributes", {})
            obj_id = str(attrs.get("OBJECTID", ""))
            if not obj_id:
                continue
            name = attrs.get("CampusName") or attrs.get("CaseNumber") or ""
            status = attrs.get("ProjectStatus") or ""
            planned_gfa = attrs.get("PlannedGFA") or 0
            case = attrs.get("CaseNumber") or ""

            new_state["projects"][obj_id] = {"name": name, "status": status}
            prev = self._prev_state.get("projects", {}).get(obj_id)

            if prev is None:
                self._handle_new_project(name, status, planned_gfa, case)
            elif self._progressed(prev.get("status"), status, PROJECT_STATUS_ORDER):
                self._handle_project_change(name, prev["status"], status, planned_gfa, case)

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

    def _fetch_all(self, url: str) -> list[dict]:
        all_features = []
        offset = 0
        while True:
            params = {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json",
                "resultRecordCount": 1000,
                "resultOffset": offset,
            }
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[pwc_dc] API error {url}: {e}")
                break

            features = data.get("features", [])
            if not features:
                break
            all_features.extend(features)
            if not data.get("exceededTransferLimit"):
                break
            offset += len(features)
        return all_features

    def _handle_new_building(self, name: str, status: str, gfa: float, mw: int) -> None:
        company = self._match_company(name)
        sqft_str = f"{gfa:,.0f} sq ft" if gfa else "unknown sq ft"
        mw_str = f", {mw}MW" if mw else ""
        title = f"PWC data center building: {name} ({status})"
        summary = (
            f"New data center building detected in Prince William County. "
            f"Name: {name}. Status: {status}. Size: {sqft_str}{mw_str}. "
            f"PWC is the second-largest data center market in Northern Virginia."
        )
        if company:
            self._create_signal(
                company_id=company.id,
                signal_type="outgrowing",
                title=title[:500],
                summary=summary,
                source_url="https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040",
                source_type="industry_news",
                magnitude=max(1.0, (gfa or 0) / 100_000),
                is_active=True,
            )
        else:
            print(f"[pwc_dc] New building, no match: {name} ({status}, {sqft_str})")

    def _handle_building_change(
        self, name: str, old_status: str, new_status: str, gfa: float, mw: int
    ) -> None:
        company = self._match_company(name)
        sqft_str = f"{gfa:,.0f} sq ft" if gfa else "unknown sq ft"
        title = f"PWC DC building progressed: {name} → {new_status}"
        summary = (
            f"Prince William County data center building advanced from '{old_status}' to '{new_status}'. "
            f"Name: {name}. Size: {sqft_str}."
        )
        if company:
            self._create_signal(
                company_id=company.id,
                signal_type="outgrowing",
                title=title[:500],
                summary=summary,
                source_url="https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040",
                source_type="industry_news",
                magnitude=max(1.5, (gfa or 0) / 100_000),
                is_active=True,
            )
        else:
            print(f"[pwc_dc] Building change, no match: {name} ({old_status} → {new_status})")

    def _handle_new_project(
        self, name: str, status: str, planned_gfa: float, case: str
    ) -> None:
        company = self._match_company(name)
        sqft_str = f"{planned_gfa:,.0f} sq ft planned" if planned_gfa else "size unspecified"
        title = f"PWC data center campus: {name} ({status})"
        summary = (
            f"New data center campus project in Prince William County. "
            f"Campus: {name}. Status: {status}. {sqft_str}. "
            f"Case: {case}."
        )
        if company:
            self._create_signal(
                company_id=company.id,
                signal_type="outgrowing",
                title=title[:500],
                summary=summary,
                source_url="https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040",
                source_type="industry_news",
                magnitude=max(1.0, (planned_gfa or 0) / 1_000_000),
                is_active=True,
            )
        else:
            print(f"[pwc_dc] New project, no match: {name} ({status}, {sqft_str})")

    def _handle_project_change(
        self, name: str, old_status: str, new_status: str, planned_gfa: float, case: str
    ) -> None:
        company = self._match_company(name)
        sqft_str = f"{planned_gfa:,.0f} sq ft planned" if planned_gfa else "size unspecified"
        title = f"PWC DC campus progressed: {name} → {new_status}"
        summary = (
            f"Prince William County data center campus advanced from '{old_status}' to '{new_status}'. "
            f"Campus: {name}. {sqft_str}. Case: {case}."
        )
        if company:
            self._create_signal(
                company_id=company.id,
                signal_type="outgrowing",
                title=title[:500],
                summary=summary,
                source_url="https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040",
                source_type="industry_news",
                magnitude=max(2.0, (planned_gfa or 0) / 1_000_000),
                is_active=True,
            )
        else:
            print(f"[pwc_dc] Project change, no match: {name} ({old_status} → {new_status})")

    def _progressed(self, old: str | None, new: str | None, order: list[str]) -> bool:
        return _status_rank(new, order) > _status_rank(old, order)

    def _match_company(self, text: str) -> Company | None:
        text_lower = text.lower()
        best: Company | None = None
        best_len = 0
        for name_variant, company in self._name_map.items():
            if name_variant in text_lower and len(name_variant) > best_len:
                best = company
                best_len = len(name_variant)
        return best

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {"buildings": {}, "projects": {}}

    def _save_state(self, state: dict) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))
