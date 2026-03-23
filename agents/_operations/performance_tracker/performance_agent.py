#!/usr/bin/env python3
"""
AUROS AI — Agent 9: Performance Tracker
Tracks and analyzes content performance metrics for clients.
Accepts manual metric input via CLI args or JSON file, researches public
engagement data via Tavily, compares against industry benchmarks, and
generates graded performance reports.

Usage:
    python -m agents.performance_tracker.performance_agent --company "Company Name" --metrics path/to/metrics.json
    python -m agents.performance_tracker.performance_agent --company "Company Name"
"""

from __future__ import annotations

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, LOGS_DIR, TAVILY_API_KEY
from agents.shared.llm import generate


# ---------------------------------------------------------------------------
# Tavily research helper
# ---------------------------------------------------------------------------

def _research_public_metrics(company: str) -> dict:
    """Use Tavily to research a company's recent social media engagement."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(
            query=f"{company} social media engagement metrics followers growth 2026",
            max_results=5,
            search_depth="advanced",
        )
        snippets = [r.get("content", "") for r in results.get("results", [])]
        return {
            "source": "tavily_research",
            "query": f"{company} social media engagement",
            "findings": snippets[:5],
        }
    except Exception as e:
        print(f"[AUROS] Tavily research skipped: {e}")
        return {"source": "tavily_research", "findings": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Metrics loading
# ---------------------------------------------------------------------------

def _load_metrics(metrics_path: str | None) -> dict | None:
    """Load metrics from a JSON file if provided."""
    if not metrics_path:
        return None
    path = Path(metrics_path)
    if not path.exists():
        print(f"[AUROS] Metrics file not found: {path}")
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT = """You are the AUROS performance analytics specialist. Analyze the following content performance data for {company}.

METRICS DATA:
{metrics_json}

PUBLIC RESEARCH:
{research_json}

Produce a comprehensive performance analysis. Return valid JSON with this structure:
{{
  "company": "{company}",
  "analysis_date": "{today}",
  "period": "...",
  "summary": "3-4 sentence executive summary of overall performance",
  "platform_breakdown": [
    {{
      "platform": "instagram",
      "total_posts": 0,
      "avg_views": 0,
      "avg_likes": 0,
      "avg_comments": 0,
      "avg_shares": 0,
      "avg_saves": 0,
      "engagement_rate": "X.XX%",
      "grade": "A/B/C/D/F",
      "grade_reasoning": "...",
      "best_content_type": "...",
      "worst_content_type": "...",
      "trend": "growing/stable/declining"
    }}
  ],
  "content_type_performance": [
    {{
      "type": "reel",
      "avg_engagement_rate": "X.XX%",
      "total_posts": 0,
      "recommendation": "..."
    }}
  ],
  "industry_benchmarks": {{
    "source": "industry averages",
    "benchmarks": [
      {{
        "platform": "instagram",
        "avg_engagement_rate": "X.XX%",
        "comparison": "above/at/below average",
        "gap": "+/-X.XX%"
      }}
    ]
  }},
  "growth_trends": {{
    "overall_direction": "growing/stable/declining",
    "details": "..."
  }},
  "top_performing_posts": [
    {{
      "date": "...",
      "platform": "...",
      "type": "...",
      "engagement_rate": "X.XX%",
      "why_it_worked": "..."
    }}
  ],
  "recommendations": [
    {{
      "priority": 1,
      "action": "...",
      "expected_impact": "...",
      "reasoning": "..."
    }}
  ],
  "overall_grade": "A/B/C/D/F",
  "overall_grade_reasoning": "..."
}}

Grade scale:
- A: Engagement rate 2x+ industry average, consistent growth
- B: Above industry average, positive trends
- C: At industry average, stable but no standout performance
- D: Below industry average, some concerning trends
- F: Significantly below benchmarks, urgent action needed

If metrics data is limited, use the public research findings and industry knowledge to fill gaps. Be specific and actionable in recommendations."""


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------

def _analysis_to_markdown(analysis: dict) -> str:
    """Convert analysis JSON to a readable markdown report."""
    lines = [
        f"# AUROS Performance Report — {analysis.get('company', 'Unknown')}",
        f"**Period:** {analysis.get('period', 'N/A')}",
        f"**Analysis Date:** {analysis.get('analysis_date', 'N/A')}",
        f"**Overall Grade:** {analysis.get('overall_grade', 'N/A')}",
        "",
        "---",
        "",
        "## Executive Summary",
        analysis.get("summary", ""),
        "",
    ]

    # Platform breakdown
    lines.append("## Platform Performance")
    for platform in analysis.get("platform_breakdown", []):
        lines.append(f"### {platform.get('platform', 'Unknown').title()} — Grade: {platform.get('grade', 'N/A')}")
        lines.append(f"- **Total Posts:** {platform.get('total_posts', 'N/A')}")
        lines.append(f"- **Avg Views:** {platform.get('avg_views', 'N/A')}")
        lines.append(f"- **Avg Likes:** {platform.get('avg_likes', 'N/A')}")
        lines.append(f"- **Avg Comments:** {platform.get('avg_comments', 'N/A')}")
        lines.append(f"- **Engagement Rate:** {platform.get('engagement_rate', 'N/A')}")
        lines.append(f"- **Best Content Type:** {platform.get('best_content_type', 'N/A')}")
        lines.append(f"- **Trend:** {platform.get('trend', 'N/A')}")
        lines.append(f"- *{platform.get('grade_reasoning', '')}*")
        lines.append("")

    # Content type performance
    lines.append("## Content Type Performance")
    for ct in analysis.get("content_type_performance", []):
        lines.append(f"### {ct.get('type', 'Unknown').title()}")
        lines.append(f"- **Avg Engagement Rate:** {ct.get('avg_engagement_rate', 'N/A')}")
        lines.append(f"- **Total Posts:** {ct.get('total_posts', 'N/A')}")
        lines.append(f"- **Recommendation:** {ct.get('recommendation', '')}")
        lines.append("")

    # Industry benchmarks
    benchmarks = analysis.get("industry_benchmarks", {})
    if benchmarks.get("benchmarks"):
        lines.append("## Industry Benchmark Comparison")
        for b in benchmarks["benchmarks"]:
            lines.append(f"- **{b.get('platform', '').title()}:** Industry avg {b.get('avg_engagement_rate', 'N/A')} | You are {b.get('comparison', 'N/A')} ({b.get('gap', '')})")
        lines.append("")

    # Growth trends
    growth = analysis.get("growth_trends", {})
    if growth:
        lines.append("## Growth Trends")
        lines.append(f"**Direction:** {growth.get('overall_direction', 'N/A')}")
        lines.append(growth.get("details", ""))
        lines.append("")

    # Top performing posts
    top_posts = analysis.get("top_performing_posts", [])
    if top_posts:
        lines.append("## Top Performing Posts")
        for i, post in enumerate(top_posts, 1):
            lines.append(f"**{i}.** {post.get('date', '')} — {post.get('platform', '')} {post.get('type', '')} — {post.get('engagement_rate', '')}")
            lines.append(f"   *Why it worked:* {post.get('why_it_worked', '')}")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    for rec in analysis.get("recommendations", []):
        lines.append(f"**{rec.get('priority', '?')}.** {rec.get('action', '')}")
        lines.append(f"   Expected Impact: {rec.get('expected_impact', '')} | {rec.get('reasoning', '')}")
        lines.append("")

    lines.append("---")
    lines.append(f"**Overall Grade: {analysis.get('overall_grade', 'N/A')}** — {analysis.get('overall_grade_reasoning', '')}")
    lines.append("")
    lines.append("*Generated by AUROS — Intelligence, Elevated.*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(company: str, metrics: str | None = None) -> dict:
    """Run a full performance analysis for a company."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[AUROS] Performance Tracker starting — {company} — {today}")

    # Load metrics from file
    metrics_data = _load_metrics(metrics)
    if metrics_data:
        print(f"[AUROS] Loaded metrics: {len(metrics_data.get('posts', []))} posts")
    else:
        print("[AUROS] No metrics file provided — relying on public research")

    # Research public engagement data
    print("[AUROS] Researching public engagement data...")
    research = _research_public_metrics(company)
    finding_count = len(research.get("findings", []))
    print(f"[AUROS] Found {finding_count} research snippets")

    # Generate analysis via Claude
    print("[AUROS] Generating performance analysis...")
    prompt = ANALYSIS_PROMPT.format(
        company=company,
        today=today,
        metrics_json=json.dumps(metrics_data, indent=2)[:8000] if metrics_data else "No direct metrics provided.",
        research_json=json.dumps(research, indent=2)[:4000],
    )
    raw = generate(prompt, temperature=0.3, max_tokens=4096)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    analysis = json.loads(json_str)

    # Save results
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    client_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = client_dir / f"performance_{today}.json"
    json_path.write_text(json.dumps(analysis, indent=2))
    print(f"[AUROS] JSON report saved to {json_path}")

    # Markdown report
    md_path = client_dir / f"performance_{today}.md"
    md_path.write_text(_analysis_to_markdown(analysis))
    print(f"[AUROS] Markdown report saved to {md_path}")

    grade = analysis.get("overall_grade", "N/A")
    print(f"[AUROS] Performance Tracker complete — Overall Grade: {grade}")
    return analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Performance Tracker Agent")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--metrics", help="Path to metrics JSON file")
    args = parser.parse_args()
    run(**vars(args))
