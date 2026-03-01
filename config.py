# Why: Central env vars, constants, enums
# Deps: os, pathlib, dotenv
# How: Reads .env then exports typed defaults

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'iren_intel.db'}")

# CORS — wildcard in dev; set CORS_ORIGINS=https://app.example.com in production
CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()] or ["*"]

# Logging — INFO default; set LOG_LEVEL=DEBUG or VERBOSE=1 for verbose
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
if os.getenv("VERBOSE", "").strip().lower() in ("1", "true", "yes"):
    LOG_LEVEL = "DEBUG"

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

# HuggingFace Inference API — cloud fallback for embeddings when Ollama isn't running
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Four-tier LLM models (via OpenRouter)
AI_MODEL_BULK = os.getenv("AI_MODEL_BULK", "google/gemini-2.5-flash")
AI_MODEL_ANALYSIS = os.getenv("AI_MODEL_ANALYSIS", "") or AI_MODEL
AI_MODEL_PREMIUM = os.getenv("AI_MODEL_PREMIUM", "anthropic/claude-4.6-opus-20260205")

# Scheduler — UTC hour to run daily collection (default 7am UTC)
COLLECT_SCHEDULE_HOUR = int(os.getenv("COLLECT_SCHEDULE_HOUR", "7"))

SEC_EDGAR_USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "IrenIntel research@iren.com",
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

NEWS_RSS_FEEDS = [
    "https://www.datacenterdynamics.com/en/rss/",
    "https://www.datacenterknowledge.com/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
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

try:
    from private.iren_config import (
        IREN_BENCHMARK,
        COMPETITOR_SEGMENTS,
        SEGMENT_PROFILES,
        PRODUCT_FIT_TO_SEGMENTS,
    )
except ImportError:
    IREN_BENCHMARK = {
        "name": "ACME Corp",
        "industry": "Data Center / Energy",
        "capacity_mw": 0,
        "gpu_count": None,
        "is_public": False,
        "ticker": "",
        "exchange": "",
        "hq_location": "",
        "website": "",
        "key_customers": [],
        "known_pricing": "",
        "products": {
            "ai_cloud": "GPU-as-a-service",
            "colocation": "High-density colocation",
            "build_to_suit": "Dedicated campus builds",
        },
        "gpu_models": [],
        "locations": [],
        "cooling": [],
        "strengths": [],
        "weaknesses": [],
        "expansion_plans": "",
    }
    COMPETITOR_SEGMENTS: dict[str, str] = {}
    SEGMENT_PROFILES: dict[str, dict[str, str]] = {}
    PRODUCT_FIT_TO_SEGMENTS: dict[str, list[str]] = {
        "ai_cloud": [],
        "colocation": [],
        "build_to_suit": [],
    }

COMPETITOR_SEGMENT_DEFAULT = "Data Center"
