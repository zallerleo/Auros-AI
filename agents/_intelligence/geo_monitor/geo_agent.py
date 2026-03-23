#!/usr/bin/env python3
"""
AUROS AI — GEO Monitor Agent
Generative Engine Optimization: checks client brand visibility in AI search results.

Usage:
    python -m agents.geo_monitor.geo_agent --company "The Imagine Team" --city "Barcelona"
    python -m agents.geo_monitor.geo_agent --company "The Imagine Team" --city "Madrid" --output report.html
"""

from __future__ import annotations

import sys
import os
import json
import argparse
import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import TAVILY_API_KEY, LOGS_DIR

# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# ---------------------------------------------------------------------------
# Discovery query templates
# ---------------------------------------------------------------------------

DEFAULT_QUERIES = [
    "best exhibitions in {city}",
    "immersive experiences near me in {city}",
    "things to do in {city} this weekend",
    "best family activities in {city}",
    "interactive art exhibitions {city}",
]

BRANDED_QUERIES = [
    "harry potter exhibition tickets {city}",
    "{company} exhibitions",
    "{company} tickets",
    "{company} reviews",
]

# ---------------------------------------------------------------------------
# Perplexity (OpenAI-compatible) search
# ---------------------------------------------------------------------------


def _query_perplexity(query: str) -> dict:
    """Query Perplexity sonar-pro via OpenAI-compatible API."""
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai package not installed", "query": query}

    if not PERPLEXITY_API_KEY:
        return {"error": "PERPLEXITY_API_KEY not set", "query": query}

    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )

    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful search assistant. Answer the user's "
                        "question with specific brand names, companies, and "
                        "venues. Be thorough and include URLs when possible."
                    ),
                },
                {"role": "user", "content": query},
            ],
            max_tokens=1024,
            temperature=0.1,
        )
        return {
            "query": query,
            "response": response.choices[0].message.content,
            "model": "sonar-pro",
            "source": "perplexity",
        }
    except Exception as exc:
        return {"error": str(exc), "query": query, "source": "perplexity"}


# ---------------------------------------------------------------------------
# Tavily fallback
# ---------------------------------------------------------------------------


def _query_tavily(query: str) -> dict:
    """Fallback search via Tavily API."""
    try:
        from tavily import TavilyClient
    except ImportError:
        return {"error": "tavily-python package not installed", "query": query}

    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not set", "query": query}

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(query=query, max_results=5, search_depth="advanced")
        combined = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')}"
            for r in results.get("results", [])
        )
        return {
            "query": query,
            "response": combined,
            "results": results.get("results", []),
            "source": "tavily",
        }
    except Exception as exc:
        return {"error": str(exc), "query": query, "source": "tavily"}


def _search(query: str) -> dict:
    """Search using Perplexity, falling back to Tavily."""
    result = _query_perplexity(query)
    if "error" in result:
        print(f"[AUROS] Perplexity unavailable ({result['error']}), falling back to Tavily")
        result = _query_tavily(query)
    return result


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _score_single(response_text: str, company: str) -> dict:
    """Score a single search response for brand visibility."""
    text_lower = response_text.lower()
    company_lower = company.lower()

    # Exact brand mention
    mention_count = text_lower.count(company_lower)

    # Check individual significant words (skip short ones)
    words = [w for w in company.split() if len(w) > 2]
    word_hits = sum(1 for w in words if w.lower() in text_lower)
    word_ratio = word_hits / len(words) if words else 0

    # Position scoring: earlier = better
    first_pos = text_lower.find(company_lower)
    total_len = max(len(text_lower), 1)
    position_score = 0
    if first_pos >= 0:
        position_score = max(0, 100 - int((first_pos / total_len) * 100))

    # Build score components
    mention_score = min(mention_count * 25, 50)  # Up to 50 for mentions
    position_component = position_score * 0.3     # Up to 30 for position
    word_component = word_ratio * 20              # Up to 20 for partial matches

    score = int(min(mention_score + position_component + word_component, 100))

    return {
        "score": score,
        "mentions": mention_count,
        "first_position": first_pos,
        "word_hits": word_hits,
        "word_total": len(words),
    }


def score_visibility(results: list[dict], company: str) -> dict:
    """Aggregate visibility score across all query results."""
    if not results:
        return {"overall_score": 0, "query_scores": [], "summary": "No results to score"}

    query_scores = []
    for r in results:
        response_text = r.get("response", "")
        if not response_text or "error" in r:
            query_scores.append({
                "query": r.get("query", ""),
                "score": 0,
                "error": r.get("error"),
            })
            continue

        detail = _score_single(response_text, company)
        detail["query"] = r["query"]
        detail["source"] = r.get("source", "unknown")
        query_scores.append(detail)

    valid_scores = [q["score"] for q in query_scores if "error" not in q]
    overall = int(sum(valid_scores) / len(valid_scores)) if valid_scores else 0

    # Determine tier
    if overall >= 75:
        tier = "strong"
        summary = f"{company} has strong AI search visibility."
    elif overall >= 40:
        tier = "moderate"
        summary = f"{company} appears in some AI results but lacks consistency."
    else:
        tier = "weak"
        summary = f"{company} has minimal AI search presence. GEO work is needed."

    return {
        "overall_score": overall,
        "tier": tier,
        "summary": summary,
        "query_scores": query_scores,
        "queries_tested": len(results),
        "queries_with_mentions": sum(
            1 for q in query_scores if q.get("mentions", 0) > 0
        ),
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def _generate_recommendations(visibility: dict, company: str) -> list[str]:
    """Generate actionable GEO recommendations based on scores."""
    recs = []
    score = visibility["overall_score"]
    query_scores = visibility.get("query_scores", [])

    if score < 40:
        recs.append(
            "Create structured FAQ content targeting the exact questions "
            "AI assistants use to find businesses in your category."
        )
        recs.append(
            "Add schema.org structured data (Event, Organization, LocalBusiness) "
            "to all web properties."
        )
        recs.append(
            "Build authoritative backlinks from tourism boards, city guides, "
            "and event listing sites."
        )

    if score < 75:
        recs.append(
            "Publish detailed, information-rich pages for each exhibition "
            "with clear location, pricing, and availability data."
        )
        recs.append(
            "Maintain an active presence on review platforms (Google, "
            "TripAdvisor, Yelp) — AI models weight these sources heavily."
        )

    # Check for zero-score generic queries
    zero_generics = [
        q for q in query_scores
        if q.get("score", 0) == 0 and company.lower() not in q.get("query", "").lower()
    ]
    if zero_generics:
        recs.append(
            f"Brand invisible in {len(zero_generics)} generic discovery queries. "
            f"Prioritize content that answers: "
            f"{', '.join(repr(q['query']) for q in zero_generics[:3])}."
        )

    if score >= 75:
        recs.append(
            "Visibility is strong. Focus on monitoring for regression and "
            "expanding to new query categories."
        )

    return recs


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _build_html_report(report: dict) -> str:
    """Generate an HTML report from the GEO data."""
    score = report["visibility"]["overall_score"]
    tier = report["visibility"]["tier"]
    company = report["company"]
    city = report["city"]
    ts = report["timestamp"]
    query_scores = report["visibility"]["query_scores"]
    recs = report["recommendations"]

    # Score color
    if score >= 75:
        score_color = "#2ecc71"
    elif score >= 40:
        score_color = "#f39c12"
    else:
        score_color = "#e74c3c"

    query_rows = ""
    for q in query_scores:
        s = q.get("score", 0)
        mentions = q.get("mentions", 0)
        source = q.get("source", "—")
        error = q.get("error", "")
        status = f'<span style="color:#e74c3c">{error}</span>' if error else f"{s}/100"
        query_rows += f"""
        <tr>
            <td>{q.get('query', '')}</td>
            <td style="text-align:center">{status}</td>
            <td style="text-align:center">{mentions}</td>
            <td style="text-align:center">{source}</td>
        </tr>"""

    rec_items = "\n".join(f"<li>{r}</li>" for r in recs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>GEO Report — {company}</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 800px;
         margin: 2rem auto; padding: 0 1rem; color: #1a1a2e; }}
  h1 {{ color: #0a0a23; border-bottom: 3px solid #c9a84c; padding-bottom: .5rem; }}
  .score-box {{ display: inline-block; font-size: 3rem; font-weight: 700;
                color: {score_color}; border: 3px solid {score_color};
                border-radius: 12px; padding: .5rem 1.5rem; margin: 1rem 0; }}
  .tier {{ font-size: 1.2rem; color: #555; text-transform: uppercase; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; }}
  th, td {{ padding: .6rem .8rem; border: 1px solid #ddd; text-align: left; }}
  th {{ background: #0a0a23; color: #fff; }}
  tr:nth-child(even) {{ background: #f7f7f7; }}
  .recs li {{ margin-bottom: .5rem; }}
  footer {{ margin-top: 2rem; color: #999; font-size: .85rem; }}
</style>
</head>
<body>
<h1>GEO Visibility Report</h1>
<p><strong>Company:</strong> {company} &nbsp;|&nbsp; <strong>City:</strong> {city}
   &nbsp;|&nbsp; <strong>Date:</strong> {ts}</p>

<div class="score-box">{score}</div>
<div class="tier">{tier} visibility</div>
<p>{report['visibility']['summary']}</p>

<h2>Query Results</h2>
<table>
  <thead><tr><th>Query</th><th>Score</th><th>Mentions</th><th>Source</th></tr></thead>
  <tbody>{query_rows}</tbody>
</table>

<h2>Recommendations</h2>
<ul class="recs">{rec_items}</ul>

<footer>Generated by AUROS AI — GEO Monitor Agent</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(
    company: str,
    city: str = "Barcelona",
    extra_queries: list[str] | None = None,
    output_path: str | None = None,
) -> dict:
    """Run full GEO visibility audit for a company in a city."""
    print(f"[AUROS] GEO Monitor: auditing '{company}' in {city}")

    # Build query list
    queries = [q.format(city=city, company=company) for q in DEFAULT_QUERIES]
    queries += [q.format(city=city, company=company) for q in BRANDED_QUERIES]
    if extra_queries:
        queries += [q.format(city=city, company=company) for q in extra_queries]

    # Execute searches
    results = []
    for i, query in enumerate(queries, 1):
        print(f"[AUROS]   ({i}/{len(queries)}) Searching: {query}")
        result = _search(query)
        results.append(result)

    # Score
    visibility = score_visibility(results, company)
    print(f"[AUROS] Overall visibility score: {visibility['overall_score']}/100 ({visibility['tier']})")

    # Recommendations
    recs = _generate_recommendations(visibility, company)

    # Build report
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = {
        "company": company,
        "city": city,
        "timestamp": timestamp,
        "visibility": visibility,
        "recommendations": recs,
        "raw_results": results,
    }

    # Save JSON log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "geo_reports.jsonl"
    # Strip raw responses for the log (they can be large)
    log_entry = {k: v for k, v in report.items() if k != "raw_results"}
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    print(f"[AUROS] JSON log appended to {log_path}")

    # Save HTML report
    html = _build_html_report(report)
    if output_path:
        html_path = Path(output_path)
    else:
        reports_dir = Path(__file__).resolve().parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe_name = company.lower().replace(" ", "_")
        html_path = reports_dir / f"geo_{safe_name}_{city.lower()}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"[AUROS] HTML report saved to {html_path}")

    report["html_path"] = str(html_path)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS GEO Monitor Agent")
    parser.add_argument("--company", required=True, help="Company/brand name to audit")
    parser.add_argument("--city", default="Barcelona", help="Target city (default: Barcelona)")
    parser.add_argument("--output", help="Output HTML path (optional)")
    parser.add_argument(
        "--queries",
        nargs="*",
        help="Additional discovery queries (use {city} and {company} as placeholders)",
    )
    args = parser.parse_args()

    report = run(
        company=args.company,
        city=args.city,
        extra_queries=args.queries,
        output_path=args.output,
    )
    # Print summary JSON (without raw_results)
    summary = {k: v for k, v in report.items() if k != "raw_results"}
    print(json.dumps(summary, indent=2))
