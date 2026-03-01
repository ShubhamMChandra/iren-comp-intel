# Iren Sales Intelligence Platform

## Executive Summary

Iren Sales Intelligence is a signal-driven GTM platform that detects infrastructure buying signals across 396 prospect companies using 19 collectors on free public data sources. It maps signals to the buyer journey — detecting need before budget, and budget before evaluation — to give Iren's commercial team a timing advantage on $10M+ infrastructure deals. The platform runs on a four-tier AI cost model (free local embeddings, $0.15/run collection, on-demand analysis, premium daily digest via Opus 4.6) with a total budget of $15, replacing the function of a $15K/month data vendor subscription. Every AI feature degrades gracefully to keyword fallbacks — the tool is fully operational with zero LLM spend.

---

## GTM Signal Strategy

Iren sells three products into three buyer profiles. Each has distinct lead indicators, sales cycles, and signal signatures.

**AI Cloud** — Mid-market ($100M–$1B). GPU hours as a service. Buyers are AI labs and startups scaling training runs.

- Lead indicators: hiring ML infrastructure roles, publishing large-scale papers, scaling GitHub infra repos, closing funding rounds
- Sales cycle: 3–6 months. Signal-to-deal is fast because these buyers have urgent compute needs and short procurement cycles
- Primary signals: `hiring`, `ai_initiative`, `fundraising`

**Colocation** — Enterprise ($1B+). Own the rack. Buyers are companies repatriating cloud workloads or building on-prem AI infrastructure.

- Lead indicators: CEO mentions AI infrastructure on earnings calls, hiring VP Infrastructure, cloud cost pressure, provider dissatisfaction
- Sales cycle: 6–12 months. Longer procurement, facilities planning, power negotiation
- Primary signals: `cloud_spend`, `outgrowing`, `hiring`

**Build-to-Suit** — Hyperscaler ($10B+). Entire campuses. Buyers are hyperscalers and sovereign AI programs needing GW-scale capacity faster than they can build it.

- Lead indicators: CAPEX guidance on earnings calls, massive GPU orders, construction hiring, multi-billion funding rounds
- Sales cycle: 12–24 months. Board-level decisions, long construction timelines
- Primary signals: `funding_completed`, `fundraising`, `cloud_spend`

The scoring engine weights signals by product fit so reps know who to call, why, and by when. Each signal carries an urgency level (URGENT / HIGH / MEDIUM) and a computed engagement window.

---

## Scoring Model

6 signal categories. Max 100 points. Exponential recency decay.

| Signal | Buyer Stage | Urgency | Why It Matters |
|---|---|---|---|
| Hiring | Need Detected | MEDIUM | Strongest leading indicator — accumulates per posting, reflects sustained buildout pressure |
| Fundraising | Budget Available | HIGH | Time-sensitive window; decays fastest because the timing narrows as a round closes |
| Cloud Spend | Need Detected | MEDIUM | Repatriation opportunity; slower decay reflects longer decision cycle |
| Funding Completed | Budget Available | HIGH | Capital deployed — infrastructure purchasing follows |
| AI Initiative | Need Detected | MEDIUM | Training runs, model launches, scaling compute |
| Outgrowing | Actively Evaluating | URGENT | In-market now; shortest decay, highest urgency |

The scoring is not a signal count. It is a **decay function that surfaces timing**.

**Formula:** `points = base_points × recency_decay × magnitude_multiplier × source_confidence`, capped per category.

**Recency decay** is exponential with per-signal-type half-lives that encode how fast a signal loses decision relevance. Fundraising and outgrowing decay fastest because they represent narrow timing windows. Cloud spend decays slowest because repatriation decisions unfold over quarters.

**Magnitude multipliers** scale funding signals nonlinearly based on round size — small rounds score below baseline, large rounds above — with fundraising multipliers slightly more aggressive than completed-funding because an active raise is a timing signal.

**Source confidence** discounts unreliable origins in order: SEC filing → major news → industry news → blog → social media → rumor.

**Why hiring is weighted highest:** Infrastructure job postings are the strongest leading indicator of capacity buildout. Unlike funding signals (one-off events), hiring accumulates — a company posting multiple GPU infra roles generates more sustained signal pressure than a single funding announcement.

**Engagement windows** — the period where outreach has the highest conversion probability:

| Signal | Window | Action Insight |
|---|---|---|
| Outgrowing | Weeks–months | Provider dissatisfaction. They are in-market now. Competitive displacement. |
| Funding Completed | 30–120 days | Capital deployed. Infrastructure purchasing follows within one quarter. |
| Fundraising | 60–90 days | Active raise. Position Iren before the round closes. |
| Hiring | 3–6 months | Capacity buildout coming. Start technical conversations now. |
| AI Initiative | 3–9 months | Growing compute demand. Engage early on workload requirements. |
| Cloud Spend | 6–12 months | Repatriation opportunity. Lead with TCO analysis. |

**Score deltas** track movement over time. The system stores a scored snapshot on each scoring run and computes the delta between the two most recent scores. A rep doesn't just see "Anthropic: 78/100" — they see "Anthropic: 78/100, +12 this week." That delta is often more actionable than the absolute score.

---

## Competitive Intelligence

24 competitors tracked across 6 named segments. Each competitor is profiled with key customers, pricing intel, strengths, weaknesses, and an Iren-relative threat level (high/medium/low).

| Segment | Competitors | Iren Positioning |
|---------|------------|------------------|
| Neocloud | CoreWeave, Crusoe, Lambda, Nebius, Voltage Park, etc. | Iren supplies the infrastructure neoclouds run on — they are both customers and competitors |
| Hyperscaler | AWS, Google Cloud | Iren builds overflow capacity when demand exceeds their DC pipeline |
| DC REIT | Equinix, Digital Realty, QTS, CyrusOne, Vantage | Iren differentiates on AI-ready high-density design and renewable energy cost advantage |
| Power-First | Lancium, Applied Digital | Direct competitors — same energy-first playbook |
| International | Adani Group | Iren competes on US proximity and operational track record |
| Miner-to-HPC | Hut 8, Core Scientific, Cipher Mining, HIVE Digital, TeraWulf, Bit Digital | Direct peers — same Bitcoin-to-AI pivot. Iren differentiates on execution speed, customer quality, renewable energy |

**Prospect-level competitive context.** Every prospect's product fit maps to relevant competitor segments via `PRODUCT_FIT_TO_SEGMENTS`. When a rep opens a prospect, they see which competitors they're likely bidding against, recent competitive moves from those competitors, and Iren's positioning edge:

- `ai_cloud` → Neocloud + Hyperscaler + Miner-to-HPC
- `colocation` → DC REIT + Power-First
- `build_to_suit` → Power-First + DC REIT + Miner-to-HPC

**Deal threat detection.** The `/api/compete/deal-threats` endpoint cross-references the top third of prospects by score with competitor activity in their segment from the last 30 days. If a prospect is scoring high (active buying signals) AND a competitor in their segment just announced a deal, expansion, pricing change, or talent hire — that gets surfaced as a deal threat. This answers: "where do we have high-intent prospects AND active competitor movement at the same time?"

---

## Signal Deduplication

Collectors run on schedules and will encounter the same story from multiple sources. The dedup pipeline has two layers:

1. **Exact title match** — if a signal with the same title already exists for a company, skip it. Fast, no ML.
2. **Semantic similarity** — if Ollama is running, embed the signal title and compare against all existing embeddings for that company using cosine similarity. Threshold: 0.85. This catches cases like "Anthropic raises $3B Series D" and "Anthropic closes $3 billion funding round" — different titles, same event.

When Ollama is not available, the system falls back to exact-title-only dedup. No collector breaks, no errors — just slightly more duplicates that get cleaned up on the next run with embeddings enabled.

---

## AI Generation

Three types of AI-generated output, all grounded in the actual signals collected. No hallucinated context — every prompt is assembled from real database rows.

**Pre-call briefs.** The LLM receives structured context: company profile, inferred funding stage, product fit label, current score breakdown by category, recent signals, likely competitors (mapped from product fit to segment), competitor pricing intel, and recent competitor moves. Output structure: thesis, urgency, lead-with, decision makers, competitive context. Cached for 7 days.

**Outreach emails.** Same context assembly, optimized for a different output format — short, direct, signal-grounded. Under 120 words. References a specific recent signal in the opening hook.

**Battle cards.** Competitor-specific output that includes capacity, pricing, key customers, strengths/weaknesses, Iren's positioning angle, and objection handling for that segment. 500–700 words.

**Daily digest.** Premium tier (Opus 4.6 with adaptive thinking). Morning and afternoon editions with different lookback windows. Focused on actionable intelligence — not a summary, but a briefing. Cached for 12 hours.

---

## Data Architecture

19 collectors. All free public sources. Zero paid subscriptions.

### Need Detected

| Collector | Source | Signal Type | What It Finds |
|---|---|---|---|
| ATS | Greenhouse / Lever APIs | `hiring` | GPU, ML infra, data center job postings |
| GitHub | GitHub org activity | `ai_initiative` | Infrastructure repo scaling, new ML repos |
| ArXiv | ArXiv RSS feeds | `ai_initiative` | Large-scale training papers, benchmark publications |
| Cloud Blogs | AWS/GCP/Azure blogs | `ai_initiative`, `cloud_spend` | AI partnership announcements, spend signals |
| PeeringDB | PeeringDB API | `cloud_spend` | Network facility expansions, peering changes |
| Google Trends | Google Trends data | `ai_initiative` | Rising search interest in AI/compute terms |

### Budget Available

| Collector | Source | Signal Type | What It Finds |
|---|---|---|---|
| Funding | Google News regex | `fundraising`, `funding_completed` | Funding rounds with dollar amounts |
| SEC EDGAR | SEC EDGAR API | `fundraising`, `funding_completed` | S-1, 10-K, 8-K filings indicating capital raises |
| HackerNews | HN Algolia API | `fundraising`, `funding_completed` | Community discussion of funding events |
| EDGAR RSS | SEC EDGAR RSS feed | `fundraising`, `funding_completed` | Real-time filing notifications |

### Actively Evaluating

| Collector | Source | Signal Type | What It Finds |
|---|---|---|---|
| Earnings | Earnings call transcripts | `cloud_spend`, `outgrowing` | CAPEX guidance, cloud repatriation language |
| News | Industry RSS (DCK, DCD, TechCrunch, Reuters) | All types | Broad signal detection across trade press |
| HackerNews | HN Algolia API | `outgrowing` | Provider complaints, migration discussions |
| Press Releases | Company press release pages | All types | Direct company announcements |

### Competitive Intel

| Collector | Source | What It Creates |
|---|---|---|
| Competitive Intel | DuckDuckGo web search | `CompetitorEvent` rows: deal, expansion, pricing, talent |

### Virginia Market Intelligence

| Collector | Source | Signal Type | What It Finds |
|---|---|---|---|
| VEDP | VEDP press releases + sitemap | `cloud_spend`, `ai_initiative` | State-announced data center investments, site selection deals |
| Loudoun DC | Loudoun County ArcGIS BuildOut API | `cloud_spend` | New data center permits, construction status changes |
| PWC DC | Prince William County ArcGIS FeatureServer | `cloud_spend` | Data center buildings and campus projects, MW capacity |
| COF | VEDP COF/VJIP incentive PDF reports | `funding_completed` | Companies receiving Virginia deal-closing grants and workforce incentives |

---

## Four-Tier AI Cost Model

| Tier | Model | Cost | Function | Fallback |
|---|---|---|---|---|
| Free | Ollama `nomic-embed-text` (local) | $0 | Embeddings, semantic dedup, similar signal search | Exact-title dedup only |
| Bulk | Gemini 2.5 Flash (OpenRouter) | ~$0.15/run | Signal classification, article summaries | Keyword extraction |
| Analysis | Kimi K2 (OpenRouter) | ~$0.05/request | Briefs, outreach emails, battle cards | Falls back to Bulk |
| Premium | Opus 4.6 (OpenRouter) | ~$0.10/digest | Daily digest with adaptive thinking (2x/day) | Falls back to Analysis |

$15 total budget: ~$4.50 for 30 collection runs, ~$2.50 for 50 analysis requests, ~$6.00 for 60 daily digests, ~$2.00 buffer.

The fallback chain is strict and uni-directional: Premium → Analysis → Bulk → keywords. Bulk never escalates to Analysis on failure. Every AI call has a zero-cost fallback path, meaning the platform scores and surfaces prospects with no API keys configured.

---

## Degradation Layers

The platform is designed to be useful at every tier of infrastructure availability:

| Layer | When it's running | When it's not |
|---|---|---|
| Ollama (embeddings) | Semantic dedup, similar-signal search | Exact-title dedup only, keyword search |
| OpenRouter Bulk | LLM signal classification, summaries | Keyword/regex classification |
| OpenRouter Analysis | AI briefs, emails, battle cards | Static template briefs |
| OpenRouter Premium | AI daily digest | No digest (null response) |
| All collectors | 15 data pipelines feeding signals | Score from whatever signals exist |
| SQLite | Persistent signal + score history | Fresh start on re-seed |

---

## What This Enables

A rep's morning with this platform:

1. **Open the dashboard.** AI-generated morning digest: _"Anthropic published 3 new papers on scaling this week and posted 8 GPU infra roles. Score up +12. CoreWeave announced Dallas expansion — competitive alert."_

2. **Check the call list.** Rows colored by urgency. Each shows the "so what" and "by when." Outgrowing signals surface at the top.

3. **Click into Anthropic.** Score breakdown by category. Engagement window: _"Hiring signal — engage technical buyer in 3–6 months."_ Competitive context: likely bidding against CoreWeave and Lambda (Neocloud segment), with recent moves listed.

4. **Generate a pre-call brief.** AI produces: thesis (why they need Iren and which product), urgency (specific signal and timing), lead-with (opening line for the call), decision makers (titles and why), competitive context (who's pitching, Iren's angle) — all grounded in the signals actually collected.

5. **Draft outreach.** AI writes an email referencing the specific signals detected: the roles posted, the papers published, the funding announced. Under 120 words. Not salesy.

---

## Build Decisions

| Choice | Rationale |
|---|---|
| **SQLite** over Postgres | Portable, zero-config, single-file DB. 290 companies and thousands of signals fit comfortably. Easy to demo, easy to deploy. |
| **OpenRouter** over direct APIs | Model flexibility. Switch between Kimi K2, Gemini Flash, Opus 4.6, or any model by changing an env var. No vendor lock-in. |
| **Ollama** for embeddings | Zero cost, local execution, no data leaves the machine. Powers semantic dedup and search without API spend. |
| **Keyword fallbacks everywhere** | Every AI function works without an API key. The platform is fully useful with zero LLM budget. |
| **Free data sources only** | 15 collectors, all public APIs or RSS feeds. No Crunchbase, no ZoomInfo, no paid subscriptions. |
| **Recency decay over raw counts** | Signals lose relevance over time. A scoring model that reflects this surfaces timing, not just volume. |
| **Product data in config, not prompts** | `IREN_BENCHMARK` stores Iren's capacity, products, GPUs, locations, strengths, weaknesses. Every prompt reads from it via `_build_iren_context()`. When Iren's capacity changes, update one dict — every brief, email, and battle card reflects it. |
| **Strict fallback direction** | Premium → Analysis → Bulk → keywords. Never escalates upward on failure. Predictable cost ceiling. |
| **Brief caching (7 days)** | AI briefs are cached per-company in the DB. Avoids re-generating the same brief on every page load while keeping content reasonably fresh. Digests cache for 12 hours. |

---

## What I'd Build Next

- **CRM integration** (HubSpot/Salesforce) — sync prospect scores and signals bidirectionally, trigger workflows on score changes, auto-create tasks when urgency escalates
- **Slack/Teams alerts** — push high-urgency signals and call list changes to a channel in real time, with configurable thresholds per rep
- **Deal stage tracking** — close the loop from signal to meeting to proposal to win; measure which signal combinations predict pipeline progression
- **Win/loss feedback loop** — use deal outcomes to retrain scoring weights; answer "which signals actually predicted closed deals?" and adjust configuration accordingly
- **Virginia intelligence expansion** — the VEDP/Loudoun/PWC/COF layer covers the densest data center market in the US (Northern Virginia); extend the same pattern to other priority geographies (Texas, Arizona, Georgia) using state economic development APIs and county permit data
- **Multi-tenant deployment** — support multiple sales teams with isolated prospect lists, custom scoring configs, and role-based access; move from SQLite to Postgres for concurrent access
