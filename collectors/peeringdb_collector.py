# Why: Detects new data center facilities via PeeringDB
# Deps: BaseCollector, requests, CompetitorEvent model
# How: Queries PeeringDB facility API, matches competitor names

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from dateutil import parser as dateparser

from collectors.base import BaseCollector
from database.models import Company, CompetitorEvent

PEERINGDB_FAC_URL = "https://www.peeringdb.com/api/fac"
STATE_FILE = Path("data/peeringdb_last_id.json")


class PeeringDBCollector(BaseCollector):
    collector_name = "peeringdb"

    def __init__(self):
        super().__init__()
        self.events_created = 0
        self._last_seen_id = self._load_last_id()

    def collect(self) -> None:
        competitors = (
            self.session.query(Company)
            .filter(Company.company_type == "competitor")
            .all()
        )
        if not competitors:
            print("[peeringdb] No competitors in database.")
            self.finish()
            return

        name_variants: dict[str, Company] = {}
        for c in competitors:
            name_variants[c.name.lower()] = c
            short = c.name.lower().split()[0]
            if len(short) > 3:
                name_variants[short] = c

        print(f"[peeringdb] Querying PeeringDB for facility updates...")

        try:
            params = {"limit": 200, "status": "ok"}
            if self._last_seen_id:
                params["id__gt"] = self._last_seen_id
            resp = requests.get(PEERINGDB_FAC_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except Exception as e:
            print(f"[peeringdb] API error: {e}")
            self.finish()
            return

        max_id = self._last_seen_id or 0

        for fac in data:
            fac_id = fac.get("id", 0)
            fac_name = fac.get("name", "").lower()
            fac_org = fac.get("org_name", "").lower()
            fac_city = fac.get("city", "")
            fac_country = fac.get("country", "")
            created = fac.get("created", "")

            if fac_id > max_id:
                max_id = fac_id

            matched_company = None
            for variant, company in name_variants.items():
                if variant in fac_name or variant in fac_org:
                    matched_company = company
                    break

            if not matched_company:
                continue

            event_title = f"New PeeringDB facility: {fac.get('name', '')} ({fac_city}, {fac_country})"
            if self._event_exists(matched_company.id, event_title):
                continue

            detected_at = datetime.now(timezone.utc)
            if created:
                try:
                    detected_at = dateparser.parse(created)
                    if detected_at.tzinfo is None:
                        detected_at = detected_at.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            event = CompetitorEvent(
                company_id=matched_company.id,
                event_type="expansion",
                title=event_title[:500],
                description=f"Facility registered on PeeringDB in {fac_city}, {fac_country}.",
                source_url=f"https://www.peeringdb.com/fac/{fac_id}",
                detected_at=detected_at,
            )
            self.session.add(event)
            self.events_created += 1

        if max_id > (self._last_seen_id or 0):
            self._save_last_id(max_id)

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

    def _load_last_id(self) -> int | None:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text()).get("last_id")
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _save_last_id(self, fac_id: int) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({"last_id": fac_id}))

    def finish(self) -> None:
        self.session.commit()
        print(f"[{self.collector_name}] Created {self.events_created} competitor events, {self.signals_created} signals.")
        self.session.close()
