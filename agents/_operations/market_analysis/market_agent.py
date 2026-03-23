#!/usr/bin/env python3
"""
AUROS AI — Market Analysis Agent
Scans sectors, tracks competitors, and generates opportunity reports.

Usage:
    python -m agents.market_analysis.market_agent
    python -m agents.market_analysis.market_agent --dry-run
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import MARKET_DIR, LOGS_DIR
from agents.shared.llm import generate
from agents.market_analysis.sector_scanner import scan_sectors
from agents.market_analysis.competitor_tracker import track_competitors
from agents.newsletter.sender import send_newsletter


ANALYSIS_PROMPT = """You are the AUROS market intelligence analyst. Analyze the following research data and produce a strategic market report.

For each sector, score on a 1-10 scale:
- **AI Adoption Gap**: How behind is this sector in adopting AI for marketing? (10 = very behind, huge opportunity)
- **Marketing Budget Level**: Does this sector spend heavily on marketing? (10 = big budgets)
- **Pain Point Severity**: How urgent are their marketing problems? (10 = very urgent)
- **Accessibility**: How easy is it to reach decision-makers? (10 = very accessible)
- **Competition Density**: How many AI agencies already serve them? (10 = low competition, open field)

Then provide:
1. **Composite score** (weighted average: gaps 25%, budget 25%, pain 20%, access 15%, competition 15%)
2. **Top 3 sectors** to target this week with reasoning
3. **Competitor intelligence summary** — what are other AI agencies doing?
4. **3 specific outreach opportunities** — concrete actions AUROS should take

Return as valid JSON:
{{
  "sectors": [
    {{
      "name": "...",
      "scores": {{"ai_gap": 0, "budget": 0, "pain": 0, "access": 0, "competition": 0}},
      "composite": 0.0,
      "analysis": "..."
    }}
  ],
  "top_3": ["...", "...", "..."],
  "top_3_reasoning": "...",
  "competitor_summary": "...",
  "outreach_opportunities": [
    {{"target": "...", "action": "...", "reasoning": "..."}}
  ],
  "market_pulse": "..."
}}

SECTOR RESEARCH DATA:
{sector_data}

COMPETITOR RESEARCH DATA:
{competitor_data}
"""


def run(dry_run: bool = False) -> dict:
    """Execute the full market analysis pipeline."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[AUROS] Market analysis agent starting — {today}")

    # Step 1: Scan sectors
    print("[AUROS] Scanning sectors...")
    sector_data = scan_sectors()

    # Step 2: Track competitors
    print("[AUROS] Tracking competitors...")
    competitor_data = track_competitors()

    # Step 3: Analyze via Claude
    print("[AUROS] Generating market analysis...")
    prompt = ANALYSIS_PROMPT.format(
        sector_data=json.dumps(sector_data, indent=2)[:8000],
        competitor_data=json.dumps(competitor_data, indent=2)[:4000],
    )
    raw_response = generate(prompt, temperature=0.4, max_tokens=4096)

    # Parse JSON
    json_str = raw_response.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    report = json.loads(json_str)
    report["date"] = today

    # Step 4: Save report
    reports_dir = MARKET_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"market_report_{today}.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"[AUROS] Report saved to {report_path}")

    # Update running intelligence file
    intel_path = MARKET_DIR / "reports" / "market_intelligence.json"
    intel = []
    if intel_path.exists():
        intel = json.loads(intel_path.read_text())
    intel.append({
        "date": today,
        "top_3": report.get("top_3", []),
        "sectors": [
            {"name": s["name"], "composite": s["composite"]}
            for s in report.get("sectors", [])
        ],
    })
    intel_path.write_text(json.dumps(intel, indent=2))

    # Step 5: Email summary
    if not dry_run:
        summary_html = _build_summary_html(report)
        send_newsletter(
            subject=f"AUROS Market Intelligence — {today}",
            html_content=summary_html,
        )

    print(f"[AUROS] Market analysis complete")
    return {"status": "complete", "report": report}


def _build_summary_html(report: dict) -> str:
    """Build a simple HTML summary email for the market report."""
    sectors_html = ""
    for s in sorted(report.get("sectors", []), key=lambda x: x.get("composite", 0), reverse=True):
        sectors_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #1a1a2e;color:#FAFAF8;font-size:14px;">{s['name']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #1a1a2e;color:#C9A84C;font-size:14px;font-weight:700;text-align:center;">{s['composite']:.1f}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #1a1a2e;color:#9CA3AF;font-size:13px;">{s.get('analysis', '')[:120]}...</td>
        </tr>"""

    top3 = ", ".join(report.get("top_3", []))

    return f"""
    <html><body style="margin:0;padding:0;background:#0B0F1A;font-family:Inter,Arial,sans-serif;color:#FAFAF8;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:32px 40px;border-bottom:1px solid rgba(201,168,76,0.2);">
        <span style="font-size:28px;font-weight:900;color:#C9A84C;">AUROS</span>
        <span style="font-size:10px;color:#6B7280;letter-spacing:3px;float:right;margin-top:12px;">MARKET INTELLIGENCE</span>
      </td></tr>
      <tr><td style="padding:32px 40px;">
        <p style="font-size:10px;letter-spacing:3px;color:#C9A84C;text-transform:uppercase;font-weight:700;">Top 3 Sectors This Week</p>
        <p style="font-size:20px;font-weight:700;margin:8px 0 24px;">{top3}</p>
        <p style="font-size:14px;color:#9CA3AF;line-height:1.7;">{report.get('top_3_reasoning', '')}</p>
      </td></tr>
      <tr><td style="padding:0 40px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#111827;">
          <tr>
            <th style="padding:12px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Sector</th>
            <th style="padding:12px;text-align:center;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Score</th>
            <th style="padding:12px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Analysis</th>
          </tr>
          {sectors_html}
        </table>
      </td></tr>
      <tr><td style="padding:24px 40px;border-top:1px solid rgba(201,168,76,0.2);">
        <p style="font-size:10px;letter-spacing:3px;color:#C9A84C;text-transform:uppercase;font-weight:700;">Competitor Pulse</p>
        <p style="font-size:14px;color:#9CA3AF;line-height:1.7;margin-top:8px;">{report.get('competitor_summary', '')}</p>
      </td></tr>
      <tr><td style="padding:32px 40px;text-align:center;border-top:1px solid rgba(201,168,76,0.2);">
        <span style="font-size:20px;font-weight:900;color:#C9A84C;">AUROS</span><br>
        <span style="font-size:10px;color:#6B7280;letter-spacing:1px;">Intelligence, Elevated.</span>
      </td></tr>
    </table>
    </body></html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Market Analysis Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending email")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
