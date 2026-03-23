#!/usr/bin/env python3
"""
AUROS AI — Content Calendar Agent
Generates a full monthly content calendar with posts, captions, hashtags, and an HTML view.

Usage:
    python -m agents.content_calendar.calendar_agent --company "Company Name" --month "2026-04" --platforms "instagram,tiktok,linkedin"
"""

from __future__ import annotations

import sys
import json
import argparse
import re
import calendar
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, BRAND
from agents.shared.llm import generate


def _slugify(name: str) -> str:
    """Convert company name to slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _load_client_data(slug: str) -> tuple[dict, dict, dict | None]:
    """Load audit, brand identity, and optional trend data."""
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    audit = {}
    brand_identity = {}
    trends = None

    audit_files = sorted(client_dir.glob("marketing_audit_*.json"), reverse=True)
    if audit_files:
        audit = json.loads(audit_files[0].read_text())
        print(f"[AUROS] Loaded audit: {audit_files[0].name}")

    brand_files = sorted(client_dir.glob("brand_identity_*.json"), reverse=True)
    if brand_files:
        brand_identity = json.loads(brand_files[0].read_text())
        print(f"[AUROS] Loaded brand identity: {brand_files[0].name}")

    # Check for trend reports
    trend_dir = PORTFOLIO_DIR / "trend_reports"
    if trend_dir.exists():
        trend_files = sorted(trend_dir.glob("trend_report_*.json"), reverse=True)
        if trend_files:
            trends = json.loads(trend_files[0].read_text())
            print(f"[AUROS] Loaded trend data: {trend_files[0].name}")

    return audit, brand_identity, trends


CALENDAR_PROMPT = """You are the AUROS content strategist. Generate a complete monthly content calendar.

COMPANY: {company}
MONTH: {month} ({month_name} {year})
PLATFORMS: {platforms}
DAYS IN MONTH: {days_in_month}

CLIENT DATA:
{client_data}

TREND DATA:
{trend_data}

Generate a 30-day content calendar as valid JSON. Create content for EVERY day of the month ({days_in_month} days).

{{
  "company": "{company}",
  "month": "{month}",
  "platforms": {platforms_list},
  "calendar": [
    {{
      "date": "YYYY-MM-DD",
      "day_of_week": "Monday",
      "platform": "instagram",
      "content_type": "reel",
      "topic": "Specific topic",
      "caption": "Full caption with hooks and CTA (include line breaks as \\n)",
      "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
      "optimal_time": "10:00 AM EST",
      "notes": "Production notes, props needed, etc.",
      "engagement_hook": "Question or hook to drive comments",
      "cta": "Specific call to action"
    }}
  ],
  "monthly_themes": ["2-3 overarching themes for the month"],
  "content_mix_summary": {{
    "reels": 0,
    "carousels": 0,
    "static_posts": 0,
    "stories": 0,
    "lives": 0
  }},
  "notes": "Overall strategy notes for the month"
}}

RULES:
- Every day must have at least one post
- Rotate platforms evenly across {platforms}
- Mix content types: reels, carousels, static posts, stories, lives
- Include weekend content (lighter/more casual)
- Account for seasonality and industry events for {month_name}
- Vary CTAs: follow, comment, share, save, link in bio, DM
- Captions should be ready to post — not placeholders
- Include engagement hooks that drive comments
- Hashtags should be a mix of trending, niche, and branded

Return ONLY valid JSON."""


def _build_calendar_html(cal_data: dict, month_str: str) -> str:
    """Render the content calendar as a visual HTML monthly grid."""
    company = cal_data.get("company", "Client")
    entries = cal_data.get("calendar", [])
    themes = cal_data.get("monthly_themes", [])
    content_mix = cal_data.get("content_mix_summary", {})
    notes = cal_data.get("notes", "")

    # Parse month
    year, month = int(month_str.split("-")[0]), int(month_str.split("-")[1])
    month_name = calendar.month_name[month]
    cal = calendar.Calendar(firstweekday=0)  # Monday start
    month_days = cal.monthdayscalendar(year, month)

    # Build lookup: date -> entry
    entry_lookup = {}
    for e in entries:
        d = e.get("date", "")
        if d:
            entry_lookup[d] = e

    # Platform colors
    platform_colors = {
        "instagram": "#E1306C", "tiktok": "#00F2EA", "linkedin": "#0A66C2",
        "twitter": "#1DA1F2", "facebook": "#1877F2", "youtube": "#FF0000",
        "x": "#000000", "threads": "#000000", "pinterest": "#E60023",
    }

    # Content type icons
    type_labels = {
        "reel": "REEL", "carousel": "CRSL", "static": "POST", "static_post": "POST",
        "story": "STRY", "stories": "STRY", "live": "LIVE", "video": "VID",
    }

    # Build week rows
    weeks_html = ""
    for week in month_days:
        cells = ""
        for day in week:
            if day == 0:
                cells += '<td class="day empty"></td>'
                continue

            date_str = f"{year}-{month:02d}-{day:02d}"
            entry = entry_lookup.get(date_str)

            if entry:
                platform = entry.get("platform", "").lower()
                pcolor = platform_colors.get(platform, "#C9A84C")
                ctype = entry.get("content_type", "").lower().replace(" ", "_")
                label = type_labels.get(ctype, ctype.upper()[:4])
                topic = entry.get("topic", "")
                if len(topic) > 50:
                    topic = topic[:47] + "..."
                time = entry.get("optimal_time", "")

                cells += f"""
                <td class="day has-content" onclick="showDetail('{date_str}')">
                    <div class="day-number">{day}</div>
                    <div class="day-platform" style="background:{pcolor};">{platform.upper()}</div>
                    <div class="day-type">{label}</div>
                    <div class="day-topic">{topic}</div>
                    <div class="day-time">{time}</div>
                </td>"""
            else:
                cells += f"""
                <td class="day">
                    <div class="day-number">{day}</div>
                    <div class="day-empty-label">No post</div>
                </td>"""

        weeks_html += f"<tr>{cells}</tr>"

    # Build content mix stats
    mix_html = ""
    for ctype, count in content_mix.items():
        mix_html += f'<div class="stat"><span class="stat-num">{count}</span><span class="stat-label">{ctype.replace("_", " ").title()}</span></div>'

    # Build themes
    themes_html = "".join(f'<span class="theme-tag">{t}</span>' for t in themes)

    # Build detail entries as JS data
    entries_js = json.dumps(entries, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Content Calendar — {company} — {month_name} {year}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap" rel="stylesheet">
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ background:#0B0F1A; color:#FAFAF8; font-family:'Inter',sans-serif; }}

    .header {{
        padding:40px; border-bottom:1px solid rgba(201,168,76,0.15);
        display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;
    }}
    .header-left {{ }}
    .header-label {{ font-size:10px; letter-spacing:4px; color:#C9A84C; text-transform:uppercase; font-weight:700; }}
    .header-title {{ font-size:36px; font-weight:900; letter-spacing:-2px; margin-top:8px; }}
    .header-title span {{ color:#C9A84C; }}
    .header-meta {{ font-size:14px; color:#6B7280; margin-top:4px; }}

    .stats-bar {{
        padding:24px 40px; background:#111827;
        display:flex; gap:32px; flex-wrap:wrap; align-items:center;
        border-bottom:1px solid rgba(201,168,76,0.1);
    }}
    .stat {{ text-align:center; }}
    .stat-num {{ display:block; font-size:28px; font-weight:900; color:#C9A84C; }}
    .stat-label {{ font-size:10px; letter-spacing:2px; color:#6B7280; text-transform:uppercase; }}
    .themes {{ display:flex; gap:8px; margin-left:auto; flex-wrap:wrap; }}
    .theme-tag {{ background:rgba(201,168,76,0.1); color:#C9A84C; padding:6px 14px; border-radius:20px; font-size:12px; font-weight:600; }}

    .calendar-grid {{ padding:24px 40px; overflow-x:auto; }}
    .cal-table {{ width:100%; border-collapse:collapse; table-layout:fixed; min-width:900px; }}
    .cal-table th {{
        padding:12px 8px; font-size:11px; letter-spacing:2px; color:#C9A84C;
        text-transform:uppercase; text-align:center; border-bottom:1px solid rgba(201,168,76,0.15);
    }}
    .day {{
        border:1px solid rgba(255,255,255,0.05); vertical-align:top; padding:8px;
        height:120px; background:#0B0F1A; transition:background 0.2s;
    }}
    .day.empty {{ background:transparent; border-color:transparent; }}
    .day.has-content {{ cursor:pointer; }}
    .day.has-content:hover {{ background:#111827; }}
    .day-number {{ font-size:14px; font-weight:700; color:#6B7280; margin-bottom:6px; }}
    .day-platform {{
        display:inline-block; padding:2px 6px; border-radius:3px; font-size:9px;
        font-weight:700; color:#fff; letter-spacing:1px; margin-bottom:4px;
    }}
    .day-type {{ font-size:10px; color:#C9A84C; font-weight:700; letter-spacing:1px; }}
    .day-topic {{ font-size:11px; color:#9CA3AF; margin-top:4px; line-height:1.4; }}
    .day-time {{ font-size:10px; color:#6B7280; margin-top:4px; }}
    .day-empty-label {{ font-size:10px; color:#374151; }}

    .modal-overlay {{
        display:none; position:fixed; top:0; left:0; width:100%; height:100%;
        background:rgba(0,0,0,0.8); z-index:1000; justify-content:center; align-items:center;
    }}
    .modal-overlay.active {{ display:flex; }}
    .modal {{
        background:#111827; border-radius:16px; padding:40px; max-width:600px; width:90%;
        max-height:80vh; overflow-y:auto; border:1px solid rgba(201,168,76,0.2);
    }}
    .modal-close {{ float:right; cursor:pointer; color:#6B7280; font-size:24px; }}
    .modal-close:hover {{ color:#FAFAF8; }}
    .modal-date {{ font-size:10px; letter-spacing:3px; color:#C9A84C; text-transform:uppercase; font-weight:700; }}
    .modal-topic {{ font-size:22px; font-weight:700; margin:8px 0 16px; }}
    .modal-label {{ font-size:10px; letter-spacing:2px; color:#C9A84C; text-transform:uppercase; font-weight:700; margin-top:16px; margin-bottom:4px; }}
    .modal-value {{ font-size:14px; color:#9CA3AF; line-height:1.7; }}
    .modal-tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }}
    .modal-tag {{ background:rgba(59,130,246,0.1); color:#3B82F6; padding:3px 8px; border-radius:4px; font-size:11px; }}

    .strategy-notes {{
        padding:32px 40px; border-top:1px solid rgba(201,168,76,0.15);
    }}
    .strategy-notes .section-label {{ font-size:10px; letter-spacing:4px; color:#C9A84C; text-transform:uppercase; font-weight:700; margin-bottom:8px; }}
    .strategy-notes p {{ font-size:14px; color:#9CA3AF; line-height:1.7; }}

    .footer {{
        padding:40px; text-align:center; border-top:1px solid rgba(201,168,76,0.15);
    }}
    .footer-brand {{ font-size:20px; font-weight:900; color:#C9A84C; }}
    .footer-tagline {{ font-size:10px; color:#6B7280; letter-spacing:2px; margin-top:4px; }}

    @media (max-width:768px) {{
        .header, .stats-bar, .calendar-grid, .strategy-notes, .footer {{ padding-left:16px; padding-right:16px; }}
        .day {{ height:100px; padding:4px; }}
        .day-topic {{ display:none; }}
    }}
</style>
</head>
<body>

<div class="header">
    <div class="header-left">
        <div class="header-label">AUROS Content Calendar</div>
        <h1 class="header-title"><span>{month_name}</span> {year} &mdash; {company}</h1>
        <div class="header-meta">Generated {datetime.now().strftime('%B %d, %Y')}</div>
    </div>
</div>

<div class="stats-bar">
    {mix_html}
    <div class="themes">{themes_html}</div>
</div>

<div class="calendar-grid">
    <table class="cal-table">
        <thead>
            <tr>
                <th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th>
            </tr>
        </thead>
        <tbody>
            {weeks_html}
        </tbody>
    </table>
</div>

<div class="strategy-notes">
    <div class="section-label">Strategy Notes</div>
    <p>{notes}</p>
</div>

<div class="modal-overlay" id="modal" onclick="closeModal(event)">
    <div class="modal" onclick="event.stopPropagation()">
        <span class="modal-close" onclick="document.getElementById('modal').classList.remove('active')">&times;</span>
        <div id="modal-content"></div>
    </div>
</div>

<div class="footer">
    <div class="footer-brand">AUROS</div>
    <div class="footer-tagline">Intelligence, Elevated.</div>
</div>

<script>
const entries = {entries_js};

const entryMap = {{}};
entries.forEach(e => {{ entryMap[e.date] = e; }});

function showDetail(dateStr) {{
    const e = entryMap[dateStr];
    if (!e) return;
    const hashtags = (e.hashtags || []).map(h => '<span class="modal-tag">#' + h + '</span>').join('');
    const caption = (e.caption || '').replace(/\\n/g, '<br>');
    document.getElementById('modal-content').innerHTML = `
        <div class="modal-date">${{e.day_of_week}} &mdash; ${{e.date}}</div>
        <div class="modal-topic">${{e.topic}}</div>
        <div class="modal-label">Platform</div>
        <div class="modal-value">${{e.platform}} &mdash; ${{e.content_type}} &mdash; ${{e.optimal_time}}</div>
        <div class="modal-label">Caption</div>
        <div class="modal-value">${{caption}}</div>
        <div class="modal-label">Engagement Hook</div>
        <div class="modal-value">${{e.engagement_hook || ''}}</div>
        <div class="modal-label">CTA</div>
        <div class="modal-value">${{e.cta || ''}}</div>
        <div class="modal-label">Hashtags</div>
        <div class="modal-tags">${{hashtags}}</div>
        <div class="modal-label">Notes</div>
        <div class="modal-value">${{e.notes || ''}}</div>
    `;
    document.getElementById('modal').classList.add('active');
}}

function closeModal(event) {{
    if (event.target === document.getElementById('modal')) {{
        document.getElementById('modal').classList.remove('active');
    }}
}}

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') document.getElementById('modal').classList.remove('active');
}});
</script>

</body>
</html>"""


def run(
    company: str,
    month: str = "",
    platforms: str = "instagram,tiktok,linkedin",
) -> dict:
    """Execute the content calendar generation pipeline.

    When called by the orchestrator, only ``company`` is passed.
    ``month`` defaults to next month, ``platforms`` to a standard set.
    """
    from datetime import date as _date

    today = datetime.now().strftime("%Y-%m-%d")

    # Default month to next month if not provided
    if not month:
        _today = _date.today()
        _next = _today.replace(day=28) + timedelta(days=4)
        month = _next.strftime("%Y-%m")

    slug = _slugify(company)
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    client_dir.mkdir(parents=True, exist_ok=True)
    platform_list = [p.strip() for p in platforms.split(",")]

    # Parse month
    year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
    month_name = calendar.month_name[month_num]
    days_in_month = calendar.monthrange(year, month_num)[1]

    print(f"[AUROS] Content calendar agent starting for '{company}' — {month_name} {year}")

    # Step 1: Load client data
    print("[AUROS] Loading client data...")
    audit, brand_identity, trends = _load_client_data(slug)

    if not audit and not brand_identity:
        print("[AUROS] Warning: No audit or brand identity found. Calendar will be generated with limited context.")

    # Step 2: Prepare data for Claude
    client_data = {
        "company": company,
        "audit_summary": {k: audit[k] for k in list(audit.keys())[:10]} if audit else {},
        "brand_identity_summary": {k: brand_identity[k] for k in list(brand_identity.keys())[:10]} if brand_identity else {},
    }
    trend_data = "No trend data available." if not trends else json.dumps(trends, indent=2)[:3000]

    # Step 3: Generate calendar via Claude
    print("[AUROS] Generating content calendar...")
    prompt = CALENDAR_PROMPT.format(
        company=company,
        month=month,
        month_name=month_name,
        year=year,
        days_in_month=days_in_month,
        platforms=", ".join(platform_list),
        platforms_list=json.dumps(platform_list),
        client_data=json.dumps(client_data, indent=2)[:5000],
        trend_data=trend_data,
    )

    raw = generate(prompt, max_tokens=16000, temperature=0.6)

    # Parse JSON
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    # Attempt JSON parse with truncation repair
    try:
        cal_data = json.loads(json_str)
    except json.JSONDecodeError:
        # Try to repair truncated JSON by closing open structures
        repair = json_str.rstrip()
        for ch in ['"', '}', ']', '}', ']', '}']:
            try:
                cal_data = json.loads(repair)
                break
            except json.JSONDecodeError:
                repair += ch
        else:
            cal_data = json.loads(repair)

    # Step 4: Save JSON
    json_path = client_dir / f"content_calendar_{month}.json"
    json_path.write_text(json.dumps(cal_data, indent=2))
    print(f"[AUROS] Calendar JSON saved to {json_path}")

    # Step 5: Generate HTML calendar view
    print("[AUROS] Rendering HTML calendar...")
    html = _build_calendar_html(cal_data, month)
    html_path = client_dir / f"content_calendar_{month}.html"
    html_path.write_text(html)
    print(f"[AUROS] Calendar HTML saved to {html_path}")

    print("[AUROS] Content calendar complete.")
    return {"status": "complete", "json_path": str(json_path), "html_path": str(html_path), "calendar": cal_data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Content Calendar Agent")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--month", required=True, help="Target month (YYYY-MM)")
    parser.add_argument("--platforms", default="instagram,tiktok,linkedin", help="Comma-separated platforms")
    args = parser.parse_args()
    run(company=args.company, month=args.month, platforms=args.platforms)
