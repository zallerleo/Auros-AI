#!/usr/bin/env python3
"""
AUROS AI — Outreach Agent
Generates personalized cold outreach emails and DM scripts for potential clients.

Usage:
    python -m agents.outreach.outreach_agent --company "Company Name" --contact "John Smith" --role "CEO" --channel "email"
"""

from __future__ import annotations

import sys
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, TAVILY_API_KEY
from agents.shared.llm import generate, AUROS_SYSTEM_PROMPT


def _slugify(name: str) -> str:
    """Convert company name to slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search Tavily for company research."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query, max_results=max_results, search_depth="advanced")
    return response.get("results", [])


def _load_audit(slug: str) -> dict | None:
    """Try to load existing audit data for the company."""
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    if not client_dir.exists():
        return None
    audit_files = sorted(client_dir.glob("marketing_audit_*.json"), reverse=True)
    if audit_files:
        return json.loads(audit_files[0].read_text())
    return None


OUTREACH_PROMPT = """You are the AUROS outreach specialist. Generate personalized cold outreach messages for a potential client.

TARGET:
- Company: {company}
- Contact: {contact}
- Role: {role}
- Channel focus: {channel}

COMPANY INTELLIGENCE:
{company_intel}

AUROS BRAND VOICE RULES:
- Direct, confident, data-led
- No buzzwords without substance
- Short sentences — every word earns its place
- Reference specific findings about their marketing gaps
- Position AUROS as the solution without being salesy
- Never promise income or specific results numbers
- Sign off as AUROS team, not individual names

Generate all outreach content as valid JSON:

{{
  "company": "{company}",
  "contact": "{contact}",
  "role": "{role}",
  "generated_date": "{date}",
  "email_variations": [
    {{
      "style": "short_direct",
      "subject_line": "...",
      "body": "Full email body with personalization",
      "cta": "The specific call to action"
    }},
    {{
      "style": "value_led",
      "subject_line": "...",
      "body": "Full email body leading with value",
      "cta": "..."
    }},
    {{
      "style": "curiosity_driven",
      "subject_line": "...",
      "body": "Full email body using curiosity hooks",
      "cta": "..."
    }}
  ],
  "linkedin_dms": [
    {{
      "style": "connection_request",
      "message": "Short connection request note (300 chars max)"
    }},
    {{
      "style": "follow_up_dm",
      "message": "Follow-up DM after connecting"
    }}
  ],
  "instagram_dm": {{
    "message": "Casual but professional IG DM"
  }},
  "follow_up_sequences": {{
    "email": [
      {{
        "day": 3,
        "subject_line": "...",
        "body": "Follow-up 1"
      }},
      {{
        "day": 7,
        "subject_line": "...",
        "body": "Follow-up 2"
      }},
      {{
        "day": 14,
        "subject_line": "...",
        "body": "Follow-up 3 — breakup email"
      }}
    ],
    "linkedin": [
      {{
        "day": 3,
        "message": "LinkedIn follow-up 1"
      }},
      {{
        "day": 7,
        "message": "LinkedIn follow-up 2"
      }},
      {{
        "day": 14,
        "message": "LinkedIn follow-up 3"
      }}
    ],
    "instagram": [
      {{
        "day": 3,
        "message": "IG follow-up 1"
      }},
      {{
        "day": 7,
        "message": "IG follow-up 2"
      }},
      {{
        "day": 14,
        "message": "IG follow-up 3"
      }}
    ]
  }},
  "key_angles": ["3 specific angles used based on their marketing gaps"]
}}

Return ONLY valid JSON. Every message must reference something specific about {company}'s current marketing — never be generic. Keep emails under 150 words. DMs under 100 words."""


def _build_markdown(outreach: dict) -> str:
    """Convert outreach JSON to a readable markdown document."""
    company = outreach.get("company", "")
    contact = outreach.get("contact", "")
    role = outreach.get("role", "")
    date = outreach.get("generated_date", "")

    lines = [
        f"# AUROS Outreach — {company}",
        f"**Contact:** {contact} ({role})",
        f"**Generated:** {date}",
        "",
        "---",
        "",
        "## Key Angles",
        "",
    ]
    for angle in outreach.get("key_angles", []):
        lines.append(f"- {angle}")

    lines.extend(["", "---", "", "## Email Variations", ""])
    for email in outreach.get("email_variations", []):
        lines.append(f"### {email.get('style', '').replace('_', ' ').title()}")
        lines.append(f"**Subject:** {email.get('subject_line', '')}")
        lines.append("")
        lines.append(email.get("body", ""))
        lines.append("")
        lines.append(f"**CTA:** {email.get('cta', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend(["## LinkedIn DMs", ""])
    for dm in outreach.get("linkedin_dms", []):
        lines.append(f"### {dm.get('style', '').replace('_', ' ').title()}")
        lines.append(dm.get("message", ""))
        lines.append("")

    lines.extend(["---", "", "## Instagram DM", ""])
    ig = outreach.get("instagram_dm", {})
    lines.append(ig.get("message", ""))
    lines.append("")

    lines.extend(["---", "", "## Follow-Up Sequences", ""])
    for channel, followups in outreach.get("follow_up_sequences", {}).items():
        lines.append(f"### {channel.title()}")
        lines.append("")
        for fu in followups:
            lines.append(f"**Day {fu.get('day', '')}:**")
            if "subject_line" in fu:
                lines.append(f"Subject: {fu['subject_line']}")
            lines.append(fu.get("body", fu.get("message", "")))
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("*Generated by AUROS AI — Intelligence, Elevated.*")
    return "\n".join(lines)


def run(company: str, contact: str, role: str, channel: str) -> dict:
    """Execute the outreach generation pipeline."""
    today = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(company)
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    client_dir.mkdir(parents=True, exist_ok=True)

    print(f"[AUROS] Outreach agent starting for '{company}' — {today}")

    # Step 1: Check for existing audit
    print("[AUROS] Checking for existing audit data...")
    audit = _load_audit(slug)

    if audit:
        print("[AUROS] Found existing audit. Using audit intelligence.")
        company_intel = json.dumps(audit, indent=2)[:5000]
    else:
        # Quick Tavily research
        print("[AUROS] No audit found. Running quick research...")
        research_queries = [
            f"{company} marketing social media presence",
            f"{company} brand website digital marketing",
        ]
        research = []
        for q in research_queries:
            try:
                research.extend(_search_tavily(q, max_results=3))
            except Exception as e:
                print(f"[AUROS] Search warning: {e}")

        company_intel = json.dumps(
            [{"title": r.get("title", ""), "content": r.get("content", "")[:400]} for r in research],
            indent=2,
        )[:5000]

    # Step 2: Generate outreach via Claude
    print("[AUROS] Generating outreach content...")
    prompt = OUTREACH_PROMPT.format(
        company=company,
        contact=contact,
        role=role,
        channel=channel,
        company_intel=company_intel,
        date=today,
    )

    raw = generate(prompt, system=AUROS_SYSTEM_PROMPT, max_tokens=4096, temperature=0.6)

    # Parse JSON
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    outreach = json.loads(json_str)

    # Step 3: Save JSON
    json_path = client_dir / f"outreach_{today}.json"
    json_path.write_text(json.dumps(outreach, indent=2))
    print(f"[AUROS] Outreach JSON saved to {json_path}")

    # Step 4: Save Markdown
    md_content = _build_markdown(outreach)
    md_path = client_dir / f"outreach_{today}.md"
    md_path.write_text(md_content)
    print(f"[AUROS] Outreach markdown saved to {md_path}")

    print("[AUROS] Outreach generation complete.")
    return {"status": "complete", "json_path": str(json_path), "md_path": str(md_path), "outreach": outreach}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Outreach Agent")
    parser.add_argument("--company", required=True, help="Target company name")
    parser.add_argument("--contact", required=True, help="Contact person name")
    parser.add_argument("--role", default="Founder", help="Contact's role/title")
    parser.add_argument("--channel", default="email", help="Primary channel (email/linkedin/instagram)")
    args = parser.parse_args()
    run(company=args.company, contact=args.contact, role=args.role, channel=args.channel)
