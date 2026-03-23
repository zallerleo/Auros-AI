#!/usr/bin/env python3
"""
AUROS AI — Social Trend Analyst
Researches trending content, engagement patterns, and recommends replicable strategies.

Usage:
    python -m agents.trend_analyst.trend_agent --industry "entertainment exhibitions" --platforms "instagram,tiktok"
"""

from __future__ import annotations

import sys
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, TAVILY_API_KEY, LOGS_DIR
from agents.shared.llm import generate
from agents.shared.client_config import load_client_config


def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search Tavily for trend data."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query, max_results=max_results, search_depth="advanced")
    return response.get("results", [])


TREND_PROMPT = """You are the AUROS social media trend analyst. Analyze the following research data about trending content in the {industry} industry across {platforms}.

TRENDING CONTENT RESEARCH:
{trending_data}

VIRAL CONTENT RESEARCH:
{viral_data}

ALGORITHM & FORMAT RESEARCH:
{algorithm_data}

Generate a comprehensive trend analysis as valid JSON:

{{
  "industry": "{industry}",
  "platforms": {platforms_list},
  "analysis_date": "{date}",
  "trending_formats": [
    {{
      "format": "Format name (e.g., behind-the-scenes reels)",
      "platform": "Which platform",
      "engagement_level": "high/very high/moderate",
      "description": "Why this format is trending",
      "example": "Specific example description"
    }}
  ],
  "viral_patterns": [
    {{
      "pattern": "Pattern name",
      "description": "What makes this pattern work",
      "engagement_driver": "What triggers shares/saves/comments",
      "replicability": "easy/moderate/hard"
    }}
  ],
  "platform_specific_tactics": {{
    "platform_name": {{
      "algorithm_priorities": ["What the algorithm currently favors"],
      "optimal_formats": ["Top 3 formats"],
      "engagement_tactics": ["3-5 specific tactics"],
      "avoid": ["What to avoid right now"]
    }}
  }},
  "content_ideas": [
    {{
      "idea": "Specific content idea",
      "platform": "Best platform for this",
      "format": "reel/carousel/static/story/etc",
      "hook": "Opening hook or caption hook",
      "why_it_works": "Why this should perform well"
    }}
  ],
  "optimal_posting": {{
    "best_times": {{"platform": "time range"}},
    "frequency": {{"platform": "X times per week"}},
    "spacing_notes": "How to space content"
  }},
  "hashtag_strategy": {{
    "trending_hashtags": ["10 relevant trending hashtags"],
    "niche_hashtags": ["10 niche/industry hashtags"],
    "branded_suggestions": ["3 branded hashtag ideas"],
    "strategy_notes": "How to mix and use hashtags"
  }}
}}

Return ONLY valid JSON. Provide 10 content ideas. Be specific to the {industry} industry — no generic advice. Every recommendation should be actionable this week."""


def run(
    company: str = "",
    industry: str = "",
    platforms: str = "instagram,tiktok",
) -> dict:
    """Execute the trend analysis pipeline.

    When called by the orchestrator, only ``company`` is passed.
    ``industry`` and ``platforms`` fall back to client config or sensible defaults.
    """
    # Resolve industry from client config when not explicitly provided
    if not industry and company:
        try:
            cfg = load_client_config(company)
            industry = cfg.get("industry", "")
        except (FileNotFoundError, Exception):
            pass
    if not industry:
        industry = "entertainment exhibitions"
    today = datetime.now().strftime("%Y-%m-%d")
    platform_list = [p.strip() for p in platforms.split(",")]
    platforms_str = ", ".join(platform_list)

    print(f"[AUROS] Trend analyst starting — {industry} on {platforms_str} — {today}")

    # Step 1: Research trending content
    print("[AUROS] Researching trending content...")
    trending_queries = [
        f"{industry} trending content {platforms_str} 2025 2026 what performs best",
        f"{industry} social media content strategy {platforms_str} high engagement",
    ]
    trending_data = []
    for q in trending_queries:
        try:
            trending_data.extend(_search_tavily(q, max_results=4))
        except Exception as e:
            print(f"[AUROS] Search warning: {e}")

    # Step 2: Research viral content
    print("[AUROS] Researching viral content examples...")
    viral_queries = [
        f"{industry} viral content examples {platforms_str} most liked shared",
        f"{industry} best performing posts {platforms_str} engagement",
    ]
    viral_data = []
    for q in viral_queries:
        try:
            viral_data.extend(_search_tavily(q, max_results=3))
        except Exception as e:
            print(f"[AUROS] Search warning: {e}")

    # Step 3: Research algorithm and format trends
    print("[AUROS] Researching algorithm preferences and formats...")
    algo_queries = [
        f"{platforms_str} algorithm changes 2025 2026 what content gets reach",
        f"{platforms_str} content format trends reels carousel stories",
    ]
    algorithm_data = []
    for q in algo_queries:
        try:
            algorithm_data.extend(_search_tavily(q, max_results=3))
        except Exception as e:
            print(f"[AUROS] Search warning: {e}")

    # Step 4: Generate analysis via Claude
    print("[AUROS] Generating trend analysis...")
    trending_summary = [
        {"title": r.get("title", ""), "content": r.get("content", "")[:400]}
        for r in trending_data
    ]
    viral_summary = [
        {"title": r.get("title", ""), "content": r.get("content", "")[:400]}
        for r in viral_data
    ]
    algo_summary = [
        {"title": r.get("title", ""), "content": r.get("content", "")[:400]}
        for r in algorithm_data
    ]

    prompt = TREND_PROMPT.format(
        industry=industry,
        platforms=platforms_str,
        platforms_list=json.dumps(platform_list),
        date=today,
        trending_data=json.dumps(trending_summary, indent=2)[:4000],
        viral_data=json.dumps(viral_summary, indent=2)[:3000],
        algorithm_data=json.dumps(algo_summary, indent=2)[:3000],
    )

    raw = generate(prompt, max_tokens=4096, temperature=0.5)

    # Parse JSON
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    report = json.loads(json_str)

    # Step 5: Save report
    reports_dir = PORTFOLIO_DIR / "trend_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", industry.lower()).strip("_")
    report_path = reports_dir / f"trend_report_{slug}_{today}.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"[AUROS] Trend report saved to {report_path}")

    print("[AUROS] Trend analysis complete.")
    return {"status": "complete", "report_path": str(report_path), "report": report}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Social Trend Analyst")
    parser.add_argument("--industry", required=True, help="Industry to analyze")
    parser.add_argument("--platforms", default="instagram,tiktok", help="Comma-separated platforms")
    args = parser.parse_args()
    run(industry=args.industry, platforms=args.platforms)
