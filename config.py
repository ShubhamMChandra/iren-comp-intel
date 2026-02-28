# Why: Central env vars, constants, enums
# Deps: os, pathlib, dotenv
# How: Reads .env then exports typed defaults

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'iren_intel.db'}")

# OpenRouter (OpenAI-compatible API) — used for all AI features
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Legacy OpenAI support (falls back to OpenRouter if not set)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") or OPENROUTER_API_KEY
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "") or AI_MODEL

# Ollama (local) — used for embeddings only
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

SEC_EDGAR_USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "IrenIntel research@iren.com",
)

NEWS_RSS_FEEDS = [
    "https://www.datacenterdynamics.com/en/rss/",
    "https://www.datacenterknowledge.com/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.reuters.com/technology/rss",
]

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

SIGNAL_TYPES = [
    "fundraising",
    "funding_completed",
    "hiring",
    "ai_initiative",
    "cloud_spend",
    "outgrowing",
    "other",
]

# Human-readable labels and descriptions for README scoring table (used by scripts/update_readme.py)
SIGNAL_LABELS = {
    "fundraising": "Active Fundraising",
    "funding_completed": "Completed Funding",
    "hiring": "Infrastructure Hiring",
    "ai_initiative": "AI Initiatives",
    "cloud_spend": "Cloud Spend",
    "outgrowing": "Outgrowing Provider",
}
SIGNAL_DESCRIPTIONS = {
    "fundraising": "Currently raising — timing signal for outreach",
    "funding_completed": "Recently closed a round — capacity signal",
    "hiring": "GPU/ML/infra job postings — strongest demand signal",
    "ai_initiative": "Model training, AI product launches",
    "cloud_spend": "High cloud bills, cost optimization signals",
    "outgrowing": "Capacity complaints, provider switching",
}

COMPETITOR_EVENT_TYPES = [
    "deal",
    "expansion",
    "pricing",
    "talent",
]

COMPANY_TYPES = ["prospect", "competitor"]

SOURCE_CONFIDENCE = {
    "sec_filing": 1.0,
    "major_news": 0.85,
    "industry_news": 0.7,
    "blog": 0.5,
    "social_media": 0.35,
    "rumor": 0.2,
}
