# Why: Generates sales briefs, emails, battle cards
# Deps: OpenRouter via ai.client, DB models
# How: LLM prompts with context assembly and caching

from datetime import datetime, timedelta, timezone

from ai.client import get_ai_client, call_with_fallback
from database.db import get_session
from database.models import Company, CompetitorEvent, ProspectBrief, ProspectScore, Signal

BRIEF_SYSTEM_PROMPT = """You are a senior sales strategist at Iren, a high-performance computing
data center company. Iren offers:
- AI Cloud: GPU cloud with NVIDIA H100, H200, B200, B300, GB300 NVL72
- Colocation: AI-focused colocation with air and liquid cooling
- Build-to-Suit: Custom data centers with 4.5+ GW of renewable power in Texas, Oklahoma, and British Columbia
- 100% renewable energy, vertically integrated (own land, power, substations, compute)

Write a pre-call brief for the commercial team. Be concise, direct, and financially literate.
Structure:
1. THESIS — one sentence on why this company needs Iren
2. URGENCY — timing and why now
3. LEAD WITH — what to open the conversation with
4. DECISION MAKERS — likely titles to target
5. COMPETITIVE CONTEXT — what they're likely using now, who else is pitching them

Keep it under 250 words. No filler. Write for infrastructure finance dealmakers."""


EMAIL_SYSTEM_PROMPT = """You are drafting a cold outreach email from Iren's commercial team to a
prospect company. Iren is an HPC data center company with 4.5+ GW of renewable power, offering
GPU cloud, colocation, and build-to-suit data centers.

Write a 3-paragraph email:
1. Opening hook referencing a specific, recent signal about the prospect (funding, hiring, AI initiative)
2. Value proposition — why Iren is relevant to their situation right now
3. Soft close — suggest a brief call to explore fit

Tone: professional, confident, not salesy. Write like an infrastructure banker, not a SaaS SDR.
Keep it under 150 words. No subject line needed — just the body."""


BATTLECARD_SYSTEM_PROMPT = """You are a competitive intelligence analyst at Iren, an HPC data center company.
Iren offers: AI Cloud (NVIDIA H100-GB300), Colocation (liquid cooling), Build-to-Suit (4.5+ GW renewable
power, Texas/Oklahoma/BC). 100% renewable, vertically integrated.

Generate a competitive battle card positioning Iren against the specified competitor.
Structure:
1. COMPETITOR OVERVIEW — what they offer, their strengths
2. IREN ADVANTAGES — where Iren wins (power scale, renewables, vertical integration, pricing)
3. COMPETITOR ADVANTAGES — be honest about where they're stronger
4. WHEN TO LEAD WITH IREN — specific scenarios where Iren is the better fit
5. OBJECTION HANDLING — top 3 objections and responses

Keep it under 300 words. Be specific and honest — salespeople trust tools that don't BS them."""

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


def _cache_brief(session, company_id: int, brief_type: str, text: str):
    brief = ProspectBrief(
        company_id=company_id,
        brief_text=text,
        brief_type=brief_type,
    )
    session.add(brief)
    session.commit()


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str | None:
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
        temperature=0.4,
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

    comp_events = (
        session.query(CompetitorEvent)
        .order_by(CompetitorEvent.detected_at.desc())
        .limit(10)
        .all()
    )

    lines = [
        f"PROSPECT: {company.name}",
        f"Industry: {company.industry}",
        f"HQ: {company.hq_location}",
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

    if comp_events:
        lines.append("COMPETITOR ACTIVITY:")
        for e in comp_events[:5]:
            lines.append(f"  [{e.event_type}] {e.title}")

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

        result = _call_llm(EMAIL_SYSTEM_PROMPT, context, max_tokens=300)

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

        if signals:
            context_lines.append("\nRECENT ACTIVITY:")
            for s in signals[:8]:
                context_lines.append(f"  {s.title[:150]}")

        context = "\n".join(context_lines)
        result = _call_llm(BATTLECARD_SYSTEM_PROMPT, context, max_tokens=600)

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
