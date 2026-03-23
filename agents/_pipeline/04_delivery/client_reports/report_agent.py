#!/usr/bin/env python3
"""
AUROS AI — Agent 10: Client Report Generator
Generates polished, AUROS-branded monthly client reports in HTML format.
Pulls together all available data for a client and renders a premium report.

Usage:
    python -m agents.client_reports.report_agent --company "Company Name" --month "2026-03"
"""

from __future__ import annotations

import sys
import json
import argparse
import glob as globmod
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, LOGS_DIR
from agents.shared.llm import generate


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_latest_json(client_dir: Path, prefix: str) -> dict | None:
    """Load the most recent JSON file matching a prefix from the client dir."""
    pattern = str(client_dir / f"{prefix}*.json")
    files = sorted(globmod.glob(pattern), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def _load_client_data(company: str, month: str) -> dict:
    """Load all available data for a client."""
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"

    data: dict = {
        "company": company,
        "month": month,
        "data_available": [],
    }

    if not client_dir.exists():
        print(f"[AUROS] No client directory found at {client_dir}")
        return data

    # Marketing audit
    audit = _load_latest_json(client_dir, "marketing_audit")
    if audit:
        data["marketing_audit"] = audit
        data["data_available"].append("marketing_audit")
        print("[AUROS] Loaded marketing audit")

    # Brand identity
    brand = _load_latest_json(client_dir, "brand_identity")
    if brand:
        data["brand_identity"] = brand
        data["data_available"].append("brand_identity")
        print("[AUROS] Loaded brand identity")

    # Performance metrics
    perf = _load_latest_json(client_dir, "performance")
    if perf:
        data["performance"] = perf
        data["data_available"].append("performance")
        print("[AUROS] Loaded performance metrics")

    # Content calendar
    calendar = _load_latest_json(client_dir, "content_calendar")
    if calendar:
        data["content_calendar"] = calendar
        data["data_available"].append("content_calendar")
        print("[AUROS] Loaded content calendar")

    # Trend analysis
    trends = _load_latest_json(client_dir, "trend")
    if trends:
        data["trends"] = trends
        data["data_available"].append("trends")
        print("[AUROS] Loaded trend analysis")

    return data


# ---------------------------------------------------------------------------
# Report generation prompt
# ---------------------------------------------------------------------------

REPORT_PROMPT = """You are the AUROS client report specialist. Generate a comprehensive monthly client report for {company} covering {month}.

Available client data:
{client_data}

Generate a premium monthly report with the following sections. Return valid JSON:
{{
  "company": "{company}",
  "month": "{month}",
  "generated_date": "{today}",
  "executive_summary": "3-5 sentences summarizing the month. Lead with wins. Be specific with numbers where available.",
  "content_delivered": {{
    "total_pieces": 0,
    "breakdown": [
      {{"platform": "...", "count": 0, "types": ["..."]}}
    ],
    "highlights": ["specific content pieces that performed well"]
  }},
  "performance_highlights": {{
    "top_metric": {{"label": "...", "value": "...", "context": "..."}},
    "engagement_summary": "...",
    "growth_indicators": ["..."],
    "platform_grades": [
      {{"platform": "...", "grade": "A-F", "note": "..."}}
    ]
  }},
  "key_wins": [
    {{"win": "...", "impact": "...", "detail": "..."}}
  ],
  "learnings": [
    {{"insight": "...", "action_taken": "...", "result": "..."}}
  ],
  "recommendations_next_month": [
    {{"priority": 1, "recommendation": "...", "rationale": "...", "expected_outcome": "..."}}
  ],
  "roi_indicators": {{
    "engagement_trend": "up/stable/down",
    "audience_growth": "...",
    "content_efficiency": "...",
    "brand_visibility": "..."
  }},
  "looking_ahead": "2-3 sentences on next month's strategy and focus areas"
}}

Important:
- If data is limited, work with what's available and note where more data would improve future reports
- Be specific, not generic. Use real numbers from the data where possible.
- Lead with positives but be honest about areas for improvement
- Make every sentence earn its place — no filler"""


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def _render_html_report(report: dict) -> str:
    """Render the report JSON as a premium AUROS-branded HTML page."""

    company = report.get("company", "Client")
    month = report.get("month", "")
    today = report.get("generated_date", "")

    # Executive summary
    exec_summary = report.get("executive_summary", "")

    # Content delivered
    content = report.get("content_delivered", {})
    total_pieces = content.get("total_pieces", 0)
    content_breakdown_html = ""
    for item in content.get("breakdown", []):
        types_str = ", ".join(item.get("types", []))
        content_breakdown_html += f"""
        <div class="stat-card">
            <div class="stat-label">{item.get('platform', '').upper()}</div>
            <div class="stat-value">{item.get('count', 0)}</div>
            <div class="stat-sub">{types_str}</div>
        </div>"""

    content_highlights_html = ""
    for h in content.get("highlights", []):
        content_highlights_html += f"<li>{h}</li>"

    # Performance highlights
    perf = report.get("performance_highlights", {})
    top_metric = perf.get("top_metric", {})
    engagement_summary = perf.get("engagement_summary", "")

    growth_html = ""
    for g in perf.get("growth_indicators", []):
        growth_html += f"<li>{g}</li>"

    grades_html = ""
    for pg in perf.get("platform_grades", []):
        grade = pg.get("grade", "N/A")
        grade_class = "grade-high" if grade in ("A", "B") else "grade-mid" if grade == "C" else "grade-low"
        grades_html += f"""
        <div class="grade-card">
            <div class="grade-platform">{pg.get('platform', '').upper()}</div>
            <div class="grade-letter {grade_class}">{grade}</div>
            <div class="grade-note">{pg.get('note', '')}</div>
        </div>"""

    # Key wins
    wins_html = ""
    for w in report.get("key_wins", []):
        wins_html += f"""
        <div class="win-card">
            <div class="win-title">{w.get('win', '')}</div>
            <div class="win-impact">{w.get('impact', '')}</div>
            <div class="win-detail">{w.get('detail', '')}</div>
        </div>"""

    # Learnings
    learnings_html = ""
    for l in report.get("learnings", []):
        learnings_html += f"""
        <div class="learning-card">
            <div class="learning-insight">{l.get('insight', '')}</div>
            <div class="learning-action">Action: {l.get('action_taken', '')}</div>
            <div class="learning-result">Result: {l.get('result', '')}</div>
        </div>"""

    # Recommendations
    recs_html = ""
    for r in report.get("recommendations_next_month", []):
        recs_html += f"""
        <div class="rec-card">
            <div class="rec-priority">#{r.get('priority', '')}</div>
            <div class="rec-body">
                <div class="rec-title">{r.get('recommendation', '')}</div>
                <div class="rec-rationale">{r.get('rationale', '')}</div>
                <div class="rec-outcome">Expected: {r.get('expected_outcome', '')}</div>
            </div>
        </div>"""

    # ROI indicators
    roi = report.get("roi_indicators", {})
    roi_items_html = ""
    roi_labels = {
        "engagement_trend": "Engagement Trend",
        "audience_growth": "Audience Growth",
        "content_efficiency": "Content Efficiency",
        "brand_visibility": "Brand Visibility",
    }
    for key, label in roi_labels.items():
        val = roi.get(key, "N/A")
        roi_items_html += f"""
        <div class="roi-item">
            <div class="roi-label">{label}</div>
            <div class="roi-value">{val}</div>
        </div>"""

    # Looking ahead
    looking_ahead = report.get("looking_ahead", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Monthly Report — {company} — {month}</title>
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
  .container {{ max-width: 900px; margin: 0 auto; padding: 40px 24px; }}

  /* Header */
  .header {{
    text-align: center;
    padding: 60px 0 40px;
    border-bottom: 1px solid rgba(201,168,76,0.2);
    margin-bottom: 48px;
  }}
  .header-brand {{
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 4px;
    color: #C9A84C;
    margin-bottom: 24px;
  }}
  .header-title {{
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 8px;
  }}
  .header-subtitle {{
    font-size: 16px;
    color: #9CA3AF;
    font-weight: 400;
  }}
  .header-meta {{
    margin-top: 16px;
    font-size: 13px;
    color: #6B7280;
  }}

  /* Section */
  .section {{
    margin-bottom: 48px;
  }}
  .section-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #C9A84C;
    text-transform: uppercase;
    margin-bottom: 12px;
  }}
  .section-title {{
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-bottom: 16px;
  }}
  .section-body {{
    font-size: 15px;
    color: #F0EDE6;
    line-height: 1.7;
  }}

  /* Cards */
  .card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 16px;
  }}

  /* Stat cards grid */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
  }}
  .stat-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
  }}
  .stat-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #C9A84C;
    margin-bottom: 8px;
  }}
  .stat-value {{
    font-size: 32px;
    font-weight: 800;
    color: #FAFAF8;
    margin-bottom: 4px;
  }}
  .stat-sub {{
    font-size: 12px;
    color: #9CA3AF;
  }}

  /* Top metric hero */
  .metric-hero {{
    background: linear-gradient(135deg, #111827 0%, #1a1f2e 100%);
    border: 1px solid rgba(201,168,76,0.25);
    border-radius: 16px;
    padding: 36px;
    text-align: center;
    margin-bottom: 24px;
  }}
  .metric-hero-label {{
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 2px;
    color: #C9A84C;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .metric-hero-value {{
    font-size: 48px;
    font-weight: 900;
    color: #C9A84C;
    letter-spacing: -2px;
    margin-bottom: 8px;
  }}
  .metric-hero-context {{
    font-size: 14px;
    color: #9CA3AF;
  }}

  /* Grades */
  .grades-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-top: 20px;
  }}
  .grade-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
  }}
  .grade-platform {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #9CA3AF;
    margin-bottom: 8px;
  }}
  .grade-letter {{
    font-size: 40px;
    font-weight: 900;
    margin-bottom: 8px;
  }}
  .grade-high {{ color: #22c55e; }}
  .grade-mid {{ color: #C9A84C; }}
  .grade-low {{ color: #ef4444; }}
  .grade-note {{
    font-size: 12px;
    color: #9CA3AF;
    line-height: 1.4;
  }}

  /* Win cards */
  .win-card {{
    background: #111827;
    border-left: 3px solid #C9A84C;
    border-radius: 0 12px 12px 0;
    padding: 24px;
    margin-bottom: 12px;
  }}
  .win-title {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 6px;
  }}
  .win-impact {{
    font-size: 14px;
    color: #C9A84C;
    font-weight: 600;
    margin-bottom: 4px;
  }}
  .win-detail {{
    font-size: 13px;
    color: #9CA3AF;
  }}

  /* Learning cards */
  .learning-card {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 12px;
  }}
  .learning-insight {{
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 8px;
  }}
  .learning-action, .learning-result {{
    font-size: 13px;
    color: #9CA3AF;
    margin-bottom: 4px;
  }}

  /* Recommendation cards */
  .rec-card {{
    display: flex;
    gap: 20px;
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 12px;
    align-items: flex-start;
  }}
  .rec-priority {{
    font-size: 24px;
    font-weight: 800;
    color: #C9A84C;
    min-width: 36px;
  }}
  .rec-title {{
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 6px;
  }}
  .rec-rationale {{
    font-size: 13px;
    color: #9CA3AF;
    margin-bottom: 4px;
  }}
  .rec-outcome {{
    font-size: 13px;
    color: #C9A84C;
    font-weight: 500;
  }}

  /* ROI grid */
  .roi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 16px;
  }}
  .roi-item {{
    background: #111827;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
  }}
  .roi-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #9CA3AF;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .roi-value {{
    font-size: 15px;
    font-weight: 600;
    color: #FAFAF8;
  }}

  /* Lists */
  .highlights-list {{
    list-style: none;
    padding: 0;
  }}
  .highlights-list li {{
    padding: 8px 0;
    padding-left: 20px;
    position: relative;
    font-size: 14px;
    color: #F0EDE6;
  }}
  .highlights-list li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 14px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #C9A84C;
  }}

  /* Footer */
  .footer {{
    text-align: center;
    padding: 48px 0 32px;
    border-top: 1px solid rgba(201,168,76,0.2);
    margin-top: 48px;
  }}
  .footer-brand {{
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 3px;
    color: #C9A84C;
    margin-bottom: 8px;
  }}
  .footer-tagline {{
    font-size: 13px;
    color: #6B7280;
    font-style: italic;
  }}
  .footer-legal {{
    margin-top: 16px;
    font-size: 11px;
    color: #4B5563;
  }}

  /* Divider */
  .divider {{
    height: 1px;
    background: rgba(201,168,76,0.15);
    margin: 48px 0;
  }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div class="header-brand">AUROS</div>
    <div class="header-title">Monthly Performance Report</div>
    <div class="header-subtitle">{company} — {month}</div>
    <div class="header-meta">Generated {today} | Confidential</div>
  </div>

  <!-- Executive Summary -->
  <div class="section">
    <div class="section-label">Overview</div>
    <div class="section-title">Executive Summary</div>
    <div class="card">
      <div class="section-body">{exec_summary}</div>
    </div>
  </div>

  <!-- Content Delivered -->
  <div class="section">
    <div class="section-label">Deliverables</div>
    <div class="section-title">Content Delivered This Month</div>
    <div class="metric-hero">
      <div class="metric-hero-label">Total Content Pieces</div>
      <div class="metric-hero-value">{total_pieces}</div>
      <div class="metric-hero-context">Across all platforms</div>
    </div>
    <div class="stats-grid">
      {content_breakdown_html}
    </div>
    <div class="card">
      <div class="stat-label" style="margin-bottom:12px">Highlights</div>
      <ul class="highlights-list">
        {content_highlights_html}
      </ul>
    </div>
  </div>

  <!-- Performance Highlights -->
  <div class="section">
    <div class="section-label">Performance</div>
    <div class="section-title">Performance Highlights</div>
    <div class="metric-hero">
      <div class="metric-hero-label">{top_metric.get('label', 'Top Metric')}</div>
      <div class="metric-hero-value">{top_metric.get('value', 'N/A')}</div>
      <div class="metric-hero-context">{top_metric.get('context', '')}</div>
    </div>
    <div class="card">
      <div class="section-body">{engagement_summary}</div>
      <ul class="highlights-list" style="margin-top:16px">
        {growth_html}
      </ul>
    </div>
    <div class="grades-grid">
      {grades_html}
    </div>
  </div>

  <div class="divider"></div>

  <!-- Key Wins -->
  <div class="section">
    <div class="section-label">Wins</div>
    <div class="section-title">Key Wins This Month</div>
    {wins_html}
  </div>

  <!-- Learnings -->
  <div class="section">
    <div class="section-label">Insights</div>
    <div class="section-title">Key Learnings</div>
    {learnings_html}
  </div>

  <div class="divider"></div>

  <!-- Recommendations -->
  <div class="section">
    <div class="section-label">Next Steps</div>
    <div class="section-title">Recommendations for Next Month</div>
    {recs_html}
  </div>

  <!-- ROI Indicators -->
  <div class="section">
    <div class="section-label">ROI</div>
    <div class="section-title">Return on Investment Indicators</div>
    <div class="roi-grid">
      {roi_items_html}
    </div>
  </div>

  <!-- Looking Ahead -->
  <div class="section">
    <div class="section-label">Outlook</div>
    <div class="section-title">Looking Ahead</div>
    <div class="card">
      <div class="section-body">{looking_ahead}</div>
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    <div class="footer-brand">AUROS</div>
    <div class="footer-tagline">Intelligence, Elevated.</div>
    <div class="footer-legal">This report is confidential and prepared exclusively for {company}.</div>
  </div>

</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(company: str, month: str | None = None) -> dict:
    """Generate a monthly client report."""
    today = datetime.now().strftime("%Y-%m-%d")
    if not month:
        month = datetime.now().strftime("%Y-%m")

    print(f"[AUROS] Client Report Generator starting — {company} — {month}")

    # Load all available client data
    client_data = _load_client_data(company, month)
    available = client_data.get("data_available", [])
    print(f"[AUROS] Data sources available: {', '.join(available) if available else 'none'}")

    # Generate report via Claude
    print("[AUROS] Generating monthly report...")
    prompt = REPORT_PROMPT.format(
        company=company,
        month=month,
        today=today,
        client_data=json.dumps(client_data, indent=2)[:12000],
    )
    raw = generate(prompt, temperature=0.4, max_tokens=4096)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    report = json.loads(json_str)

    # Save results
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    reports_dir = client_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # JSON version
    json_path = reports_dir / f"monthly_{month}.json"
    json_path.write_text(json.dumps(report, indent=2))
    print(f"[AUROS] JSON report saved to {json_path}")

    # HTML version
    html_content = _render_html_report(report)
    html_path = reports_dir / f"monthly_{month}.html"
    html_path.write_text(html_content)
    print(f"[AUROS] HTML report saved to {html_path}")

    print(f"[AUROS] Client Report complete — {company} — {month}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Client Report Generator")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--month", help="Report month (YYYY-MM), defaults to current month")
    args = parser.parse_args()
    run(**vars(args))
