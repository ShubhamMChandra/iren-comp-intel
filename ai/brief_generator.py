# Why: Generates sales briefs, emails, battle cards
# Deps: OpenRouter via ai.client, DB models, config
# How: LLM prompts with context assembly and caching

import json
from datetime import datetime, timedelta, timezone

from ai.client import get_ai_client, call_with_fallback
from config import (
    COMPETITOR_SEGMENTS,
    COMPETITOR_SEGMENT_DEFAULT,
    IREN_BENCHMARK,
    PRODUCT_FIT_TO_SEGMENTS,
    SEGMENT_PROFILES,
)
from database.db import get_session
from database.models import Company, CompetitorEvent, ProspectBrief, ProspectScore, Signal


PRODUCT_FIT_LABELS: dict[str, str] = {
    "ai_cloud": "AI Cloud",
    "colocation": "Colo",
    "build_to_suit": "BTS",
}


def _build_iren_context() -> str:
    """Format IREN_BENCHMARK into the context block every prompt needs."""
    b = IREN_BENCHMARK
    products = b.get("products", {})
    gpus = ", ".join(b.get("gpu_models", []))
    locations = ", ".join(b.get("locations", []))
    customers = ", ".join(b.get("key_customers", []))
    cooling = " and ".join(b.get("cooling", []))
    cap = b.get("capacity_mw", 0)
    expansion = b.get("expansion_plans", "")
    ticker = b.get("ticker", "")
    exchange = b.get("exchange", "")
    ticker_str = f" ({exchange}: {ticker})" if exchange and ticker else ""

    lines = [f"ABOUT IREN{ticker_str}:"]
    if products.get("ai_cloud"):
        lines.append(f"  AI Cloud: {products['ai_cloud']} ({gpus})")
    if products.get("colocation"):
        lines.append(f"  Colocation: {products['colocation']} ({cooling} cooling)")
    if products.get("build_to_suit"):
        lines.append(f"  Build-to-Suit: {products['build_to_suit']}")
    if locations:
        lines.append(f"  Locations: {locations}")
    if cap:
        lines.append(f"  Capacity: {cap:,} MW operational, {expansion}")
    strengths = b.get("strengths", [])
    if strengths:
        lines.append(f"  Edge: {'; '.join(strengths[:3])}")
    if customers:
        lines.append(f"  Key customers: {customers}")
    return "\n".join(lines)


def _funding_stage(total_funding: float | None, is_public: bool) -> str:
    """Map total funding + public status to a human-readable stage label."""
    if is_public:
        return "public"
    if total_funding is None:
        return "unknown"
    if total_funding < 10_000_000:
        return "pre-seed/seed"
    if total_funding < 50_000_000:
        return "Series A"
    if total_funding < 200_000_000:
        return "Series B"
    if total_funding < 500_000_000:
        return "growth"
    return "late-stage"


def _derive_segment(industry: str | None) -> str:
    """Map a company's industry string to a canonical competitor segment."""
    if not industry:
        return COMPETITOR_SEGMENT_DEFAULT
    upper = industry.upper()
    for keyword, segment in COMPETITOR_SEGMENTS.items():
        if keyword.upper() in upper:
            return segment
    return COMPETITOR_SEGMENT_DEFAULT


def _parse_json_field(value: str | None) -> list:
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

try:
    from private.prompts import build_brief_prompt as _private_brief
    from private.prompts import build_email_prompt as _private_email
    from private.prompts import build_battlecard_prompt as _private_battlecard
    _HAS_PRIVATE = True
except ImportError:
    _HAS_PRIVATE = False

_iren_ctx = _build_iren_context()

if _HAS_PRIVATE:
    BRIEF_SYSTEM_PROMPT = _private_brief(_iren_ctx)
    EMAIL_SYSTEM_PROMPT = _private_email(_iren_ctx)
    BATTLECARD_SYSTEM_PROMPT = _private_battlecard(_iren_ctx)
else:
    BRIEF_SYSTEM_PROMPT = (
        "You are a sales strategist preparing a brief for a prospect meeting.\n\n"
        + _iren_ctx + "\n\n"
        "Provide a concise analysis with talking points, competitive context, and urgency."
    )
    EMAIL_SYSTEM_PROMPT = (
        "You are a BD lead drafting a cold outreach email to a prospect.\n\n"
        + _iren_ctx + "\n\n"
        "Reference a recent signal, explain relevance, and close with a soft ask."
    )
    BATTLECARD_SYSTEM_PROMPT = (
        "You are a competitive intelligence analyst creating a battle card.\n\n"
        + _iren_ctx + "\n\n"
        "Provide competitor snapshot, where we win, where they win, deal scenarios, "
        "and objection handling."
    )

BRIEF_CACHE_DAYS = 7


def _get_cached_brief(session, company_id: int, brief_type: str) -> str | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=BRIEF_CACHE_DAYS)
    cached = (
        session.query(ProspectBrief)
        .filter(
            ProspectBrief.company_id == company_id,
            ProspectBrief.brief_type == brief_type,
            ProspectBrief.generated_at >= cutoff,
        )
        .order_by(ProspectBrief.generated_at.desc())
        .first()
    )
    return cached.brief_text if cached else None


def _cache_brief(session, company_id: int, brief_type: str, text: str) -> None:
    brief = ProspectBrief(
        company_id=company_id,
        brief_text=text,
        brief_type=brief_type,
    )
    session.add(brief)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[brief_generator] cache write skipped (db contention?): {e}")


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500, temperature: float = 0.4) -> str | None:
    client = get_ai_client()
    if not client:
        return None
    return call_with_fallback(
        client,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _build_prospect_context(session, company_id: int) -> tuple[Company | None, str]:
    company = session.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None, ""

    signals = (
        session.query(Signal)
        .filter(Signal.company_id == company_id)
        .order_by(Signal.detected_at.desc())
        .limit(20)
        .all()
    )

    latest_score = (
        session.query(ProspectScore)
        .filter(ProspectScore.company_id == company_id)
        .order_by(ProspectScore.scored_at.desc())
        .first()
    )

    stage = _funding_stage(company.total_funding, company.is_public)
    pfit_label = PRODUCT_FIT_LABELS.get(company.product_fit or "", company.product_fit or "unknown")

    lines = [
        f"PROSPECT: {company.name}",
        f"Industry: {company.industry}",
        f"HQ: {company.hq_location}",
        f"Stage: {stage}",
        f"Product Fit: {pfit_label}",
        f"Employees: {company.employee_count or 'Unknown'}",
        f"Public: {'Yes (' + company.ticker + ')' if company.is_public else 'No'}",
    ]
    if company.total_funding:
        lines.append(f"Total Funding: ${company.total_funding:,.0f}")
    lines.append(f"Description: {company.description}")
    lines.append("")

    if latest_score:
        lines.extend([
            f"SCORE: {latest_score.total_score:.1f}/100",
            f"  Fundraising: {latest_score.fundraising_score:.1f}/20",
            f"  Funded: {latest_score.funding_completed_score:.1f}/15",
            f"  Hiring: {latest_score.hiring_score:.1f}/25",
            f"  AI Initiative: {latest_score.ai_initiative_score:.1f}/15",
            f"  Cloud Spend: {latest_score.cloud_spend_score:.1f}/15",
            f"  Outgrowing: {latest_score.outgrowing_score:.1f}/10",
            "",
        ])

    if signals:
        lines.append("SIGNALS:")
        for s in signals[:15]:
            lines.append(f"  [{s.signal_type}] {s.title} ({s.detected_at.strftime('%Y-%m-%d')})")
        lines.append("")

    pfit = company.product_fit or ""
    relevant_segments = PRODUCT_FIT_TO_SEGMENTS.get(pfit, list(SEGMENT_PROFILES.keys()))
    competitors = session.query(Company).filter(Company.company_type == "competitor").all()
    likely_competitors = []
    for c in competitors:
        seg = _derive_segment(c.industry)
        if seg in relevant_segments:
            likely_competitors.append((c, seg))

    if likely_competitors:
        lines.append("LIKELY COMPETITORS (based on product fit):")
        for c, seg in likely_competitors[:8]:
            threat = c.threat_level or "medium"
            lines.append(f"  {c.name} [{seg}, threat: {threat}]")
            if c.known_pricing:
                lines.append(f"    Pricing: {c.known_pricing[:100]}")
        lines.append("")

    comp_ids = [c.id for c, _ in likely_competitors]
    if comp_ids:
        recent_events = (
            session.query(CompetitorEvent)
            .filter(CompetitorEvent.company_id.in_(comp_ids))
            .order_by(CompetitorEvent.detected_at.desc())
            .limit(5)
            .all()
        )
        if recent_events:
            comp_names = {c.id: c.name for c, _ in likely_competitors}
            lines.append("RECENT COMPETITOR MOVES:")
            for e in recent_events:
                name = comp_names.get(e.company_id, "Unknown")
                lines.append(f"  [{e.event_type}] {name}: {e.title[:120]}")

    return company, "\n".join(lines)


def generate_brief(company_id: int) -> str:
    session = get_session()
    try:
        cached = _get_cached_brief(session, company_id, "sales_brief")
        if cached:
            return cached

        company, context = _build_prospect_context(session, company_id)
        if not company:
            return "Company not found."

        result = _call_llm(BRIEF_SYSTEM_PROMPT, context, max_tokens=500)

        if result:
            _cache_brief(session, company_id, "sales_brief", result)
            return result

        return _fallback_brief(company, context)
    finally:
        session.close()


def generate_outreach_email(company_id: int) -> str:
    session = get_session()
    try:
        cached = _get_cached_brief(session, company_id, "outreach_email")
        if cached:
            return cached

        company, context = _build_prospect_context(session, company_id)
        if not company:
            return "Company not found."

        result = _call_llm(EMAIL_SYSTEM_PROMPT, context, max_tokens=300, temperature=0.5)

        if result:
            _cache_brief(session, company_id, "outreach_email", result)
            return result

        return f"[Set OPENAI_API_KEY to generate outreach emails for {company.name}]"
    finally:
        session.close()


def generate_battle_card(competitor_id: int) -> str:
    session = get_session()
    try:
        cached = _get_cached_brief(session, competitor_id, "battle_card")
        if cached:
            return cached

        competitor = session.query(Company).filter(Company.id == competitor_id).first()
        if not competitor:
            return "Competitor not found."

        signals = (
            session.query(Signal)
            .filter(Signal.company_id == competitor_id)
            .order_by(Signal.detected_at.desc())
            .limit(10)
            .all()
        )

        context_lines = [
            f"COMPETITOR: {competitor.name}",
            f"Industry: {competitor.industry}",
            f"HQ: {competitor.hq_location}",
            f"Description: {competitor.description}",
        ]
        if competitor.capacity_mw:
            context_lines.append(f"Capacity: {competitor.capacity_mw:,.0f} MW")
        if competitor.gpu_count:
            context_lines.append(f"GPUs: {competitor.gpu_count:,}")
        if competitor.known_pricing:
            context_lines.append(f"Pricing: {competitor.known_pricing}")
        if competitor.is_public:
            context_lines.append(f"Ticker: {competitor.ticker}")

        key_customers = _parse_json_field(competitor.key_customers)
        if key_customers:
            context_lines.append(f"Key customers: {', '.join(key_customers)}")

        strengths = _parse_json_field(competitor.strengths)
        if strengths:
            context_lines.append(f"Known strengths: {'; '.join(strengths)}")

        weaknesses = _parse_json_field(competitor.weaknesses)
        if weaknesses:
            context_lines.append(f"Known weaknesses: {'; '.join(weaknesses)}")

        seg = _derive_segment(competitor.industry)
        profile = SEGMENT_PROFILES.get(seg)
        if profile:
            context_lines.append("")
            context_lines.append(f"COMPETITOR SEGMENT: {seg}")
            context_lines.append(f"  {profile['description']}")
            context_lines.append(f"  Iren positioning: {profile['iren_positioning']}")
            context_lines.append(f"  Key battleground: {profile['key_battleground']}")

        iren_strengths = IREN_BENCHMARK.get("strengths", [])
        iren_weaknesses = IREN_BENCHMARK.get("weaknesses", [])
        if iren_strengths or iren_weaknesses:
            context_lines.append("")
            context_lines.append("IREN SELF-ASSESSMENT:")
            if iren_strengths:
                context_lines.append(f"  Strengths: {'; '.join(iren_strengths)}")
            if iren_weaknesses:
                context_lines.append(f"  Weaknesses: {'; '.join(iren_weaknesses)}")

        if signals:
            context_lines.append("\nRECENT ACTIVITY:")
            for s in signals[:8]:
                context_lines.append(f"  [{s.signal_type}] {s.title[:150]}")

        context = "\n".join(context_lines)
        result = _call_llm(BATTLECARD_SYSTEM_PROMPT, context, max_tokens=1000)

        if result:
            _cache_brief(session, competitor_id, "battle_card", result)
            return result

        return f"[Set OPENAI_API_KEY to generate battle cards for {competitor.name}]"
    finally:
        session.close()


def _fallback_brief(company: Company, context: str) -> str:
    return (
        f"# {company.name} — Prospect Brief\n\n"
        f"**Industry:** {company.industry}\n"
        f"**HQ:** {company.hq_location}\n\n"
        f"*Set OPENAI_API_KEY for AI-generated analysis and talking points.*"
    )
