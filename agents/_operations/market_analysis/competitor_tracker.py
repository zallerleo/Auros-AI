"""
AUROS AI — Competitor Tracker
Monitors AI marketing agencies and their activities.
"""

from tavily import TavilyClient
from agents.shared.config import TAVILY_API_KEY


COMPETITOR_QUERIES = [
    "AI marketing agency new services 2026",
    "AI advertising agency pricing packages",
    "AI content creation agency competitors",
    "generative AI marketing agency funding news",
    "AI video marketing agency trends",
]


def track_competitors() -> list[dict]:
    """
    Research competitor AI marketing agencies and market movements.
    Returns a list of relevant findings.
    """
    client = TavilyClient(api_key=TAVILY_API_KEY)
    results = []
    seen_urls = set()

    for query in COMPETITOR_QUERIES:
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=4,
                days=14,
            )
            for r in response.get("results", []):
                url = r.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    results.append({
                        "title": r.get("title", ""),
                        "content": r.get("content", "")[:500],
                        "url": url,
                    })
        except Exception as e:
            print(f"[AUROS] Competitor tracking failed: {query} — {e}")
            continue

    print(f"[AUROS] Competitor tracking: {len(results)} results")
    return results
