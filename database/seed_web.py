# Why: Fetch company descriptions via web search for seed enrichment
# Deps: duckduckgo_search
# How: DDG text search, first result body as description snippet

def fetch_company_description(name: str, industry: str = "", max_chars: int = 500) -> str | None:
    """
    Use web search to get a short description for a company.
    Returns None on failure or if no result; caller can fall back to static description.
    """
    try:
        from duckduckgo_search import DDGS
        query = f'"{name}" company'
        if industry:
            query += f" {industry}"
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=3))
        if not results:
            return None
        first = results[0] if isinstance(results[0], dict) else getattr(results[0], "__dict__", {})
        body = (first.get("body") or getattr(first, "body", None) or "").strip()
        if not body:
            return None
        if len(body) > max_chars:
            body = body[: max_chars - 3].rsplit(" ", 1)[0] + "..."
        return body
    except Exception:
        return None
