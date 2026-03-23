#!/usr/bin/env python3
"""
AUROS AI — Agent 3: Marketing Plan Builder
Combines data from the Marketing Audit (Agent 1) and Brand Identity Extraction (Agent 2)
to create a comprehensive, executable marketing plan with timelines and deliverables.

Usage:
    python -m agents.plan_builder.plan_agent --company "Company Name"
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


PLAN_PROMPT = """You are the AUROS chief marketing strategist. You have been given a company's marketing audit and brand identity extraction. Build a comprehensive, executable marketing plan.

This plan must be specific enough that a team could execute it without further briefing. No vague recommendations — every action item needs a timeline, a deliverable, and a success metric.

Return as valid JSON:
{{
  "company": "...",
  "plan_date": "...",
  "plan_duration": "90 days",

  "executive_summary": "...",

  "objectives": [
    {{"objective": "...", "metric": "...", "target": "...", "timeline": "..."}}
  ],

  "target_audience": {{
    "primary": {{"description": "...", "demographics": "...", "psychographics": "...", "platforms": ["..."]}},
    "secondary": {{"description": "...", "demographics": "...", "psychographics": "...", "platforms": ["..."]}}
  }},

  "content_strategy": {{
    "content_pillars": [
      {{"name": "...", "description": "...", "percentage_of_content": 0, "example_posts": ["..."]}}
    ],
    "content_mix": {{
      "video_short": {{"percentage": 0, "platforms": ["..."], "frequency": "..."}},
      "video_long": {{"percentage": 0, "platforms": ["..."], "frequency": "..."}},
      "static_images": {{"percentage": 0, "platforms": ["..."], "frequency": "..."}},
      "carousels": {{"percentage": 0, "platforms": ["..."], "frequency": "..."}},
      "stories": {{"percentage": 0, "platforms": ["..."], "frequency": "..."}}
    }},
    "posting_schedule": {{
      "instagram": {{"posts_per_week": 0, "best_times": ["..."], "content_types": ["..."]}},
      "tiktok": {{"posts_per_week": 0, "best_times": ["..."], "content_types": ["..."]}},
      "linkedin": {{"posts_per_week": 0, "best_times": ["..."], "content_types": ["..."]}},
      "youtube": {{"posts_per_week": 0, "best_times": ["..."], "content_types": ["..."]}},
      "facebook": {{"posts_per_week": 0, "best_times": ["..."], "content_types": ["..."]}}
    }}
  }},

  "phase_1_foundation": {{
    "duration": "Weeks 1-2",
    "focus": "...",
    "tasks": [
      {{"task": "...", "deliverable": "...", "owner": "AUROS", "deadline": "...", "status": "pending"}}
    ]
  }},

  "phase_2_launch": {{
    "duration": "Weeks 3-6",
    "focus": "...",
    "tasks": [
      {{"task": "...", "deliverable": "...", "owner": "AUROS", "deadline": "...", "status": "pending"}}
    ]
  }},

  "phase_3_scale": {{
    "duration": "Weeks 7-12",
    "focus": "...",
    "tasks": [
      {{"task": "...", "deliverable": "...", "owner": "AUROS", "deadline": "...", "status": "pending"}}
    ]
  }},

  "paid_media_strategy": {{
    "recommended_monthly_budget": "...",
    "platforms": ["..."],
    "campaign_types": ["..."],
    "targeting_approach": "..."
  }},

  "kpis": [
    {{"metric": "...", "current": "...", "target_30_days": "...", "target_60_days": "...", "target_90_days": "..."}}
  ],

  "competitive_advantages": ["..."],

  "risks_and_mitigation": [
    {{"risk": "...", "mitigation": "..."}}
  ],

  "investment_summary": {{
    "recommended_package": "...",
    "monthly_investment": "...",
    "includes": ["..."],
    "expected_roi_timeline": "..."
  }}
}}

Be extremely specific to THIS company. Reference their actual weaknesses from the audit. Use their brand colors and voice characteristics from the brand extraction. Make recommendations that directly address the gaps found.

MARKETING AUDIT DATA:
{audit_data}

BRAND IDENTITY DATA:
{brand_data}
"""


def run(company: str) -> dict:
    """Generate a comprehensive marketing plan for a company."""
    today = datetime.now().strftime("%Y-%m-%d")
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"

    print(f"[AUROS] Marketing Plan Builder starting — {company}")

    # Load audit data
    audit_data = {}
    audit_files = sorted(client_dir.glob("marketing_audit_*.json"), reverse=True)
    if audit_files:
        audit_data = json.loads(audit_files[0].read_text())
        print(f"[AUROS] Loaded audit: {audit_files[0].name}")
    else:
        print("[AUROS] WARNING: No marketing audit found. Plan will be less specific.")

    # Load brand data
    brand_data = {}
    brand_files = sorted(client_dir.glob("brand_identity_*.json"), reverse=True)
    if brand_files:
        brand_data = json.loads(brand_files[0].read_text())
        print(f"[AUROS] Loaded brand identity: {brand_files[0].name}")
    else:
        print("[AUROS] WARNING: No brand identity found. Plan will be less specific.")

    # Load marketing knowledge base
    try:
        from agents.shared.knowledge import get_plan_knowledge
        knowledge = get_plan_knowledge()
        print("[AUROS] Loaded marketing knowledge base for plan enrichment")
    except Exception:
        knowledge = ""

    # Generate plan
    print("[AUROS] Building marketing plan...")
    prompt = PLAN_PROMPT.format(
        audit_data=json.dumps(audit_data, indent=2)[:8000],
        brand_data=json.dumps(brand_data, indent=2)[:4000],
    )
    if knowledge:
        prompt += f"\n\n{knowledge[:5000]}"
    raw = generate(prompt, temperature=0.4, max_tokens=8000)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    plan = json.loads(json_str)

    # Save JSON
    plan_path = client_dir / f"marketing_plan_{today}.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    print(f"[AUROS] Plan JSON saved to {plan_path}")

    # Save HTML
    html_path = client_dir / f"marketing_plan_{today}.html"
    html_path.write_text(_plan_to_html(plan))
    print(f"[AUROS] Plan HTML saved to {html_path}")

    # Save markdown
    md_path = client_dir / f"marketing_plan_{today}.md"
    md_path.write_text(_plan_to_markdown(plan))
    print(f"[AUROS] Plan markdown saved to {md_path}")

    print(f"[AUROS] Marketing Plan complete — {plan.get('plan_duration', '90 days')} plan generated")
    return plan


def _plan_to_html(plan: dict) -> str:
    """Render the marketing plan as an AUROS-branded HTML page."""
    # Build objectives HTML
    objectives_html = ""
    for obj in plan.get("objectives", []):
        objectives_html += f"""
        <div style="background:#111827;padding:24px;border-left:3px solid #C9A84C;margin-bottom:2px;">
          <div style="font-size:16px;font-weight:700;color:#FAFAF8;margin-bottom:8px;">{obj.get('objective','')}</div>
          <div style="font-size:13px;color:#9CA3AF;">
            <span style="color:#C9A84C;font-weight:600;">Metric:</span> {obj.get('metric','')} →
            <span style="color:#E8C96A;font-weight:600;">{obj.get('target','')}</span> |
            <span style="color:#6B7280;">Timeline: {obj.get('timeline','')}</span>
          </div>
        </div>"""

    # Build content pillars HTML
    pillars_html = ""
    for pillar in plan.get("content_strategy", {}).get("content_pillars", []):
        pillars_html += f"""
        <div style="background:#111827;padding:24px;flex:1;min-width:200px;">
          <div style="font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;font-weight:700;margin-bottom:8px;">{pillar.get('percentage_of_content',0)}% of content</div>
          <div style="font-size:18px;font-weight:700;margin-bottom:8px;">{pillar.get('name','')}</div>
          <div style="font-size:13px;color:#9CA3AF;line-height:1.6;">{pillar.get('description','')}</div>
        </div>"""

    # Build phase tasks HTML
    def phase_html(phase_data, phase_num, color):
        tasks = ""
        for t in phase_data.get("tasks", []):
            tasks += f"""
            <tr>
              <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#FAFAF8;font-size:13px;">{t.get('task','')}</td>
              <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#9CA3AF;font-size:13px;">{t.get('deliverable','')}</td>
              <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#C9A84C;font-size:13px;">{t.get('deadline','')}</td>
            </tr>"""
        return f"""
        <div style="margin-bottom:32px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
            <div style="background:{color};color:#0B0F1A;padding:6px 14px;font-size:11px;font-weight:700;letter-spacing:1px;">PHASE {phase_num}</div>
            <span style="font-size:14px;color:#9CA3AF;">{phase_data.get('duration','')}</span>
          </div>
          <div style="font-size:18px;font-weight:700;margin-bottom:16px;">{phase_data.get('focus','')}</div>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#111827;">
            <tr>
              <th style="padding:10px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Task</th>
              <th style="padding:10px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Deliverable</th>
              <th style="padding:10px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Deadline</th>
            </tr>
            {tasks}
          </table>
        </div>"""

    phases = ""
    phases += phase_html(plan.get("phase_1_foundation", {}), 1, "#C9A84C")
    phases += phase_html(plan.get("phase_2_launch", {}), 2, "#E8C96A")
    phases += phase_html(plan.get("phase_3_scale", {}), 3, "#3B82F6")

    # KPIs HTML
    kpis_html = ""
    for kpi in plan.get("kpis", []):
        kpis_html += f"""
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#FAFAF8;font-size:13px;font-weight:600;">{kpi.get('metric','')}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#6B7280;font-size:13px;">{kpi.get('current','')}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#E8C96A;font-size:13px;">{kpi.get('target_30_days','')}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#C9A84C;font-size:13px;">{kpi.get('target_60_days','')}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1a1f2e;color:#C9A84C;font-size:13px;font-weight:700;">{kpi.get('target_90_days','')}</td>
        </tr>"""

    investment = plan.get("investment_summary", {})
    includes_html = "".join(f"<div style='padding:8px 0;border-bottom:1px solid #1a1f2e;color:#9CA3AF;font-size:13px;'>✓ {item}</div>" for item in investment.get("includes", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Marketing Plan — {plan.get('company','')}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:#0B0F1A; color:#FAFAF8; }}
  .section {{ padding:60px 80px; border-bottom:1px solid rgba(201,168,76,0.1); }}
  .label {{ font-size:10px; font-weight:700; letter-spacing:4px; color:#C9A84C; text-transform:uppercase; margin-bottom:12px; }}
  h1 {{ font-size:48px; font-weight:900; letter-spacing:-2px; line-height:1.05; }}
  h2 {{ font-size:28px; font-weight:800; letter-spacing:-0.5px; margin-bottom:24px; }}
  .sub {{ font-size:16px; color:#9CA3AF; max-width:600px; line-height:1.7; margin-top:16px; }}
</style>
</head>
<body>

<!-- Cover -->
<div class="section" style="min-height:60vh;display:flex;flex-direction:column;justify-content:center;">
  <div class="label">AUROS — Marketing Plan</div>
  <h1>{plan.get('company','')}</h1>
  <div class="sub">{plan.get('executive_summary','')}</div>
  <div style="margin-top:32px;font-size:13px;color:#6B7280;">
    {plan.get('plan_duration','')} · Generated {plan.get('plan_date','')} · Confidential
  </div>
</div>

<!-- Objectives -->
<div class="section">
  <div class="label">Strategic Objectives</div>
  <h2>What We're Going to Achieve</h2>
  {objectives_html}
</div>

<!-- Content Strategy -->
<div class="section">
  <div class="label">Content Strategy</div>
  <h2>Content Pillars</h2>
  <div style="display:flex;gap:2px;flex-wrap:wrap;">
    {pillars_html}
  </div>
</div>

<!-- Execution Phases -->
<div class="section">
  <div class="label">Execution Roadmap</div>
  <h2>How We Execute</h2>
  {phases}
</div>

<!-- KPIs -->
<div class="section">
  <div class="label">Key Performance Indicators</div>
  <h2>How We Measure Success</h2>
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#111827;">
    <tr>
      <th style="padding:12px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">Metric</th>
      <th style="padding:12px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#6B7280;text-transform:uppercase;">Current</th>
      <th style="padding:12px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">30 Days</th>
      <th style="padding:12px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">60 Days</th>
      <th style="padding:12px 16px;text-align:left;font-size:10px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;">90 Days</th>
    </tr>
    {kpis_html}
  </table>
</div>

<!-- Investment -->
<div class="section">
  <div class="label">Investment</div>
  <h2>{investment.get('recommended_package','')}</h2>
  <div style="display:flex;gap:32px;align-items:flex-start;">
    <div style="background:rgba(201,168,76,0.08);border:1px solid rgba(201,168,76,0.2);padding:32px;min-width:280px;">
      <div style="font-size:36px;font-weight:900;color:#C9A84C;">{investment.get('monthly_investment','')}</div>
      <div style="font-size:12px;color:#6B7280;letter-spacing:1px;margin-top:4px;">PER MONTH</div>
      <div style="margin-top:20px;">{includes_html}</div>
    </div>
    <div style="flex:1;">
      <div style="font-size:14px;color:#9CA3AF;line-height:1.7;">
        <strong style="color:#FAFAF8;">Expected ROI Timeline:</strong> {investment.get('expected_roi_timeline','')}
      </div>
    </div>
  </div>
</div>

<!-- Footer -->
<div style="padding:40px 80px;text-align:center;border-top:1px solid rgba(201,168,76,0.2);">
  <div style="font-size:24px;font-weight:900;color:#C9A84C;">AUROS</div>
  <div style="font-size:11px;color:#6B7280;letter-spacing:1px;margin-top:4px;">Intelligence, Elevated.</div>
</div>

</body>
</html>"""


def _plan_to_markdown(plan: dict) -> str:
    """Convert plan to readable markdown."""
    lines = [
        f"# AUROS Marketing Plan — {plan.get('company', '')}",
        f"**Duration:** {plan.get('plan_duration', '')} | **Date:** {plan.get('plan_date', '')}",
        "",
        "---",
        "",
        "## Executive Summary",
        plan.get("executive_summary", ""),
        "",
        "## Strategic Objectives",
    ]

    for obj in plan.get("objectives", []):
        lines.append(f"- **{obj.get('objective', '')}** — {obj.get('metric', '')}: {obj.get('target', '')} ({obj.get('timeline', '')})")
    lines.append("")

    # Content pillars
    lines.append("## Content Pillars")
    for pillar in plan.get("content_strategy", {}).get("content_pillars", []):
        lines.append(f"### {pillar.get('name', '')} ({pillar.get('percentage_of_content', 0)}%)")
        lines.append(pillar.get("description", ""))
        lines.append("")

    # Phases
    for phase_key, phase_num in [("phase_1_foundation", 1), ("phase_2_launch", 2), ("phase_3_scale", 3)]:
        phase = plan.get(phase_key, {})
        lines.append(f"## Phase {phase_num}: {phase.get('focus', '')} ({phase.get('duration', '')})")
        for task in phase.get("tasks", []):
            lines.append(f"- [ ] **{task.get('task', '')}** → {task.get('deliverable', '')} (by {task.get('deadline', '')})")
        lines.append("")

    # KPIs
    lines.append("## KPIs")
    lines.append("| Metric | Current | 30 Days | 60 Days | 90 Days |")
    lines.append("|--------|---------|---------|---------|---------|")
    for kpi in plan.get("kpis", []):
        lines.append(f"| {kpi.get('metric','')} | {kpi.get('current','')} | {kpi.get('target_30_days','')} | {kpi.get('target_60_days','')} | {kpi.get('target_90_days','')} |")
    lines.append("")

    # Investment
    inv = plan.get("investment_summary", {})
    lines.append("## Investment")
    lines.append(f"**Package:** {inv.get('recommended_package', '')}")
    lines.append(f"**Monthly:** {inv.get('monthly_investment', '')}")
    lines.append(f"**ROI Timeline:** {inv.get('expected_roi_timeline', '')}")
    lines.append("")
    for item in inv.get("includes", []):
        lines.append(f"- ✓ {item}")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by AUROS — Intelligence, Elevated.*")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Marketing Plan Builder")
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    run(company=args.company)
