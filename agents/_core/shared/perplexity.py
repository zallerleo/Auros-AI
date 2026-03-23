"""
AUROS AI — Perplexity API Wrapper
Deep market research via Perplexity's sonar-pro model.
Falls back to Tavily if Perplexity API key is not configured.
"""

from __future__ import annotations

import json
from typing import Any

from agents.shared.config import PERPLEXITY_API_KEY, TAVILY_API_KEY


def _get_client():
    """Return an OpenAI-compatible client pointed at Perplexity."""
    from openai import OpenAI

    return OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )


def _perplexity_query(query: str, system: str = "") -> str:
    """Send a single query to Perplexity sonar-pro and return the response."""
    client = _get_client()
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": query})

    response = client.chat.completions.create(
        model="sonar-pro",
        messages=messages,
    )
    return response.choices[0].message.content


def _tavily_fallback(query: str) -> str:
    """Fallback research using Tavily search API."""
    if not TAVILY_API_KEY:
        return f"[AUROS] No research API keys configured. Manual research needed for: {query}"

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=TAVILY_API_KEY)
        result = client.search(query, search_depth="advanced", max_results=5)
        snippets = []
        for r in result.get("results", []):
            snippets.append(f"- {r.get('title', '')}: {r.get('content', '')[:300]}")
            if r.get("url"):
                snippets.append(f"  Source: {r['url']}")
        return "\n".join(snippets) if snippets else f"No results found for: {query}"
    except Exception as e:
        return f"[AUROS] Tavily fallback failed: {e}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def research(query: str, context: str = "") -> str:
    """Run a single research query and return synthesized results with citations.

    Args:
        query: The research question.
        context: Optional background context to ground the query.

    Returns:
        Synthesized research text with inline citations.
    """
    if not PERPLEXITY_API_KEY:
        print("[AUROS] Perplexity API key missing — falling back to Tavily")
        return _tavily_fallback(query)

    system = (
        "You are a market research analyst working for AUROS, a premium AI marketing agency. "
        "Provide thorough, data-backed answers with inline citations. "
        "Focus on actionable insights, market data, and competitive intelligence."
    )
    if context:
        system += f"\n\nAdditional context:\n{context}"

    try:
        return _perplexity_query(query, system=system)
    except Exception as e:
        print(f"[AUROS] Perplexity request failed ({e}) — falling back to Tavily")
        return _tavily_fallback(query)


def deep_research(
    queries: list[str] | None = None,
    context: str = "",
    company: str = "",
    **kwargs,
) -> dict[str, Any]:
    """Run multiple research queries and combine into a structured document.

    Args:
        queries: List of research questions.
        context: Optional shared context for all queries.

    Returns:
        Dict with keys: queries, results (list of {query, findings}), summary.
    """
    # Auto-generate queries when called by orchestrator with just company
    if not queries and company:
        queries = [
            f"{company} company overview market position industry",
            f"{company} marketing strategy digital presence social media",
            f"{company} competitors competitive landscape",
            f"{company} target audience customer demographics",
        ]
        context = context or f"Research for marketing agency working with {company}"

    if not queries:
        return {"queries": [], "results": [], "summary": "No queries provided."}

    results: list[dict[str, str]] = []
    all_findings: list[str] = []

    for i, query in enumerate(queries, 1):
        print(f"[AUROS] Research query {i}/{len(queries)}: {query[:80]}...")
        findings = research(query, context=context)
        results.append({"query": query, "findings": findings})
        all_findings.append(findings)

    # Build a combined summary if we used Perplexity for at least one query
    summary = ""
    if PERPLEXITY_API_KEY and all_findings:
        try:
            combined = "\n\n---\n\n".join(
                f"**{r['query']}**\n{r['findings']}" for r in results
            )
            summary = _perplexity_query(
                f"Synthesize the following research findings into a coherent executive summary "
                f"with key takeaways and strategic recommendations:\n\n{combined[:12000]}",
                system=(
                    "You are a senior strategy consultant at AUROS. "
                    "Produce a concise executive summary that connects the dots across findings."
                ),
            )
        except Exception:
            summary = "Summary generation failed — see individual query results."
    else:
        summary = "Summary unavailable — research ran in fallback mode."

    return {
        "queries": queries,
        "results": results,
        "summary": summary,
    }


def competitive_analysis(
    company_url: str, competitors: list[str] | None = None
) -> dict[str, Any]:
    """Run a competitive analysis for a company against named competitors.

    Args:
        company_url: The target company's website URL.
        competitors: Optional list of competitor names/URLs. If omitted,
                     Perplexity will identify top competitors automatically.

    Returns:
        Dict with keys: company, competitors, analysis, opportunities,
        positioning_gaps, recommended_angles.
    """
    competitor_str = ", ".join(competitors) if competitors else "auto-identify top 5 competitors"

    query = (
        f"Perform a detailed competitive analysis for the company at {company_url}.\n"
        f"Competitors to analyze: {competitor_str}.\n\n"
        "For each competitor, cover:\n"
        "1. Market positioning and brand messaging\n"
        "2. Content strategy (channels, frequency, formats)\n"
        "3. Pricing signals and target segment\n"
        "4. Digital presence strength (SEO, social, ads)\n"
        "5. Key differentiators vs the target company\n\n"
        "Then provide:\n"
        "- Positioning gaps the target company can exploit\n"
        "- Content opportunities competitors are missing\n"
        "- Three recommended strategic angles\n"
    )

    raw = research(query, context=f"Target company: {company_url}")

    # Structure the raw output
    return {
        "company": company_url,
        "competitors": competitors or [],
        "analysis": raw,
        "generated_via": "perplexity" if PERPLEXITY_API_KEY else "tavily_fallback",
    }
