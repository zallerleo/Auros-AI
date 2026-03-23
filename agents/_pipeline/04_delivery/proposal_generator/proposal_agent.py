#!/usr/bin/env python3
"""
AUROS AI — Agent 11: Proposal Generator
Auto-generates AUROS-branded client proposals using audit data, brand
extraction, and trend analysis. Renders a premium multi-section HTML page
ready to send directly to prospects.

Usage:
    python -m agents.proposal_generator.proposal_agent --company "Company Name" --package "growth"

Packages:
    starter  — $2,500/mo — 8 posts/mo, 2 platforms, monthly report
    growth   — $4,000/mo — 16 posts/mo, 3 platforms, bi-weekly reports, 2 video ads
    premium  — $7,500/mo — 24 posts/mo, all platforms, weekly reports, 4 video ads, strategy calls
    custom   — pulls from audit to recommend custom scope
"""

from __future__ import annotations

import sys
import json
import argparse
import glob as globmod
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, LOGS_DIR, TAVILY_API_KEY
from agents.shared.llm import generate


# ---------------------------------------------------------------------------
# Package definitions
# ---------------------------------------------------------------------------

PACKAGES = {
    "starter": {
        "name": "Starter",
        "price": "$2,500/mo",
        "price_value": 2500,
        "posts_per_month": 8,
        "platforms": 2,
        "reports": "Monthly performance report",
        "video_ads": 0,
        "strategy_calls": "None",
        "deliverables": [
            "8 custom content pieces per month",
            "2 platform management (e.g. Instagram + TikTok)",
            "Monthly performance report",
            "Content calendar planning",
            "Hashtag and caption strategy",
            "Basic community management",
        ],
    },
    "growth": {
        "name": "Growth",
        "price": "$4,000/mo",
        "price_value": 4000,
        "posts_per_month": 16,
        "platforms": 3,
        "reports": "Bi-weekly performance reports",
        "video_ads": 2,
        "strategy_calls": "Monthly",
        "deliverables": [
            "16 custom content pieces per month",
            "3 platform management",
            "Bi-weekly performance reports",
            "2 professional video ads per month",
            "Content calendar planning and optimization",
            "Advanced hashtag and SEO strategy",
            "Community management and engagement",
            "Monthly strategy call",
            "Competitor monitoring",
        ],
    },
    "premium": {
        "name": "Premium",
        "price": "$7,500/mo",
        "price_value": 7500,
        "posts_per_month": 24,
        "platforms": "All",
        "reports": "Weekly performance reports",
        "video_ads": 4,
        "strategy_calls": "Weekly",
        "deliverables": [
            "24 custom content pieces per month",
            "All platform management (Instagram, TikTok, LinkedIn, X, Facebook, YouTube)",
            "Weekly performance reports with actionable insights",
            "4 professional video ads per month",
            "Full content calendar with strategic planning",
            "Advanced SEO and hashtag optimization",
            "Proactive community management",
            "Weekly strategy calls",
            "Competitor and industry monitoring",
            "Influencer collaboration strategy",
            "Paid ad creative consultation",
            "Priority response (< 4 hour turnaround)",
        ],
    },
    "custom": {
        "name": "Custom",
        "price": "Custom pricing",
        "price_value": 0,
        "posts_per_month": "TBD",
        "platforms": "TBD",
        "reports": "Custom cadence",
        "video_ads": "TBD",
        "strategy_calls": "TBD",
        "deliverables": ["Scope determined by audit findings and client goals"],
    },
}


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_latest_json(client_dir: Path, prefix: str) -> dict | None:
    """Load the most recent JSON file matching a prefix."""
    pattern = str(client_dir / f"{prefix}*.json")
    files = sorted(globmod.glob(pattern), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def _quick_research(company: str) -> dict:
    """Fallback Tavily research when no audit exists."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(
            query=f"{company} company social media marketing website",
            max_results=5,
            search_depth="advanced",
        )
        snippets = [r.get("content", "") for r in results.get("results", [])]
        return {"source": "tavily_quick_research", "findings": snippets[:5]}
    except Exception as e:
        print(f"[AUROS] Tavily research skipped: {e}")
        return {"source": "tavily_quick_research", "findings": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Proposal generation prompt
# ---------------------------------------------------------------------------

PROPOSAL_PROMPT = """You are the AUROS proposal strategist. Generate a compelling, data-driven client proposal for {company}.

SELECTED PACKAGE: {package_name} ({package_price})
PACKAGE DELIVERABLES: {package_deliverables}

CLIENT DATA (from audit/research):
{client_data}

Generate a full proposal. Return valid JSON:
{{
  "company": "{company}",
  "package": "{package_name}",
  "date": "{today}",
  "valid_until": "{valid_until}",
  "cover": {{
    "headline": "A bold, specific headline for this client (not generic)",
    "subheadline": "One line that connects their pain point to our solution"
  }},
  "about_auros": {{
    "intro": "2-3 sentences about AUROS as a premium AI marketing agency",
    "differentiators": ["3-4 unique selling points"],
    "stats": [
      {{"label": "...", "value": "..."}}
    ]
  }},
  "the_problem": {{
    "headline": "Bold problem statement",
    "pain_points": [
      {{"issue": "...", "impact": "...", "evidence": "..."}}
    ],
    "cost_of_inaction": "What happens if they don't fix this"
  }},
  "the_solution": {{
    "headline": "Bold solution statement",
    "approach": "2-3 sentences on our strategic approach",
    "pillars": [
      {{"title": "...", "description": "..."}}
    ]
  }},
  "scope_of_work": {{
    "summary": "One sentence overview",
    "deliverables": [
      {{"item": "...", "frequency": "...", "detail": "..."}}
    ]
  }},
  "content_examples": [
    {{"type": "...", "description": "What we'd create and why it works for them", "platform": "..."}}
  ],
  "timeline": {{
    "phase_1": {{"name": "Foundation (Days 1-30)", "activities": ["..."]}},
    "phase_2": {{"name": "Acceleration (Days 31-60)", "activities": ["..."]}},
    "phase_3": {{"name": "Optimization (Days 61-90)", "activities": ["..."]}}
  }},
  "investment": {{
    "package_name": "{package_name}",
    "monthly_price": "{package_price}",
    "includes": ["..."],
    "optional_addons": [
      {{"item": "...", "price": "..."}}
    ],
    "commitment": "3-month minimum engagement",
    "payment_terms": "Net 15, invoiced on the 1st of each month"
  }},
  "why_auros": [
    {{"point": "...", "explanation": "..."}}
  ],
  "next_steps": [
    {{"step": 1, "action": "...", "detail": "..."}}
  ]
}}

Important:
- Make the problem section hit hard — use specific findings from the audit
- The solution should directly address every weakness found
- Content examples should be realistic and specific to their industry
- The timeline should show quick wins in phase 1
- Make it impossible to say no"""


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def _render_html_proposal(proposal: dict, package: dict) -> str:
    """Render the proposal as a stunning multi-section HTML page."""

    company = proposal.get("company", "Client")
    date = proposal.get("date", "")
    valid_until = proposal.get("valid_until", "")
    cover = proposal.get("cover", {})
    about = proposal.get("about_auros", {})
    problem = proposal.get("the_problem", {})
    solution = proposal.get("the_solution", {})
    scope = proposal.get("scope_of_work", {})
    examples = proposal.get("content_examples", [])
    timeline = proposal.get("timeline", {})
    investment = proposal.get("investment", {})
    why_auros = proposal.get("why_auros", [])
    next_steps = proposal.get("next_steps", [])

    # About AUROS section
    differentiators_html = ""
    for d in about.get("differentiators", []):
        differentiators_html += f"<li>{d}</li>"

    about_stats_html = ""
    for s in about.get("stats", []):
        about_stats_html += f"""
        <div class="stat-card">
            <div class="stat-value">{s.get('value', '')}</div>
            <div class="stat-label">{s.get('label', '')}</div>
        </div>"""

    # Problem section
    pain_points_html = ""
    for p in problem.get("pain_points", []):
        pain_points_html += f"""
        <div class="pain-card">
            <div class="pain-issue">{p.get('issue', '')}</div>
            <div class="pain-impact">{p.get('impact', '')}</div>
            <div class="pain-evidence">{p.get('evidence', '')}</div>
        </div>"""

    # Solution pillars
    pillars_html = ""
    for p in solution.get("pillars", []):
        pillars_html += f"""
        <div class="pillar-card">
            <div class="pillar-title">{p.get('title', '')}</div>
            <div class="pillar-desc">{p.get('description', '')}</div>
        </div>"""

    # Scope of work
    scope_html = ""
    for d in scope.get("deliverables", []):
        scope_html += f"""
        <tr>
            <td class="scope-item">{d.get('item', '')}</td>
            <td class="scope-freq">{d.get('frequency', '')}</td>
            <td class="scope-detail">{d.get('detail', '')}</td>
        </tr>"""

    # Content examples
    examples_html = ""
    for ex in examples:
        examples_html += f"""
        <div class="example-card">
            <div class="example-type">{ex.get('type', '')}</div>
            <div class="example-platform">{ex.get('platform', '')}</div>
            <div class="example-desc">{ex.get('description', '')}</div>
        </div>"""

    # Timeline
    timeline_html = ""
    for phase_key in ["phase_1", "phase_2", "phase_3"]:
        phase = timeline.get(phase_key, {})
        activities_html = ""
        for a in phase.get("activities", []):
            activities_html += f"<li>{a}</li>"
        timeline_html += f"""
        <div class="phase-card">
            <div class="phase-name">{phase.get('name', '')}</div>
            <ul class="phase-activities">{activities_html}</ul>
        </div>"""

    # Investment
    includes_html = ""
    for inc in investment.get("includes", []):
        includes_html += f"<li>{inc}</li>"

    addons_html = ""
    for addon in investment.get("optional_addons", []):
        addons_html += f"""
        <div class="addon-row">
            <span class="addon-item">{addon.get('item', '')}</span>
            <span class="addon-price">{addon.get('price', '')}</span>
        </div>"""

    # Why AUROS
    why_html = ""
    for w in why_auros:
        why_html += f"""
        <div class="why-card">
            <div class="why-point">{w.get('point', '')}</div>
            <div class="why-explain">{w.get('explanation', '')}</div>
        </div>"""

    # Next steps
    steps_html = ""
    for s in next_steps:
        steps_html += f"""
        <div class="step-card">
            <div class="step-number">{s.get('step', '')}</div>
            <div class="step-body">
                <div class="step-action">{s.get('action', '')}</div>
                <div class="step-detail">{s.get('detail', '')}</div>
            </div>
        </div>"""

    # Build pricing table rows for comparison (show all packages)
    pricing_rows_html = ""
    for pkg_key, pkg in PACKAGES.items():
        if pkg_key == "custom":
            continue
        is_selected = pkg.get("name", "") == package.get("name", "")
        selected_class = "pricing-selected" if is_selected else ""
        badge = '<span class="pricing-badge">RECOMMENDED</span>' if is_selected else ""
        pricing_rows_html += f"""
        <div class="pricing-card {selected_class}">
            <div class="pricing-name">{pkg.get('name', '')}{badge}</div>
            <div class="pricing-price">{pkg.get('price', '')}</div>
            <div class="pricing-detail">{pkg.get('posts_per_month', '')} posts/mo &middot; {pkg.get('platforms', '')} platforms</div>
            <div class="pricing-detail">{pkg.get('reports', '')}</div>
            <div class="pricing-detail">{pkg.get('video_ads', '')} video ads/mo</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Proposal — {company}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0B0F1A;
    color: #FAFAF8;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}

  /* Full-width sections */
  .full-section {{
    width: 100%;
    padding: 80px 24px;
  }}
  .section-inner {{
    max-width: 900px;
    margin: 0 auto;
  }}

  /* Cover */
  .cover {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 60px 24px;
    position: relative;
    background: linear-gradient(180deg, #0B0F1A 0%, #111827 50%, #0B0F1A 100%);
  }}
  .cover-brand {{
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 6px;
    color: #C9A84C;
    margin-bottom: 48px;
  }}
  .cover-for {{
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 3px;
    color: #9CA3AF;
    text-transform: uppercase;
    margin-bottom: 16px;
  }}
  .cover-company {{
    font-size: 48px;
    font-weight: 900;
    letter-spacing: -2px;
    margin-bottom: 24px;
    background: linear-gradient(135deg, #FAFAF8, #C9A84C);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .cover-headline {{
    font-size: 22px;
    font-weight: 600;
    color: #F0EDE6;
    max-width: 600px;
    margin-bottom: 12px;
  }}
  .cover-sub {{
    font-size: 15px;
    color: #9CA3AF;
    max-width: 500px;
  }}
  .cover-meta {{
    position: absolute;
    bottom: 40px;
    font-size: 12px;
    color: #4B5563;
  }}
  .cover-divider {{
    width: 60px;
    height: 2px;
    background: #C9A84C;
    margin: 32px auto;
  }}

  /* Section headings */
  .section-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #C9A84C;
    text-transform: uppercase;
    margin-bottom: 12px;
  }}
  .section-title {{
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 20px;
  }}
  .section-body {{
    font-size: 15px;
    color: #F0EDE6;
    line-height: 1.7;
    margin-bottom: 24px;
  }}

  /* Dividers between sections */
  .section-divider {{
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
    height: 1px;
    background: rgba(201,168,76,0.15);
  }}

  /* Cards */
  .card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 16px;
  }}

  /* Stat cards */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin: 24px 0;
  }}
  .stat-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
  }}
  .stat-value {{
    font-size: 28px;
    font-weight: 800;
    color: #C9A84C;
    margin-bottom: 4px;
  }}
  .stat-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: #9CA3AF;
    text-transform: uppercase;
  }}

  /* Lists */
  .styled-list {{
    list-style: none;
    padding: 0;
  }}
  .styled-list li {{
    padding: 10px 0;
    padding-left: 24px;
    position: relative;
    font-size: 14px;
    color: #F0EDE6;
    border-bottom: 1px solid rgba(201,168,76,0.06);
  }}
  .styled-list li:last-child {{ border-bottom: none; }}
  .styled-list li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 16px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #C9A84C;
  }}

  /* Pain point cards */
  .pain-card {{
    background: #111827;
    border-left: 3px solid #ef4444;
    border-radius: 0 12px 12px 0;
    padding: 24px;
    margin-bottom: 12px;
  }}
  .pain-issue {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #FAFAF8;
  }}
  .pain-impact {{
    font-size: 14px;
    color: #ef4444;
    font-weight: 500;
    margin-bottom: 4px;
  }}
  .pain-evidence {{
    font-size: 13px;
    color: #9CA3AF;
  }}
  .cost-inaction {{
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 12px;
    padding: 24px;
    margin-top: 20px;
    font-size: 15px;
    color: #F0EDE6;
    font-weight: 500;
  }}

  /* Pillar cards */
  .pillars-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 16px;
    margin-top: 20px;
  }}
  .pillar-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.2);
    border-radius: 12px;
    padding: 28px;
  }}
  .pillar-title {{
    font-size: 16px;
    font-weight: 700;
    color: #C9A84C;
    margin-bottom: 8px;
  }}
  .pillar-desc {{
    font-size: 13px;
    color: #F0EDE6;
    line-height: 1.6;
  }}

  /* Scope table */
  .scope-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
  }}
  .scope-table th {{
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #C9A84C;
    text-transform: uppercase;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(201,168,76,0.2);
  }}
  .scope-table td {{
    padding: 14px 16px;
    font-size: 14px;
    color: #F0EDE6;
    border-bottom: 1px solid rgba(201,168,76,0.06);
    vertical-align: top;
  }}
  .scope-item {{ font-weight: 600; }}
  .scope-freq {{ color: #C9A84C; font-weight: 500; }}
  .scope-detail {{ color: #9CA3AF; }}

  /* Content examples */
  .examples-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin-top: 16px;
  }}
  .example-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
  }}
  .example-type {{
    font-size: 15px;
    font-weight: 700;
    color: #FAFAF8;
    margin-bottom: 4px;
  }}
  .example-platform {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: #C9A84C;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .example-desc {{
    font-size: 13px;
    color: #9CA3AF;
    line-height: 1.5;
  }}

  /* Timeline phases */
  .timeline-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 16px;
    margin-top: 16px;
  }}
  .phase-card {{
    background: #111827;
    border-top: 3px solid #C9A84C;
    border-radius: 0 0 12px 12px;
    padding: 28px;
  }}
  .phase-name {{
    font-size: 16px;
    font-weight: 700;
    color: #C9A84C;
    margin-bottom: 12px;
  }}
  .phase-activities {{
    list-style: none;
    padding: 0;
  }}
  .phase-activities li {{
    font-size: 13px;
    color: #F0EDE6;
    padding: 6px 0 6px 16px;
    position: relative;
  }}
  .phase-activities li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 12px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(201,168,76,0.5);
  }}

  /* Pricing cards */
  .pricing-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin: 24px 0;
  }}
  .pricing-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 28px;
    text-align: center;
    transition: transform 0.2s;
  }}
  .pricing-selected {{
    border: 2px solid #C9A84C;
    background: linear-gradient(180deg, #111827 0%, #1a1a2e 100%);
    transform: scale(1.03);
  }}
  .pricing-name {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 8px;
  }}
  .pricing-badge {{
    display: inline-block;
    background: #C9A84C;
    color: #0B0F1A;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 3px 8px;
    border-radius: 4px;
    margin-left: 8px;
    vertical-align: middle;
  }}
  .pricing-price {{
    font-size: 28px;
    font-weight: 900;
    color: #C9A84C;
    margin-bottom: 12px;
  }}
  .pricing-detail {{
    font-size: 13px;
    color: #9CA3AF;
    margin-bottom: 4px;
  }}

  /* Investment detail */
  .investment-includes {{
    margin-top: 20px;
  }}
  .addon-row {{
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid rgba(201,168,76,0.08);
    font-size: 14px;
  }}
  .addon-item {{ color: #F0EDE6; }}
  .addon-price {{ color: #C9A84C; font-weight: 600; }}
  .terms {{
    margin-top: 20px;
    font-size: 13px;
    color: #6B7280;
  }}

  /* Why AUROS */
  .why-card {{
    background: #111827;
    border-left: 3px solid #C9A84C;
    border-radius: 0 12px 12px 0;
    padding: 24px;
    margin-bottom: 12px;
  }}
  .why-point {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 6px;
  }}
  .why-explain {{
    font-size: 13px;
    color: #9CA3AF;
  }}

  /* Next steps */
  .step-card {{
    display: flex;
    gap: 20px;
    align-items: flex-start;
    margin-bottom: 16px;
  }}
  .step-number {{
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: #C9A84C;
    color: #0B0F1A;
    font-size: 20px;
    font-weight: 900;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .step-action {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 4px;
  }}
  .step-detail {{
    font-size: 13px;
    color: #9CA3AF;
  }}

  /* Footer */
  .footer {{
    text-align: center;
    padding: 60px 24px 40px;
    border-top: 1px solid rgba(201,168,76,0.2);
  }}
  .footer-brand {{
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 4px;
    color: #C9A84C;
    margin-bottom: 8px;
  }}
  .footer-tagline {{
    font-size: 14px;
    color: #6B7280;
    font-style: italic;
    margin-bottom: 20px;
  }}
  .footer-legal {{
    font-size: 11px;
    color: #4B5563;
    max-width: 500px;
    margin: 0 auto;
  }}
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover">
  <div class="cover-brand">AUROS</div>
  <div class="cover-for">Prepared For</div>
  <div class="cover-company">{company}</div>
  <div class="cover-divider"></div>
  <div class="cover-headline">{cover.get('headline', '')}</div>
  <div class="cover-sub">{cover.get('subheadline', '')}</div>
  <div class="cover-meta">{date} &middot; Valid until {valid_until} &middot; Confidential</div>
</div>

<!-- ABOUT AUROS -->
<div class="full-section" style="background:#111827;">
  <div class="section-inner">
    <div class="section-label">Who We Are</div>
    <div class="section-title">About AUROS</div>
    <div class="section-body">{about.get('intro', '')}</div>
    <div class="stats-grid">
      {about_stats_html}
    </div>
    <ul class="styled-list">
      {differentiators_html}
    </ul>
  </div>
</div>

<div class="section-divider"></div>

<!-- THE PROBLEM -->
<div class="full-section">
  <div class="section-inner">
    <div class="section-label">The Challenge</div>
    <div class="section-title">{problem.get('headline', 'The Problem')}</div>
    {pain_points_html}
    <div class="cost-inaction">{problem.get('cost_of_inaction', '')}</div>
  </div>
</div>

<div class="section-divider"></div>

<!-- THE SOLUTION -->
<div class="full-section" style="background:#111827;">
  <div class="section-inner">
    <div class="section-label">Our Approach</div>
    <div class="section-title">{solution.get('headline', 'The Solution')}</div>
    <div class="section-body">{solution.get('approach', '')}</div>
    <div class="pillars-grid">
      {pillars_html}
    </div>
  </div>
</div>

<div class="section-divider"></div>

<!-- SCOPE OF WORK -->
<div class="full-section">
  <div class="section-inner">
    <div class="section-label">Scope</div>
    <div class="section-title">Scope of Work</div>
    <div class="section-body">{scope.get('summary', '')}</div>
    <table class="scope-table">
      <thead>
        <tr><th>Deliverable</th><th>Frequency</th><th>Details</th></tr>
      </thead>
      <tbody>
        {scope_html}
      </tbody>
    </table>
  </div>
</div>

<div class="section-divider"></div>

<!-- CONTENT EXAMPLES -->
<div class="full-section" style="background:#111827;">
  <div class="section-inner">
    <div class="section-label">Creative</div>
    <div class="section-title">Content We'll Create</div>
    <div class="examples-grid">
      {examples_html}
    </div>
  </div>
</div>

<div class="section-divider"></div>

<!-- TIMELINE -->
<div class="full-section">
  <div class="section-inner">
    <div class="section-label">Roadmap</div>
    <div class="section-title">First 90 Days</div>
    <div class="timeline-grid">
      {timeline_html}
    </div>
  </div>
</div>

<div class="section-divider"></div>

<!-- INVESTMENT -->
<div class="full-section" style="background:#111827;">
  <div class="section-inner">
    <div class="section-label">Investment</div>
    <div class="section-title">Your Investment</div>
    <div class="pricing-grid">
      {pricing_rows_html}
    </div>
    <div class="card investment-includes">
      <div class="section-label" style="margin-bottom:12px">Your {investment.get('package_name', '')} Package Includes</div>
      <ul class="styled-list">
        {includes_html}
      </ul>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="section-label" style="margin-bottom:12px">Optional Add-Ons</div>
      {addons_html}
    </div>
    <div class="terms">
      {investment.get('commitment', '')} &middot; {investment.get('payment_terms', '')}
    </div>
  </div>
</div>

<div class="section-divider"></div>

<!-- WHY AUROS -->
<div class="full-section">
  <div class="section-inner">
    <div class="section-label">Why Us</div>
    <div class="section-title">Why AUROS</div>
    {why_html}
  </div>
</div>

<div class="section-divider"></div>

<!-- NEXT STEPS -->
<div class="full-section" style="background:#111827;">
  <div class="section-inner">
    <div class="section-label">Get Started</div>
    <div class="section-title">Next Steps</div>
    {steps_html}
  </div>
</div>

<!-- FOOTER -->
<div class="footer">
  <div class="footer-brand">AUROS</div>
  <div class="footer-tagline">Intelligence, Elevated.</div>
  <div class="footer-legal">
    This proposal is confidential and prepared exclusively for {company}.
    Valid until {valid_until}. All pricing is in USD.
  </div>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(company: str, package: str = "growth") -> dict:
    """Generate a client proposal."""
    today = datetime.now().strftime("%Y-%m-%d")
    valid_until_dt = datetime.now()
    # Valid for 30 days
    from datetime import timedelta
    valid_until = (valid_until_dt + timedelta(days=30)).strftime("%Y-%m-%d")

    pkg = PACKAGES.get(package)
    if not pkg:
        print(f"[AUROS] Unknown package '{package}'. Options: {', '.join(PACKAGES.keys())}")
        sys.exit(1)

    print(f"[AUROS] Proposal Generator starting — {company} — {pkg['name']} package")

    # Load existing client data
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"

    client_data: dict = {"company": company}

    # Try to load audit
    audit = _load_latest_json(client_dir, "marketing_audit") if client_dir.exists() else None
    if audit:
        client_data["marketing_audit"] = audit
        print("[AUROS] Loaded existing marketing audit")
    else:
        print("[AUROS] No audit found — running quick research...")
        client_data["research"] = _quick_research(company)

    # Try to load brand identity
    brand = _load_latest_json(client_dir, "brand_identity") if client_dir.exists() else None
    if brand:
        client_data["brand_identity"] = brand
        print("[AUROS] Loaded brand identity")

    # Load marketing knowledge base
    try:
        from agents.shared.knowledge import get_proposal_knowledge
        knowledge = get_proposal_knowledge()
        print("[AUROS] Loaded marketing knowledge base for proposal enrichment")
    except Exception:
        knowledge = ""

    # Generate proposal via Claude
    print("[AUROS] Generating proposal...")
    prompt = PROPOSAL_PROMPT.format(
        company=company,
        today=today,
        valid_until=valid_until,
        package_name=pkg["name"],
        package_price=pkg["price"],
        package_deliverables=json.dumps(pkg["deliverables"], indent=2),
        client_data=json.dumps(client_data, indent=2)[:10000],
    )
    if knowledge:
        prompt += f"\n\n{knowledge[:4000]}"
    raw = generate(prompt, temperature=0.5, max_tokens=4096)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    proposal = json.loads(json_str)

    # Save results
    client_dir.mkdir(parents=True, exist_ok=True)

    # JSON version
    json_path = client_dir / f"proposal_{today}.json"
    json_path.write_text(json.dumps(proposal, indent=2))
    print(f"[AUROS] JSON proposal saved to {json_path}")

    # HTML version
    html_content = _render_html_proposal(proposal, pkg)
    html_path = client_dir / f"proposal_{today}.html"
    html_path.write_text(html_content)
    print(f"[AUROS] HTML proposal saved to {html_path}")

    print(f"[AUROS] Proposal Generator complete — {company} — {pkg['name']}")
    return proposal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Proposal Generator")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument(
        "--package",
        default="growth",
        choices=["starter", "growth", "premium", "custom"],
        help="Package tier (default: growth)",
    )
    args = parser.parse_args()
    run(**vars(args))
