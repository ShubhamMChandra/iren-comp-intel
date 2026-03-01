# Why: Scores prospects from collected signal data
# Deps: SQLAlchemy models, weights config, datetime
# How: Recency-decayed weighted sum per signal type

import math
from datetime import datetime, timezone

from sqlalchemy import func

from database.db import get_session
from database.models import Company, ProspectScore, Signal
from scoring.weights import (
    MAGNITUDE_THRESHOLDS,
    SIGNAL_WEIGHTS,
    SOURCE_CONFIDENCE_MULTIPLIER,
)


def _recency_decay(detected_at: datetime, halflife_days: float) -> float:
    """Exponential decay: returns a multiplier between 0 and 1."""
    now = datetime.now(timezone.utc)
    if detected_at.tzinfo is None:
        detected_at = detected_at.replace(tzinfo=timezone.utc)
    age_days = (now - detected_at).total_seconds() / 86400
    if age_days < 0:
        return 1.0
    return math.pow(0.5, age_days / halflife_days)


def _magnitude_multiplier(signal_type: str, magnitude: float) -> float:
    """
    Translate raw magnitude (e.g., dollar amount) to a score multiplier.
    Returns 1.0 if no thresholds defined for this signal type.
    """
    thresholds = MAGNITUDE_THRESHOLDS.get(signal_type)
    if not thresholds or not magnitude:
        return 1.0

    multiplier = 0.5  # baseline for any detected signal
    for threshold_value, mult in thresholds:
        if magnitude >= threshold_value:
            multiplier = mult
        else:
            break
    return multiplier


def _source_confidence(source_type: str) -> float:
    return SOURCE_CONFIDENCE_MULTIPLIER.get(source_type, 0.5)


def score_prospect(company_id: int, session=None) -> ProspectScore:
    """Compute and store a prospect's score based on all their signals."""
    own_session = session is None
    if own_session:
        session = get_session()

    signals = (
        session.query(Signal)
        .filter(Signal.company_id == company_id)
        .all()
    )

    category_scores = {st: 0.0 for st in SIGNAL_WEIGHTS}

    for signal in signals:
        weight_config = SIGNAL_WEIGHTS.get(signal.signal_type)
        if not weight_config:
            continue

        base = weight_config["base_points"]
        decay = _recency_decay(signal.detected_at, weight_config["recency_halflife_days"])
        magnitude = _magnitude_multiplier(signal.signal_type, signal.magnitude or 0)
        confidence = _source_confidence(signal.source_type)

        points = base * decay * magnitude * confidence
        category_scores[signal.signal_type] = min(
            category_scores[signal.signal_type] + points,
            weight_config["max_points"],
        )

    total = sum(category_scores.values())

    score = ProspectScore(
        company_id=company_id,
        total_score=round(total, 2),
        fundraising_score=round(category_scores.get("fundraising", 0), 2),
        funding_completed_score=round(category_scores.get("funding_completed", 0), 2),
        hiring_score=round(category_scores.get("hiring", 0), 2),
        ai_initiative_score=round(category_scores.get("ai_initiative", 0), 2),
        cloud_spend_score=round(category_scores.get("cloud_spend", 0), 2),
        outgrowing_score=round(category_scores.get("outgrowing", 0), 2),
    )

    session.add(score)
    session.commit()

    if own_session:
        session.close()

    return score


def score_all_prospects() -> list[ProspectScore]:
    """Recompute scores for every prospect in the database."""
    session = get_session()
    prospects = session.query(Company).filter(Company.company_type == "prospect").all()

    scores = []
    for prospect in prospects:
        score = score_prospect(prospect.id, session=session)
        scores.append(score)
        print(f"  {prospect.name}: {score.total_score:.1f}")

    session.close()
    return scores


def get_latest_scores(session) -> dict[int, ProspectScore]:
    """Fetch the most recent score for every prospect in a single query."""
    latest_subq = (
        session.query(
            ProspectScore.company_id,
            func.max(ProspectScore.scored_at).label("max_date"),
        )
        .group_by(ProspectScore.company_id)
        .subquery()
    )
    scores = (
        session.query(ProspectScore)
        .join(
            latest_subq,
            (ProspectScore.company_id == latest_subq.c.company_id)
            & (ProspectScore.scored_at == latest_subq.c.max_date),
        )
        .all()
    )
    return {s.company_id: s for s in scores}


def get_score_deltas(session) -> dict[int, float]:
    """
    Compare the two most recent scores per prospect.
    Returns {company_id: delta} where delta = latest - previous.
    """
    all_scores = (
        session.query(ProspectScore)
        .order_by(ProspectScore.company_id, ProspectScore.scored_at.desc())
        .all()
    )

    by_company: dict[int, list[ProspectScore]] = {}
    for s in all_scores:
        by_company.setdefault(s.company_id, []).append(s)

    deltas = {}
    for company_id, scores in by_company.items():
        if len(scores) >= 2 and scores[1].total_score > 0:
            deltas[company_id] = scores[0].total_score - scores[1].total_score
        elif len(scores) == 1 and scores[0].total_score > 0:
            # First-ever score — the whole score is the delta (came from nothing)
            deltas[company_id] = scores[0].total_score
        else:
            deltas[company_id] = 0.0

    return deltas
