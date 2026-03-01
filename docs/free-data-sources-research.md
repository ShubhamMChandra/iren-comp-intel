# Free Programmatic Data Sources for Data Center / GPU Cloud Intelligence

*Compiled February 2026. All sources verified as free unless noted.*

---

## A) Funding Round Data (Crunchbase/PitchBook Alternatives)

### A1. SEC EDGAR — Form D Filings (BEST SOURCE)

Form D filings reveal **private company funding rounds** (Regulation D exempt offerings). CoreWeave, Lambda Labs, Crusoe, Applied Digital, and Lancium all file Form D when raising privately.

**Two access methods:**

#### Bulk Data Sets (recommended for systematic collection)

| Item | Details |
|------|---------|
| **URL** | `https://www.sec.gov/files/structureddata/data/form-d-data-sets/{year}q{quarter}_d.zip` |
| **Format** | Quarterly ZIP → tab-delimited TXT (ISSUERS, OFFERING, RELATEDPERSONS, etc.) |
| **Free** | Yes, no API key |
| **Coverage** | 2008–present, quarterly |
| **Key fields** | Issuer name, total offering amount (when disclosed), date of first sale, federal exemption |

```python
import requests, zipfile, io, csv

HEADERS = {"User-Agent": "IrenIntel/1.0 (contact@example.com)"}

def download_form_d_quarter(year: int, quarter: int) -> list[dict]:
    url = f"https://www.sec.gov/files/structureddata/data/form-d-data-sets/{year}q{quarter}_d.zip"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()

    offerings = []
    issuers = {}
    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        for name in zf.namelist():
            if "ISSUERS" in name.upper():
                with zf.open(name) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f), delimiter="\t")
                    for row in reader:
                        acc = row.get("ACCESSIONNUMBER", "")
                        issuers[acc] = row.get("ENTITYNAME", row.get("ISSUERNAME", ""))
            elif "OFFERING" in name.upper():
                with zf.open(name) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f), delimiter="\t")
                    for row in reader:
                        acc = row.get("ACCESSIONNUMBER", "")
                        offerings.append({
                            "accession": acc,
                            "issuer": issuers.get(acc, ""),
                            "total_amount": row.get("TOTALOFFERINGAMOUNT", ""),
                            "date_of_first_sale": row.get("DATEOFFIRSTSALE", ""),
                        })
    return offerings

keywords = ["coreweave", "lambda", "crusoe", "applied digital", "lancium", "gpu", "datacenter"]
offerings = download_form_d_quarter(2025, 4)
matches = [o for o in offerings if any(k in (o["issuer"] or "").lower() for k in keywords)]
```

#### EFTS Full-Text Search API (for targeted lookups)

| Item | Details |
|------|---------|
| **URL** | `https://efts.sec.gov/LATEST/search-index` |
| **Method** | GET |
| **Params** | `q` (query), `forms=D`, `dateRange=custom`, `startdt`, `enddt`, `count` |
| **Rate limit** | 10 requests/second, **User-Agent header required** |
| **Free** | Yes |

```python
import requests

HEADERS = {"User-Agent": "IrenIntel/1.0 (contact@example.com)", "Accept": "application/json"}

def search_form_d(query: str, start_dt: str = "2020-01-01", end_dt: str = "2026-12-31"):
    resp = requests.get("https://efts.sec.gov/LATEST/search-index", params={
        "q": f'"{query}"', "forms": "D",
        "dateRange": "custom", "startdt": start_dt, "enddt": end_dt, "count": 20,
    }, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return [hit["_source"] for hit in resp.json().get("hits", {}).get("hits", [])]

for company in ["CoreWeave", "Lambda Labs", "Crusoe Energy"]:
    for r in search_form_d(company):
        print(f"{r.get('display_names', [''])[0]}: {r.get('form_type')} filed {r.get('file_date')}")
```

### A2. OpenCorporates API

| Item | Details |
|------|---------|
| **URL** | `https://api.opencorporates.com/v0.4/` |
| **Endpoints** | `/companies/search?q={name}`, `/companies/{jurisdiction}/{number}` |
| **Free** | Yes for open-data use; API key required; ~5K–10K req/month |
| **Data** | Company name, jurisdiction, officers, filings, addresses, SEC links |
| **Verdict** | Complements Form D for entity resolution and officer data; **not a primary funding source** |

```python
import requests

API_TOKEN = "YOUR_OPENCORPORATES_TOKEN"

def search_company(name: str, jurisdiction: str | None = None):
    params = {"q": name, "api_token": API_TOKEN}
    if jurisdiction:
        params["jurisdiction_code"] = jurisdiction
    resp = requests.get("https://api.opencorporates.com/v0.4/companies/search",
                        params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()
```

### A3. Y Combinator Company Data (yc-oss)

| Item | Details |
|------|---------|
| **All companies** | `https://yc-oss.github.io/api/companies/all.json` (~5,700) |
| **By tag** | `https://yc-oss.github.io/api/tags/ai.json`, `infrastructure.json` |
| **Meta** | `https://yc-oss.github.io/api/meta.json` |
| **Free** | Yes, no auth |
| **Data** | Name, batch, industry, tags, team size, description — **no funding amounts** |

```python
import requests

ai_companies = requests.get("https://yc-oss.github.io/api/tags/ai.json").json()
dc_keywords = ["gpu", "cloud", "compute", "datacenter", "infrastructure"]
for c in ai_companies:
    desc = (c.get("long_description") or c.get("one_liner") or "").lower()
    if any(k in desc for k in dc_keywords):
        print(f"{c['name']} ({c['batch']}): {c.get('one_liner', '')[:80]}")
```

### A4. Hacker News — Funding Announcements (Algolia API)

| Item | Details |
|------|---------|
| **URL** | `https://hn.algolia.com/api/v1/search_by_date` |
| **Params** | `query`, `tags=story`, `numericFilters=created_at_i>{unix_ts}`, `hitsPerPage` |
| **Free** | Yes |
| **Data** | Title, URL, author, points, comments, date |

```python
import requests
from datetime import datetime, timedelta

def search_hn_funding(query: str = "raised funding series", days_back: int = 90):
    since = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
    resp = requests.get("https://hn.algolia.com/api/v1/search_by_date", params={
        "query": query, "tags": "story",
        "numericFilters": f"created_at_i>{since}", "hitsPerPage": 100,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json().get("hits", [])
```

### A5. Sources That Are NOT Free

| Source | Status |
|--------|--------|
| Tracxn | No free API (Lite is browse-only) |
| Dealroom | No free API |
| Fundz | No free tier ($29+/mo) |
| AngelList/Wellfound Relay API | Portfolio-only, not a public funding database |
| State SOS databases (DE, NV) | Searchable but no API; no funding amounts |

---

## B) USPTO Patent Filings

### B1. PatentsView PatentSearch API

| Item | Details |
|------|---------|
| **Base URL** | `https://search.patentsview.org/api/v1/` |
| **Endpoints** | `/patent/` (granted), `/publication/` (pre-grant), `/assignee/`, `/cpc_group/` |
| **Auth** | API key required: `X-Api-Key` header |
| **Key request** | https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18 |
| **Rate limit** | 45 requests/minute |
| **Status** | New API key grants **temporarily suspended** — monitor for reopening |
| **Swagger** | https://search.patentsview.org/swagger-ui/ |

```python
import requests, json

BASE = "https://search.patentsview.org/api/v1"
API_KEY = "YOUR_API_KEY"

def search_patents(assignee: str, cpc_codes: list[str]) -> dict:
    q = {"_and": [
        {"_contains": {"assignees.assignee_organization": assignee}},
        {"_or": [{"cpc_current.cpc_group_id": c} for c in cpc_codes]}
    ]}
    params = {
        "q": json.dumps(q),
        "f": json.dumps(["patent_id", "patent_title", "patent_date",
                          "assignees.assignee_organization", "cpc_current.cpc_group_id"]),
        "o": json.dumps({"size": 100})
    }
    r = requests.get(f"{BASE}/patent/", params=params,
                     headers={"X-Api-Key": API_KEY}, timeout=30)
    r.raise_for_status()
    return r.json()

# NVIDIA cooling patents
result = search_patents("NVIDIA", ["G06F1/20", "G06F1/206", "H05K7/20", "H01L23/46"])
```

### B2. Google Patents Public Data on BigQuery (BEST FOR BULK)

| Item | Details |
|------|---------|
| **Table** | `patents-public-data.patents.publications` |
| **Free** | 1 TB query processing/month (BigQuery free tier) |
| **Coverage** | Global, all patent offices, applications + grants |
| **Updates** | Quarterly |
| **Key fields** | `publication_number`, `title`, `abstract`, `assignee_harmonized`, `cpc`, `filing_date`, `publication_date` |

```sql
-- Cooling patents by major data center companies
SELECT DISTINCT
  p.publication_number, p.title, p.publication_date, a.name AS assignee
FROM `patents-public-data.patents.publications` AS p,
  UNNEST(assignee_harmonized) AS a,
  UNNEST(cpc) AS c
WHERE a.name IN ('NVIDIA Corporation', 'Intel Corporation', 'Microsoft Corporation',
                  'Google LLC', 'Amazon Technologies Inc', 'Meta Platforms Inc',
                  'Advanced Micro Devices Inc')
  AND (c.code LIKE 'G06F1/20%' OR c.code LIKE 'H05K7/20%'
       OR c.code LIKE 'H01L23/46%' OR c.code LIKE 'F28D%')
  AND p.country_code = 'US'
ORDER BY p.publication_date DESC;
```

```python
from google.cloud import bigquery

client = bigquery.Client(project="your-gcp-project")
query = """
SELECT publication_number, title, publication_date, filing_date,
  (SELECT STRING_AGG(a.name) FROM UNNEST(assignee_harmonized) a) AS assignees
FROM `patents-public-data.patents.publications`
WHERE EXISTS (SELECT 1 FROM UNNEST(cpc) c WHERE c.code LIKE 'G06F1/20%' OR c.code LIKE 'H05K7/20%')
  AND country_code = 'US' AND publication_date >= '2020-01-01'
ORDER BY publication_date DESC LIMIT 100
"""
df = client.query(query).to_dataframe()
```

### B3. USPTO PAIR / ODP

| Item | Details |
|------|---------|
| **PEDS API** | `https://ped.uspto.gov/api/` — **retired March 2025** |
| **Replacement** | Open Data Portal (ODP): `https://data.uspto.gov` — API key required |
| **Bulk Search** | `https://developer.uspto.gov/data/bulk-search` — up to 100 apps/request |
| **Data** | Application status, examiner, art unit, office actions (beyond PatentsView) |

### B4. CPC Classification Codes for Data Center Technology

#### Cooling

| CPC Code | Description |
|----------|-------------|
| **G06F 1/20** | Cooling means (computers) |
| **G06F 1/206** | Thermal management (computers) |
| **G06F 2200/201** | Cooling arrangements using cooling fluid |
| **G06F 2200/202** | Heat pipe cooling |
| **H05K 7/20** | Cooling, ventilating, heating (electrical apparatus) |
| **H01L 23/46** | Semiconductor cooling; heat transfer by flowing fluids |
| **F28D 1/00** | Heat exchangers (stationary conduits, radiators) |
| **F28D 15/00** | Heat pipes, intermediate heat-transfer media |
| **F28D 20/00** | Heat storage, regenerative heat exchange |

#### Power Management

| CPC Code | Description |
|----------|-------------|
| **G06F 1/26** | Power supply means |
| **G06F 1/28** | Power supply supervision |
| **G06F 1/30** | Power failure/interruption handling |
| **G06F 1/32** | Power saving |
| **G06F 1/3203** | Power management (computers) |
| **H02J 1/00** | DC mains circuits |
| **H02J 3/00** | AC networks (power distribution) |

#### GPU / Accelerator Infrastructure

| CPC Code | Description |
|----------|-------------|
| **G06F 9/50** | Resource allocation (incl. power/heat) |
| **G06F 15/76** | Parallel computer architectures |
| **H01L 25/00** | Assemblies of multiple semiconductor devices |

#### Server Rack / Enclosure

| CPC Code | Description |
|----------|-------------|
| **H05K 7/14** | Mounting of structural units |
| **H05K 7/18** | Rack construction |
| **H05K 5/00** | Casings, cabinets, drawers |

**CPC browser:** https://www.uspto.gov/web/patents/classification/cpc/html/cpc.html

### B5. Recommended CPC Set for Collectors

```python
DATA_CENTER_CPC = [
    "G06F1/20",    # Cooling
    "G06F1/206",   # Thermal management
    "G06F1/26",    # Power supply
    "G06F1/32",    # Power saving
    "G06F1/3203",  # Power management
    "H05K7/20",    # Apparatus cooling
    "H01L23/46",   # Semiconductor cooling
    "F28D1/00",    # Heat exchangers
    "F28D15/00",   # Heat pipes
    "H05K7/18",    # Rack construction
]
```

### B6. Assignee Name Variants

| Company | Search variants |
|---------|----------------|
| NVIDIA | `NVIDIA Corporation`, `Nvidia Corp`, `NVIDIA, Inc.` |
| AMD | `Advanced Micro Devices Inc`, `AMD Inc` |
| Intel | `Intel Corporation`, `Intel Corp` |
| Google | `Google LLC`, `Google Inc` |
| Microsoft | `Microsoft Corporation`, `Microsoft Technology Licensing` |
| Meta | `Meta Platforms Inc`, `Facebook Inc` |
| Amazon | `Amazon Technologies Inc`, `Amazon.com Inc` |
| CoreWeave | `CoreWeave Inc`, `CoreWeave, Inc.` |
| Crusoe | `Crusoe Energy Systems LLC`, `Crusoe Energy` |
| Lancium | `Lancium LLC`, `Lancium Technologies` |
| Applied Digital | `Applied Digital Corporation`, `Applied Digital Inc` |

---

## C) PeeringDB — Internet Exchange / Peering Data

### C1. API Overview

| Item | Details |
|------|---------|
| **Base URL** | `https://www.peeringdb.com/api/` |
| **Free** | Yes |
| **Auth** | Anonymous (20 req/min) or API key (40 req/min) |
| **API keys** | https://docs.peeringdb.com/howto/api_keys/ |
| **Docs** | https://docs.peeringdb.com/api_specs/ |

### C2. Object Types

| Tag | Object | Description |
|-----|--------|-------------|
| `org` | Organization | Root entity |
| `fac` | Facility | Data center / colo |
| `ix` | Internet Exchange | IXP |
| `net` | Network | ASN / Autonomous System |
| `netfac` | Network–Facility | Network presence at a facility |
| `netixlan` | Network–IX | Network presence at an exchange |
| `ixfac` | IX–Facility | IX at a facility |
| `carrier` | Carrier | Carrier networks |
| `campus` | Campus | Group of facilities |

### C3. Query Parameters

| Parameter | Description |
|-----------|-------------|
| `since={unix_ts}` | Objects updated since timestamp |
| `fields=name,city` | Select specific fields |
| `depth=0-4` | Expand nested sets |
| `{field}__contains` | Substring match |
| `{field}__startswith` | Prefix match |
| `{field}__in=a,b,c` | List match |
| `{field}__gt`, `__gte`, `__lt`, `__lte` | Numeric comparison |
| `limit`, `skip` | Pagination |

### C4. Company Facility Lookup

```python
import requests

BASE = "https://www.peeringdb.com/api"
HEADERS = {"Accept": "application/json", "User-Agent": "IrenIntel/1.0 (contact@example.com)"}

def get_company_facilities(company_name: str) -> list[dict]:
    r = requests.get(f"{BASE}/org", params={"name__contains": company_name},
                     headers=HEADERS, timeout=15)
    r.raise_for_status()
    orgs = r.json().get("data", [])
    if not orgs:
        return []

    org_id = orgs[0]["id"]
    r = requests.get(f"{BASE}/net", params={"org_id": org_id}, headers=HEADERS, timeout=15)
    r.raise_for_status()
    nets = r.json().get("data", [])
    if not nets:
        return []

    net_id = nets[0]["id"]
    r = requests.get(f"{BASE}/netfac", params={"net_id": net_id}, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])

for nf in get_company_facilities("CoreWeave"):
    print(f"{nf['name']} — {nf['city']}, {nf['country']}")
```

### C5. Change Detection (Polling)

```python
import time

def get_updated_since(obj_type: str, since_ts: int) -> list[dict]:
    r = requests.get(f"{BASE}/{obj_type}", params={"since": since_ts},
                     headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])

last_ts = int(time.time()) - 86400  # last 24 hours
new_facilities = get_updated_since("fac", last_ts)
new_netfac = get_updated_since("netfac", last_ts)  # new network-facility links
```

No webhooks or changelog — polling with `since` is the only change detection method.

### C6. Known Company Identifiers

| Company | Org ID | ASN | Notes |
|---------|--------|-----|-------|
| CoreWeave | 36160 | 33425 | 22+ facility presences |
| Lambda Labs | 40972 | — | Listed as "Lambda, Inc." |
| Vultr | — | 20473 | Search by name or ASN |

### C7. Intelligence Signals

| Signal | What it reveals |
|--------|----------------|
| New `netfac` entries | Geographic expansion (e.g., CoreWeave adding Frankfurt, Amsterdam) |
| IX presence (`netixlan`) | Peering posture; open peering = growth |
| `info_prefixes4/6` | IP space = scale indicator |
| `speed` at IXPs | Bandwidth commitment |
| Facility count over time | Growth trajectory |

---

## D) NVIDIA Partner Pages / GTC Announcements

### D1. RSS Feeds (Primary Programmatic Source)

| Feed | URL |
|------|-----|
| **All press releases** | `https://nvidianews.nvidia.com/releases.xml` |
| **AI Platforms** | `https://nvidianews.nvidia.com/cats/ai_platforms_deployment.xml` |
| **Cloud** | `https://nvidianews.nvidia.com/cats/cloud.xml` |
| **Data Center/Cloud** | `https://nvidianews.nvidia.com/cats/cybersecurity_data_center_cloud.xml` |
| **Generative AI** | `https://nvidianews.nvidia.com/cats/generative_al.xml` |
| **Enterprise/HPC** | `https://nvidianews.nvidia.com/cats/enterprise_hpc.xml` |
| **NVIDIA Blog** | `https://feeds.feedburner.com/nvidiablog` |
| **Developer Blog** | `https://developer.nvidia.com/blog/feed` |

All free, no auth, no documented rate limit.

```python
import requests
import xml.etree.ElementTree as ET

GPU_KEYWORDS = ["coreweave", "lambda", "crusoe", "applied digital", "lancium",
                "gpu cloud", "h100", "h200", "blackwell", "gb200", "dgx"]

def fetch_nvidia_rss(feed_url: str, limit: int = 30) -> list[dict]:
    resp = requests.get(feed_url, headers={"User-Agent": "IrenIntel/1.0"}, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = root.findall(".//item")[:limit]
    results = []
    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        desc_el = item.find("description")
        results.append({
            "title": title_el.text if title_el is not None else "",
            "link": link_el.text if link_el is not None else "",
            "pubDate": pub_el.text if pub_el is not None else "",
            "description": (desc_el.text or "")[:500] if desc_el is not None else "",
        })
    return results

def filter_gpu_cloud(items: list[dict]) -> list[dict]:
    return [i for i in items
            if any(kw in (i["title"] + i["description"]).lower() for kw in GPU_KEYWORDS)]
```

### D2. SEC 8-K for GPU Allocation Deals

Public companies (Applied Digital, Lancium) file 8-K for material GPU purchase agreements.

```python
def search_sec_8k_nvidia(start_dt: str = "2024-01-01"):
    resp = requests.get("https://efts.sec.gov/LATEST/search-index", params={
        "q": "NVIDIA GPU", "forms": "8-K",
        "dateRange": "custom", "startdt": start_dt, "enddt": "2026-12-31", "count": 25,
    }, headers={"User-Agent": "IrenIntel/1.0 (contact@example.com)",
                "Accept": "application/json"}, timeout=15)
    resp.raise_for_status()
    return [hit["_source"] for hit in resp.json().get("hits", {}).get("hits", [])]
```

### D3. Partner Directory

| Item | Details |
|------|---------|
| **URL** | https://marketplace.nvidia.com/en-us/enterprise/partners/ |
| **API** | None. Web UI only. |
| **Scrapeable** | Yes (JavaScript rendering may be needed), but check ToS |
| **Tiers** | Elite, Preferred, Select |

### D4. GTC Announcements

No dedicated GTC API. Announcements flow through the press/blog RSS feeds above. GTC keynotes are streamed live (no programmatic access).

---

## E) Data Center Listing Databases

### E1. Sources With NO Free API

| Source | What it has | API? | Free? |
|--------|------------|------|-------|
| **Cloudscene** | 11,400+ vendors | No | Browse free; scraping allowed per robots.txt |
| **Baxtel** | 7,000+ facilities | No | Browse free |
| **DataCenterMap.com** | 8,000+ DCs, power capacity, specs | No (planned) | Media can request data |
| **Data Center Knowledge** | Articles only (not a database) | No | Partial paywall |
| **datacenterHawk** | 113 markets, metrics | Paid only | No free tier |

#### Cloudscene Sitemap Scraping

```python
import requests
from xml.etree import ElementTree

resp = requests.get("https://cloudscene.com/sitemap/data-centers.xml")
root = ElementTree.fromstring(resp.content)
ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = [loc.text for loc in root.findall(".//sm:loc", ns)]
# Each URL is a facility page — parse with BeautifulSoup
```

### E2. OpenStreetMap (Overpass API) — FREE

| Item | Details |
|------|---------|
| **Endpoint** | `https://overpass-api.de/api/interpreter` |
| **Free** | Yes |
| **Tags** | `facility=data_center`, `building=datacenter` |

```python
import requests

query = """
[out:json][timeout:60];
(
  node["facility"="data_center"](24.5,-125,49.5,-66);
  way["facility"="data_center"](24.5,-125,49.5,-66);
  node["building"="datacenter"](24.5,-125,49.5,-66);
  way["building"="datacenter"](24.5,-125,49.5,-66);
);
out body;
"""
r = requests.get("https://overpass-api.de/api/interpreter", params={"data": query})
for el in r.json().get("elements", []):
    tags = el.get("tags", {})
    print(f"{tags.get('name', tags.get('operator', 'Unknown'))} — {tags.get('addr:city', '')}")
```

### E3. IM3 Open Source Data Center Atlas (DOE/PNNL) — FREE

| Item | Details |
|------|---------|
| **Download** | https://www.osti.gov/servlets/purl/2550666 |
| **Info** | https://www.osti.gov/biblio/2550666 |
| **License** | ODbL (open) |
| **Format** | GeoPackage (GPKG), CSV |
| **Data** | US data center locations (from OSM), facility area, county, state |

### E4. EPA Greenhouse Gas Reporting (GHGRP) — FREE

Large energy consumers (data centers) report emissions. Reveals operator identity and facility locations.

| Item | Details |
|------|---------|
| **Bulk 2023** | `https://www.epa.gov/system/files/other-files/2024-10/2023_data_summary_spreadsheets.zip` |
| **Parent companies** | `https://www.epa.gov/system/files/other-files/2024-10/ghgp_data_parent_company.xlsb` |
| **Envirofacts API** | `https://data.epa.gov/efservice/{table}/ROWS/{first}:{last}/JSON` |
| **Free** | Yes |
| **Fields** | Facility name, company, address, lat/lon, NAICS, CO2e emissions |

### E5. EIA (Energy Information Administration) — FREE

| Item | Details |
|------|---------|
| **API** | `https://api.eia.gov/v2/` |
| **Key** | Free registration at https://www.eia.gov/opendata/register.php |
| **Data** | Electricity generation, demand by region, retail sales |
| **Use** | Correlate high-load regions with data center growth |

### E6. ERCOT / PJM Interconnection Queues — FREE

Planned large power loads (often data centers) appear in ISO interconnection queues.

| Source | Access | Notes |
|--------|--------|-------|
| **ERCOT** | `apiexplorer.ercot.com` (registration + API key) | 30 req/min; TX data center loads |
| **PJM Data Miner** | `https://dataminer.pjm.com/` (CSV) | VA/OH data center demand |
| **PJM API** | `https://apiportal.pjm.com/` (free key) | Programmatic access |

### E7. FCC Antenna Registrations — FREE

| Item | Details |
|------|---------|
| **Download** | https://www.fcc.gov/wireless/data/public-access-files-database-downloads |
| **Format** | Weekly ZIP files |
| **Use** | Antenna/tower sites near data centers — connectivity signals |

---

## Master Summary Table

| Source | Free? | API? | Rate Limit | Best Signal |
|--------|-------|------|------------|-------------|
| **SEC Form D bulk** | Yes | Download | 10 req/s | Private funding rounds |
| **SEC EFTS** | Yes | REST | 10 req/s | Targeted filing search |
| **OpenCorporates** | Free tier | REST | ~5K/mo | Entity/officer resolution |
| **YC yc-oss** | Yes | REST | None | AI/infra startup discovery |
| **HN Algolia** | Yes | REST | None | Funding news |
| **PatentsView** | Yes (key) | REST | 45/min | US patents by assignee+CPC |
| **BigQuery Patents** | 1 TB/mo | SQL | Per-query billing | Global patent analytics |
| **PeeringDB** | Yes | REST | 20-40/min | Facility presence, expansion |
| **NVIDIA RSS** | Yes | RSS | None | GPU deals, partnerships |
| **SEC 8-K** | Yes | REST | 10 req/s | Public company GPU purchases |
| **Overpass (OSM)** | Yes | REST | Respectful use | DC facility locations |
| **IM3 Atlas** | Yes | Download | N/A | US DC facility baseline |
| **EPA GHGRP** | Yes | Bulk+REST | N/A | Large energy consumers |
| **EIA** | Yes (key) | REST | N/A | Regional electricity demand |
| **ERCOT/PJM** | Yes (key) | REST/CSV | 30/min | Interconnection queues |
| **Cloudscene** | Browse | Scrape | 1 req/s | Facility listings |
| **Baxtel** | Browse | Scrape | Respectful | Provider/facility pages |

---

## Recommended Collection Priority

**Tier 1 — Build first (highest signal, truly free, easy to automate):**
1. SEC Form D bulk + EFTS — private funding detection
2. PeeringDB — facility expansion tracking
3. NVIDIA RSS feeds — GPU deal announcements
4. HN Algolia — funding/hiring news

**Tier 2 — High value, moderate effort:**
5. Google BigQuery Patents — cooling/power/GPU patent tracking
6. SEC 8-K search — public company GPU purchases
7. EPA GHGRP bulk — large energy consumer identification

**Tier 3 — Supplementary:**
8. YC company data — startup discovery
9. OSM Overpass — facility geo-mapping
10. EIA / ERCOT / PJM — power demand correlation
11. Cloudscene/Baxtel sitemap scraping — facility listings
