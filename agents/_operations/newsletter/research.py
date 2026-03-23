"""
AUROS AI — Newsletter Research Module
Uses Tavily API to gather the latest AI + Marketing news.
"""

from datetime import datetime
from tavily import TavilyClient
from agents.shared.config import TAVILY_API_KEY


def get_client() -> TavilyClient:
    return TavilyClient(api_key=TAVILY_API_KEY)


# Rotating query sets — covers broad AI marketing landscape
QUERY_SETS = [
    [
        "AI marketing news and trends today",
        "generative AI advertising tools updates",
        "AI video content creation marketing",
        "marketing automation artificial intelligence",
        "AI social media marketing trends",
    ],
    [
        "AI marketing industry news this week",
        "new AI tools for digital advertising",
        "AI content generation marketing brands",
        "machine learning marketing analytics",
        "AI influencer marketing technology",
    ],
    [
        "artificial intelligence marketing campaigns",
        "AI powered advertising platforms news",
        "generative AI brand marketing strategies",
        "AI marketing ROI case studies",
        "AI personalization marketing technology",
    ],
]


def research_ai_marketing_news() -> list[dict]:
    """
    Search for the latest AI + Marketing news using Tavily.
    Returns a list of results with title, url, content, and score.
    """
    client = get_client()
    day_of_year = datetime.now().timetuple().tm_yday
    queries = QUERY_SETS[day_of_year % len(QUERY_SETS)]

    all_results = []
    seen_urls = set()

    for query in queries:
        try:
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                days=2,  # last 48 hours for freshness
            )
            for result in response.get("results", []):
                url = result.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append({
                        "title": result.get("title", ""),
                        "url": url,
                        "content": result.get("content", ""),
                        "score": result.get("score", 0),
                    })
        except Exception as e:
            print(f"[AUROS] Research query failed: {query} — {e}")
            continue

    # Sort by relevance score, return top 15
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:15]
