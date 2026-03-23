#!/usr/bin/env python3
"""
AUROS AI — Lead Magnet Creation Agent
Generates three types of lead magnets for exhibitions and experiences:
  1. Insider Guide (what to expect, tips, photo spots)
  2. Checklist (must-see moments, best times to visit)
  3. Behind the Scenes (how the exhibition was built, exclusive facts)

Usage:
    python -m agents.lead_magnet.lead_magnet_agent --company "The Imagine Team" --exhibition "Harry Potter"
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


# ─── PROMPTS ────────────────────────────────────────────────────────────────

INSIDER_GUIDE_PROMPT = """You are AUROS's lead magnet specialist. Create an "Insider Guide" PDF content for the {exhibition} exhibition by {company}.

CONTEXT:
{context}

AUDIENCE SEGMENTS:
{segments_summary}

Create a complete Insider Guide lead magnet with the following structure:

- **title**: A compelling title (e.g. "The Ultimate Insider Guide to [Exhibition]")
- **subtitle**: Supporting line that adds urgency or exclusivity
- **sections**: An array of 6-8 sections, each with:
  - heading: Section title
  - content: 2-3 paragraphs of valuable, actionable content
- Sections should cover: What to Expect, Best Photo Spots (with specific tips), Hidden Details Most Visitors Miss, Pro Tips for the Best Experience, What to Wear / Bring, Best Times to Visit, Food & Drink Guide, How to Get There
- **cta**: A call-to-action for after they read the guide (book tickets)
- **email_capture_hook**: The headline used on the landing page to get them to download (e.g. "Get the free guide 47,000 visitors wish they had before their visit")

Make the content genuinely valuable — this should feel like insider knowledge, not a brochure.

Return valid JSON:
{{
  "type": "insider_guide",
  "title": "...",
  "subtitle": "...",
  "sections": [
    {{"heading": "...", "content": "..."}}
  ],
  "cta": "...",
  "email_capture_hook": "...",
  "estimated_pages": 0,
  "target_segments": ["segment names this magnet appeals to most"]
}}"""


CHECKLIST_PROMPT = """You are AUROS's lead magnet specialist. Create a "Must-See Checklist" for the {exhibition} exhibition by {company}.

CONTEXT:
{context}

AUDIENCE SEGMENTS:
{segments_summary}

Create a checklist lead magnet with the following structure:

- **title**: Compelling checklist title (e.g. "The [Exhibition] Must-See Checklist: Don't Miss a Single Moment")
- **subtitle**: Supporting line
- **sections**: An array of 5-6 grouped checklist sections, each with:
  - heading: Category name (e.g. "Must-See Installations", "Best Photo Moments", "Interactive Experiences")
  - content: Array of 4-6 checklist items, each a specific, actionable item with a brief description
- Include sections for: Must-See Highlights, Best Times to Visit (by day/hour), Photo Checklist, Interactive Moments, Nearby Eats & Activities, Post-Visit Sharing Ideas
- **cta**: Post-checklist CTA
- **email_capture_hook**: Landing page headline to drive downloads

Each checklist item should be specific and exciting, not generic.

Return valid JSON:
{{
  "type": "checklist",
  "title": "...",
  "subtitle": "...",
  "sections": [
    {{"heading": "...", "content": "..."}}
  ],
  "cta": "...",
  "email_capture_hook": "...",
  "estimated_pages": 0,
  "target_segments": ["..."]
}}"""


BEHIND_SCENES_PROMPT = """You are AUROS's lead magnet specialist. Create a "Behind the Scenes" content piece for the {exhibition} exhibition by {company}.

CONTEXT:
{context}

AUDIENCE SEGMENTS:
{segments_summary}

Create a behind-the-scenes lead magnet with the following structure:

- **title**: Intriguing title (e.g. "Behind the Magic: How [Exhibition] Was Built")
- **subtitle**: Supporting line that promises exclusive access
- **sections**: An array of 5-7 sections, each with:
  - heading: Section title
  - content: 2-3 paragraphs of fascinating behind-the-scenes details
- Sections should cover: The Vision (how the exhibition concept was born), The Build (scale, materials, engineering), The Details (easter eggs, hidden references, artistic choices), The Technology (interactive systems, lighting, sound design), The Team (key creators, designers, artisans), By the Numbers (impressive stats — weight of props, hours of work, etc.), What Even Superfans Don't Know
- **cta**: Post-content CTA
- **email_capture_hook**: Landing page headline to drive downloads

This should make the reader feel like they have VIP access to information nobody else has.

Return valid JSON:
{{
  "type": "behind_the_scenes",
  "title": "...",
  "subtitle": "...",
  "sections": [
    {{"heading": "...", "content": "..."}}
  ],
  "cta": "...",
  "email_capture_hook": "...",
  "estimated_pages": 0,
  "target_segments": ["..."]
}}"""


def run(company: str, exhibition: str | None = None) -> dict:
    """Generate three types of lead magnets for a company/exhibition."""
    today = datetime.now().strftime("%Y-%m-%d")
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    magnets_dir = client_dir / "lead_magnets"
    magnets_dir.mkdir(parents=True, exist_ok=True)

    print(f"[AUROS] Lead Magnet Agent starting — {company} — {today}")

    # Load existing client data
    audit = _load_latest_json(client_dir, "marketing_audit") or {}
    brand = _load_latest_json(client_dir, "brand_identity") or {}
    segments_data = _load_latest_json(client_dir, "audience_segments") or {}

    context = json.dumps({
        "company": company,
        "exhibition": exhibition or "N/A",
        "audit_summary": audit.get("executive_summary", ""),
        "brand_voice": brand.get("voice", {}),
        "industry": "experiential design / entertainment exhibitions",
    }, indent=2)[:4000]

    # Summarise audience segments for the prompts
    segments_list = segments_data.get("segments", [])
    segments_summary = ""
    if segments_list:
        summaries = []
        for seg in segments_list:
            summaries.append(
                f"- {seg.get('name', 'Unknown')}: {seg.get('messaging_angle', '')}"
            )
        segments_summary = "\n".join(summaries)
    else:
        segments_summary = "No audience segments available — infer likely segments from the exhibition context."

    exhibition_name = exhibition or company
    results: dict = {"company": company, "exhibition": exhibition, "lead_magnets": []}

    prompts = [
        ("Insider Guide", INSIDER_GUIDE_PROMPT),
        ("Checklist", CHECKLIST_PROMPT),
        ("Behind the Scenes", BEHIND_SCENES_PROMPT),
    ]

    for label, prompt_template in prompts:
        print(f"[AUROS] Generating {label}...")
        prompt = prompt_template.format(
            company=company,
            exhibition=exhibition_name,
            context=context,
            segments_summary=segments_summary,
        )
        raw = generate(prompt, temperature=0.6, max_tokens=4096)

        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1]
            json_str = json_str.rsplit("```", 1)[0]

        magnet = json.loads(json_str)
        results["lead_magnets"].append(magnet)

        # Save individual JSON
        type_slug = magnet.get("type", label.lower().replace(" ", "_"))
        magnet_path = magnets_dir / f"{type_slug}_{today}.json"
        magnet_path.write_text(json.dumps(magnet, indent=2))
        print(f"[AUROS] {label} saved to {magnet_path}")

    # Save combined JSON
    combined_path = magnets_dir / f"all_lead_magnets_{today}.json"
    combined_path.write_text(json.dumps(results, indent=2))
    print(f"[AUROS] Combined lead magnets saved to {combined_path}")

    # Render HTML
    html_path = magnets_dir / f"lead_magnets_preview_{today}.html"
    html_path.write_text(_render_html(company, exhibition, results, today))
    print(f"[AUROS] HTML preview saved to {html_path}")

    print(f"[AUROS] Lead Magnet Agent complete — {len(results['lead_magnets'])} magnets generated")
    return results


def _render_html(company: str, exhibition: str | None, data: dict, today: str) -> str:
    """Render all lead magnets into an AUROS-branded HTML preview."""
    magnets = data.get("lead_magnets", [])
    type_colours = {
        "insider_guide": "#C9A84C",
        "checklist": "#10B981",
        "behind_the_scenes": "#8B5CF6",
    }
    type_icons = {
        "insider_guide": "&#128218;",
        "checklist": "&#9989;",
        "behind_the_scenes": "&#127916;",
    }

    magnets_html = ""
    for magnet in magnets:
        mag_type = magnet.get("type", "unknown")
        colour = type_colours.get(mag_type, "#C9A84C")
        icon = type_icons.get(mag_type, "&#128196;")

        sections_html = ""
        for sec in magnet.get("sections", []):
            content = sec.get("content", "")
            if isinstance(content, list):
                items = "".join(f"<li>{item}</li>" for item in content)
                content_rendered = f"<ul>{items}</ul>"
            else:
                paragraphs = content.split("\n\n") if "\n\n" in content else [content]
                content_rendered = "".join(f"<p>{p}</p>" for p in paragraphs)

            sections_html += f"""
            <div class="magnet-section">
              <h4>{sec.get('heading', '')}</h4>
              {content_rendered}
            </div>"""

        targets = ", ".join(magnet.get("target_segments", []))

        magnets_html += f"""
        <div class="magnet-card" style="border-top: 4px solid {colour};">
          <div class="magnet-header">
            <div class="magnet-icon" style="background: {colour};">{icon}</div>
            <div>
              <div class="magnet-type" style="color: {colour};">{mag_type.replace('_', ' ').upper()}</div>
              <h3>{magnet.get('title', '')}</h3>
              <p class="magnet-subtitle">{magnet.get('subtitle', '')}</p>
            </div>
          </div>

          <div class="capture-hook">
            <div class="capture-label">Email Capture Hook</div>
            <p>"{magnet.get('email_capture_hook', '')}"</p>
          </div>

          <div class="sections-preview">
            {sections_html}
          </div>

          <div class="magnet-footer">
            <div class="cta-preview">
              <strong>CTA:</strong> {magnet.get('cta', '')}
            </div>
            <div class="magnet-meta">
              <span>~{magnet.get('estimated_pages', '?')} pages</span>
              <span>Targets: {targets}</span>
            </div>
          </div>
        </div>"""

    subtitle = company
    if exhibition:
        subtitle += f" &mdash; {exhibition}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Lead Magnets &mdash; {company}</title>
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

  .magnet-card {{
    background: #111827; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 28px; margin-bottom: 32px;
  }}
  .magnet-header {{ display: flex; align-items: flex-start; gap: 16px; margin-bottom: 20px; }}
  .magnet-icon {{
    width: 48px; height: 48px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; flex-shrink: 0;
  }}
  .magnet-type {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; margin-bottom: 4px; }}
  .magnet-header h3 {{ font-size: 20px; font-weight: 800; line-height: 1.3; }}
  .magnet-subtitle {{ font-size: 14px; color: #9CA3AF; margin-top: 4px; }}

  .capture-hook {{
    background: rgba(201,168,76,0.06); border: 1px solid rgba(201,168,76,0.15);
    border-radius: 10px; padding: 16px; margin-bottom: 20px;
  }}
  .capture-label {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #C9A84C; margin-bottom: 6px; }}
  .capture-hook p {{ font-size: 16px; font-weight: 700; color: #FAFAF8; font-style: italic; }}

  .sections-preview {{ margin-bottom: 20px; }}
  .magnet-section {{
    padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  }}
  .magnet-section:last-child {{ border-bottom: none; }}
  .magnet-section h4 {{ font-size: 14px; font-weight: 700; color: #C9A84C; margin-bottom: 8px; }}
  .magnet-section p {{ font-size: 13px; color: #D1D5DB; margin-bottom: 6px; }}
  .magnet-section ul {{ padding-left: 18px; font-size: 13px; color: #D1D5DB; }}
  .magnet-section li {{ margin-bottom: 4px; }}

  .magnet-footer {{ display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.06); }}
  .cta-preview {{ font-size: 13px; color: #D1D5DB; }}
  .cta-preview strong {{ color: #C9A84C; }}
  .magnet-meta {{ font-size: 11px; color: #6B7280; display: flex; gap: 16px; }}

  .footer {{ text-align: center; padding: 40px; color: #6B7280; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; }}
  .footer span {{ color: #C9A84C; }}
</style>
</head>
<body>

<div class="header">
  <h1>Lead Magnets</h1>
  <p>{subtitle} &mdash; Generated {today} by AUROS AI</p>
  <div class="stats">
    <div class="stat-box"><div class="stat-num">{len(magnets)}</div><div class="stat-lbl">Lead Magnets</div></div>
  </div>
</div>

<div class="content">
  <div class="section-title">Generated Lead Magnets</div>
  {magnets_html}
</div>

<div class="footer"><span>AUROS</span> &middot; Intelligence, Elevated</div>

</body>
</html>"""
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Lead Magnet Agent")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--exhibition", default=None, help="Exhibition name (optional)")
    args = parser.parse_args()
    run(company=args.company, exhibition=args.exhibition)
