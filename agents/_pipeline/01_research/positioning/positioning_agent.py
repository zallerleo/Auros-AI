#!/usr/bin/env python3
"""
AUROS AI — Positioning Angles Agent
Surfaces, scores, and ranks distinct positioning angles for a client brand
based on audit data, brand identity, and optional market research.

Usage:
    python -m agents.positioning.positioning_agent --company "The Imagine Team"
"""

from __future__ import annotations

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, BRAND
from agents.shared.llm import generate


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

POSITIONING_PROMPT = """You are the AUROS positioning strategist — the sharpest strategic mind in brand positioning.

Given the following data about a company (audit results, brand identity, and optional market research), produce exactly 5 distinct positioning angles.

For EACH angle, provide:
- **name**: Short memorable name for the angle (2-4 words)
- **tagline**: A punchy tagline (max 10 words)
- **target_audience**: Who this angle speaks to (specific, not generic)
- **key_differentiator**: The single thing that makes this angle defensible
- **emotional_hook**: The core emotion this angle triggers in the target audience
- **risk_level**: "low", "medium", or "high" — how risky is this positioning bet?
- **market_fit_score**: 1-10 rating of how well this fits current market conditions

After listing all 5 angles, PICK A WINNER:
- State which angle you recommend and why
- Provide 3-5 sentences of strategic reasoning
- Note any conditions under which a different angle would be better

Return as valid JSON:
{{
  "company": "...",
  "analysis_date": "...",
  "angles": [
    {{
      "rank": 1,
      "name": "...",
      "tagline": "...",
      "target_audience": "...",
      "key_differentiator": "...",
      "emotional_hook": "...",
      "risk_level": "low|medium|high",
      "market_fit_score": 8
    }}
  ],
  "recommended_angle": "...",
  "recommendation_reasoning": "...",
  "alternative_conditions": "..."
}}

Rank angles by market_fit_score descending. The recommended angle should be rank 1.

COMPANY DATA:
{company_data}
"""


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_client_data(company: str) -> dict:
    """Load all available data for a client from the portfolio directory."""
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"

    data: dict = {"company": company}

    if not client_dir.exists():
        print(f"[AUROS] No portfolio directory found for {company} — running with minimal data")
        return data

    # Load the most recent audit
    audits = sorted(client_dir.glob("marketing_audit_*.json"), reverse=True)
    if audits:
        try:
            data["audit"] = json.loads(audits[0].read_text())
            print(f"[AUROS] Loaded audit: {audits[0].name}")
        except Exception as e:
            print(f"[AUROS] Failed to load audit: {e}")

    # Load the most recent brand identity
    brands = sorted(client_dir.glob("brand_identity_*.json"), reverse=True)
    if brands:
        try:
            data["brand"] = json.loads(brands[0].read_text())
            print(f"[AUROS] Loaded brand identity: {brands[0].name}")
        except Exception as e:
            print(f"[AUROS] Failed to load brand identity: {e}")

    # Load any research files
    research_files = sorted(client_dir.glob("research_*.json"), reverse=True)
    if research_files:
        try:
            data["research"] = json.loads(research_files[0].read_text())
            print(f"[AUROS] Loaded research: {research_files[0].name}")
        except Exception as e:
            print(f"[AUROS] Failed to load research: {e}")

    return data


def _load_knowledge() -> str:
    """Load positioning knowledge base if available."""
    try:
        from agents.shared.knowledge import get_positioning_knowledge
        knowledge = get_positioning_knowledge()
        print("[AUROS] Loaded positioning knowledge base")
        return knowledge
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def run(
    company: str,
    audit_data: dict | None = None,
    brand_data: dict | None = None,
    research_context: str | None = None,
) -> dict:
    """Generate and rank 5 positioning angles for a company.

    Args:
        company: Company name.
        audit_data: Pre-loaded audit dict (skips portfolio lookup if provided).
        brand_data: Pre-loaded brand identity dict.
        research_context: Optional market research text to enrich the analysis.

    Returns:
        Positioning angles dict with ranked angles and recommendation.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[AUROS] Positioning Angles starting — {company} — {today}")

    # Assemble company data
    if audit_data or brand_data:
        company_data: dict = {"company": company}
        if audit_data:
            company_data["audit"] = audit_data
        if brand_data:
            company_data["brand"] = brand_data
    else:
        company_data = _load_client_data(company)

    company_data["analysis_date"] = today

    if research_context:
        company_data["research_context"] = research_context

    # Load knowledge base
    knowledge = _load_knowledge()

    # Generate positioning via Claude
    print("[AUROS] Generating positioning angles...")
    prompt = POSITIONING_PROMPT.format(
        company_data=json.dumps(company_data, indent=2, default=str)[:12000]
    )
    if knowledge:
        prompt += f"\n\nPOSITIONING KNOWLEDGE BASE:\n{knowledge[:3000]}"

    raw = generate(prompt, temperature=0.5, max_tokens=4096)

    # Parse JSON
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    positioning = json.loads(json_str)

    # Ensure angles are sorted by market_fit_score
    if "angles" in positioning:
        positioning["angles"] = sorted(
            positioning["angles"],
            key=lambda a: a.get("market_fit_score", 0),
            reverse=True,
        )
        for i, angle in enumerate(positioning["angles"], 1):
            angle["rank"] = i

    # Save outputs
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    client_dir.mkdir(parents=True, exist_ok=True)

    json_path = client_dir / f"positioning_angles_{today}.json"
    json_path.write_text(json.dumps(positioning, indent=2))
    print(f"[AUROS] Positioning JSON saved to {json_path}")

    html_path = client_dir / f"positioning_angles_{today}.html"
    html_path.write_text(_positioning_to_html(positioning))
    print(f"[AUROS] HTML summary saved to {html_path}")

    winner = positioning.get("recommended_angle", "N/A")
    print(f"[AUROS] Positioning complete — Recommended angle: {winner}")
    return positioning


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


def _positioning_to_html(data: dict) -> str:
    """Render positioning angles as a branded HTML summary."""
    gold = BRAND.get("colors", {}).get("primary", {}).get("gold", "#C9A84C")
    dark_bg = BRAND.get("colors", {}).get("backgrounds", {}).get("obsidian", "#0B0F1A")

    angles_html = ""
    for angle in data.get("angles", []):
        risk_color = {"low": "#10B981", "medium": "#F59E0B", "high": "#EF4444"}.get(
            angle.get("risk_level", "medium"), "#F59E0B"
        )
        score = angle.get("market_fit_score", 0)
        bar_width = score * 10

        angles_html += f"""
        <div class="angle-card {'winner' if angle.get('rank') == 1 else ''}">
          <div class="angle-rank">#{angle.get('rank', '?')}</div>
          <h3 class="angle-name">{angle.get('name', 'Untitled')}</h3>
          <div class="angle-tagline">"{angle.get('tagline', '')}"</div>
          <div class="angle-details">
            <div class="detail">
              <span class="detail-label">Target Audience</span>
              <span class="detail-value">{angle.get('target_audience', 'N/A')}</span>
            </div>
            <div class="detail">
              <span class="detail-label">Key Differentiator</span>
              <span class="detail-value">{angle.get('key_differentiator', 'N/A')}</span>
            </div>
            <div class="detail">
              <span class="detail-label">Emotional Hook</span>
              <span class="detail-value">{angle.get('emotional_hook', 'N/A')}</span>
            </div>
            <div class="detail">
              <span class="detail-label">Risk Level</span>
              <span class="detail-value" style="color:{risk_color};font-weight:700;">{angle.get('risk_level', 'N/A').upper()}</span>
            </div>
            <div class="detail">
              <span class="detail-label">Market Fit</span>
              <div class="score-bar"><div class="score-fill" style="width:{bar_width}%;"></div></div>
              <span class="score-num">{score}/10</span>
            </div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Positioning Angles — {data.get('company', '')}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:{dark_bg}; color:#FAFAF8; padding:60px; }}
  .header {{ margin-bottom:48px; }}
  .label {{ font-size:10px; font-weight:700; letter-spacing:4px; color:{gold}; text-transform:uppercase; margin-bottom:12px; }}
  h1 {{ font-size:42px; font-weight:900; letter-spacing:-1px; margin-bottom:8px; }}
  .sub {{ font-size:16px; color:#9CA3AF; }}
  .angles-grid {{ display:flex; flex-direction:column; gap:2px; margin-top:32px; }}
  .angle-card {{ background:#111827; padding:32px; position:relative; }}
  .angle-card.winner {{ border-left:4px solid {gold}; }}
  .angle-rank {{ position:absolute; top:32px; right:32px; font-size:36px; font-weight:900; color:rgba(201,168,76,0.15); }}
  .angle-name {{ font-size:22px; font-weight:700; margin-bottom:4px; }}
  .angle-tagline {{ font-size:14px; color:{gold}; font-style:italic; margin-bottom:20px; }}
  .angle-details {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .detail {{ }}
  .detail-label {{ display:block; font-size:10px; font-weight:700; letter-spacing:2px; color:#6B7280; text-transform:uppercase; margin-bottom:4px; }}
  .detail-value {{ font-size:14px; color:#D1D5DB; line-height:1.5; }}
  .score-bar {{ display:inline-block; width:100px; height:8px; background:#1F2937; border-radius:4px; overflow:hidden; vertical-align:middle; margin-right:8px; }}
  .score-fill {{ height:100%; background:linear-gradient(90deg,{gold},#E8D48B); border-radius:4px; }}
  .score-num {{ font-size:14px; font-weight:700; color:{gold}; }}
  .recommendation {{ background:#111827; border:1px solid rgba(201,168,76,0.3); padding:32px; margin-top:32px; }}
  .recommendation h2 {{ font-size:18px; font-weight:700; color:{gold}; margin-bottom:12px; }}
  .recommendation p {{ font-size:14px; color:#D1D5DB; line-height:1.7; }}
  .footer {{ margin-top:48px; padding-top:24px; border-top:1px solid rgba(201,168,76,0.2); text-align:center; }}
</style>
</head>
<body>

<div class="header">
  <div class="label">AUROS — Positioning Analysis</div>
  <h1>{data.get('company', 'Company')}</h1>
  <div class="sub">Generated {data.get('analysis_date', '')} &middot; 5 Strategic Angles</div>
</div>

<div class="angles-grid">{angles_html}</div>

<div class="recommendation">
  <h2>Recommended Angle: {data.get('recommended_angle', 'N/A')}</h2>
  <p>{data.get('recommendation_reasoning', '')}</p>
  <p style="margin-top:12px;color:#9CA3AF;font-size:13px;">{data.get('alternative_conditions', '')}</p>
</div>

<div class="footer">
  <span style="font-size:20px;font-weight:900;color:{gold};">AUROS</span><br>
  <span style="font-size:10px;color:#6B7280;letter-spacing:1px;">Intelligence, Elevated.</span>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Positioning Angles Agent")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--research", help="Optional research context (text or file path)")
    args = parser.parse_args()

    research_ctx = None
    if args.research:
        research_path = Path(args.research)
        if research_path.exists():
            research_ctx = research_path.read_text()
        else:
            research_ctx = args.research

    run(company=args.company, research_context=research_ctx)
