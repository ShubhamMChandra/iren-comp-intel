# Iren Sales Intelligence Platform

Prospecting-first sales intelligence for Iren's commercial team. Scores and ranks prospect companies based on public signals (funding, hiring, AI initiatives), with a competitive intelligence layer for market context.

## Architecture

```
Python backend (collectors, scoring, AI)
    ├── FastAPI layer  →  Next.js frontend  (primary UI)
    └── Streamlit app                       (legacy UI)
```

- **Collectors** fetch data from RSS feeds, Google News, SEC EDGAR, and job boards
- **Scoring engine** computes a 0–100 score per prospect based on weighted signals with recency decay
- **AI layer** summarizes articles, classifies signals, and generates sales briefs (OpenRouter) with keyword fallbacks
- **Embeddings** power signal dedup and semantic search via Ollama (`nomic-embed-text`), with graceful no-op fallback

## Quick Start

### 1. Python backend

```bash
pip install -r requirements.txt

# Seed the database
python -c "from database.seed import seed_database; seed_database()"

# Collect signals, score prospects
python -m collectors.runner
python -c "from scoring.engine import score_all_prospects; score_all_prospects()"
```

### 2. API server

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 3. Next.js frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 4. (Legacy) Streamlit UI

```bash
streamlit run app.py
```

## AI Features (Optional)

Set your OpenRouter API key for AI-powered summaries, signal classification, prospect briefs, outreach emails, and battle cards:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

The platform works without it — every AI function falls back to keyword-based analysis automatically.

For semantic dedup and search, run Ollama locally:

```bash
ollama pull nomic-embed-text
# Then backfill embeddings for existing signals:
python -m ai.embed_backfill
```

## Scoring Model

| Signal | Max Points | What It Detects |
|--------|-----------|-----------------|
| Active Fundraising | 20 | Currently raising — timing signal for outreach |
| Completed Funding | 15 | Recently closed a round — capacity signal |
| Infrastructure Hiring | 25 | GPU/ML/infra job postings — strongest demand signal |
| AI Initiatives | 15 | Model training, AI product launches |
| Cloud Spend | 15 | High cloud bills, cost optimization signals |
| Outgrowing Provider | 10 | Capacity complaints, provider switching |

Scores decay exponentially with signal age; configurable half-lives per signal type in `scoring/weights.py`.

## Project Layout

```
app.py                  Streamlit entrypoint (legacy)
config.py               Env vars, constants, signal/source type enums
api/
  main.py               FastAPI JSON API wrapping the Python backend
frontend/               Next.js app (prospects, competitors, admin)
database/
  models.py             SQLAlchemy models: Company, Signal, ProspectScore, CompetitorEvent
  db.py                 Engine, SessionLocal, init_db(), get_session()
  seed.py               Initial prospect + competitor company data
collectors/
  base.py               BaseCollector with dedup + session management
  news_collector.py     RSS + Google News
  funding_collector.py  Funding signal regex classification
  jobs_collector.py     Infrastructure hiring keyword detection
  sec_collector.py      SEC EDGAR filings
  runner.py             CLI orchestrator
scoring/
  weights.py            Signal weight config (max_points, base_points, halflife)
  engine.py             Recency decay, magnitude multiplier, score_prospect()
ai/
  embeddings.py         Ollama-powered embeddings: dedup, semantic search
  summarizer.py         Article summarization (OpenRouter + fallback)
  signal_extractor.py   Signal classification (OpenRouter + fallback)
  brief_generator.py    Sales briefs, outreach emails, battle cards
pages/                  Streamlit pages (legacy)
tests/                  pytest suite with in-memory SQLite fixtures
```

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests use in-memory SQLite and mocked embeddings — no API keys or Ollama required.

## Publishing to GitHub (or other Git host)

From the project root:

```bash
git init
git add .
git commit -m "Initial commit: Iren Sales Intelligence Platform"
git branch -M main
git remote add origin https://github.com/YOUR_ORG/iren-comp-intel.git
git push -u origin main
```

Before pushing, ensure no secrets are committed: `.env`, `data/`, and `.venv/` are in `.gitignore`. Copy `.env.example` to `.env` locally and fill in any keys; never commit `.env`.
