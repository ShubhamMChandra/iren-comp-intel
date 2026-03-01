# VEDP Data Sources Research

**Date:** 2026-02-28
**Source:** vedp.org (Virginia Economic Development Partnership)
**Verdict:** VEDP is a **goldmine** for Virginia data center intelligence. Several sources are genuinely programmatically accessible.

---

## 1. Press Releases — BEST SOURCE

### What's Available
VEDP publishes press releases for every Governor-announced economic development project. These follow a **highly consistent format** with structured data embedded in prose.

### URL Pattern
```
https://www.vedp.org/press-release/{YYYY-MM}/{company-slug}
```
Examples:
- `https://www.vedp.org/press-release/2025-11/vantage-stafford`
- `https://www.vedp.org/press-release/2025-11/cleanarc-caroline`

### Data Fields Consistently Present
- **Company name** (always in title and first paragraph)
- **Investment amount** (always stated, e.g. "$2 billion", "$3 billion")
- **Locality/County** (always stated)
- **Job count** (always stated, e.g. "50 new jobs")
- **Facility details** (square footage, MW capacity for data centers)
- **Incentives received** (COF grants, VIP grants, VJIP, Data Center Sales Tax Exemption)
- **Governor/Secretary quotes** with strategic context
- **Company description** and history

### RSS Feed — CONFIRMED WORKING
```
https://www.vedp.org/rss.xml
```
Standard RSS 2.0 feed. Contains full HTML content of articles (not just summaries). Includes press releases AND VER magazine articles mixed together.

### Update Frequency
New press releases appear several times per month. Data center announcements cluster around major project wins.

### Programmatic Access: YES — Fully Accessible

```python
import feedparser
import re
from datetime import datetime

VEDP_RSS = "https://www.vedp.org/rss.xml"

def fetch_vedp_press_releases():
    """Fetch all items from VEDP RSS feed."""
    feed = feedparser.parse(VEDP_RSS)
    releases = []
    for entry in feed.entries:
        # Filter to press releases only (vs VER articles)
        if "/press-release/" in entry.link:
            releases.append({
                "title": entry.title,
                "url": entry.link,
                "published": entry.published,
                "summary": entry.get("summary", ""),
            })
    return releases

def extract_investment_data(title: str, summary: str) -> dict:
    """Extract structured data from press release text."""
    text = f"{title} {summary}"
    
    # Investment amount
    investment_match = re.search(
        r'\$([0-9,.]+)\s*(billion|million|B|M)', text, re.IGNORECASE
    )
    investment = None
    if investment_match:
        amount = float(investment_match.group(1).replace(",", ""))
        unit = investment_match.group(2).lower()
        if unit in ("billion", "b"):
            investment = amount * 1_000_000_000
        else:
            investment = amount * 1_000_000

    # Job count
    jobs_match = re.search(
        r'(?:create|creating|add|adding)\s+(?:more than\s+)?(\d[\d,]*)\s+(?:new\s+)?jobs',
        text, re.IGNORECASE
    )
    jobs = int(jobs_match.group(1).replace(",", "")) if jobs_match else None

    # Data center signal
    is_data_center = bool(re.search(
        r'data\s+center|hyperscale|colocation|MW|megawatt|gigawatt',
        text, re.IGNORECASE
    ))

    return {
        "investment_usd": investment,
        "jobs": jobs,
        "is_data_center": is_data_center,
    }

# Usage
releases = fetch_vedp_press_releases()
for r in releases:
    data = extract_investment_data(r["title"], r["summary"])
    if data["is_data_center"]:
        print(f"DC SIGNAL: {r['title']}")
        print(f"  Investment: ${data['investment_usd']:,.0f}" if data['investment_usd'] else "  Investment: unknown")
        print(f"  Jobs: {data['jobs']}")
        print(f"  URL: {r['url']}")
```

### Data Center Signal Value: EXCELLENT
Every data center press release includes investment $, jobs, locality, MW capacity, and which incentives were used. Recent examples:
- Vantage Data Centers: $2B, 50 jobs, Stafford County, 782MW statewide
- CleanArc Data Centers: $3B, 50 jobs, Caroline County, ~1GW capacity

---

## 2. COF Performance Reports — STRUCTURED TABULAR DATA

### What's Available
VEDP publishes **two PDF reports** for the Commonwealth's Opportunity Fund, updated semi-annually (as of 12/31/2024):

| Report | URL | Records |
|--------|-----|---------|
| Post-Performance Period | [PDF](https://www.vedp.org/sites/default/files/incentives/COF%20Post%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf) | ~70 projects (FY18-FY25) |
| Within Performance Period | [PDF](https://www.vedp.org/sites/default/files/incentives/COF%20Within%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf) | ~100+ active projects |

### Data Fields Per Project
- **Project number** (e.g., "2018-140024")
- **Company name** (real name, not anonymized)
- **Locality** (county/city)
- **Grant amount ($)**
- **Jobs target** and **actual jobs**
- **Capital investment target ($)** and **actual capital investment ($)**
- **Average annual wage target ($)** and **actual wage ($)**
- **Performance agreement date**
- **Performance date** (deadline)
- **Extension granted** (yes/no + reason)
- **Status** (Metrics Achieved / Clawback / Underperformed)

### Update Frequency
Semi-annual (reports as of 6/30 and 12/31 each year). URL pattern is predictable.

### Programmatic Access: PARTIALLY — PDF Extraction Required

```python
import requests
import tabula  # pip install tabula-py (requires Java)

COF_POST_URL = (
    "https://www.vedp.org/sites/default/files/incentives/"
    "COF%20Post%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf"
)
COF_WITHIN_URL = (
    "https://www.vedp.org/sites/default/files/incentives/"
    "COF%20Within%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf"
)

def download_cof_report(url: str, output_path: str) -> str:
    """Download COF report PDF."""
    resp = requests.get(url)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path

def parse_cof_pdf(pdf_path: str) -> list[dict]:
    """Extract tabular data from COF performance report PDF."""
    # tabula extracts tables from PDF into DataFrames
    dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
    
    projects = []
    for df in dfs:
        for _, row in df.iterrows():
            # Column mapping varies by report format — normalize here
            try:
                projects.append({
                    "project_number": str(row.iloc[0]),
                    "company": str(row.iloc[1]),
                    "locality": str(row.iloc[2]),
                    "grant_amount": row.iloc[3],
                    "jobs_target": row.iloc[4],
                    "capex_target": row.iloc[5],
                    "wage_target": row.iloc[6],
                })
            except (IndexError, ValueError):
                continue
    return projects

# Alternative: use pdfplumber for cleaner extraction
import pdfplumber

def parse_cof_with_pdfplumber(pdf_path: str) -> list[dict]:
    projects = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:  # skip header
                    if row and len(row) >= 7:
                        projects.append({
                            "project_number": row[0],
                            "company": row[1],
                            "locality": row[2],
                            "grant_amount": row[3],
                        })
    return projects
```

### Data Center Signal Value: HIGH
The COF reports name **every company** that received a deal-closing grant. Notable data center entry:
- **Microsoft BN 9-13**, Mecklenburg County, $1.5M COF grant, **$1.067B capital investment target**, 108 jobs

The "Within Performance" report shows the full pipeline of active projects before they've hit deadlines.

### Honest Assessment
The data is rich but locked in PDF tables. Extraction with `tabula-py` or `pdfplumber` works but requires column mapping since the PDF tables have merged cells and spanning headers. Worth the effort because the data is otherwise unavailable anywhere else.

---

## 3. VIP Performance Report — MANUFACTURER FOCUS

### What's Available
Single PDF report for Virginia Investment Performance grants:
```
https://www.vedp.org/sites/default/files/incentives/VIP%20Performance%20Report%2012-31-2024%20for%20Website.pdf
```

### Data Fields
Same structure as COF: company name, locality, grant amount, jobs/capex targets and actuals, performance stage.

### Update Frequency
Semi-annual, same cadence as COF.

### Data Center Signal Value: LOW
VIP is for manufacturers only. Data centers wouldn't appear here directly. But companies in the data center supply chain (cooling, power equipment) might — e.g., Condair (humidification), Modine (thermal management).

---

## 4. VJIP Performance Reports — MASSIVE DATASET

### What's Available
Two PDF reports for the Virginia Jobs Investment Program:

| Report | URL |
|--------|-----|
| Post-Performance | [PDF](https://www.vedp.org/sites/default/files/incentives/VJIP%20Post%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf) |
| Within Performance | [PDF](https://www.vedp.org/sites/default/files/incentives/VJIP%20Within%20Performance%20Period%20Report%2012-31-24%20for%20Website.pdf) |

### Data Fields Per Project
- **Project number**
- **Company name**
- **Locality**
- **Awarded grant amount ($)**
- **Actual grant amount paid ($)**
- **Reimbursement rate per job ($)**
- **New jobs target** and **actual new jobs**
- **Retrained jobs target** and **actual retrained**
- **Average hourly wage target ($)** and **actual hourly wage ($)**
- **Capital investment target ($)**
- **VJIP application date**
- **Date of first hire**
- **Performance date**

### Update Frequency
Semi-annual.

### Data Center Signal Value: MEDIUM
VJIP covers all industries. Data center operators and their suppliers appear when they receive workforce training grants. The dataset is huge (~500+ projects in post-performance alone).

---

## 5. Data Center Sales & Use Tax Exemption MOUs

### What's Available
VEDP administers the DCRSUT (Data Center Retail Sales & Use Tax Exemption). Every qualifying data center must sign an MOU with VEDP.

**MOU templates are public:**
- [Enterprise MOU Form (.docx)](https://www.vedp.org/sites/default/files/incentives/Enterprise%20MOU%20Form.docx)
- [Colocation MOU Form (.docx)](https://www.vedp.org/sites/default/files/incentives/Colocation%20MOU%20Form.docx)
- [Information Packet (.pdf)](https://www.vedp.org/sites/default/files/vedp-media/incentives/Information%20Packet_Resources.pdf)

### Are Executed MOUs Public?
**Not published online.** However, per VEDP's FOIA page, they are subject to FOIA requests. VEDP charges $36.85-$84.80/hour for search time. Key FOIA exemption risk: §2.2-3705.6(3) allows withholding proprietary business information provided under confidentiality promises.

**Bottom line:** You can FOIA the list of companies with active MOUs and basic terms (locality, investment thresholds). Specific financial details may be redacted. This is NOT programmatically accessible — it's a manual FOIA process.

### Data Center Signal Value: VERY HIGH (if obtainable)
The MOU list would be a definitive registry of every data center operator with tax exemptions in Virginia, including their investment and job commitments.

---

## 6. Annual Report — AGGREGATE ONLY

### What's Available
```
https://www.vedp.org/annual-report
```
Published on Issuu (not a downloadable data file). FY24 report contains:
- Total projects (620+)
- Total jobs (~103,000)
- Total CapEx ($103B+)
- VJIP client count (249)
- Rankings and testimonials

### Programmatic Access: NO
Hosted on Issuu as a magazine flipbook. Aggregate numbers only — no project-level data.

### Data Center Signal Value: LOW
Useful for macro trends ("VEDP-assisted projects brought $103B+ since 2018") but no company-specific data.

---

## 7. Incentives Policies & Procedures Document

### What's Available
```
https://www.vedp.org/sites/default/files/incentives/VEDP%20Incentives%20Policies%20and%20Procedures%202025%20FINAL%209.30.2025.pdf
```
Comprehensive PDF detailing all incentive program rules, thresholds, and procedures. Updated annually.

### Data Center Signal Value: LOW (reference only)
No company data. Useful for understanding eligibility thresholds (e.g., $150M minimum for data center tax exemption).

---

## 8. Local Prevailing Wages Worksheet

### What's Available
```
https://www.vedp.org/sites/default/files/incentives/Local%20Prevailing%20Salary%202025Q3%20%26%202024%20Poverty.xlsx
```
Excel file with prevailing wages and poverty rates for every Virginia locality.

### Data Fields
- Locality name
- Prevailing average annual wage
- Unemployment rate
- Poverty rate
- Distressed status (single/double)

### Update Frequency
Quarterly.

### Programmatic Access: YES — Direct Excel Download

```python
import requests
import pandas as pd

WAGES_URL = (
    "https://www.vedp.org/sites/default/files/incentives/"
    "Local%20Prevailing%20Salary%202025Q3%20%26%202024%20Poverty.xlsx"
)

def fetch_prevailing_wages() -> pd.DataFrame:
    """Download and parse the VEDP prevailing wages Excel file."""
    resp = requests.get(WAGES_URL)
    resp.raise_for_status()
    df = pd.read_excel(resp.content)
    return df
```

### Data Center Signal Value: LOW-MEDIUM
Cross-reference with data center localities to understand wage requirements and whether an area qualifies for distressed-locality thresholds.

---

## 9. Sitemap — Structured URL Discovery

### What's Available
```
https://www.vedp.org/sitemap.xml
```
Standard sitemap index with 2 sub-sitemaps (~3000 URLs). Every page on vedp.org is listed with `lastmod` dates.

### Programmatic Access: YES

```python
import requests
from xml.etree import ElementTree

def get_vedp_press_release_urls() -> list[dict]:
    """Extract all press release URLs from VEDP sitemap."""
    sitemap_index = requests.get("https://www.vedp.org/sitemap.xml").text
    root = ElementTree.fromstring(sitemap_index)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    press_releases = []
    for sitemap in root.findall("s:sitemap", ns):
        loc = sitemap.find("s:loc", ns).text
        sub_resp = requests.get(loc)
        sub_root = ElementTree.fromstring(sub_resp.text)
        for url_elem in sub_root.findall("s:url", ns):
            url = url_elem.find("s:loc", ns).text
            lastmod = url_elem.find("s:lastmod", ns)
            if "/press-release/" in url:
                press_releases.append({
                    "url": url,
                    "lastmod": lastmod.text if lastmod is not None else None,
                })
    return press_releases

# Then scrape each press release page for structured data
```

### Data Center Signal Value: HIGH
The sitemap gives you a complete inventory of every press release ever published. Combined with scraping, you can build a historical database of all announced projects.

---

## Summary: What's Actually Usable

| Source | Format | Programmatic? | Data Center Value | Effort |
|--------|--------|:---:|:---:|:---:|
| **RSS Feed** | XML/RSS 2.0 | **YES** | **Excellent** | Low |
| **Press Releases** (via sitemap + scraping) | HTML | **YES** | **Excellent** | Medium |
| **COF Performance Reports** | PDF tables | Partial (PDF parsing) | **High** | Medium |
| **VJIP Performance Reports** | PDF tables | Partial (PDF parsing) | Medium | Medium |
| **VIP Performance Report** | PDF tables | Partial (PDF parsing) | Low | Medium |
| **Prevailing Wages** | Excel (.xlsx) | **YES** | Low-Medium | Low |
| **Sitemap** | XML | **YES** | High (discovery) | Low |
| **Data Center MOUs** | FOIA only | **NO** | Very High | High (manual) |
| **Annual Report** | Issuu flipbook | **NO** | Low | N/A |
| **VEDIG Reports** | Not found online | **NO** | Medium | N/A |

---

## Recommended Collection Strategy for Iren

### Tier 1: Automated (build a collector)
1. **RSS feed polling** — Check `vedp.org/rss.xml` daily, filter for press releases, extract investment/jobs/locality with regex
2. **Sitemap-based historical scrape** — One-time scrape of all `/press-release/` URLs from sitemap, parse each for structured data
3. **Prevailing wages Excel** — Quarterly download for locality context

### Tier 2: Semi-automated (PDF parsing pipeline)
4. **COF reports** — Semi-annual PDF download + pdfplumber extraction. URL pattern is predictable (change date in filename)
5. **VJIP reports** — Same approach as COF
6. **VIP report** — Same approach

### Tier 3: Manual/FOIA
7. **Data Center MOU list** — File FOIA request with VEDP for list of all active DCRSUT MOUs. Cost: $36.85-$84.80/hr for search time. This would give you the definitive list of data center operators in Virginia.

---

## Key Data Center Findings from This Research

From the COF "Within Performance" report, **Microsoft** has an active project:
- **Microsoft BN 9-13**, Mecklenburg County
- COF grant: $1,500,000
- Capital investment target: **$1,066,755,918** (~$1.07B)
- Jobs target: 108
- Performance agreement date: 11/8/2018

From press releases:
- **Vantage Data Centers**: $2B, Stafford County, 782MW statewide capacity
- **CleanArc Data Centers**: $3B, Caroline County, ~1GW capacity

The DCRSUT exemption page reveals the thresholds that signal MAJOR commitments:
- Extension to 2040: $35B investment, 1,000 jobs
- Extension to 2050: $100B investment, 2,500 jobs
(Only the largest hyperscalers — AWS, Microsoft, Google — could hit these numbers)

---

## No API Exists

VEDP has **no public API, no JSON endpoints, and no structured data feeds** beyond the RSS feed. The site runs on Drupal (Pantheon-hosted: `live-vedp-d9.pantheonsite.io`). There are no GraphQL or REST endpoints exposed.

The RSS feed at `/rss.xml` is the only machine-readable endpoint. Everything else requires HTML scraping or PDF parsing.
