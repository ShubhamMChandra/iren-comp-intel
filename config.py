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
    # Public fallback — all data sourced from iren.com, SEC filings, press releases
    IREN_BENCHMARK = {
        "name": "Iren",
        "industry": "AI Data Center / Energy",
        "capacity_mw": 4500,
        "gpu_count": 10900,
        "is_public": True,
        "ticker": "IREN",
        "exchange": "NASDAQ",
        "hq_location": "Sydney, Australia",
        "website": "https://iren.com",
        "key_customers": ["Microsoft", "Together AI", "FluidStack", "Fireworks AI"],
        "known_pricing": (
            "AI Cloud pricing via direct engagement. "
            "BTS power ~$0.028/kWh at Childress (spot), ~$0.05/kWh all-in West Texas. "
            "$9.7B Microsoft contract at ~$1.94B annualized revenue with 20% prepayment."
        ),
        "products": {
            "ai_cloud": "GPU-as-a-service for AI training and inference (3.2 TB/s InfiniBand, NVIDIA H100 through GB300)",
            "colocation": "High-density colocation with air, liquid, and direct-to-chip cooling (up to 200 kW/rack)",
            "build_to_suit": "Dedicated campus builds on 2,000+ owned acres with 2.75 GW locked grid power in West Texas",
        },
        "gpu_models": ["H100", "H200", "B200", "B300", "GB300 NVL72"],
        "locations": [
            "Childress, TX (750 MW)",
            "Sweetwater, TX (2,000 MW — two sites)",
            "Oklahoma (1,600 MW)",
            "Prince George, BC (160 MW)",
            "Mackenzie, BC",
            "Canal Flats, BC (30 MW)",
        ],
        "cooling": ["air", "liquid (including direct-to-chip for Blackwell, up to 200 kW/rack)"],
        "strengths": [
            "4.5 GW secured grid-connected power across North America",
            "$9.7B Microsoft contract — $1.94B annualized revenue, ~85% project margins",
            "NVIDIA Preferred Partner with 10.9K+ GPUs deployed, scaling to 140K by end 2026",
            "100% renewable energy across all facilities",
            "Vertically integrated: own land, grid connections, substations, data centers, and GPUs",
            "Low-cost power: $0.028/kWh at Childress (spot), ~$0.05/kWh all-in West Texas BTS",
            "Public company (NASDAQ: IREN) with $2.8B cash and $9.2B+ total funding secured in FY26",
        ],
        "weaknesses": [
            "Revenue still transitioning from Bitcoin mining (Q2 FY26 revenue down 23% on BTC decline)",
            "Execution risk: 140K GPU ramp across multiple simultaneous construction projects",
            "High stock volatility (beta >2.5, 52-week range ~$5–$77)",
            "Smaller operational footprint vs. Equinix/Digital Realty (810 MW operational of 4.5 GW secured)",
            "Near-term customer concentration as Microsoft contract dominates revenue",
        ],
        "expansion_plans": (
            "Sweetwater 1 (1.4 GW) energizing April 2026. "
            "Sweetwater 2 (600 MW) energizing late 2027. "
            "Oklahoma (1.6 GW) campus energizing 2028. "
            "Childress Horizon 1–4 (200 MW IT load) under construction for Microsoft ($9.7B deal). "
            "Targeting 140K GPUs and $3.4B ARR by end of calendar year 2026."
        ),
    }
    COMPETITOR_SEGMENTS: dict[str, str] = {
        "GPU Cloud": "Neocloud",
        "Neocloud": "Neocloud",
        "AI Cloud": "Neocloud",
        "Hyperscaler": "Hyperscaler",
        "REIT": "DC REIT",
        "Energy": "Power-First",
        "Power": "Power-First",
        "Conglomerate": "International",
        "Mining": "Miner-to-HPC",
        "HPC": "Miner-to-HPC",
    }
    SEGMENT_PROFILES: dict[str, dict[str, str]] = {
        "Neocloud": {
            "description": "GPU cloud providers selling compute-as-a-service to AI labs and enterprises",
            "iren_positioning": "Iren supplies the infrastructure neoclouds run on — they are both customers and competitors",
            "key_battleground": "GPU availability, NVIDIA allocation, pricing per GPU-hour, speed to deploy",
        },
        "Hyperscaler": {
            "description": "Mega-scale cloud platforms (AWS, GCP, Azure) with their own silicon and massive capex",
            "iren_positioning": "Iren builds overflow capacity for hyperscalers when demand exceeds their own DC pipeline",
            "key_battleground": "Scale (GW-level power), speed to deployment, location near grid capacity",
        },
        "DC REIT": {
            "description": "Data center REITs with large portfolios of colocation and wholesale facilities",
            "iren_positioning": "Iren differentiates on AI-ready high-density design and renewable energy cost advantage",
            "key_battleground": "Power density (kW/rack), campus scale, PUE, contract flexibility",
        },
        "Power-First": {
            "description": "Energy-native data center developers building on cheap/renewable power",
            "iren_positioning": "Direct competitors — Iren's renewable energy heritage is the same playbook",
            "key_battleground": "Power cost ($/kWh), MW pipeline, construction speed, energy source",
        },
        "International": {
            "description": "Global conglomerates and international players entering the AI data center market",
            "iren_positioning": "Iren competes on proximity to US demand centers and proven operational track record",
            "key_battleground": "Geography, regulatory approval, subsea connectivity, talent access",
        },
        "Miner-to-HPC": {
            "description": "Bitcoin miners pivoting to AI/HPC data centers — same origin story as Iren",
            "iren_positioning": "Direct peers with the same playbook. Iren differentiates on execution speed, renewable energy cost, and customer quality.",
            "key_battleground": "Pivot execution speed, HPC customer contracts, power cost, GPU deployment timeline",
        },
    }
    PRODUCT_FIT_TO_SEGMENTS: dict[str, list[str]] = {
        "ai_cloud": ["Neocloud", "Hyperscaler", "Miner-to-HPC"],
        "colocation": ["DC REIT", "Power-First"],
        "build_to_suit": ["Power-First", "DC REIT", "Miner-to-HPC"],
    }

COMPETITOR_SEGMENT_DEFAULT = "Data Center"
