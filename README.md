# Iren Sales Intelligence Platform

Signal-driven GTM intelligence for Iren's commercial team — 290 prospects across 15 segments, 10 data collectors, AI-generated briefs, and a scoring engine that surfaces timing.

## The Problem

Iren sells $10M+ infrastructure deals — GPU cloud, colocation, build-to-suit data centers — to AI labs, enterprise companies, and hyperscalers. The commercial team tracks 290 prospects across segments from foundation model labs to quant trading firms to defense contractors. Manual signal tracking doesn't scale. By the time a rep reads about a funding round in the news, the prospect has already fielded five vendor calls. The companies that win these deals detect need before budget, and detect budget before evaluation.

This platform automates that. Public signals are collected continuously, scored for urgency, and translated into prioritized outreach with timing windows and recommended next actions.

## The Approach

Signal intelligence mapped to the buyer journey. Every prospect signal maps to one of three stages:

**Need Detected** — Company is scaling AI compute. Hiring infra engineers, publishing ML papers, pushing to GPU-related GitHub repos, announcing AI initiatives. They'll need capacity in 3–9 months.

**Budget Available** — Company just raised capital or has CAPEX allocated. SEC filings, funding news, earnings calls showing infrastructure spend. Procurement conversations start within a quarter.

**Actively Evaluating** — Company is outgrowing current provider. Capacity complaints, migration signals, vendor switching discussions. This is the highest-urgency window — they're in-market now.

10 data collectors pull from free public sources. A weighted scoring engine with exponential recency decay ranks prospects across 6 signal categories (max 100 points). AI-generated briefs surface what happened, why it matters, what to do, and by when. Three-tier LLM cost model runs the entire collection pipeline for ~$0.15/run.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  DATA SOURCES (all free)                                        │
│  RSS Feeds · Google News · SEC EDGAR · ATS (Greenhouse/Lever)   │
│  Earnings Transcripts · GitHub · ArXiv · Hacker News · Blogs    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  10 Collectors  │
                    │  (Python)       │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │  Signals DB (SQLite)    │
              │  + Ollama Embeddings    │  ← semantic dedup, similar signal search
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Scoring Engine         │
              │  recency decay ×        │
              │  magnitude × confidence │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  AI Layer               │
              │  briefs, emails,        │
              │  battle cards, digest   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  FastAPI (JSON API)     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Next.js Frontend       │
              └─────────────────────────┘
```

**LLM tiers:**

| Tier | Model | Cost | Role |
|------|-------|------|------|
| Free | Ollama `nomic-embed-text` (local) | $0 | Embeddings, dedup, semantic search |
| Bulk | Gemini 2.5 Flash | $0.30/$2.50 per M tokens | Signal classification, article summaries |
| Analysis | Kimi K2 | $0.55/$2.20 per M tokens | Briefs, outreach emails, battle cards |

Every AI call has a keyword-based fallback. The platform scores and surfaces prospects with zero API keys configured.

## Signal Framework

| Signal | Buyer Stage | Detects | Engagement Window | Iren Product Fit | Primary Collectors |
|--------|-------------|---------|-------------------|------------------|--------------------|
| Infrastructure Hiring | Need Detected | GPU/ML/infra job postings | 3–6 months | AI Cloud, Colo | ATS, HN, News |
| AI Initiatives | Need Detected | Model training, AI product launches | 3–9 months | AI Cloud | ArXiv, GitHub, News, Cloud Blogs |
| Cloud Spend | Need Detected | High cloud bills, cost optimization signals | 6–12 months | Colo | Earnings, Cloud Blogs |
| Active Fundraising | Budget Available | Currently raising — procurement starts soon | 60–90 days | AI Cloud, BTS | Funding, SEC, HN |
| Completed Funding | Budget Available | Round closed — infra purchasing within 1 quarter | 30–120 days | AI Cloud, BTS | Funding, SEC, HN |
| Outgrowing Provider | Actively Evaluating | Capacity complaints, provider switching | 1–3 months | All | HN, Earnings, News |

Each signal carries an urgency level (URGENT / HIGH / MEDIUM) and an action template — the full chain from "what happened" to "so what" to "do this" to "by when."

## Data Collectors

| Collector | Source | Signal Types | Cost |
|-----------|--------|-------------|------|
| `news` | RSS feeds (Data Center Dynamics, DCK, TechCrunch, Reuters) + Google News | All | Free |
| `funding` | Google News funding regex | fundraising, funding_completed | Free |
| `sec` | SEC EDGAR filings API | fundraising, funding_completed | Free |
| `jobs` | Google News job keyword detection | hiring | Free |
| `ats` | Greenhouse & Lever ATS APIs | hiring | Free |
| `earnings` | Earnings call transcripts | cloud_spend, ai_initiative, outgrowing | Free |
| `github` | GitHub API (repos, activity) | ai_initiative | Free |
| `arxiv` | ArXiv RSS (cs.AI, cs.LG, cs.CL) | ai_initiative | Free |
| `hn` | Hacker News API | hiring, fundraising, outgrowing | Free |
| `cloud_blogs` | AWS/GCP/Azure blog RSS | ai_initiative, cloud_spend | Free |

All collectors inherit from `BaseCollector` which handles session management, semantic dedup via Ollama embeddings, and per-item error isolation (one failed article doesn't skip the rest).

## Prospect Coverage

290 prospects across 15 segments, each tagged with a product fit (AI Cloud, Colocation, or Build-to-Suit):

| Segment | Count | Product Fit |
|---------|-------|-------------|
| AI Labs / Foundation Models | 10 | Build-to-Suit |
| Well-Funded AI Startups | 10 | AI Cloud |
| Enterprise AI / Large Tech | 8 | Colocation |
| Hyperscalers (Overflow) | 10 | Build-to-Suit |
| AI-Native (Inference, SaaS) | 32 | AI Cloud |
| AI Infrastructure (MLOps, Vector DBs, Serving) | 32 | AI Cloud |
| Enterprise Software Adding AI | 54 | Colocation |
| Biotech / Pharma | 29 | AI Cloud |
| Fintech / Quant Trading | 24 | Colocation |
| Gaming / Media | 19 | Colocation |
| Government / Defense | 17 | Colocation |
| Crypto / Web3 | 13 | AI Cloud |
| Mid-Market AI Adopters | 32 | AI Cloud |

**Product fit distribution:** 139 AI Cloud, 135 Colocation, 16 Build-to-Suit.

15 competitors tracked across 5 segments: Neoclouds, Hyperscaler Cloud, DC REITs, Power-First/Energy, and International players. Each competitor has a battle card with positioning, strengths/weaknesses, and key battleground metrics.

## Scoring Model

Each prospect is scored 0–100 across 6 categories. Formula per signal:

```
points = base_points × recency_decay × magnitude_multiplier × source_confidence
```

- **Recency decay**: exponential half-life per signal type (30–60 days). A hiring signal from last week scores higher than one from three months ago.
- **Magnitude multiplier**: tiered thresholds for funding amounts — a $1B raise scores 1.8× while a $50M raise scores 0.6×. Scales up to 2.0× at $5B+.
- **Source confidence**: SEC filing (1.0) → major news (0.85) → industry news (0.7) → blog (0.5) → social media (0.35) → rumor (0.2).
- **Category cap**: each signal type has a max_points ceiling. All caps sum to 100.

| Signal Type | Max Points | Base Points | Half-Life |
|-------------|-----------|-------------|-----------|
| Infrastructure Hiring | 25 | 3 per posting | 45 days |
| Active Fundraising | 20 | 15 | 30 days |
| AI Initiatives | 15 | 8 | 45 days |
| Completed Funding | 15 | 10 | 60 days |
| Cloud Spend | 15 | 10 | 60 days |
| Outgrowing Provider | 10 | 8 | 30 days |

Hiring is weighted highest (25 points) because infrastructure job postings are the strongest leading indicator of capacity buildout. Fundraising decays fastest (30-day half-life) because it's a time-sensitive timing signal — if you're not in the conversation within a month, you've missed the window.

## Frontend

Next.js 16 + React 19 + Tailwind CSS 4 + shadcn/ui. Four pages:

- **Today** — Dashboard with a prioritized call list, live funding tracker, competitor alerts, and the daily digest. The call list ranks prospects by score × urgency and shows the engagement window for each.
- **Prospects** — Filterable table (by segment, product fit, score range) with expandable detail sheets. Each prospect has an AI brief, engagement window, recommended contacts, and outreach email draft.
- **Compete** — Battle cards for each competitor segment. Side-by-side comparison on power density, campus scale, PUE, pricing, and NVIDIA allocation.
- **Admin** — Company management, scoring config, collector status, system health.

Signal cards display the full reasoning chain: **What happened** → **So what** → **Do this** → **By when**. Reps don't need to interpret signals — the platform tells them what the signal means for Iren and what the next action is.

## Quick Start

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env  # add OPENROUTER_API_KEY for AI features

# Seed prospects and run collectors
python -c "from database.seed import seed_database; seed_database()"
python -m collectors.runner

# Score all prospects
python -c "from scoring.engine import score_all_prospects; score_all_prospects()"

# API
cd api && pip install -r requirements.txt
uvicorn main:app --reload --port 8000 &
cd ..

# Frontend
cd frontend && npm install && npm run dev
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Ollama (optional): `ollama pull nomic-embed-text` then `python -m ai.embed_backfill` for semantic dedup

## Tech Stack

Python 3.14, FastAPI, SQLAlchemy 2.x, SQLite, OpenRouter (Kimi K2 + Gemini 2.5 Flash), Ollama (`nomic-embed-text`), Next.js 16, React 19, Tailwind CSS 4, shadcn/ui, Recharts, TanStack Table.

## Cost Model

Three tiers: **Free** (Ollama local, $0 for all embeddings), **Bulk** (Gemini 2.5 Flash at ~$0.15/collection run for classification and summaries), **Analysis** (Kimi K2 at ~$0.05/request for briefs and emails). Full collection run + 10 AI briefs = ~$0.65. $15 total budget covers 30+ full runs and 100+ user-facing briefs.

## Tests

```bash
python -m pytest tests/ -v  # no API keys or Ollama needed
```

All tests use in-memory SQLite and mocked embeddings. No external services required.
