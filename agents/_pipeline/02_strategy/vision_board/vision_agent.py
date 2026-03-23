#!/usr/bin/env python3
"""
AUROS AI — Vision Board Creator
Creates interactive HTML vision/mood boards for clients showing what AUROS will build.

Usage:
    python -m agents.vision_board.vision_agent --company "Company Name"
"""

from __future__ import annotations

import sys
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, TAVILY_API_KEY, BRAND
from agents.shared.llm import generate, AUROS_SYSTEM_PROMPT


def _slugify(name: str) -> str:
    """Convert company name to slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search Tavily for visual inspiration."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query, max_results=max_results, search_depth="advanced")
    return response.get("results", [])


def _load_client_data(slug: str) -> tuple[dict, dict]:
    """Load marketing audit and brand identity JSONs for a client."""
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    audit = {}
    brand_identity = {}

    # Find most recent audit
    audit_files = sorted(client_dir.glob("marketing_audit_*.json"), reverse=True)
    if audit_files:
        audit = json.loads(audit_files[0].read_text())
        print(f"[AUROS] Loaded audit: {audit_files[0].name}")

    # Find most recent brand identity
    brand_files = sorted(client_dir.glob("brand_identity_*.json"), reverse=True)
    if brand_files:
        brand_identity = json.loads(brand_files[0].read_text())
        print(f"[AUROS] Loaded brand identity: {brand_files[0].name}")

    return audit, brand_identity


VISION_PROMPT = """You are the AUROS creative director. Based on the marketing audit and brand identity data below, create a comprehensive vision board concept for this client.

CLIENT DATA:
{client_data}

VISUAL INSPIRATION RESEARCH:
{inspiration_data}

Generate a vision board concept as valid JSON with these sections:

{{
  "company_name": "...",
  "tagline_proposal": "A short tagline/creative direction statement",
  "mood_aesthetic": {{
    "title": "...",
    "description": "2-3 sentences on the overall mood",
    "keywords": ["5-8 mood keywords"],
    "visual_direction": "How the content should feel visually"
  }},
  "content_pillars": [
    {{
      "name": "Pillar Name",
      "description": "What this pillar covers",
      "example_topics": ["3 example topics"],
      "formats": ["reel", "carousel", "etc"],
      "frequency": "How often per week"
    }}
  ],
  "platform_strategy": [
    {{
      "platform": "Instagram",
      "role": "What this platform does for the brand",
      "content_mix": "Breakdown of content types",
      "posting_frequency": "X times per week",
      "key_tactics": ["3 specific tactics"]
    }}
  ],
  "reference_examples": [
    {{
      "description": "Description of reference content that works",
      "why_it_works": "Why this approach is effective",
      "how_we_adapt": "How we apply this for the client"
    }}
  ],
  "color_visual_treatment": {{
    "primary_palette": ["#hex1", "#hex2", "#hex3"],
    "accent_colors": ["#hex1", "#hex2"],
    "treatment_notes": "How to adapt brand colors for social",
    "typography_direction": "Font/text style recommendations",
    "filter_style": "Photo/video filter direction"
  }}
}}

Return ONLY valid JSON. Make the content pillars specific to this client's industry. Be concrete, not generic."""


def _build_html(vision: dict, client_colors: list[str], accent_colors: list[str]) -> str:
    """Render the vision board as an interactive HTML page."""
    company = vision.get("company_name", "Client")
    mood = vision.get("mood_aesthetic", {})
    pillars = vision.get("content_pillars", [])
    platforms = vision.get("platform_strategy", [])
    references = vision.get("reference_examples", [])
    color_treatment = vision.get("color_visual_treatment", {})

    # Build pillar cards
    pillar_html = ""
    pillar_colors = ["#C9A84C", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6"]
    for i, p in enumerate(pillars):
        color = pillar_colors[i % len(pillar_colors)]
        topics = "".join(f'<li>{t}</li>' for t in p.get("example_topics", []))
        formats = " &bull; ".join(p.get("formats", []))
        pillar_html += f"""
        <div class="card pillar-card" style="border-top:3px solid {color};">
            <div class="card-label" style="color:{color};">{p.get('name', '')}</div>
            <p class="card-body">{p.get('description', '')}</p>
            <ul class="topic-list">{topics}</ul>
            <div class="card-meta"><span class="tag">{formats}</span> &mdash; {p.get('frequency', '')}</div>
        </div>"""

    # Build platform cards
    platform_html = ""
    platform_colors = {
        "instagram": "#E1306C", "tiktok": "#00F2EA", "linkedin": "#0A66C2",
        "twitter": "#1DA1F2", "facebook": "#1877F2", "youtube": "#FF0000",
        "x": "#000000", "threads": "#000000", "pinterest": "#E60023"
    }
    for p in platforms:
        pname = p.get("platform", "")
        pcolor = platform_colors.get(pname.lower(), "#C9A84C")
        tactics = "".join(f'<li>{t}</li>' for t in p.get("key_tactics", []))
        platform_html += f"""
        <div class="card platform-card">
            <div class="platform-header" style="border-left:4px solid {pcolor};">
                <div class="card-label" style="color:{pcolor};">{pname}</div>
                <div class="card-meta">{p.get('posting_frequency', '')}</div>
            </div>
            <p class="card-body">{p.get('role', '')}</p>
            <p class="card-body" style="color:#9CA3AF;font-size:13px;">{p.get('content_mix', '')}</p>
            <ul class="tactic-list">{tactics}</ul>
        </div>"""

    # Build reference cards
    reference_html = ""
    for r in references:
        reference_html += f"""
        <div class="card ref-card">
            <p class="card-body" style="color:#FAFAF8;font-weight:600;">{r.get('description', '')}</p>
            <p class="card-body"><span style="color:#C9A84C;">Why it works:</span> {r.get('why_it_works', '')}</p>
            <p class="card-body"><span style="color:#3B82F6;">Our adaptation:</span> {r.get('how_we_adapt', '')}</p>
        </div>"""

    # Build color swatches
    all_colors = client_colors + accent_colors
    swatch_html = ""
    for c in all_colors:
        swatch_html += f"""
        <div class="swatch">
            <div class="swatch-color" style="background:{c};"></div>
            <div class="swatch-label">{c}</div>
        </div>"""

    # Mood keywords
    keywords_html = "".join(f'<span class="mood-tag">{k}</span>' for k in mood.get("keywords", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Vision Board — {company}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap" rel="stylesheet">
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ background:#0B0F1A; color:#FAFAF8; font-family:'Inter',sans-serif; line-height:1.6; }}

    .hero {{
        min-height:60vh; display:flex; flex-direction:column; justify-content:center; align-items:center;
        padding:80px 40px; text-align:center;
        background:linear-gradient(180deg, #0B0F1A 0%, #111827 50%, #0B0F1A 100%);
        position:relative; overflow:hidden;
    }}
    .hero::before {{
        content:''; position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
        width:500px; height:500px; border-radius:50%;
        background:radial-gradient(circle, rgba(201,168,76,0.06) 0%, transparent 70%);
    }}
    .hero-label {{ font-size:10px; letter-spacing:4px; color:#C9A84C; text-transform:uppercase; font-weight:700; margin-bottom:24px; }}
    .hero-title {{ font-size:clamp(36px,6vw,72px); font-weight:900; letter-spacing:-2px; margin-bottom:16px; }}
    .hero-title span {{ color:#C9A84C; }}
    .hero-subtitle {{ font-size:18px; color:#9CA3AF; max-width:600px; font-weight:300; }}
    .hero-tagline {{ margin-top:32px; font-size:24px; font-weight:600; color:#C9A84C; font-style:italic; }}

    .section {{ padding:80px 40px; max-width:1200px; margin:0 auto; }}
    .section-label {{ font-size:10px; letter-spacing:4px; color:#C9A84C; text-transform:uppercase; font-weight:700; margin-bottom:12px; }}
    .section-title {{ font-size:32px; font-weight:900; letter-spacing:-1px; margin-bottom:32px; }}
    .section-divider {{ width:60px; height:2px; background:#C9A84C; margin-bottom:40px; }}

    .mood-section {{ background:#111827; border-top:1px solid rgba(201,168,76,0.15); border-bottom:1px solid rgba(201,168,76,0.15); }}
    .mood-text {{ font-size:18px; color:#9CA3AF; line-height:1.8; max-width:700px; margin-bottom:24px; }}
    .mood-visual {{ font-size:15px; color:#FAFAF8; line-height:1.7; background:rgba(201,168,76,0.05); padding:20px 24px; border-radius:8px; border-left:3px solid #C9A84C; margin-top:16px; }}
    .mood-tags {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:24px; }}
    .mood-tag {{ background:rgba(201,168,76,0.1); color:#C9A84C; padding:6px 16px; border-radius:20px; font-size:13px; font-weight:600; letter-spacing:1px; }}

    .cards-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(320px,1fr)); gap:24px; }}
    .card {{ background:#111827; border-radius:12px; padding:28px; transition:transform 0.2s, box-shadow 0.2s; }}
    .card:hover {{ transform:translateY(-4px); box-shadow:0 8px 30px rgba(0,0,0,0.3); }}
    .card-label {{ font-size:11px; letter-spacing:3px; text-transform:uppercase; font-weight:700; margin-bottom:12px; }}
    .card-body {{ font-size:14px; color:#9CA3AF; line-height:1.7; margin-bottom:12px; }}
    .card-meta {{ font-size:12px; color:#6B7280; margin-top:8px; }}
    .tag {{ background:rgba(59,130,246,0.1); color:#3B82F6; padding:2px 8px; border-radius:4px; font-size:11px; }}

    .topic-list, .tactic-list {{ list-style:none; padding:0; margin:8px 0; }}
    .topic-list li, .tactic-list li {{ font-size:13px; color:#9CA3AF; padding:4px 0; padding-left:16px; position:relative; }}
    .topic-list li::before {{ content:'\\2022'; color:#C9A84C; position:absolute; left:0; }}
    .tactic-list li::before {{ content:'\\2192'; color:#C9A84C; position:absolute; left:0; }}

    .platform-header {{ padding-left:16px; margin-bottom:12px; }}

    .color-section {{ background:#0B0F1A; }}
    .swatches {{ display:flex; flex-wrap:wrap; gap:20px; margin-bottom:32px; }}
    .swatch {{ text-align:center; }}
    .swatch-color {{ width:80px; height:80px; border-radius:12px; border:2px solid rgba(255,255,255,0.1); }}
    .swatch-label {{ font-size:11px; color:#6B7280; margin-top:8px; font-family:monospace; }}

    .treatment-notes {{ font-size:15px; color:#9CA3AF; line-height:1.8; max-width:700px; }}
    .treatment-detail {{ background:#111827; padding:20px 24px; border-radius:8px; margin-top:16px; }}
    .treatment-detail-label {{ font-size:11px; letter-spacing:2px; color:#C9A84C; text-transform:uppercase; font-weight:700; margin-bottom:6px; }}
    .treatment-detail-value {{ font-size:14px; color:#FAFAF8; }}

    .footer {{
        padding:60px 40px; text-align:center;
        border-top:1px solid rgba(201,168,76,0.15);
    }}
    .footer-brand {{ font-size:24px; font-weight:900; color:#C9A84C; }}
    .footer-tagline {{ font-size:12px; color:#6B7280; letter-spacing:2px; margin-top:8px; }}

    @media (max-width:768px) {{
        .section {{ padding:60px 20px; }}
        .cards-grid {{ grid-template-columns:1fr; }}
        .hero {{ padding:60px 20px; min-height:50vh; }}
    }}
</style>
</head>
<body>

<div class="hero">
    <div class="hero-label">AUROS Vision Board</div>
    <h1 class="hero-title">The Vision for <span>{company}</span></h1>
    <p class="hero-subtitle">{mood.get('description', 'A strategic creative direction for your brand presence.')}</p>
    <p class="hero-tagline">"{vision.get('tagline_proposal', '')}"</p>
</div>

<div class="section mood-section">
    <div class="section-label">Mood &amp; Aesthetic Direction</div>
    <h2 class="section-title">{mood.get('title', 'Creative Direction')}</h2>
    <div class="section-divider"></div>
    <p class="mood-text">{mood.get('description', '')}</p>
    <div class="mood-visual">{mood.get('visual_direction', '')}</div>
    <div class="mood-tags">{keywords_html}</div>
</div>

<div class="section">
    <div class="section-label">Content Pillars</div>
    <h2 class="section-title">What We'll Create</h2>
    <div class="section-divider"></div>
    <div class="cards-grid">{pillar_html}</div>
</div>

<div class="section mood-section">
    <div class="section-label">Platform Strategy</div>
    <h2 class="section-title">Where We'll Show Up</h2>
    <div class="section-divider"></div>
    <div class="cards-grid">{platform_html}</div>
</div>

<div class="section">
    <div class="section-label">Reference Examples</div>
    <h2 class="section-title">What's Working Right Now</h2>
    <div class="section-divider"></div>
    <div class="cards-grid">{reference_html}</div>
</div>

<div class="section color-section">
    <div class="section-label">Color &amp; Visual Treatment</div>
    <h2 class="section-title">Your Brand on Social</h2>
    <div class="section-divider"></div>
    <div class="swatches">{swatch_html}</div>
    <p class="treatment-notes">{color_treatment.get('treatment_notes', '')}</p>
    <div class="treatment-detail">
        <div class="treatment-detail-label">Typography Direction</div>
        <div class="treatment-detail-value">{color_treatment.get('typography_direction', '')}</div>
    </div>
    <div class="treatment-detail" style="margin-top:12px;">
        <div class="treatment-detail-label">Filter &amp; Editing Style</div>
        <div class="treatment-detail-value">{color_treatment.get('filter_style', '')}</div>
    </div>
</div>

<div class="footer">
    <div class="footer-brand">AUROS</div>
    <div class="footer-tagline">Intelligence, Elevated.</div>
    <p style="color:#6B7280;font-size:12px;margin-top:24px;">Generated {datetime.now().strftime('%B %d, %Y')}</p>
</div>

</body>
</html>"""


def run(company: str) -> dict:
    """Execute the vision board creation pipeline."""
    today = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(company)
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    client_dir.mkdir(parents=True, exist_ok=True)

    print(f"[AUROS] Vision board agent starting for '{company}' — {today}")

    # Step 1: Load client data
    print("[AUROS] Loading client data...")
    audit, brand_identity = _load_client_data(slug)

    if not audit and not brand_identity:
        print("[AUROS] Warning: No audit or brand identity found. Generating with limited data.")

    # Step 2: Search for visual inspiration
    print("[AUROS] Searching for visual inspiration...")
    industry = audit.get("industry", brand_identity.get("industry", company))
    inspiration_queries = [
        f"{industry} social media visual inspiration best content 2025 2026",
        f"{industry} brand aesthetic mood board design trends",
        f"{company} competitors social media content strategy",
    ]
    inspiration = []
    for q in inspiration_queries:
        try:
            results = _search_tavily(q, max_results=3)
            inspiration.extend(results)
        except Exception as e:
            print(f"[AUROS] Tavily search warning: {e}")

    # Step 3: Generate vision board concept via Claude
    print("[AUROS] Generating vision board concept...")
    client_data = {
        "company_name": company,
        "audit": audit,
        "brand_identity": brand_identity,
    }
    inspiration_summary = [
        {"title": r.get("title", ""), "content": r.get("content", "")[:300]}
        for r in inspiration
    ]

    prompt = VISION_PROMPT.format(
        client_data=json.dumps(client_data, indent=2)[:6000],
        inspiration_data=json.dumps(inspiration_summary, indent=2)[:4000],
    )

    raw = generate(prompt, max_tokens=4096, temperature=0.6)

    # Parse JSON
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    vision = json.loads(json_str)

    # Step 4: Render HTML
    print("[AUROS] Rendering interactive HTML vision board...")
    color_treatment = vision.get("color_visual_treatment", {})
    client_colors = color_treatment.get("primary_palette", ["#C9A84C", "#3B82F6", "#FAFAF8"])
    accent_colors = color_treatment.get("accent_colors", ["#10B981", "#F59E0B"])

    html = _build_html(vision, client_colors, accent_colors)

    # Step 5: Save outputs
    html_path = client_dir / f"vision_board_{today}.html"
    html_path.write_text(html)
    print(f"[AUROS] Vision board saved to {html_path}")

    json_path = client_dir / f"vision_board_{today}.json"
    json_path.write_text(json.dumps(vision, indent=2))
    print(f"[AUROS] Vision data saved to {json_path}")

    print("[AUROS] Vision board complete.")
    return {"status": "complete", "html_path": str(html_path), "vision": vision}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Vision Board Creator")
    parser.add_argument("--company", required=True, help="Company name")
    args = parser.parse_args()
    run(company=args.company)
