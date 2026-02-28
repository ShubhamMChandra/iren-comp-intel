# Why: Tunable scoring params for each signal type
# Deps: None (pure data)
# How: Dicts of max points, base, halflife, thresholds

SIGNAL_WEIGHTS = {
    "fundraising": {
        "max_points": 20,
        "base_points": 15,
        "recency_halflife_days": 30,
    },
    "funding_completed": {
        "max_points": 15,
        "base_points": 10,
        "recency_halflife_days": 60,
    },
    "hiring": {
        "max_points": 25,
        "base_points": 3,  # per job posting — accumulates
        "recency_halflife_days": 45,
    },
    "ai_initiative": {
        "max_points": 15,
        "base_points": 8,
        "recency_halflife_days": 45,
    },
    "cloud_spend": {
        "max_points": 15,
        "base_points": 10,
        "recency_halflife_days": 60,
    },
    "outgrowing": {
        "max_points": 10,
        "base_points": 8,
        "recency_halflife_days": 30,
    },
}

MAGNITUDE_THRESHOLDS = {
    "funding_completed": [
        (50_000_000, 0.5),
        (100_000_000, 0.75),
        (250_000_000, 1.0),
        (500_000_000, 1.3),
        (1_000_000_000, 1.6),
        (5_000_000_000, 2.0),
    ],
    "fundraising": [
        (50_000_000, 0.6),
        (100_000_000, 0.8),
        (250_000_000, 1.0),
        (500_000_000, 1.4),
        (1_000_000_000, 1.8),
        (5_000_000_000, 2.0),
    ],
}

SOURCE_CONFIDENCE_MULTIPLIER = {
    "sec_filing": 1.0,
    "major_news": 0.85,
    "industry_news": 0.7,
    "blog": 0.5,
    "social_media": 0.35,
    "rumor": 0.2,
}
