# Virginia Data Center Incentive Data Sources — Research Findings

**Date**: 2026-02-28
**Verdict**: Several genuinely programmatic sources exist, but the landscape is uneven. The best sources are county-level ArcGIS REST APIs and state legislative report PDFs. There is no single "Virginia data center incentive API."

---

## PART 1: Virginia MEI Commission & State-Level Sources

### Source 1: MEI Annual Reports (Reports to the General Assembly)

| Attribute | Detail |
|---|---|
| **URL** | `https://rga.lis.virginia.gov/Published/{year}/RD{number}` |
| **PDF URL** | `https://rga.lis.virginia.gov/Published/{year}/RD{number}/PDF` |
| **Cost** | Free |
| **Format** | HTML metadata page + PDF report |
| **Update Frequency** | Annual (January, before each GA session) |
| **Programmatic?** | Semi — metadata page is scrapeable HTML, report is PDF requiring extraction |

**What it provides**: Every MEI-endorsed incentive package that has been publicly announced:
- Industrial sector, company name (once public), project codename
- Employment creation and capital investment amounts
- Average annual wage of new jobs
- Competitor states
- State/local ROI estimates (prepared by VEDP)
- Incentive package breakdown with payment timeline
- Draft legislation for financing

**Known reports**:
- RD115 (2026) — 2025 projects: Eli Lilly "Whistler" ($2.1B), AstraZeneca "Zodiac" ($4.0B)
- RD27 (2024) — 2023 projects
- RD844 (2025) — related report
- RD34 (2020) — included Merck "Pony" project ($31.5M incentives)

**Honest assessment**: The MEI reports are the gold standard for large Virginia incentive packages, but they are PDFs requiring parsing. The RGA system has no API — you must scrape or manually check. Also, most recent data center projects went through the **sales tax exemption** path (which doesn't require MEI approval), so MEI reports skew toward non-DC projects like pharma and manufacturing. Data centers rarely appear in MEI reports because the sales tax exemption is their primary incentive.

```python
"""Scrape MEI report metadata from Virginia RGA system."""
import requests
from bs4 import BeautifulSoup

MEI_REPORTS = {
    2026: "RD115",
    2024: "RD27",
    2020: "RD34",
}

def fetch_mei_report_metadata(year: int) -> dict | None:
    report_id = MEI_REPORTS.get(year)
    if not report_id:
        return None
    url = f"https://rga.lis.virginia.gov/Published/{year}/{report_id}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return {
        "year": year,
        "report_id": report_id,
        "pdf_url": f"https://rga.lis.virginia.gov/Published/{year}/{report_id}/PDF",
        "title": soup.find("h4").get_text(strip=True) if soup.find("h4") else None,
        "html_url": url,
    }

def download_mei_pdf(year: int, output_path: str) -> str:
    report_id = MEI_REPORTS.get(year)
    if not report_id:
        raise ValueError(f"No known MEI report for {year}")
    url = f"https://rga.lis.virginia.gov/Published/{year}/{report_id}/PDF"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path
```

**Signal value**: Low for data centers specifically. High for pharma/manufacturing mega-projects that could compete for the same power/land/incentives.

---

### Source 2: JLARC Data Center Report (RD206)

| Attribute | Detail |
|---|---|
| **URL** | `https://rga.lis.virginia.gov/Published/2025/RD206` |
| **PDF URL** | `https://rga.lis.virginia.gov/Published/2025/RD206/PDF` |
| **Cost** | Free |
| **Format** | PDF (77 pages) |
| **Update Frequency** | One-time study (Dec 2024), but JLARC may do follow-ups |
| **Programmatic?** | No — PDF only |

**What it provides** (key data points):
- Northern Virginia = 13% of global data center capacity, 25% of Americas
- 74,000 jobs, $5.5B labor income, $9.1B GDP annually
- Typical 250K sq ft facility = ~50 FTEs, ~1,500 construction workers
- Sales tax exemption = $928M savings in FY23, used by ~90% of industry
- Energy demand forecast to double in 10 years
- 5,050 MW current consumption = 2 million VA households
- Data on 5 mature localities: DC revenue = <1% to 31% of total local revenue

**Honest assessment**: Incredible reference document but a one-time PDF. Not a monitoring source. The underlying data (interviews, energy models) is not published separately. Useful for contextual enrichment of your signals, not for ongoing collection.

---

### Source 3: Governor's Office Press Releases

| Attribute | Detail |
|---|---|
| **URL** | `https://www.governor.virginia.gov/newsroom/news-releases/` |
| **Cost** | Free |
| **Format** | HTML pages, no RSS feed, no API |
| **Update Frequency** | As events occur |
| **Programmatic?** | Scrapeable but fragile — HTML structure changes with each administration |

**What it provides**: Announcements of major economic development projects including:
- Company name, investment amount, job commitments
- Location (county/city)
- Sometimes references MEI approval or VEDP involvement

**Honest assessment**: This is a news source, not a data source. The URL structure (`/newsroom/news-releases/{year}/{month}/name-{id}-en.html`) is semi-predictable but there's no index page that returns structured data. Every new governor changes the website. Scraping is possible but brittle. You'd be better served by your existing Google News collector with `site:governor.virginia.gov` queries.

---

### Source 4: VEDP Press Releases

| Attribute | Detail |
|---|---|
| **URL** | `https://www.vedp.org/press-release/{year-month}/{slug}` |
| **Sitemap** | `https://www.vedp.org/sitemap.xml` (Drupal CMS, two XML sub-sitemaps) |
| **Cost** | Free |
| **Format** | HTML, sitemap XML |
| **Update Frequency** | As events occur (several per month) |
| **Programmatic?** | Yes — sitemap is parseable for all press release URLs |

**What it provides**: Official announcements of business investments in Virginia:
- Company name, investment amount, job creation numbers
- Location, project details
- Often quotes from Governor, VEDP, company executives
- Specifically tags data center investments

**Recent data center examples**:
- CleanArc $3B in Caroline County (2025-11)
- Vantage $2B in Stafford County (2025-11)
- Google $9B across Virginia (2025-08)
- AWS $35B by 2040 (2023-01)

```python
"""Scrape VEDP press releases via sitemap for data center announcements."""
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

VEDP_SITEMAP = "https://www.vedp.org/sitemap.xml"
DC_KEYWORDS = ["data center", "data centre", "hyperscale", "cloud infrastructure", "campus"]

def get_vedp_press_release_urls() -> list[str]:
    """Parse VEDP sitemap to extract all press release URLs."""
    resp = requests.get(VEDP_SITEMAP, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sub_sitemaps = [loc.text for loc in root.findall(".//sm:loc", ns)]

    press_urls = []
    for sub_url in sub_sitemaps:
        sub_resp = requests.get(sub_url, timeout=15)
        sub_root = ET.fromstring(sub_resp.content)
        for loc in sub_root.findall(".//sm:loc", ns):
            url = loc.text
            if "/press-release/" in url:
                press_urls.append(url)
    return press_urls

def is_data_center_related(html: str) -> bool:
    text = BeautifulSoup(html, "html.parser").get_text().lower()
    return any(kw in text for kw in DC_KEYWORDS)
```

**Signal value**: HIGH. This is probably the best single state-level source for data center expansion signals. Pair with your news collector.

---

### Source 5: Virginia Sales Tax Exemption Data

| Attribute | Detail |
|---|---|
| **Exists?** | No public database |
| **Programmatic?** | No |

**Honest assessment**: The VA Department of Taxation does NOT publish a list of companies using the data center sales tax exemption. The exemption requires a Memorandum of Understanding with VEDP, but those MOUs are not public. JLARC reports aggregate numbers ($928M in FY23 savings) but not per-company data. Getting the list of qualifying companies would require a FOIA request to VEDP or the Department of Taxation, and it might be denied as confidential tax information.

---

## PART 2: Local County Data Sources

---

### LOUDOUN COUNTY (World's Largest Data Center Market)

#### Source 6: Loudoun BuildOut Land Use — Data Center Layer ⭐ BEST SOURCE

| Attribute | Detail |
|---|---|
| **Endpoint** | `https://logis.loudoun.gov/gis/rest/services/Projects/BuildOut_LandUse/MapServer/0` |
| **Cost** | Free, no API key |
| **Format** | ArcGIS REST API → JSON/GeoJSON |
| **Max records per query** | 1,000 |
| **Update Frequency** | Maintained by Loudoun County GIS (quarterly-ish) |
| **Programmatic?** | YES — fully queryable REST API |

**What it provides (confirmed by live query)**:
- `LU_USE` = `COM_DATA_CENTER` (223 records as of today)
- `LU_ADDRESS` — street address
- `LU_MCPI` — parcel identification number (PIN)
- `LU_NON_RES_SQ_FT` — square footage
- `LU_DEVELOP_STATUS` — development status (built, under construction, entitled, etc.)
- `LU_BP_ISSUE_DATE` — building permit issue date
- `LU_DEMOG_YEAR_BUILT` — year built
- `LU_AS_OF_DATE` — data freshness date
- `LU_X_Coord`, `LU_Y_Coord` — coordinates
- `LU_DISPLAY` — display name

**All `LU_USE` categories** (with counts):
| Code | Count |
|---|---|
| COM_DATA_CENTER | 223 |
| COM_OFFICE_GENERAL | 582 |
| COM_LIGHT_IND_FLEX | 607 |
| COM_RETAIL | 1,653 |
| RES_SFD | 75,372 |
| VACANT_ENTITLED | 2,042 |
| VACANT_UNENTITLED | 629 |
| ... and others | |

```python
"""Query Loudoun County data center structures via ArcGIS REST API."""
import requests
from datetime import datetime

LOUDOUN_BUILDOUT_URL = (
    "https://logis.loudoun.gov/gis/rest/services/Projects/BuildOut_LandUse/MapServer/0/query"
)

def fetch_loudoun_data_centers(
    status_filter: str | None = None,
) -> list[dict]:
    """
    Fetch all COM_DATA_CENTER records from Loudoun County.
    Optional status_filter: e.g. "Built", "Under Construction", "Entitled"
    """
    where = "LU_USE = 'COM_DATA_CENTER'"
    if status_filter:
        where += f" AND LU_DEVELOP_STATUS = '{status_filter}'"

    all_features = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",  # WGS84 lat/lon
            "f": "json",
            "resultRecordCount": 1000,
            "resultOffset": offset,
        }
        resp = requests.get(LOUDOUN_BUILDOUT_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            break
        all_features.extend(features)
        if not data.get("exceededTransferLimit"):
            break
        offset += len(features)
    return all_features

def loudoun_dc_summary() -> dict:
    """Get aggregate stats on Loudoun data centers."""
    stats_url = LOUDOUN_BUILDOUT_URL
    params = {
        "where": "LU_USE = 'COM_DATA_CENTER'",
        "outStatistics": '[{"statisticType":"count","onStatisticField":"OBJECTID","outStatisticFieldName":"total_count"},'
                         '{"statisticType":"sum","onStatisticField":"LU_NON_RES_SQ_FT","outStatisticFieldName":"total_sqft"}]',
        "groupByFieldsForStatistics": "LU_DEVELOP_STATUS",
        "returnGeometry": "false",
        "f": "json",
    }
    resp = requests.get(stats_url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

# Expansion signal: new records where LU_DEVELOP_STATUS changes
# from "Entitled" to "Under Construction", or new "Entitled" entries appear
```

**Signal value**: VERY HIGH. You can:
1. Monitor for new `COM_DATA_CENTER` entries (new projects approved)
2. Track `LU_DEVELOP_STATUS` changes (entitled → under construction → built)
3. Track total `LU_NON_RES_SQ_FT` growth over time
4. Cross-reference PINs with tax assessment data

---

#### Source 7: Loudoun Zoning Map

| Attribute | Detail |
|---|---|
| **Endpoint** | `https://logis.loudoun.gov/gis/rest/services/COL/Zoning/MapServer` |
| **Cost** | Free, no API key |
| **Format** | ArcGIS REST API |
| **Programmatic?** | Yes |

**What it provides**: Current zoning designations for all parcels. Useful for identifying parcels zoned for data center use (industrial districts) and tracking rezoning activity.

**Honest assessment**: Background reference data, not a monitoring source. Zoning changes are infrequent and better tracked through Board of Supervisors meeting agendas.

---

#### Source 8: Loudoun Residential Building Permits

| Attribute | Detail |
|---|---|
| **Endpoint** | `https://logis.loudoun.gov/gis/rest/services/Projects/ResBuildingPermits/MapServer` |
| **Cost** | Free, no API key |
| **Programmatic?** | Yes |

**Honest assessment**: This is RESIDENTIAL permits only. Does NOT include commercial/data center permits. The permit dashboard (`Projects/PermitDashboard`) also appears to be residential-only based on the field schema (UNIT_TYPE values are all residential types). **Commercial building permits for data centers are NOT in these endpoints.**

---

### PRINCE WILLIAM COUNTY

#### Source 9: PWC Data Center Opportunity Zone Overlay ⭐ HIGH VALUE

| Attribute | Detail |
|---|---|
| **Endpoint** | `https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData/MapServer/57` |
| **Cost** | Free, no API key |
| **Format** | ArcGIS REST API → JSON/GeoJSON |
| **Max records per query** | 1,000 |
| **Update Frequency** | Maintained by PWC GIS |
| **Programmatic?** | YES |

**Fields**: `NAME`, `ACREAGE`, `Shape` (polygon geometry)

**What it provides**: The geographic boundaries of the Data Center Opportunity Zone Overlay District — areas where data center development is encouraged with infrastructure support. Created by Ordinance No. 16-21 (May 2016).

```python
"""Query Prince William County Data Center Opportunity Zone polygons."""
import requests

PWC_DC_ZONE_URL = (
    "https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData/MapServer/57/query"
)

def fetch_pwc_dc_opportunity_zones() -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": "NAME,ACREAGE",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    resp = requests.get(PWC_DC_ZONE_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("features", [])
```

**Signal value**: MEDIUM. Useful as reference data — shows WHERE data centers can be built. Monitor for zone expansions (new polygons added) which signal policy shifts toward more DC development.

---

#### Source 10: PWC Interactive Data Center Map (NEW — Feb 2026) ⭐⭐ HIGHEST VALUE

| Attribute | Detail |
|---|---|
| **Dashboard URL** | `https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040/` |
| **County Mapper** | `https://gisweb.pwcva.gov/webapps/countymapper/` |
| **Cost** | Free |
| **Format** | ArcGIS Experience Builder app |
| **Update Frequency** | Ongoing as projects progress |
| **Programmatic?** | MAYBE — the underlying feature layers may be queryable |

**What it provides**:
- Data Center Buildings layer and Data Center Campuses layer
- Acreage, location, development status, planned square footage
- Zoning classifications and zoning case numbers
- Projects at ALL stages: pending applications → approved → under construction → completed

**Honest assessment**: This was just launched February 12, 2026. The dashboard is an ArcGIS Experience Builder app, and the underlying feature service URLs are NOT yet publicly documented. The data is visible in the interactive app but extracting it programmatically requires reverse-engineering the ArcGIS feature service endpoint from the Experience Builder configuration. This is the most valuable source PWC offers, but getting to the raw API will require some detective work (inspect network requests in the browser).

```python
"""
PWC Data Center Map — approach for finding the feature service.
The Experience Builder app loads its data from ArcGIS feature services.
You need to inspect the app's network requests to find the actual endpoint.
"""
import requests

# Step 1: Fetch the Experience Builder config to find the data sources
EXPERIENCE_URL = "https://experience.arcgis.com/experience/08d8d1a87e524a91b288a4b3e38cc040/"

# Step 2: In browser dev tools, look for requests to:
#   gisweb.pwcva.gov/arcgis/rest/services/.../FeatureServer/0/query
# The feature service will have layers like:
#   "Data Center Buildings" and "Data Center Campuses"

# Step 3: Once you find the endpoint, query it like:
def fetch_pwc_dc_buildings(feature_service_url: str) -> list[dict]:
    """Query once you've identified the feature service URL."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    resp = requests.get(f"{feature_service_url}/query", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("features", [])

# TODO: Reverse-engineer the actual feature service URL from the
# Experience Builder app's network traffic
```

---

#### Source 11: PWC Parcels + Zoning + Use Permits

| Attribute | Detail |
|---|---|
| **Parcels (Layer 0)** | `https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData/MapServer/0` |
| **Zoning (Layer 21)** | `https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData/MapServer/21` |
| **Use Permits (Layer 66)** | `https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData/MapServer/66` |
| **Technology Overlay (Layer 60)** | `https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData2/MapServer/60` |
| **E-Commerce Overlay (Layer 4)** | `https://gisweb.pwcva.gov/arcgis/rest/services/OpenData/OpenData2/MapServer/4` |
| **Cost** | Free, no API key |
| **Programmatic?** | Yes |

**Honest assessment**: Parcels and zoning are reference data. Use Permits (Layer 66) is potentially interesting for tracking data center special exception approvals. The Technology Overlay District (Layer 60) identifies areas designated for tech/DC use. You'd need to cross-reference parcel use codes with zoning to identify data center parcels since there's no explicit "data center" flag in the parcel layer.

---

#### Source 12: PWC Open Data Portal (ArcGIS Hub)

| Attribute | Detail |
|---|---|
| **URL** | `https://gisdata-pwcgov.opendata.arcgis.com/` |
| **Cost** | Free |
| **Format** | Downloadable datasets (CSV, Shapefile, GeoJSON, KML) |
| **Programmatic?** | Yes — direct download links |

**Honest assessment**: This is a download portal for the same layers available via the REST API. Useful for bulk downloads but the REST API is better for monitoring.

---

### HENRICO COUNTY

#### Source 13: Henrico Monthly Building Permits

| Attribute | Detail |
|---|---|
| **URL Pattern** | `https://henrico.gov/public-data/building-permits-{month}-{year}/` |
| **Index** | `https://henrico.gov/public-data/categories/plans-development/` |
| **Cost** | Free |
| **Format** | Downloadable spreadsheets (Excel) and PDFs |
| **Update Frequency** | Monthly |
| **Programmatic?** | Semi — predictable URL pattern, but format is Excel/PDF not JSON |

**What it provides**:
- Building permits by job address, owner, contractor
- Trade permits (electrical, mechanical, plumbing, etc.)
- Permits by census category with values

```python
"""Download Henrico County monthly building permit data."""
import requests
from datetime import datetime

def fetch_henrico_permits_page(year: int, month: str) -> str | None:
    """
    Check if a permits page exists for a given month.
    month: lowercase full name, e.g. "january", "february"
    """
    url = f"https://henrico.gov/public-data/building-permits-{month}-{year}/"
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        return resp.text  # parse for download links
    return None

# To find spreadsheet download links, parse the HTML for .xlsx or .xls links.
# The actual spreadsheets contain rows like:
#   Job Address | Job Info | Owner | Contractor | Permit Type | Value
# Filter for "data center" in Job Info or Owner fields.
```

**Signal value**: MEDIUM. Monthly permit data can reveal new data center construction starts in Henrico (especially around White Oak Technology Park). But you need to download Excel files and filter — not a clean API.

---

#### Source 14: Henrico GIS Portal

| Attribute | Detail |
|---|---|
| **Open Data Hub** | `https://data-henrico.opendata.arcgis.com` |
| **ArcGIS Services** | `https://portal.henrico.us/hosting/rest/services/` |
| **Cost** | Free |
| **Programmatic?** | Limited |

**Available layers** (from REST services):
- Basemaps, routing, geocoding, DPW utilities
- Hosted layers: flood zones, soils, survey forms
- ZoningViewer vector tiles

**Honest assessment**: Henrico's GIS is much less developed than Loudoun or PWC for data center tracking. There is NO dedicated data center layer, no building permit API, and no zoning query service with use codes. The open data hub returned minimal results. Henrico recently adopted a White Oak Technology Park Area Overlay District (WOTPA-O) zoning, but this hasn't appeared as a queryable GIS layer yet. For Henrico, your best bet is the monthly permit spreadsheets (Source 13) and Board of Supervisors meeting minutes.

---

## Summary: What Actually Works

### Tier 1 — Fully Programmatic, High Value (build collectors for these)

| Source | Type | Update Freq | Python Access |
|---|---|---|---|
| **Loudoun BuildOut `COM_DATA_CENTER`** | ArcGIS REST | Quarterly | `requests.get()` → JSON |
| **PWC DC Opportunity Zone** | ArcGIS REST | As changed | `requests.get()` → JSON |
| **VEDP Press Releases** (via sitemap) | XML + HTML | As announced | Sitemap parse → scrape |
| **PWC Data Center Map** (once endpoint found) | ArcGIS REST | Ongoing | `requests.get()` → JSON |

### Tier 2 — Semi-Programmatic, Medium Value (scrape with caveats)

| Source | Type | Update Freq | Challenge |
|---|---|---|---|
| **MEI Annual Reports** | PDF | Annual | PDF extraction needed |
| **Governor's Press Releases** | HTML | As events | Fragile HTML scraping |
| **Henrico Monthly Permits** | Excel | Monthly | Excel download + parse |
| **PWC Parcels/Zoning/Use Permits** | ArcGIS REST | Ongoing | No explicit DC flag; cross-reference needed |

### Tier 3 — Reference Only (not monitoring sources)

| Source | Type | Why It's Reference |
|---|---|---|
| **JLARC Data Center Report** | PDF | One-time study, incredible stats |
| **Loudoun Zoning Map** | ArcGIS REST | Background reference |
| **VA Sales Tax Exemption Data** | Does not exist publicly | Would need FOIA |

### What Does NOT Exist (despite what you might hope)

1. **No Virginia-wide data center permit database** — each county tracks independently
2. **No MEI Commission API** — annual PDF reports only
3. **No sales tax exemption recipient list** — confidential tax data
4. **No VEDP API** — sitemap + scraping is best option
5. **No Henrico data center GIS layer** — despite being a growing DC market
6. **No commercial building permit API** for any county — Loudoun/PWC permit endpoints are residential-only; commercial permits are tracked in the land use/structures layer (Loudoun) or planning office databases (PWC/Henrico)
7. **No Governor's office RSS feed** — pure HTML scraping

### Recommended Collection Strategy

For Iren's collector pipeline, prioritize:

1. **New collector: `loudoun_dc_collector.py`** — poll the BuildOut_LandUse endpoint weekly for `COM_DATA_CENTER` changes (new records, status changes, sq ft changes). This is your single best structured data source.

2. **New collector: `vedp_collector.py`** — parse VEDP sitemap monthly, fetch new press releases, filter for data center keywords. Produces funding/expansion signals.

3. **Enhance `news_collector.py`** — add `site:governor.virginia.gov` and `site:vedp.org` as search targets for your Google News queries.

4. **PWC DC Map** — once the feature service endpoint is identified, add as a companion to the Loudoun collector.

5. **Quarterly manual check** — download MEI annual report PDF and Henrico permit spreadsheets for enrichment. These aren't worth building automated collectors for given their low frequency and format challenges.
