"""
Timing window definitions per signal type.

Maps each signal type to an engagement window and strategic insight
that helps sales reps understand when and why to act.
"""

try:
    from private.scoring_config import (
        TIMING_WINDOWS,
        ACTION_TEMPLATES,
        URGENCY_LEVELS,
    )
except ImportError:
    TIMING_WINDOWS = {
        "fundraising": {"window": "60-90 days", "insight": "Active fundraise — engage before round closes."},
        "funding_completed": {"window": "30-120 days", "insight": "Capital deployed — infra decisions follow within a quarter."},
        "hiring": {"window": "3-6 months", "insight": "Infra hiring signals capacity buildout."},
        "ai_initiative": {"window": "3-9 months", "insight": "New AI initiative — growing compute demand."},
        "cloud_spend": {"window": "6-12 months", "insight": "Cloud cost pressure — repatriation opportunity."},
        "outgrowing": {"window": "1-3 months", "insight": "Provider dissatisfaction — actively evaluating alternatives."},
    }

    ACTION_TEMPLATES = {
        "fundraising": {"so_what": "{company} is actively raising.", "action": "Begin relationship building."},
        "funding_completed": {"so_what": "{company} just closed funding.", "action": "Request intro meeting."},
        "hiring": {"so_what": "{company} is hiring infrastructure roles.", "action": "Engage technical buyer."},
        "ai_initiative": {"so_what": "{company} announced a new AI initiative.", "action": "Share relevant case study."},
        "cloud_spend": {"so_what": "{company} showing cloud cost pressure.", "action": "Lead with TCO analysis."},
        "outgrowing": {"so_what": "{company} outgrowing current provider.", "action": "Immediate outreach."},
    }

    URGENCY_LEVELS = {
        "outgrowing": "URGENT",
        "funding_completed": "HIGH",
        "fundraising": "HIGH",
        "hiring": "MEDIUM",
        "ai_initiative": "MEDIUM",
        "cloud_spend": "MEDIUM",
    }


def get_timing_window(signal_type: str) -> dict | None:
    """Return timing window data for a signal type."""
    return TIMING_WINDOWS.get(signal_type)


def get_action_insight(signal_type: str, company_name: str = "") -> str | None:
    """Generate a combined action insight string for a signal."""
    template = ACTION_TEMPLATES.get(signal_type)
    if not template:
        return None
    so_what = template["so_what"].format(company=company_name)
    action = template["action"]
    return f"{so_what} → {action}"


def get_urgency(signal_type: str) -> str:
    """Return urgency level for a signal type."""
    return URGENCY_LEVELS.get(signal_type, "LOW")
