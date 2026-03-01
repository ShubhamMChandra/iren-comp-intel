# Why: Tunable scoring params for each signal type
# Deps: None (pure data)
# How: Dicts of max points, base, halflife, thresholds

try:
    from private.scoring_config import (
        SIGNAL_WEIGHTS,
        MAGNITUDE_THRESHOLDS,
        SOURCE_CONFIDENCE_MULTIPLIER,
    )
except ImportError:
    SIGNAL_WEIGHTS = {
        "fundraising": {"max_points": 17, "base_points": 10, "recency_halflife_days": 30},
        "funding_completed": {"max_points": 17, "base_points": 10, "recency_halflife_days": 60},
        "hiring": {"max_points": 17, "base_points": 5, "recency_halflife_days": 45},
        "ai_initiative": {"max_points": 17, "base_points": 8, "recency_halflife_days": 45},
        "cloud_spend": {"max_points": 16, "base_points": 10, "recency_halflife_days": 60},
        "outgrowing": {"max_points": 16, "base_points": 8, "recency_halflife_days": 30},
    }
    MAGNITUDE_THRESHOLDS: dict[str, list[tuple[int, float]]] = {}
    SOURCE_CONFIDENCE_MULTIPLIER = {
        "sec_filing": 1.0,
        "major_news": 0.85,
        "industry_news": 0.7,
        "blog": 0.5,
        "social_media": 0.35,
        "rumor": 0.2,
    }
