"""
FastAPI layer exposing the existing Python backend as JSON endpoints.
Thin wrapper — all business logic lives in the existing modules.
"""

import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import (
    CORS_ORIGINS,
    LOG_LEVEL,
    SIGNAL_TYPES,
    IREN_BENCHMARK,
    COMPETITOR_SEGMENTS,
    COMPETITOR_SEGMENT_DEFAULT,
    SEGMENT_PROFILES,
    PRODUCT_FIT_TO_SEGMENTS,
)

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pydantic import BaseModel

logger = logging.getLogger("iren.api")
_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(level=_level, format="%(levelname)s %(name)s %(message)s")

from database.db import get_session, init_db
from database.models import Company, CompetitorEvent, Contact, ProspectBrief, ProspectScore, Signal
from scoring.engine import get_latest_scores, get_score_deltas, score_all_prospects
from scoring.weights import SIGNAL_WEIGHTS
from scoring.timing import TIMING_WINDOWS, get_action_insight, get_urgency
from ai.brief_generator import generate_brief, generate_outreach_email, generate_battle_card
from ai.client import get_ai_client, call_premium, call_with_fallback
from ai.brief_generator import _build_iren_context, _funding_stage, PRODUCT_FIT_LABELS
from ai.embeddings import deserialize_embedding, cosine_similarity

init_db()

app = FastAPI(title="Iren Sales Intelligence API", version="1.0.0")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log each request: method, path, status, duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        logger.info("request %s %s", method, path)
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000)
        logger.info("response %s %s %s %dms", method, path, response.status_code, duration_ms)
        return response


app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Lightweight liveness check (no DB). Used by Railway healthcheck."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Naive UTC datetime for SQLite comparisons (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _company_dict(c: Company, score: ProspectScore | None = None, delta: float = 0.0) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "company_type": c.company_type,
        "industry": c.industry,
        "website": c.website,
        "description": c.description,
        "hq_location": c.hq_location,
        "employee_count": c.employee_count,
        "founded_year": c.founded_year,
        "is_public": c.is_public,
        "ticker": c.ticker,
        "product_fit": c.product_fit,
        "capacity_mw": c.capacity_mw,
        "gpu_count": c.gpu_count,
        "known_pricing": c.known_pricing,
        "total_funding": c.total_funding,
        "last_funding_amount": c.last_funding_amount,
        "score": _score_dict(score) if score else None,
        "delta": round(delta, 1),
    }


def _score_dict(s: ProspectScore) -> dict:
    return {
        "total": round(s.total_score, 1),
        "fundraising": round(s.fundraising_score, 1),
        "funding_completed": round(s.funding_completed_score, 1),
        "hiring": round(s.hiring_score, 1),
        "ai_initiative": round(s.ai_initiative_score, 1),
        "cloud_spend": round(s.cloud_spend_score, 1),
        "outgrowing": round(s.outgrowing_score, 1),
        "scored_at": s.scored_at.isoformat() if s.scored_at else None,
    }


def _signal_dict(s: Signal, company_name: str = "") -> dict:
    timing = TIMING_WINDOWS.get(s.signal_type)
    return {
        "id": s.id,
        "company_id": s.company_id,
        "company_name": company_name,
        "signal_type": s.signal_type,
        "title": s.title,
        "summary": s.summary,
        "source_url": s.source_url,
        "source_type": s.source_type,
        "magnitude": s.magnitude,
        "detected_at": s.detected_at.isoformat() if s.detected_at else None,
        "action_window": s.action_window or (timing["window"] if timing else None),
        "action_insight": s.action_insight or get_action_insight(s.signal_type, company_name),
        "urgency": get_urgency(s.signal_type),
        "timing_insight": timing["insight"] if timing else None,
    }


def _contact_dict(c: Contact) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "role_type": c.role_type,
        "seniority": c.seniority,
        "recommended_approach": c.recommended_approach,
        "name": c.name,
        "last_contacted": c.last_contacted.isoformat() if c.last_contacted else None,
    }


def _event_dict(e: CompetitorEvent) -> dict:
    return {
        "id": e.id,
        "company_id": e.company_id,
        "event_type": e.event_type,
        "title": e.title,
        "description": e.description,
        "source_url": e.source_url,
        "detected_at": e.detected_at.isoformat() if e.detected_at else None,
    }


def _tier_label(score: float, all_scores: list[float]) -> str:
    if not all_scores or score == 0:
        return "DORMANT"
    sorted_scores = sorted(all_scores)
    n = len(sorted_scores)
    low_rank = sum(1 for s in sorted_scores if s < score)
    high_rank = sum(1 for s in sorted_scores if s <= score)
    percentile = (low_rank + high_rank) / (2 * n)
    if percentile >= 0.90:
        return "VERY HIGH"
    if percentile >= 0.70:
        return "HIGH"
    if percentile >= 0.40:
        return "MEDIUM"
    if percentile >= 0.10:
        return "LOW"
    return "DORMANT"


def _top_signal_type(session, company_id: int) -> str | None:
    sig = (
        session.query(Signal)
        .filter(Signal.company_id == company_id, Signal.is_active == True, Signal.signal_type != "other")
        .order_by(Signal.detected_at.desc())
        .first()
    )
    return sig.signal_type if sig else None


def _signal_counts_7d(session, company_ids: list[int]) -> dict[int, int]:
    cutoff = _utcnow() - timedelta(days=7)
    results = (
        session.query(Signal.company_id, Signal.id)
        .filter(
            Signal.company_id.in_(company_ids),
            Signal.detected_at >= cutoff,
            Signal.signal_type != "other",
        )
        .all()
    )
    counts: dict[int, int] = {}
    for cid, _ in results:
        counts[cid] = counts.get(cid, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------

@app.get("/api/prospects")
def list_prospects():
    session = get_session()
    try:
        prospects = session.query(Company).filter(Company.company_type == "prospect").order_by(Company.name).all()
        score_map = get_latest_scores(session)
        deltas = get_score_deltas(session)
        all_scores = [s.total_score for s in score_map.values() if s.total_score > 0]
        sig_counts = _signal_counts_7d(session, [p.id for p in prospects])

        result = []
        for p in prospects:
            score = score_map.get(p.id)
            d = _company_dict(p, score, deltas.get(p.id, 0.0))
            d["tier"] = _tier_label(score.total_score if score else 0, all_scores)
            d["signals_7d"] = sig_counts.get(p.id, 0)
            d["top_signal_type"] = _top_signal_type(session, p.id)
            result.append(d)

        result.sort(key=lambda x: (x["score"]["total"] if x["score"] else 0), reverse=True)
        return result
    finally:
        session.close()


@app.get("/api/prospects/{prospect_id}")
def get_prospect(prospect_id: int):
    session = get_session()
    try:
        company = session.query(Company).filter(Company.id == prospect_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Prospect not found")

        score_map = get_latest_scores(session)
        deltas = get_score_deltas(session)
        all_scores = [s.total_score for s in score_map.values() if s.total_score > 0]
        score = score_map.get(company.id)

        d = _company_dict(company, score, deltas.get(company.id, 0.0))
        d["tier"] = _tier_label(score.total_score if score else 0, all_scores)

        signals = (
            session.query(Signal)
            .filter(Signal.company_id == company.id, Signal.is_active == True, Signal.signal_type != "other")
            .order_by(Signal.detected_at.desc())
            .limit(20)
            .all()
        )
        d["signals"] = [_signal_dict(s, company.name) for s in signals]

        # Contacts / stakeholders
        contacts = (
            session.query(Contact)
            .filter(Contact.company_id == company.id)
            .all()
        )
        d["contacts"] = [_contact_dict(c) for c in contacts]

        # Engagement windows — derive from recent signals
        engagement_windows = []
        seen_types: set[str] = set()
        for sig in signals:
            if sig.signal_type in seen_types:
                continue
            timing = TIMING_WINDOWS.get(sig.signal_type)
            if timing:
                seen_types.add(sig.signal_type)
                engagement_windows.append({
                    "signal_type": sig.signal_type,
                    "window": timing["window"],
                    "insight": timing["insight"],
                    "urgency": get_urgency(sig.signal_type),
                    "detected_at": sig.detected_at.isoformat() if sig.detected_at else None,
                })
        d["engagement_windows"] = engagement_windows

        cached_story = (
            session.query(ProspectBrief)
            .filter(
                ProspectBrief.company_id == company.id,
                ProspectBrief.brief_type == "score_story",
            )
            .order_by(ProspectBrief.generated_at.desc())
            .first()
        )
        d["score_story"] = cached_story.brief_text if cached_story else None

        return d
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

def _dedup_by_embedding(signals: list, same_company_threshold: float = 0.72, cross_company_threshold: float = 0.90) -> list:
    """
    Greedy dedup (most-recent first). Two thresholds:
    - same_company_threshold: more aggressive — collapses multiple articles
      about the same event within one company (e.g. 10 OpenAI $110B headlines)
    - cross_company_threshold: looser — only drops signals from different
      companies when they are nearly identical (rare)
    Falls back to keeping all signals when no embeddings are stored.
    """
    kept: list = []
    kept_embeddings: list[tuple[int, list[float]]] = []  # (company_id, embedding)
    for s in signals:
        emb = deserialize_embedding(s.embedding)
        if emb is None:
            kept.append(s)
            continue
        duplicate = False
        for kept_company_id, kept_emb in kept_embeddings:
            threshold = same_company_threshold if s.company_id == kept_company_id else cross_company_threshold
            if cosine_similarity(emb, kept_emb) >= threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(s)
            kept_embeddings.append((s.company_id, emb))
    return kept


@app.get("/api/signals")
def list_signals(
    signal_type: str | None = None,
    company_id: int | None = None,
    days: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=500),
    dedup: bool = Query(default=False),
):
    session = get_session()
    try:
        cutoff = _utcnow() - timedelta(days=days)
        fetch_limit = min(limit * 4, 500) if dedup else limit
        q = session.query(Signal).filter(
            Signal.detected_at >= cutoff,
            Signal.is_active == True,
            Signal.signal_type != "other",
        )
        if signal_type:
            q = q.filter(Signal.signal_type == signal_type)
        if company_id:
            q = q.filter(Signal.company_id == company_id)
        signals = q.order_by(Signal.detected_at.desc()).limit(fetch_limit).all()
        if dedup:
            signals = _dedup_by_embedding(signals)[:limit]
        company_names = {c.id: c.name for c in session.query(Company).all()}
        return [_signal_dict(s, company_names.get(s.company_id, "")) for s in signals]
    finally:
        session.close()


@app.get("/api/signals/stats")
def signal_stats(days: int = Query(default=7, ge=1, le=365)):
    session = get_session()
    try:
        cutoff = _utcnow() - timedelta(days=days)
        signals = (
            session.query(Signal)
            .filter(Signal.detected_at >= cutoff, Signal.is_active == True, Signal.signal_type != "other")
            .all()
        )
        by_type: dict[str, int] = {}
        for s in signals:
            by_type[s.signal_type] = by_type.get(s.signal_type, 0) + 1
        return {"period_days": days, "total": len(signals), "by_type": by_type}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Competitors
# ---------------------------------------------------------------------------

def _derive_segment(industry: str | None) -> str:
    """Map a company's industry string to a canonical competitor segment."""
    if not industry:
        return COMPETITOR_SEGMENT_DEFAULT
    upper = industry.upper()
    for keyword, segment in COMPETITOR_SEGMENTS.items():
        if keyword.upper() in upper:
            return segment
    return COMPETITOR_SEGMENT_DEFAULT


@app.get("/api/competitors")
def list_competitors():
    session = get_session()
    try:
        cutoff_30d = _utcnow() - timedelta(days=30)
        competitors = session.query(Company).filter(Company.company_type == "competitor").order_by(Company.name).all()

        result = []
        for c in competitors:
            d = _company_dict(c)
            d["segment"] = _derive_segment(c.industry)

            signals = (
                session.query(Signal)
                .filter(Signal.company_id == c.id)
                .order_by(Signal.detected_at.desc())
                .limit(5)
                .all()
            )
            d["signal_count_30d"] = sum(
                1 for s in signals if s.detected_at and s.detected_at >= cutoff_30d
            )
            events = (
                session.query(CompetitorEvent)
                .filter(CompetitorEvent.company_id == c.id)
                .order_by(CompetitorEvent.detected_at.desc())
                .limit(5)
                .all()
            )
            d["signals"] = [_signal_dict(s) for s in signals]
            d["events"] = [_event_dict(e) for e in events]
            result.append(d)

        iren = dict(IREN_BENCHMARK)
        iren["segment"] = _derive_segment(iren["industry"])

        return {"iren": iren, "competitors": result}
    finally:
        session.close()


@app.get("/api/competitors/{competitor_id}")
def get_competitor(competitor_id: int):
    session = get_session()
    try:
        company = session.query(Company).filter(Company.id == competitor_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Competitor not found")
        d = _company_dict(company)
        signals = (
            session.query(Signal)
            .filter(Signal.company_id == company.id)
            .order_by(Signal.detected_at.desc())
            .limit(10)
            .all()
        )
        events = (
            session.query(CompetitorEvent)
            .filter(CompetitorEvent.company_id == company.id)
            .order_by(CompetitorEvent.detected_at.desc())
            .limit(10)
            .all()
        )
        d["signals"] = [_signal_dict(s) for s in signals]
        d["events"] = [_event_dict(e) for e in events]
        return d
    finally:
        session.close()


def _parse_json_field(value: str | None) -> list:
    if not value:
        return []
    try:
        import json
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


@app.get("/api/compete/landscape")
def compete_landscape():
    session = get_session()
    try:
        cutoff_30d = _utcnow() - timedelta(days=30)
        competitors = session.query(Company).filter(Company.company_type == "competitor").order_by(Company.name).all()

        enriched = []
        segment_agg: dict[str, dict] = {}

        for c in competitors:
            seg = _derive_segment(c.industry)
            signal_count = (
                session.query(Signal)
                .filter(Signal.company_id == c.id, Signal.detected_at >= cutoff_30d)
                .count()
            )
            d = _company_dict(c)
            d["segment"] = seg
            d["signal_count_30d"] = signal_count
            d["key_customers"] = _parse_json_field(c.key_customers)
            d["strengths"] = _parse_json_field(c.strengths)
            d["weaknesses"] = _parse_json_field(c.weaknesses)
            d["threat_level"] = c.threat_level or "medium"
            enriched.append(d)

            if seg not in segment_agg:
                segment_agg[seg] = {"count": 0, "total_capacity_mw": 0}
            segment_agg[seg]["count"] += 1
            segment_agg[seg]["total_capacity_mw"] += c.capacity_mw or 0

        segments = []
        for seg_name, profile in SEGMENT_PROFILES.items():
            agg = segment_agg.get(seg_name, {"count": 0, "total_capacity_mw": 0})
            segments.append({
                "name": seg_name,
                "description": profile["description"],
                "iren_positioning": profile["iren_positioning"],
                "key_battleground": profile["key_battleground"],
                "competitor_count": agg["count"],
                "total_capacity_mw": agg["total_capacity_mw"],
            })

        all_events = (
            session.query(CompetitorEvent)
            .order_by(CompetitorEvent.detected_at.desc())
            .limit(30)
            .all()
        )
        all_signals = (
            session.query(Signal)
            .join(Company)
            .filter(
                Company.company_type == "competitor",
                Signal.detected_at >= cutoff_30d,
                Signal.signal_type != "not_relevant",
            )
            .order_by(Signal.detected_at.desc())
            .limit(30)
            .all()
        )
        company_names = {c.id: c.name for c in competitors}

        activity_feed = []
        for e in all_events:
            activity_feed.append({
                "type": "event",
                "event_type": e.event_type,
                "company_name": company_names.get(e.company_id, "Unknown"),
                "company_id": e.company_id,
                "title": e.title,
                "description": e.description,
                "source_url": e.source_url,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
            })
        for s in all_signals:
            activity_feed.append({
                "type": "signal",
                "event_type": s.signal_type,
                "company_name": company_names.get(s.company_id, "Unknown"),
                "company_id": s.company_id,
                "title": s.title,
                "description": s.summary or "",
                "source_url": s.source_url,
                "detected_at": s.detected_at.isoformat() if s.detected_at else None,
            })
        activity_feed.sort(key=lambda x: x["detected_at"] or "", reverse=True)

        iren = dict(IREN_BENCHMARK)
        iren["segment"] = _derive_segment(iren.get("industry"))

        return {
            "iren": iren,
            "competitors": enriched,
            "segments": segments,
            "activity_feed": activity_feed[:50],
        }
    finally:
        session.close()


@app.get("/api/prospects/{prospect_id}/competitive-context")
def prospect_competitive_context(prospect_id: int):
    session = get_session()
    try:
        prospect = session.query(Company).filter(Company.id == prospect_id, Company.company_type == "prospect").first()
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")

        pfit = prospect.product_fit or ""
        relevant_segments = PRODUCT_FIT_TO_SEGMENTS.get(pfit, list(SEGMENT_PROFILES.keys()))

        competitors = session.query(Company).filter(Company.company_type == "competitor").all()
        likely = []
        for c in competitors:
            seg = _derive_segment(c.industry)
            if seg in relevant_segments:
                likely.append({
                    "id": c.id,
                    "name": c.name,
                    "segment": seg,
                    "threat_level": c.threat_level or "medium",
                    "capacity_mw": c.capacity_mw,
                    "key_customers": _parse_json_field(c.key_customers),
                    "known_pricing": c.known_pricing,
                })

        comp_ids = [c["id"] for c in likely]
        cutoff_30d = _utcnow() - timedelta(days=30)
        recent_moves = []
        if comp_ids:
            events = (
                session.query(CompetitorEvent)
                .filter(CompetitorEvent.company_id.in_(comp_ids), CompetitorEvent.detected_at >= cutoff_30d)
                .order_by(CompetitorEvent.detected_at.desc())
                .limit(5)
                .all()
            )
            company_names = {c.id: c.name for c in competitors}
            for e in events:
                recent_moves.append({
                    "company_name": company_names.get(e.company_id, "Unknown"),
                    "event_type": e.event_type,
                    "title": e.title,
                    "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                })

        iren_edge = ""
        for seg in relevant_segments:
            profile = SEGMENT_PROFILES.get(seg)
            if profile:
                iren_edge = profile["iren_positioning"]
                break

        return {
            "prospect_name": prospect.name,
            "product_fit": pfit,
            "likely_competitors": likely,
            "recent_moves": recent_moves,
            "iren_edge": iren_edge,
        }
    finally:
        session.close()


@app.get("/api/compete/deal-threats")
def deal_threats():
    """Cross-reference high-score prospects with competing-segment activity."""
    session = get_session()
    try:
        cutoff_30d = _utcnow() - timedelta(days=30)

        score_map = get_latest_scores(session)
        all_scores = [s.total_score for s in score_map.values() if s.total_score > 0]
        if not all_scores:
            return {"threats": [], "total_at_risk": 0}

        threshold = sorted(all_scores, reverse=True)[len(all_scores) // 3] if len(all_scores) > 3 else 0
        high_score_ids = [cid for cid, s in score_map.items() if s.total_score >= threshold]

        prospects = (
            session.query(Company)
            .filter(Company.id.in_(high_score_ids), Company.company_type == "prospect")
            .all()
        )

        competitors = session.query(Company).filter(Company.company_type == "competitor").all()
        comp_by_segment: dict[str, list[Company]] = {}
        for c in competitors:
            seg = _derive_segment(c.industry)
            comp_by_segment.setdefault(seg, []).append(c)

        comp_names = {c.id: c.name for c in competitors}

        threats = []
        for p in prospects:
            pfit = p.product_fit or ""
            relevant_segments = PRODUCT_FIT_TO_SEGMENTS.get(pfit, [])
            if not relevant_segments:
                continue

            competing_ids = []
            for seg in relevant_segments:
                for c in comp_by_segment.get(seg, []):
                    competing_ids.append(c.id)

            if not competing_ids:
                continue

            recent_events = (
                session.query(CompetitorEvent)
                .filter(
                    CompetitorEvent.company_id.in_(competing_ids),
                    CompetitorEvent.detected_at >= cutoff_30d,
                )
                .order_by(CompetitorEvent.detected_at.desc())
                .limit(5)
                .all()
            )

            if not recent_events:
                continue

            score = score_map.get(p.id)
            threats.append({
                "prospect_id": p.id,
                "prospect_name": p.name,
                "product_fit": pfit,
                "score": round(score.total_score, 1) if score else 0,
                "tier": _tier_label(score.total_score if score else 0, all_scores),
                "competing_segments": relevant_segments,
                "recent_competitor_moves": [
                    {
                        "company_name": comp_names.get(e.company_id, "Unknown"),
                        "event_type": e.event_type,
                        "title": e.title,
                        "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                    }
                    for e in recent_events
                ],
            })

        threats.sort(key=lambda x: x["score"], reverse=True)

        return {"threats": threats, "total_at_risk": len(threats)}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def dashboard():
    session = get_session()
    try:
        prospects = session.query(Company).filter(Company.company_type == "prospect").all()
        score_map = get_latest_scores(session)
        deltas = get_score_deltas(session)
        all_scores = [s.total_score for s in score_map.values() if s.total_score > 0]

        cutoff_7d = _utcnow() - timedelta(days=7)
        cutoff_14d = _utcnow() - timedelta(days=14)

        actionable_signals_7d = (
            session.query(Signal)
            .filter(Signal.detected_at >= cutoff_7d, Signal.is_active == True, Signal.signal_type != "other")
            .count()
        )
        actionable_prior = (
            session.query(Signal)
            .filter(Signal.detected_at >= cutoff_14d, Signal.detected_at < cutoff_7d, Signal.is_active == True, Signal.signal_type != "other")
            .count()
        )

        active_count = sum(1 for s in score_map.values() if s.total_score > 0)

        hot_prospects = []
        for p in prospects:
            s = score_map.get(p.id)
            if s and _tier_label(s.total_score, all_scores) in ("VERY HIGH", "HIGH"):
                hot_prospects.append({
                    "id": p.id,
                    "name": p.name,
                    "score": round(s.total_score, 1),
                    "tier": _tier_label(s.total_score, all_scores),
                })
        hot_prospects.sort(key=lambda x: x["score"], reverse=True)
        hot_count = len(hot_prospects)

        ranked = sorted(
            [(p, score_map.get(p.id), deltas.get(p.id, 0.0)) for p in prospects if score_map.get(p.id)],
            key=lambda x: x[1].total_score,
            reverse=True,
        )

        hottest = max(ranked, key=lambda x: abs(x[2]), default=None) if ranked else None

        signal_breakdown: dict[str, int] = {}
        cutoff_sigs = (
            session.query(Signal)
            .filter(Signal.detected_at >= cutoff_7d, Signal.is_active == True, Signal.signal_type != "other")
            .all()
        )
        for sig in cutoff_sigs:
            signal_breakdown[sig.signal_type] = signal_breakdown.get(sig.signal_type, 0) + 1

        def _score_breakdown(score: ProspectScore) -> dict:
            return {
                "fundraising": round(score.fundraising_score, 1),
                "funding_completed": round(score.funding_completed_score, 1),
                "hiring": round(score.hiring_score, 1),
                "ai_initiative": round(score.ai_initiative_score, 1),
                "cloud_spend": round(score.cloud_spend_score, 1),
                "outgrowing": round(score.outgrowing_score, 1),
            }

        def _latest_signal_info(company_id: int, company_name: str) -> dict:
            sig = (
                session.query(Signal)
                .filter(
                    Signal.company_id == company_id,
                    Signal.is_active == True,
                    Signal.signal_type != "other",
                )
                .order_by(Signal.detected_at.desc())
                .first()
            )
            if not sig:
                return {"headline": None, "action_insight": None, "urgency": None}
            return {
                "headline": sig.title,
                "action_insight": sig.action_insight or get_action_insight(sig.signal_type, company_name),
                "urgency": get_urgency(sig.signal_type),
            }

        def _primary_contact(company_id: int) -> dict | None:
            # Highest seniority technical contact
            seniority_order = {"c_suite": 0, "vp": 1, "director": 2}
            contacts = session.query(Contact).filter(Contact.company_id == company_id).all()
            if not contacts:
                return None
            tech_contacts = [c for c in contacts if c.role_type == "technical"]
            target = tech_contacts if tech_contacts else contacts
            target.sort(key=lambda c: seniority_order.get(c.seniority, 99))
            c = target[0]
            return _contact_dict(c)

        call_list = []
        for company, score, delta in sorted(ranked, key=lambda x: x[2], reverse=True):
            if delta <= 0:
                break
            sig_info = _latest_signal_info(company.id, company.name)
            call_list.append({
                "id": company.id,
                "name": company.name,
                "industry": company.industry,
                "product_fit": company.product_fit,
                "score": round(score.total_score, 1),
                "tier": _tier_label(score.total_score, all_scores),
                "delta": round(delta, 1),
                "top_signal_type": _top_signal_type(session, company.id),
                "headline": sig_info["headline"],
                "action_insight": sig_info["action_insight"],
                "urgency": sig_info["urgency"],
                "primary_contact": _primary_contact(company.id),
                "score_breakdown": _score_breakdown(score),
            })
            if len(call_list) >= 8:
                break

        cooling = []
        for company, score, delta in sorted(ranked, key=lambda x: x[2]):
            if delta >= 0:
                break
            cooling.append({
                "id": company.id,
                "name": company.name,
                "industry": company.industry,
                "product_fit": company.product_fit,
                "score": round(score.total_score, 1),
                "tier": _tier_label(score.total_score, all_scores),
                "delta": round(delta, 1),
                "top_signal_type": _top_signal_type(session, company.id),
                "score_breakdown": _score_breakdown(score),
            })
            if len(cooling) >= 5:
                break

        top_ranked = []
        for company, score, delta in ranked[:10]:
            top_ranked.append({
                "id": company.id,
                "name": company.name,
                "industry": company.industry,
                "product_fit": company.product_fit,
                "score": round(score.total_score, 1),
                "tier": _tier_label(score.total_score, all_scores),
                "delta": round(delta, 1),
                "top_signal_type": _top_signal_type(session, company.id),
                "score_breakdown": _score_breakdown(score),
            })

        comp_events = (
            session.query(CompetitorEvent)
            .order_by(CompetitorEvent.detected_at.desc())
            .limit(5)
            .all()
        )
        all_companies = {c.id: c for c in session.query(Company).all()}
        alerts = []
        for e in comp_events:
            comp = all_companies.get(e.company_id)
            alerts.append({
                "company_name": comp.name if comp else "Unknown",
                "event_type": e.event_type,
                "title": e.title,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
            })

        return {
            "kpis": {
                "active_prospects": active_count,
                "pipeline_hot": hot_count,
                "hot_prospects": hot_prospects,
                "signals_7d": actionable_signals_7d,
                "signals_delta": actionable_signals_7d - actionable_prior,
                "signal_breakdown": signal_breakdown,
                "hottest_mover": {
                    "name": hottest[0].name,
                    "id": hottest[0].id,
                    "delta": round(hottest[2], 1),
                    "score": round(hottest[1].total_score, 1),
                    "top_signal_type": _top_signal_type(session, hottest[0].id),
                } if hottest else None,
            },
            "call_list": call_list,
            "cooling": cooling,
            "top_ranked": top_ranked,
            "alerts": alerts,
            "competitive_pulse": _competitive_pulse(session),
        }
    finally:
        session.close()


def _competitive_pulse(session) -> dict:
    cutoff_7d = _utcnow() - timedelta(days=7)
    events_7d = session.query(CompetitorEvent).filter(CompetitorEvent.detected_at >= cutoff_7d).count()
    competitor_signals = (
        session.query(Signal)
        .join(Company)
        .filter(Company.company_type == "competitor", Signal.detected_at >= cutoff_7d)
        .count()
    )
    competitor_companies = session.query(Company).filter(Company.company_type == "competitor").all()
    high_threat_count = sum(1 for c in competitor_companies if c.threat_level == "high")

    most_active_name, most_active_count = "None", 0
    for c in competitor_companies:
        cnt = (
            session.query(CompetitorEvent)
            .filter(CompetitorEvent.company_id == c.id, CompetitorEvent.detected_at >= cutoff_7d)
            .count()
        )
        if cnt > most_active_count:
            most_active_name, most_active_count = c.name, cnt

    return {
        "events_7d": events_7d,
        "signals_7d": competitor_signals,
        "most_active": most_active_name,
        "most_active_count": most_active_count,
        "high_threat_count": high_threat_count,
    }


DIGEST_SYSTEM_MSG = (
    "You are Iren's CRO writing the brief your VP of Sales reads before the team standup.\n\n"
    + _build_iren_context()
    + "\n\n"
    "YOUR JOB: You care about EVERY deal — a $2M AI Cloud contract from a growth startup "
    "matters because they will grow. You are building a book of business, not cherry-picking logos.\n\n"
    "RULES:\n"
    "1. Cover the full funnel. One sentence on early/growth-stage activity, one on enterprise, "
    "one action item. If a competitive threat displaces one, cut the weakest.\n"
    "2. Name names. Never say 'several companies.'\n"
    "3. Connect signals to Iren products. Hiring at an AI lab = future GPU demand (AI Cloud). "
    "Cloud spend at an enterprise = colo opportunity.\n"
    "4. Give the VP something to DO. Not 'monitor closely' — 'get [name] on the phone "
    "because [reason].'\n"
    "5. Prose only. No headers, no bullets, no bold. 3-4 sentences."
)

MORNING_FRAME = (
    "Here's the overnight data. Write my morning brief — what happened, "
    "who moved, and what the team should do first today."
)
AFTERNOON_FRAME = (
    "Here's what moved since this morning. Write my afternoon update — "
    "what changed, whose priority shifted, and how to close the day strong."
)


def _detect_digest_period() -> str:
    """Return 'morning' or 'afternoon' based on current UTC hour."""
    return "morning" if datetime.now(timezone.utc).hour < 14 else "afternoon"


def _build_digest_context(session, period: str) -> str:
    """Build the structured data block for the digest prompt."""
    now = _utcnow()
    signal_hours = 18 if period == "morning" else 8
    signal_cutoff = now - timedelta(hours=signal_hours)
    cutoff_7d = now - timedelta(days=7)

    prospects = session.query(Company).filter(Company.company_type == "prospect").all()
    all_companies = {c.id: c for c in session.query(Company).all()}

    signals = (
        session.query(Signal)
        .filter(Signal.detected_at >= signal_cutoff, Signal.is_active == True)
        .order_by(Signal.detected_at.desc())
        .limit(50)
        .all()
    )
    if len(signals) < 5:
        signals = (
            session.query(Signal)
            .filter(Signal.detected_at >= cutoff_7d, Signal.is_active == True)
            .order_by(Signal.detected_at.desc())
            .limit(50)
            .all()
        )

    score_map = get_latest_scores(session)
    deltas = get_score_deltas(session)

    movers = sum(1 for d in deltas.values() if abs(d) > 0.1)
    period_label = "overnight" if period == "morning" else "today"

    lines = [
        f"PIPELINE SNAPSHOT ({now.strftime('%Y-%m-%d')} {period}):",
        f"  {len(prospects)} prospects tracked | {movers} with score movement | {len(signals)} active signals",
        "",
        f"SIGNALS ({period_label}):",
    ]

    def _sort_key(sig):
        comp = all_companies.get(sig.company_id)
        if not comp:
            return 0
        return comp.total_funding or 0

    for s in sorted(signals[:30], key=_sort_key):
        comp = all_companies.get(s.company_id)
        if not comp:
            continue
        stage = _funding_stage(comp.total_funding, comp.is_public)
        pfit = PRODUCT_FIT_LABELS.get(comp.product_fit or "", "")
        size = f"~{comp.employee_count} ppl, " if comp.employee_count else ""
        funding = f"${comp.total_funding / 1e6:.0f}M raised" if comp.total_funding else ""
        meta_parts = [p for p in [stage, size, pfit, funding] if p]
        meta = f" ({', '.join(meta_parts)})" if meta_parts else ""
        lines.append(f"  [{s.signal_type}] {comp.name}{meta}: {s.title[:120]}")

    up_movers = sorted(
        [(cid, d) for cid, d in deltas.items() if d > 0.1],
        key=lambda x: -x[1],
    )[:5]
    down_movers = sorted(
        [(cid, d) for cid, d in deltas.items() if d < -0.1],
        key=lambda x: x[1],
    )[:3]

    lines.append("")
    lines.append("SCORE MOVERS:")
    if up_movers:
        parts = []
        for cid, d in up_movers:
            comp = all_companies.get(cid)
            score = score_map.get(cid)
            if comp and score:
                parts.append(f"{comp.name} {score.total_score:.1f} ({d:+.1f})")
        if parts:
            lines.append(f"  UP:   {' | '.join(parts)}")
    if down_movers:
        parts = []
        for cid, d in down_movers:
            comp = all_companies.get(cid)
            score = score_map.get(cid)
            if comp and score:
                parts.append(f"{comp.name} {score.total_score:.1f} ({d:+.1f})")
        if parts:
            lines.append(f"  DOWN: {' | '.join(parts)}")
    if not up_movers and not down_movers:
        lines.append("  No significant movement this period.")

    comp_events = (
        session.query(CompetitorEvent)
        .filter(CompetitorEvent.detected_at >= (now - timedelta(days=7)))
        .order_by(CompetitorEvent.detected_at.desc())
        .limit(5)
        .all()
    )
    if comp_events:
        lines.append("")
        lines.append("COMPETITIVE PULSE (7d):")
        for e in comp_events:
            comp = all_companies.get(e.company_id)
            name = comp.name if comp else "Unknown"
            lines.append(f"  {name}: {e.title[:150]}")

    return "\n".join(lines)


@app.get("/api/dashboard/digest")
def dashboard_digest(period: str | None = Query(None)):
    session = get_session()
    try:
        if period not in ("morning", "afternoon"):
            period = _detect_digest_period()

        brief_type = f"{period}_digest"
        cutoff = _utcnow() - timedelta(hours=12)
        cached = (
            session.query(ProspectBrief)
            .filter(ProspectBrief.brief_type == brief_type, ProspectBrief.generated_at >= cutoff)
            .order_by(ProspectBrief.generated_at.desc())
            .first()
        )
        if cached:
            return {"digest": cached.brief_text, "period": period}

        context_block = _build_digest_context(session, period)
        frame = MORNING_FRAME if period == "morning" else AFTERNOON_FRAME

        client = get_ai_client()
        if not client:
            return {"digest": None, "period": period}

        messages = [
            {"role": "system", "content": DIGEST_SYSTEM_MSG},
            {"role": "user", "content": f"{frame}\n\n{context_block}"},
        ]
        result = call_premium(client, messages, max_tokens=400, temperature=0.3)

        if result:
            brief = ProspectBrief(company_id=None, brief_text=result, brief_type=brief_type)
            session.add(brief)
            session.commit()

        return {"digest": result, "period": period}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------

class BriefRequest(BaseModel):
    company_id: int

@app.post("/api/briefs/generate")
def gen_brief(req: BriefRequest):
    text = generate_brief(req.company_id)
    return {"brief": text, "company_id": req.company_id}

@app.post("/api/briefs/email")
def gen_email(req: BriefRequest):
    text = generate_outreach_email(req.company_id)
    return {"email": text, "company_id": req.company_id}

@app.post("/api/briefs/battlecard")
def gen_battlecard(req: BriefRequest):
    text = generate_battle_card(req.company_id)
    return {"battlecard": text, "company_id": req.company_id}


# ---------------------------------------------------------------------------
# Search (AI-powered)
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str

@app.post("/api/search")
def smart_search(req: SearchRequest):
    session = get_session()
    try:
        prospects = session.query(Company).filter(Company.company_type == "prospect").all()
        score_map = get_latest_scores(session)
        all_scores = [s.total_score for s in score_map.values() if s.total_score > 0]

        query_lower = req.query.lower()
        name_matches = [p for p in prospects if query_lower in p.name.lower()]
        if name_matches:
            return [
                {"id": p.id, "name": p.name, "reason": "Name match", "score": score_map.get(p.id, None) and round(score_map[p.id].total_score, 1)}
                for p in name_matches[:10]
            ]

        client = get_ai_client()
        if not client:
            return []

        company_list = "\n".join(
            f"- {p.name} (industry: {p.industry}, score: {score_map.get(p.id) and round(score_map[p.id].total_score, 1) or 0})"
            for p in prospects
        )

        prompt = (
            f"The user asked: \"{req.query}\"\n\n"
            f"Here are all prospects:\n{company_list}\n\n"
            "Return a JSON array of the top 5 matching prospects. Each item should have: "
            '{"name": "...", "reason": "short reason why this matches"}. '
            "Only return the JSON array, nothing else."
        )

        result = call_with_fallback(client, [{"role": "user", "content": prompt}], max_tokens=300, temperature=0.2)

        if not result:
            return []

        import json
        try:
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            return []

        prospect_map = {p.name.lower(): p for p in prospects}
        matches = []
        for item in parsed[:10]:
            name = item.get("name", "")
            p = prospect_map.get(name.lower())
            if p:
                score = score_map.get(p.id)
                matches.append({
                    "id": p.id,
                    "name": p.name,
                    "reason": item.get("reason", "AI match"),
                    "score": round(score.total_score, 1) if score else 0,
                    "tier": _tier_label(score.total_score if score else 0, all_scores),
                })
        return matches
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.get("/api/admin/stats")
def admin_stats():
    session = get_session()
    try:
        return {
            "companies": session.query(Company).count(),
            "signals": session.query(Signal).filter(Signal.is_active == True).count(),
            "scores": session.query(ProspectScore).count(),
            "briefs": session.query(ProspectBrief).count(),
            "signal_distribution": {
                st: session.query(Signal).filter(Signal.signal_type == st, Signal.is_active == True).count()
                for st in SIGNAL_TYPES if st != "other"
            },
            "weights": {
                st: {"max_points": w["max_points"], "base_points": w["base_points"], "halflife": w["recency_halflife_days"]}
                for st, w in SIGNAL_WEIGHTS.items()
            },
        }
    finally:
        session.close()


class SeedRequest(BaseModel):
    web_search: bool = False
    embed: bool = False


@app.post("/api/admin/seed")
def seed_db(req: SeedRequest | None = Body(default=None)):
    from database.seed import seed_database
    opts = req if req is not None else SeedRequest()
    seed_database(use_web_search=opts.web_search, run_embed_after=opts.embed)
    return {"status": "seeded", "web_search": opts.web_search, "embed": opts.embed}


@app.post("/api/admin/rescore")
def rescore():
    scores = score_all_prospects()
    return {"status": "rescored", "count": len(scores)}


class CollectRequest(BaseModel):
    collectors: list[str] | None = None  # None = run all


@app.post("/api/admin/collect")
def run_collect(req: CollectRequest | None = Body(default=None)):
    """Run data collectors then rescore. Safe to call from a cron job."""
    import threading

    opts = req if req is not None else CollectRequest()

    def _run():
        from collectors.runner import run_collectors
        run_collectors(opts.collectors)
        score_all_prospects()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"status": "started", "collectors": opts.collectors or "all"}


class SignalImport(BaseModel):
    company_id: int
    signal_type: str
    title: str
    summary: str | None = None
    source_url: str | None = None
    source_type: str = "industry_news"
    magnitude: float | None = None
    is_active: bool = True
    raw_data: str | None = None
    embedding: str | None = None
    action_window: str | None = None
    action_insight: str | None = None
    detected_at: str | None = None


@app.post("/api/admin/import-signals")
def import_signals(signals: list[SignalImport]):
    from datetime import datetime
    session = get_session()
    inserted = 0
    try:
        for s in signals:
            obj = Signal(
                company_id=s.company_id,
                signal_type=s.signal_type,
                title=s.title,
                summary=s.summary,
                source_url=s.source_url,
                source_type=s.source_type,
                magnitude=s.magnitude,
                is_active=s.is_active,
                raw_data=s.raw_data,
                embedding=s.embedding,
                action_window=s.action_window,
                action_insight=s.action_insight,
                detected_at=datetime.fromisoformat(s.detected_at) if s.detected_at else datetime.utcnow(),
            )
            session.add(obj)
            inserted += 1
        session.commit()
    finally:
        session.close()
    return {"status": "imported", "count": inserted}
