"""
Timing window definitions per signal type.

Maps each signal type to an engagement window and strategic insight
that helps sales reps understand when and why to act.
"""

TIMING_WINDOWS = {
    "fundraising": {
        "window": "60-90 days",
        "insight": (
            "Active fundraise signals budget allocation ahead. "
            "Procurement conversations should begin now — by the time "
            "the round closes, IREN should already be in the evaluation set."
        ),
    },
    "funding_completed": {
        "window": "30-120 days",
        "insight": (
            "Capital recently deployed. Infrastructure purchasing decisions "
            "typically follow within one quarter. This is the highest-urgency "
            "window for outreach."
        ),
    },
    "hiring": {
        "window": "3-6 months",
        "insight": (
            "Infrastructure hiring signals capacity buildout in 3-6 months. "
            "Start technical conversations now so IREN is positioned before "
            "they commit to a provider."
        ),
    },
    "ai_initiative": {
        "window": "3-9 months",
        "insight": (
            "New AI initiative suggests growing compute demand. Engage early "
            "to understand workload requirements and position IREN's GPU "
            "availability."
        ),
    },
    "cloud_spend": {
        "window": "6-12 months",
        "insight": (
            "Cloud cost signals suggest potential repatriation opportunity. "
            "IREN colocation or AI Cloud can offer significant TCO savings."
        ),
    },
    "outgrowing": {
        "window": "1-3 months",
        "insight": (
            "Provider dissatisfaction is the most urgent signal. This prospect "
            "is actively looking for alternatives — prioritize immediate outreach."
        ),
    },
}


# Action insight templates per signal type for the signal → action chain.
# Placeholders: {company}, {amount}, {role}, {initiative}, {contact_title}, {product_fit}
ACTION_TEMPLATES = {
    "fundraising": {
        "so_what": "{company} is actively raising. Budget will be allocated to infrastructure within 60-90 days.",
        "action": "Begin relationship building. Position IREN before they commit to a competitor.",
    },
    "funding_completed": {
        "so_what": "{company} just closed funding. Infrastructure purchasing decisions follow within one quarter.",
        "action": "Request intro meeting. Share IREN AI Cloud pricing and available capacity.",
    },
    "hiring": {
        "so_what": "{company} is hiring infrastructure roles. This signals capacity buildout in 3-6 months.",
        "action": "Engage technical buyer. Share GPU cluster architecture reference and benchmark data.",
    },
    "ai_initiative": {
        "so_what": "{company} announced a new AI initiative. Growing compute demand means new capacity requirements.",
        "action": "Share relevant case study. Position IREN's offering for their workload profile.",
    },
    "cloud_spend": {
        "so_what": "{company} showing cloud cost pressure. Repatriation opportunity.",
        "action": "Lead with TCO analysis: IREN colo/AI Cloud vs. current cloud spend. Target CFO and VP Infrastructure.",
    },
    "outgrowing": {
        "so_what": "{company} outgrowing current provider. Actively evaluating alternatives.",
        "action": "URGENT: Immediate outreach. They are in-market NOW. Competitive displacement opportunity.",
    },
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
