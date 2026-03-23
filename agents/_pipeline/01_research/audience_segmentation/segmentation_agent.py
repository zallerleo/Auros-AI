#!/usr/bin/env python3
"""
AUROS AI — Audience Segmentation Agent
Generates detailed audience segments from client data (audit + brand + research).
Optimised for exhibition and experiential entertainment clients.

Usage:
    python -m agents.audience_segmentation.segmentation_agent --company "The Imagine Team" --exhibition "Harry Potter"
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


def _load_latest_json(client_dir: Path, prefix: str) -> dict | None:
    """Load the most recent JSON file matching a prefix in a client directory."""
    files = sorted(client_dir.glob(f"{prefix}_*.json"), reverse=True)
    return json.loads(files[0].read_text()) if files else None


SEGMENTATION_PROMPT = """You are the AUROS audience intelligence specialist. Analyse the provided client data and generate 4-6 highly detailed audience segments.

COMPANY: {company}
{exhibition_context}

CLIENT DATA:
{client_data}

For EACH segment, provide:
- **name**: A vivid, memorable segment label (e.g. "Nostalgic Fans", "Family Experience Seekers")
- **demographics**: Age range, gender skew, income bracket, location tendencies, education
- **psychographics**: Values, lifestyle, interests, media consumption, personality traits
- **pain_points**: What frustrations or unmet needs does this segment have that the experience solves?
- **content_preferences**: What content formats, topics, and styles resonate? (video, carousel, UGC, behind-the-scenes, etc.)
- **preferred_platforms**: Ranked list of social platforms where they're most active and receptive
- **messaging_angle**: The primary narrative angle to use when speaking to this segment
- **hook_style**: What type of hook stops their scroll? (question, statistic, visual wow, story, controversy)
- **cta_style**: What CTA language converts them? (urgency, exclusivity, social proof, value-first)

{exhibition_segments_hint}

Return valid JSON:
{{
  "company": "{company}",
  "segmentation_date": "{today}",
  "total_segments": 0,
  "segments": [
    {{
      "id": 1,
      "name": "Segment Name",
      "demographics": {{
        "age_range": "25-34",
        "gender_skew": "60% female",
        "income_bracket": "middle to upper-middle",
        "location": "urban, metropolitan areas",
        "education": "university educated"
      }},
      "psychographics": {{
        "values": ["..."],
        "lifestyle": "...",
        "interests": ["..."],
        "media_consumption": ["..."],
        "personality_traits": ["..."]
      }},
      "pain_points": ["..."],
      "content_preferences": ["..."],
      "preferred_platforms": ["Instagram", "TikTok", "..."],
      "messaging_angle": "...",
      "hook_style": "...",
      "cta_style": "...",
      "estimated_segment_size": "percentage of total addressable audience"
    }}
  ],
  "cross_segment_insights": ["..."],
  "recommended_priority_order": ["Segment 1 name", "Segment 2 name"]
}}"""


EXHIBITION_SEGMENTS_HINT = """Since this is an exhibition / experiential entertainment client, make sure to include segments such as:
- Nostalgic Fans (grew up with the IP, emotional connection)
- Family Experience Seekers (parents looking for memorable outings)
- Date Night Couples (young couples wanting unique experiences)
- History / Culture Enthusiasts (museum-goers, lifelong learners)
- Tourist Explorers (visitors looking for city highlights)
- School Group Organisers (teachers, camp directors planning field trips)

Adapt these archetypes to the specific exhibition context provided."""


def run(company: str, exhibition: str | None = None) -> dict:
    """Run audience segmentation for a company."""
    today = datetime.now().strftime("%Y-%m-%d")
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    client_dir.mkdir(parents=True, exist_ok=True)

    print(f"[AUROS] Audience Segmentation starting — {company} — {today}")

    # Load existing client data
    audit = _load_latest_json(client_dir, "marketing_audit") or {}
    brand = _load_latest_json(client_dir, "brand_identity") or {}
    research = _load_latest_json(client_dir, "market_research") or {}

    client_data = json.dumps({
        "company": company,
        "exhibition": exhibition,
        "audit_summary": audit.get("executive_summary", ""),
        "swot": audit.get("swot", {}),
        "social_media": audit.get("social_media", []),
        "brand_voice": brand.get("voice", {}),
        "target_audience_existing": brand.get("target_audience", {}),
        "market_research": {
            "competitors": research.get("competitors", []),
            "trends": research.get("trends", []),
        },
    }, indent=2)[:8000]

    exhibition_context = ""
    exhibition_hint = ""
    if exhibition:
        exhibition_context = f"EXHIBITION: {exhibition}"
        exhibition_hint = EXHIBITION_SEGMENTS_HINT

    print("[AUROS] Generating audience segments via Claude...")
    prompt = SEGMENTATION_PROMPT.format(
        company=company,
        exhibition_context=exhibition_context,
        client_data=client_data,
        exhibition_segments_hint=exhibition_hint,
        today=today,
    )
    raw = generate(prompt, temperature=0.5, max_tokens=6000)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    segments = json.loads(json_str)

    # Save JSON
    segments_path = client_dir / f"audience_segments_{today}.json"
    segments_path.write_text(json.dumps(segments, indent=2))
    print(f"[AUROS] Segments saved to {segments_path}")

    # Render HTML summary
    html_path = client_dir / f"audience_segments_{today}.html"
    html_path.write_text(_render_html(company, segments, today, exhibition))
    print(f"[AUROS] HTML visual summary saved to {html_path}")

    seg_count = len(segments.get("segments", []))
    print(f"[AUROS] Audience Segmentation complete — {seg_count} segments generated")
    return segments


def _render_html(company: str, data: dict, today: str, exhibition: str | None) -> str:
    """Render audience segments into an AUROS-branded HTML summary."""
    segments = data.get("segments", [])

    # Colour palette for segment cards
    palette = ["#C9A84C", "#B80021", "#3B82F6", "#10B981", "#8B5CF6", "#F59E0B"]

    cards_html = ""
    for i, seg in enumerate(segments):
        colour = palette[i % len(palette)]
        demo = seg.get("demographics", {})
        psycho = seg.get("psychographics", {})

        pain_items = "".join(f"<li>{p}</li>" for p in seg.get("pain_points", []))
        content_items = "".join(f"<span class='tag'>{c}</span>" for c in seg.get("content_preferences", []))
        platform_items = "".join(f"<span class='tag platform'>{p}</span>" for p in seg.get("preferred_platforms", []))
        interest_items = "".join(f"<span class='tag'>{v}</span>" for v in psycho.get("interests", []))
        value_items = "".join(f"<span class='tag'>{v}</span>" for v in psycho.get("values", []))

        cards_html += f"""
        <div class="segment-card" style="border-top: 4px solid {colour};">
          <div class="segment-header">
            <div class="segment-id" style="background: {colour};">{seg.get('id', i + 1)}</div>
            <div>
              <h3>{seg.get('name', 'Unnamed')}</h3>
              <span class="segment-size">{seg.get('estimated_segment_size', '')}</span>
            </div>
          </div>

          <div class="segment-grid">
            <div class="info-block">
              <h4>Demographics</h4>
              <p><strong>Age:</strong> {demo.get('age_range', 'N/A')}</p>
              <p><strong>Gender:</strong> {demo.get('gender_skew', 'N/A')}</p>
              <p><strong>Income:</strong> {demo.get('income_bracket', 'N/A')}</p>
              <p><strong>Location:</strong> {demo.get('location', 'N/A')}</p>
              <p><strong>Education:</strong> {demo.get('education', 'N/A')}</p>
            </div>

            <div class="info-block">
              <h4>Psychographics</h4>
              <p><strong>Lifestyle:</strong> {psycho.get('lifestyle', 'N/A')}</p>
              <div class="tags-row"><strong>Values:</strong> {value_items}</div>
              <div class="tags-row"><strong>Interests:</strong> {interest_items}</div>
            </div>

            <div class="info-block">
              <h4>Pain Points</h4>
              <ul>{pain_items}</ul>
            </div>

            <div class="info-block">
              <h4>Content &amp; Platforms</h4>
              <div class="tags-row">{content_items}</div>
              <div class="tags-row" style="margin-top:8px;">{platform_items}</div>
            </div>
          </div>

          <div class="messaging-row">
            <div class="msg-block">
              <h4>Messaging Angle</h4>
              <p>{seg.get('messaging_angle', '')}</p>
            </div>
            <div class="msg-block">
              <h4>Hook Style</h4>
              <p>{seg.get('hook_style', '')}</p>
            </div>
            <div class="msg-block">
              <h4>CTA Style</h4>
              <p>{seg.get('cta_style', '')}</p>
            </div>
          </div>
        </div>"""

    # Cross-segment insights
    insights_html = ""
    for insight in data.get("cross_segment_insights", []):
        insights_html += f"<li>{insight}</li>"

    priority_html = ""
    for j, name in enumerate(data.get("recommended_priority_order", []), 1):
        priority_html += f"<div class='priority-item'><span class='priority-num'>{j}</span> {name}</div>"

    subtitle = f"{company}"
    if exhibition:
        subtitle += f" &mdash; {exhibition}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Audience Segmentation &mdash; {company}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #0B0F1A; color: #FAFAF8; line-height: 1.6; }}

  .header {{
    padding: 48px 40px;
    border-bottom: 1px solid rgba(201,168,76,0.15);
    background: linear-gradient(135deg, #0B0F1A 0%, #111827 100%);
  }}
  .header h1 {{ font-size: 32px; font-weight: 900; color: #C9A84C; letter-spacing: -1px; }}
  .header p {{ color: #9CA3AF; margin-top: 8px; font-size: 14px; }}
  .header .stats {{ display: flex; gap: 32px; margin-top: 20px; }}
  .stat-box {{ text-align: center; }}
  .stat-num {{ font-size: 28px; font-weight: 900; color: #C9A84C; }}
  .stat-lbl {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #6B7280; margin-top: 4px; }}

  .content {{ padding: 40px; }}
  .section-title {{ font-size: 11px; font-weight: 700; letter-spacing: 4px; text-transform: uppercase; color: #8B6E2A; margin-bottom: 24px; }}

  .segment-card {{
    background: #111827; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 28px; margin-bottom: 24px;
  }}
  .segment-header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }}
  .segment-id {{
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 18px; color: #0B0F1A; flex-shrink: 0;
  }}
  .segment-header h3 {{ font-size: 20px; font-weight: 800; }}
  .segment-size {{ font-size: 12px; color: #9CA3AF; }}

  .segment-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  @media (max-width: 768px) {{ .segment-grid {{ grid-template-columns: 1fr; }} }}

  .info-block {{ background: rgba(255,255,255,0.02); border-radius: 10px; padding: 16px; }}
  .info-block h4 {{ font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #C9A84C; margin-bottom: 10px; }}
  .info-block p {{ font-size: 13px; color: #D1D5DB; margin-bottom: 4px; }}
  .info-block ul {{ padding-left: 16px; font-size: 13px; color: #D1D5DB; }}
  .info-block li {{ margin-bottom: 4px; }}

  .tags-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
  .tag {{
    display: inline-block; padding: 3px 10px; border-radius: 6px;
    font-size: 11px; font-weight: 600; background: rgba(201,168,76,0.08); color: #C9A84C;
  }}
  .tag.platform {{ background: rgba(59,130,246,0.1); color: #60A5FA; }}

  .messaging-row {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
  @media (max-width: 768px) {{ .messaging-row {{ grid-template-columns: 1fr; }} }}
  .msg-block {{ background: rgba(255,255,255,0.02); border-radius: 10px; padding: 14px; }}
  .msg-block h4 {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #8B6E2A; margin-bottom: 8px; }}
  .msg-block p {{ font-size: 13px; color: #D1D5DB; }}

  .insights-section {{ margin-top: 40px; padding: 28px; background: #111827; border-radius: 14px; border: 1px solid rgba(201,168,76,0.1); }}
  .insights-section ul {{ padding-left: 20px; }}
  .insights-section li {{ font-size: 14px; color: #D1D5DB; margin-bottom: 8px; }}

  .priority-section {{ margin-top: 24px; }}
  .priority-item {{ display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 8px; font-size: 14px; }}
  .priority-num {{ width: 28px; height: 28px; background: #C9A84C; color: #0B0F1A; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px; flex-shrink: 0; }}

  .footer {{ text-align: center; padding: 40px; color: #6B7280; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; }}
  .footer span {{ color: #C9A84C; }}
</style>
</head>
<body>

<div class="header">
  <h1>Audience Segmentation</h1>
  <p>{subtitle} &mdash; Generated {today} by AUROS AI</p>
  <div class="stats">
    <div class="stat-box"><div class="stat-num">{len(segments)}</div><div class="stat-lbl">Segments</div></div>
  </div>
</div>

<div class="content">
  <div class="section-title">Audience Segments</div>
  {cards_html}

  <div class="insights-section">
    <div class="section-title">Cross-Segment Insights</div>
    <ul>{insights_html}</ul>
  </div>

  <div class="priority-section">
    <div class="section-title">Recommended Priority Order</div>
    {priority_html}
  </div>
</div>

<div class="footer"><span>AUROS</span> &middot; Intelligence, Elevated</div>

</body>
</html>"""
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Audience Segmentation Agent")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--exhibition", default=None, help="Exhibition name (optional)")
    args = parser.parse_args()
    run(company=args.company, exhibition=args.exhibition)
