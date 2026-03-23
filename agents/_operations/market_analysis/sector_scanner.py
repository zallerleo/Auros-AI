"""
AUROS AI — Sector Scanner
Researches industry sectors to identify vulnerability and budget readiness for AI marketing services.
"""

from tavily import TavilyClient
from agents.shared.config import TAVILY_API_KEY


SECTORS = [
    "real estate",
    "entertainment and events",
    "e-commerce and DTC brands",
    "professional services (law, finance, consulting)",
    "SaaS and technology",
    "restaurants and hospitality",
    "healthcare and wellness",
    "education and coaching",
]

SECTOR_QUERIES = [
    "{sector} marketing spend trends 2026",
    "{sector} AI adoption digital marketing",
    "{sector} advertising challenges pain points",
    "{sector} digital transformation budget",
]


def scan_sectors() -> dict[str, list[dict]]:
    """
    Research each target sector for AI marketing opportunity signals.
    Returns a dict mapping sector name to research results.
    """
    client = TavilyClient(api_key=TAVILY_API_KEY)
    sector_data = {}

    for sector in SECTORS:
        results = []
        for query_template in SECTOR_QUERIES:
            query = query_template.format(sector=sector)
            try:
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=3,
                    days=30,
                )
                for r in response.get("results", []):
                    results.append({
                        "title": r.get("title", ""),
                        "content": r.get("content", "")[:500],
                        "url": r.get("url", ""),
                    })
            except Exception as e:
                print(f"[AUROS] Sector scan failed: {sector} / {query} — {e}")
                continue

        sector_data[sector] = results
        print(f"[AUROS] Scanned {sector}: {len(results)} results")

    return sector_data
