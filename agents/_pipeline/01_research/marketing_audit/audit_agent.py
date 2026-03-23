#!/usr/bin/env python3
"""
AUROS AI — Agent 1: Marketing Audit
Scrapes a company's social media presence and website to analyze their current
marketing strategy, content quality, posting frequency, and gaps.

Usage:
    python -m agents.marketing_audit.audit_agent --company "Company Name" --website "https://example.com" --instagram "@handle" --tiktok "@handle"
"""

from __future__ import annotations

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, LOGS_DIR
from agents.shared.llm import generate
from agents.marketing_audit.scraper import scrape_website, research_social_presence


AUDIT_PROMPT = """You are the AUROS marketing audit specialist. You have been given data scraped from a company's website and research about their social media presence.

Produce a comprehensive marketing audit with the following sections:

1. **Executive Summary** — 3-4 sentences on the company's current marketing posture.
2. **Website Analysis**
   - Messaging clarity (is the value prop obvious in 5 seconds?)
   - SEO indicators (meta tags, headings structure, content depth)
   - Conversion funnel (CTAs, lead capture, user journey)
   - Mobile readiness and page speed indicators
3. **Social Media Audit** (for each platform found)
   - Estimated posting frequency
   - Content types used (video, static, carousel, stories, text)
   - Engagement quality (based on available data)
   - Brand consistency across platforms
   - Content gaps and missed opportunities
4. **Competitive Positioning** — How they compare to industry standards
5. **SWOT Analysis** — Strengths, Weaknesses, Opportunities, Threats
6. **Top 5 Recommendations** — Specific, actionable improvements ranked by impact
7. **AUROS Opportunity Score** — Rate 1-100 how much AUROS can improve their marketing

Return as valid JSON:
{{
  "company": "...",
  "audit_date": "...",
  "executive_summary": "...",
  "website_analysis": {{
    "messaging_clarity": {{"score": 0, "analysis": "..."}},
    "seo_indicators": {{"score": 0, "analysis": "..."}},
    "conversion_funnel": {{"score": 0, "analysis": "..."}},
    "mobile_readiness": {{"score": 0, "analysis": "..."}}
  }},
  "social_media": [
    {{
      "platform": "...",
      "handle": "...",
      "posting_frequency": "...",
      "content_types": ["..."],
      "engagement_assessment": "...",
      "brand_consistency": "...",
      "gaps": ["..."]
    }}
  ],
  "swot": {{
    "strengths": ["..."],
    "weaknesses": ["..."],
    "opportunities": ["..."],
    "threats": ["..."]
  }},
  "top_5_recommendations": [
    {{"rank": 1, "recommendation": "...", "impact": "high/medium/low", "effort": "high/medium/low"}}
  ],
  "opportunity_score": 0,
  "opportunity_reasoning": "..."
}}

COMPANY DATA:
{company_data}
"""


def run(
    company: str,
    website: str | None = None,
    instagram: str | None = None,
    tiktok: str | None = None,
    facebook: str | None = None,
    linkedin: str | None = None,
    youtube: str | None = None,
    twitter: str | None = None,
) -> dict:
    """Run a full marketing audit on a company."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[AUROS] Marketing Audit starting — {company} — {today}")

    company_data = {"company": company, "audit_date": today}

    # Scrape website
    if website:
        print(f"[AUROS] Scraping website: {website}")
        company_data["website"] = scrape_website(website)

    # Research social media presence
    socials = {
        "instagram": instagram,
        "tiktok": tiktok,
        "facebook": facebook,
        "linkedin": linkedin,
        "youtube": youtube,
        "twitter": twitter,
    }
    active_socials = {k: v for k, v in socials.items() if v}

    if active_socials:
        print(f"[AUROS] Researching social presence: {', '.join(active_socials.keys())}")
        company_data["social_media"] = research_social_presence(company, active_socials)

    # Load marketing knowledge base
    try:
        from agents.shared.knowledge import get_audit_knowledge
        knowledge = get_audit_knowledge()
        print("[AUROS] Loaded marketing knowledge base for audit enrichment")
    except Exception:
        knowledge = ""

    # Generate audit via Claude
    print("[AUROS] Generating marketing audit...")
    prompt = AUDIT_PROMPT.format(company_data=json.dumps(company_data, indent=2)[:12000])
    if knowledge:
        prompt += f"\n\n{knowledge[:3000]}"
    raw = generate(prompt, temperature=0.3, max_tokens=4096)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    audit = json.loads(json_str)

    # Save audit
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
    client_dir.mkdir(parents=True, exist_ok=True)
    audit_path = client_dir / f"marketing_audit_{today}.json"
    audit_path.write_text(json.dumps(audit, indent=2))
    print(f"[AUROS] Audit saved to {audit_path}")

    # Also save a readable markdown version
    md_path = client_dir / f"marketing_audit_{today}.md"
    md_path.write_text(_audit_to_markdown(audit))
    print(f"[AUROS] Markdown report saved to {md_path}")

    print(f"[AUROS] Marketing Audit complete — Opportunity Score: {audit.get('opportunity_score', 'N/A')}/100")
    return audit


def _audit_to_markdown(audit: dict) -> str:
    """Convert audit JSON to readable markdown."""
    lines = [
        f"# AUROS Marketing Audit — {audit.get('company', 'Unknown')}",
        f"**Date:** {audit.get('audit_date', 'N/A')}",
        f"**Opportunity Score:** {audit.get('opportunity_score', 'N/A')}/100",
        "",
        "---",
        "",
        "## Executive Summary",
        audit.get("executive_summary", ""),
        "",
    ]

    # Website analysis
    wa = audit.get("website_analysis", {})
    if wa:
        lines.append("## Website Analysis")
        for key, data in wa.items():
            label = key.replace("_", " ").title()
            lines.append(f"### {label} — Score: {data.get('score', 'N/A')}/10")
            lines.append(data.get("analysis", ""))
            lines.append("")

    # Social media
    for social in audit.get("social_media", []):
        lines.append(f"## {social.get('platform', 'Unknown')} — {social.get('handle', '')}")
        lines.append(f"- **Posting frequency:** {social.get('posting_frequency', 'N/A')}")
        lines.append(f"- **Content types:** {', '.join(social.get('content_types', []))}")
        lines.append(f"- **Engagement:** {social.get('engagement_assessment', 'N/A')}")
        lines.append(f"- **Brand consistency:** {social.get('brand_consistency', 'N/A')}")
        if social.get("gaps"):
            lines.append(f"- **Gaps:** {', '.join(social['gaps'])}")
        lines.append("")

    # SWOT
    swot = audit.get("swot", {})
    if swot:
        lines.append("## SWOT Analysis")
        for category in ["strengths", "weaknesses", "opportunities", "threats"]:
            lines.append(f"### {category.title()}")
            for item in swot.get(category, []):
                lines.append(f"- {item}")
            lines.append("")

    # Recommendations
    lines.append("## Top 5 Recommendations")
    for rec in audit.get("top_5_recommendations", []):
        lines.append(f"**{rec.get('rank', '?')}.** {rec.get('recommendation', '')}")
        lines.append(f"   Impact: {rec.get('impact', 'N/A')} | Effort: {rec.get('effort', 'N/A')}")
        lines.append("")

    lines.append("---")
    lines.append(f"*{audit.get('opportunity_reasoning', '')}*")
    lines.append("")
    lines.append("*Generated by AUROS — Intelligence, Elevated.*")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Marketing Audit Agent")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--website", help="Company website URL")
    parser.add_argument("--instagram", help="Instagram handle")
    parser.add_argument("--tiktok", help="TikTok handle")
    parser.add_argument("--facebook", help="Facebook page")
    parser.add_argument("--linkedin", help="LinkedIn page")
    parser.add_argument("--youtube", help="YouTube channel")
    parser.add_argument("--twitter", help="X/Twitter handle")
    args = parser.parse_args()
    run(**vars(args))
