#!/usr/bin/env python3
"""
AUROS AI — Agent 2: Brand Identity Extractor
Analyzes a company's website and social presence to extract their complete
brand identity: colors, typography, logos, visual style, tone of voice.

Usage:
    python -m agents.brand_extractor.brand_agent --company "Company Name" --website "https://example.com"
"""

from __future__ import annotations

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR
from agents.shared.llm import generate
from agents.brand_extractor.visual_analyzer import extract_visual_identity


BRAND_PROMPT = """You are the AUROS brand identity analyst. Given the visual and content data extracted from a company's website, produce a comprehensive brand identity profile.

Analyze and return as valid JSON:
{{
  "company": "...",
  "extraction_date": "...",
  "colors": {{
    "primary": [{{"hex": "...", "name": "...", "usage": "..."}}],
    "secondary": [{{"hex": "...", "name": "...", "usage": "..."}}],
    "accent": [{{"hex": "...", "name": "...", "usage": "..."}}],
    "neutrals": [{{"hex": "...", "name": "...", "usage": "..."}}]
  }},
  "typography": {{
    "primary_font": "...",
    "secondary_font": "...",
    "heading_style": "...",
    "body_style": "...",
    "observations": "..."
  }},
  "logo": {{
    "type": "wordmark/icon/combination/lettermark",
    "description": "...",
    "primary_color": "...",
    "usage_notes": "..."
  }},
  "visual_style": {{
    "photography_style": "...",
    "illustration_style": "...",
    "layout_tendency": "...",
    "whitespace_usage": "...",
    "overall_aesthetic": "..."
  }},
  "tone_of_voice": {{
    "formality": "formal/semi-formal/casual/playful",
    "personality_traits": ["..."],
    "sample_phrases": ["..."],
    "messaging_themes": ["..."]
  }},
  "brand_positioning": {{
    "market_segment": "luxury/premium/mid-range/budget/niche",
    "target_audience": "...",
    "value_proposition": "...",
    "differentiators": ["..."]
  }},
  "consistency_score": 0,
  "consistency_notes": "...",
  "recommendations_for_content_creation": [
    "..."
  ]
}}

EXTRACTED DATA:
{visual_data}
"""


def run(company: str, website: str | None = None, assets_dir: str | None = None) -> dict:
    """Extract brand identity from a company's web presence."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[AUROS] Brand Identity Extraction starting — {company}")

    visual_data = {"company": company, "date": today}

    # Extract from website
    if website:
        print(f"[AUROS] Extracting visual identity from: {website}")
        visual_data["website"] = extract_visual_identity(website)

    # If assets directory provided, note it
    if assets_dir:
        assets_path = Path(assets_dir)
        if assets_path.exists():
            asset_files = [f.name for f in assets_path.iterdir() if f.is_file()]
            visual_data["provided_assets"] = asset_files
            print(f"[AUROS] Found {len(asset_files)} provided brand assets")

    # Generate brand profile via Claude
    print("[AUROS] Analyzing brand identity...")
    prompt = BRAND_PROMPT.format(visual_data=json.dumps(visual_data, indent=2)[:10000])
    raw = generate(prompt, temperature=0.3, max_tokens=4096)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    brand_profile = json.loads(json_str)

    # Save
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    client_dir.mkdir(parents=True, exist_ok=True)

    profile_path = client_dir / f"brand_identity_{today}.json"
    profile_path.write_text(json.dumps(brand_profile, indent=2))
    print(f"[AUROS] Brand profile saved to {profile_path}")

    # Generate a visual summary HTML
    html_path = client_dir / f"brand_identity_{today}.html"
    html_path.write_text(_brand_to_html(brand_profile))
    print(f"[AUROS] Visual summary saved to {html_path}")

    print(f"[AUROS] Brand extraction complete — Consistency: {brand_profile.get('consistency_score', 'N/A')}/100")
    return brand_profile


def _brand_to_html(profile: dict) -> str:
    """Generate a visual brand identity summary in HTML."""
    colors_html = ""
    for category in ["primary", "secondary", "accent", "neutrals"]:
        for color in profile.get("colors", {}).get(category, []):
            hex_val = color.get("hex", "#000")
            text_color = "#FFF" if _is_dark(hex_val) else "#000"
            colors_html += f"""
            <div style="background:{hex_val};color:{text_color};padding:20px;min-width:120px;text-align:center;">
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">{color.get('name', '')}</div>
              <div style="font-size:10px;opacity:0.8;margin-top:4px;">{hex_val}</div>
              <div style="font-size:9px;opacity:0.6;margin-top:2px;">{category}</div>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Brand Identity — {profile.get('company', '')}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:#0B0F1A; color:#FAFAF8; padding:60px; }}
  .header {{ margin-bottom:48px; }}
  .label {{ font-size:10px; font-weight:700; letter-spacing:4px; color:#C9A84C; text-transform:uppercase; margin-bottom:12px; }}
  h1 {{ font-size:42px; font-weight:900; letter-spacing:-1px; margin-bottom:8px; }}
  .sub {{ font-size:16px; color:#9CA3AF; }}
  .section {{ margin-top:48px; }}
  .section h2 {{ font-size:24px; font-weight:700; margin-bottom:20px; }}
  .color-grid {{ display:flex; gap:2px; flex-wrap:wrap; }}
  .info-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:2px; }}
  .info-card {{ background:#111827; padding:24px; }}
  .info-card h3 {{ font-size:13px; color:#C9A84C; letter-spacing:2px; text-transform:uppercase; margin-bottom:12px; }}
  .info-card p {{ font-size:14px; color:#9CA3AF; line-height:1.7; }}
  .tag {{ display:inline-block; background:rgba(201,168,76,0.1); border:1px solid rgba(201,168,76,0.2); color:#C9A84C; padding:4px 12px; font-size:11px; letter-spacing:1px; margin:4px 4px 4px 0; }}
</style>
</head>
<body>
<div class="header">
  <div class="label">AUROS — Brand Identity Extraction</div>
  <h1>{profile.get('company', 'Company')}</h1>
  <div class="sub">Extracted {profile.get('extraction_date', '')} · Consistency Score: {profile.get('consistency_score', 'N/A')}/100</div>
</div>

<div class="section">
  <h2>Color Palette</h2>
  <div class="color-grid">{colors_html}</div>
</div>

<div class="section">
  <h2>Brand Profile</h2>
  <div class="info-grid">
    <div class="info-card">
      <h3>Typography</h3>
      <p>Primary: {profile.get('typography', {}).get('primary_font', 'N/A')}<br>
      Secondary: {profile.get('typography', {}).get('secondary_font', 'N/A')}<br>
      {profile.get('typography', {}).get('observations', '')}</p>
    </div>
    <div class="info-card">
      <h3>Logo</h3>
      <p>Type: {profile.get('logo', {}).get('type', 'N/A')}<br>
      {profile.get('logo', {}).get('description', '')}</p>
    </div>
    <div class="info-card">
      <h3>Visual Style</h3>
      <p>{profile.get('visual_style', {}).get('overall_aesthetic', 'N/A')}<br>
      Photography: {profile.get('visual_style', {}).get('photography_style', 'N/A')}</p>
    </div>
    <div class="info-card">
      <h3>Tone of Voice</h3>
      <p>Formality: {profile.get('tone_of_voice', {}).get('formality', 'N/A')}<br>
      {''.join(f'<span class="tag">{t}</span>' for t in profile.get('tone_of_voice', {}).get('personality_traits', []))}</p>
    </div>
    <div class="info-card">
      <h3>Market Positioning</h3>
      <p>Segment: {profile.get('brand_positioning', {}).get('market_segment', 'N/A')}<br>
      {profile.get('brand_positioning', {}).get('value_proposition', '')}</p>
    </div>
    <div class="info-card">
      <h3>Content Recommendations</h3>
      <p>{'<br>'.join(f'• {r}' for r in profile.get('recommendations_for_content_creation', []))}</p>
    </div>
  </div>
</div>

<div style="margin-top:48px;padding-top:24px;border-top:1px solid rgba(201,168,76,0.2);text-align:center;">
  <span style="font-size:20px;font-weight:900;color:#C9A84C;">AUROS</span><br>
  <span style="font-size:10px;color:#6B7280;letter-spacing:1px;">Intelligence, Elevated.</span>
</div>
</body>
</html>"""


def _is_dark(hex_color: str) -> bool:
    """Check if a color is dark (for text contrast)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return True
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Brand Identity Extractor")
    parser.add_argument("--company", required=True)
    parser.add_argument("--website", help="Company website URL")
    parser.add_argument("--assets", help="Path to directory with provided brand assets")
    args = parser.parse_args()
    run(company=args.company, website=args.website, assets_dir=args.assets)
