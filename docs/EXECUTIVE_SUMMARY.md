# Iren Sales Intelligence Platform

## Executive Summary

Iren Sales Intelligence is a signal-driven GTM platform that detects infrastructure buying signals across 290 prospect companies using 15 collectors on free public data sources. It maps signals to the buyer journey — detecting need before budget, and budget before evaluation — to give Iren's commercial team a timing advantage on $10M+ infrastructure deals. The platform runs on a four-tier AI cost model (free local embeddings, $0.15/run collection, on-demand analysis, premium daily digest via Opus 4.6) with a total budget of $15, replacing the function of a $15K/month data vendor subscription. Every AI feature degrades gracefully to keyword fallbacks — the tool is fully operational with zero LLM spend.

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

## Data Architecture

15 collectors. All free public sources. Zero paid subscriptions. Organized by the buyer journey stage they detect.

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

### Four-Tier AI Cost Model

| Tier | Model | Cost | Function |
|---|---|---|---|
| Free | Ollama `nomic-embed-text` (local) | $0 | Embeddings, semantic dedup, similar signal search |
| Bulk | Gemini 2.5 Flash (OpenRouter) | ~$0.15/run | Signal classification, article summaries |
| Analysis | Kimi K2 (OpenRouter) | ~$0.05/request | Briefs, outreach emails, battle cards |
| Premium | Opus 4.6 (OpenRouter) | ~$0.10/digest | Daily digest with adaptive thinking (2x/day, cached) |

$15 total budget: ~$4.50 for 30 collection runs, ~$2.50 for 50 analysis requests, ~$6.00 for 60 daily digests, ~$2.00 buffer. Premium falls back to analysis tier, analysis falls back to bulk, bulk falls back to keyword extraction. Every AI call has a zero-cost fallback path.

---

## Scoring Model

6 signal categories. Max 100 points. Exponential recency decay.

| Signal | Max Points | Base Points | Half-Life | Buyer Stage | Urgency |
|---|---|---|---|---|---|
| Hiring | 25 | 3 per posting | 45 days | Need Detected | MEDIUM |
| Fundraising | 20 | 15 | 30 days | Budget Available | HIGH |
| Cloud Spend | 15 | 10 | 60 days | Need Detected | MEDIUM |
| Funding Completed | 15 | 10 | 60 days | Budget Available | HIGH |
| AI Initiative | 15 | 8 | 45 days | Need Detected | MEDIUM |
| Outgrowing | 10 | 8 | 30 days | Actively Evaluating | URGENT |

The scoring is not a signal count. It is a **decay function that surfaces timing**.

A $2B raise yesterday scores differently than the same raise 90 days ago. Magnitude multipliers scale funding signals: $50M = 0.6x, $250M = 1.0x, $1B = 1.8x, $5B = 2.0x. Source confidence weights discount unreliable sources: SEC filing = 1.0, major news = 0.85, industry news = 0.7, blog = 0.5, social media = 0.35, rumor = 0.2.

Each signal type has a computed **engagement window** — the period where outreach has the highest conversion probability:

| Signal | Window | Action Insight |
|---|---|---|
| Outgrowing | 1–3 months | Provider dissatisfaction. They are in-market now. Competitive displacement. |
| Funding Completed | 30–120 days | Capital deployed. Infrastructure purchasing follows within one quarter. |
| Fundraising | 60–90 days | Active raise. Position Iren before the round closes. |
| Hiring | 3–6 months | Capacity buildout coming. Start technical conversations now. |
| AI Initiative | 3–9 months | Growing compute demand. Engage early on workload requirements. |
| Cloud Spend | 6–12 months | Repatriation opportunity. Lead with TCO analysis. |

---

## What This Enables

A rep's morning with this platform:

1. **Open the dashboard.** AI-generated morning digest: _"Anthropic published 3 new papers on scaling this week and posted 8 GPU infra roles. Score up +12. CoreWeave announced Dallas expansion — competitive alert."_

2. **Check the call list.** Rows colored by urgency. Each shows the "so what" and "by when." Outgrowing signals surface at the top.

3. **Click into Anthropic.** Engagement windows: _"Hiring signal — engage technical buyer in 3–6 months."_ Score story explains why the score moved and which signals drove the change.

4. **Generate a pre-call brief.** AI produces: thesis, urgency, lead-with, decision makers, competitive context — all grounded in the signals actually collected.

5. **Draft outreach.** AI writes an email referencing the specific signals detected: the roles posted, the papers published, the funding announced.

---

## Build Decisions

| Choice | Rationale |
|---|---|
| **SQLite** over Postgres | Portable, zero-config, single-file DB. 290 companies and thousands of signals fit comfortably. Easy to demo, easy to deploy. |
| **OpenRouter** over direct APIs | Model flexibility. Switch between Kimi K2, Gemini Flash, or any model by changing an env var. No vendor lock-in. |
| **Ollama** for embeddings | Zero cost, local execution, no data leaves the machine. Powers semantic dedup and search without API spend. |
| **Keyword fallbacks everywhere** | Every AI function works without an API key. The platform is fully useful with zero LLM budget. |
| **Free data sources only** | 15 collectors, all public APIs or RSS feeds. No Crunchbase, no ZoomInfo, no paid subscriptions. |
| **Recency decay over raw counts** | Signals lose relevance over time. A scoring model that reflects this surfaces timing, not just volume. |

---

## What I'd Build Next

- **CRM integration** (HubSpot/Salesforce) — sync prospect scores and signals bidirectionally, trigger workflows on score changes, auto-create tasks when urgency escalates
- **Slack/Teams alerts** — push high-urgency signals and call list changes to a channel in real time, with configurable thresholds per rep
- **Deal stage tracking** — close the loop from signal to meeting to proposal to win; measure which signal combinations predict pipeline progression
- **Win/loss feedback loop** — use deal outcomes to retrain scoring weights; answer "which signals actually predicted closed deals?" and adjust half-lives and base points accordingly
- **Multi-tenant deployment** — support multiple sales teams with isolated prospect lists, custom scoring configs, and role-based access; move from SQLite to Postgres for concurrent access
