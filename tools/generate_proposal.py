#!/usr/bin/env python3
"""
AUROS AI — Proposal Generator
Generates a branded HTML proposal from the template, optionally using audit data.

Usage:
    python tools/generate_proposal.py --company "Zukerino" --package growth
    python tools/generate_proposal.py --company "Acme Corp" --package starter --findings path/to/findings.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Ensure project root is on sys.path ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.shared.config import PROJECT_ROOT, PORTFOLIO_DIR
from agents.shared.llm import generate

# ── Package Definitions ───────────────────────────────────────────────────

PACKAGES = {
    "starter": {
        "name": "Starter",
        "price": "1,500",
        "setup_fee": "Waived",
        "deliverables": [
            "15 social media posts per month",
            "2 platform management",
            "4 SEO-optimized blog articles",
            "Content calendar",
            "Brand voice calibration",
            "Monthly performance report",
        ],
    },
    "growth": {
        "name": "Growth",
        "price": "3,000",
        "setup_fee": "Waived",
        "deliverables": [
            "25 social media posts per month",
            "3 platform management",
            "8 SEO-optimized blog articles",
            "Lead generation pipeline",
            "Email outreach sequences",
            "Strategy & marketing audit",
            "Content calendar + scheduling",
            "Weekly progress updates",
        ],
    },
    "scale": {
        "name": "Scale",
        "price": "5,500",
        "setup_fee": "Waived",
        "deliverables": [
            "25+ social media posts per month",
            "3+ platform management",
            "8 SEO-optimized blog articles",
            "Lead generation pipeline",
            "Email outreach sequences",
            "Strategy & marketing audit",
            "Content calendar + scheduling",
            "Video ad production",
            "Custom website design & build",
            "Newsletter creation & management",
            "Competitive intelligence reports",
            "AI-powered lead response system",
            "Priority support channel",
            "Dedicated weekly strategy calls",
        ],
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert company name to a filesystem-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug


def load_audit_data(client_dir: Path) -> dict | None:
    """Attempt to load the most recent marketing audit JSON from a client directory."""
    research_dir = client_dir / "01_research"
    if not research_dir.is_dir():
        return None

    # Find the most recent audit file
    audit_files = sorted(research_dir.glob("marketing_audit_*.json"), reverse=True)
    if not audit_files:
        return None

    try:
        with open(audit_files[0]) as f:
            data = json.load(f)
        print(f"  [INFO] Loaded audit data from {audit_files[0].name}")
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Could not parse audit file: {e}")
        return None


def load_findings_file(path: str) -> dict | None:
    """Load findings from a user-provided JSON file path."""
    findings_path = Path(path)
    if not findings_path.is_absolute():
        findings_path = PROJECT_ROOT / findings_path

    if not findings_path.exists():
        print(f"  [WARN] Findings file not found: {findings_path}")
        return None

    try:
        with open(findings_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Could not parse findings file: {e}")
        return None


def render_deliverables(items: list[str]) -> str:
    """Render a list of deliverable strings as <li> elements."""
    return "\n        ".join(f"<li>{item}</li>" for item in items)


# ── LLM Content Generation ───────────────────────────────────────────────

def generate_executive_summary(company: str, package_name: str, audit: dict | None) -> str:
    """Use Claude to write an executive summary tailored to the client."""
    if audit:
        context = (
            f"Audit executive summary: {audit.get('executive_summary', 'N/A')}\n"
            f"Website messaging clarity score: {audit.get('website_analysis', {}).get('messaging_clarity', {}).get('score', 'N/A')}/100\n"
            f"Website SEO score: {audit.get('website_analysis', {}).get('seo_indicators', {}).get('score', 'N/A')}/100\n"
            f"Website conversion score: {audit.get('website_analysis', {}).get('conversion_funnel', {}).get('score', 'N/A')}/100\n"
        )
        # Add social media context if available
        social = audit.get("social_media", [])
        if social:
            platforms = [s.get("platform", "Unknown") for s in social]
            context += f"Social platforms analyzed: {', '.join(platforms)}\n"
    else:
        context = "No audit data available. Write a general but compelling summary."

    prompt = f"""Write a concise executive summary (2-3 paragraphs, ~150 words total) for a marketing proposal
for {company}. We are recommending the {package_name} package.

Context:
{context}

Rules:
- Write in AUROS brand voice: direct, confident, data-driven
- Focus on the opportunity and what AUROS will deliver
- Reference specific findings if audit data is available
- No filler. Every sentence earns its place.
- Do NOT include headers, labels, or markdown formatting
- Output raw HTML paragraphs using <p> tags"""

    return generate(prompt, max_tokens=1024, temperature=0.6)


def generate_findings_from_audit(company: str, audit: dict) -> list[dict]:
    """Extract structured findings from audit data."""
    website = audit.get("website_analysis", {})

    # Map audit areas to template findings
    area_map = [
        {
            "area": "Website & SEO",
            "key_messaging": "messaging_clarity",
            "key_seo": "seo_indicators",
        },
        {
            "area": "Social Presence",
            "social_data": audit.get("social_media", []),
        },
        {
            "area": "Content Strategy",
            "key": "conversion_funnel",
        },
        {
            "area": "Lead Generation",
            "key": "conversion_funnel",
        },
    ]

    prompt = f"""Based on this marketing audit for {company}, generate exactly 4 audit findings.

Audit data:
{json.dumps(audit, indent=2, default=str)[:4000]}

Return ONLY valid JSON — an array of 4 objects, each with:
- "title": short finding title (5-8 words)
- "text": 1-2 sentence description of the finding
- "score": integer 0-100 representing current performance

The 4 findings must cover these areas IN ORDER:
1. Website & SEO
2. Social Presence
3. Content Strategy
4. Lead Generation

Be specific to {company}. Use actual data from the audit where possible.
Return raw JSON only, no markdown fences."""

    raw = generate(prompt, max_tokens=1024, temperature=0.4)

    # Parse the JSON response
    try:
        # Strip any markdown fencing if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        findings = json.loads(cleaned)
        if isinstance(findings, list) and len(findings) == 4:
            return findings
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: extract from audit data directly
    print("  [WARN] LLM findings parse failed, extracting from audit data directly")
    return _fallback_findings_from_audit(audit)


def _fallback_findings_from_audit(audit: dict) -> list[dict]:
    """Direct extraction fallback if LLM output is unparseable."""
    website = audit.get("website_analysis", {})
    social = audit.get("social_media", [])

    messaging = website.get("messaging_clarity", {})
    seo = website.get("seo_indicators", {})
    conversion = website.get("conversion_funnel", {})

    # Average social engagement score
    social_score = 40  # default
    if social:
        engagement_terms = ["poor", "low", "weak", "minimal"]
        strong_terms = ["strong", "high", "excellent", "good"]
        assessments = " ".join(s.get("engagement_assessment", "").lower() for s in social)
        if any(t in assessments for t in strong_terms):
            social_score = 65
        if any(t in assessments for t in engagement_terms):
            social_score = max(25, social_score - 20)

    return [
        {
            "title": "Website needs clearer messaging",
            "text": messaging.get("analysis", "Website messaging could be improved for clarity and conversion.")[:200],
            "score": messaging.get("score", 40),
        },
        {
            "title": "Social presence is fragmented",
            "text": "Social media presence shows inconsistent posting and engagement across platforms.",
            "score": social_score,
        },
        {
            "title": "Content strategy lacks depth",
            "text": seo.get("analysis", "Content strategy needs a structured approach with regular publishing.")[:200],
            "score": seo.get("score", 35),
        },
        {
            "title": "Lead pipeline not established",
            "text": conversion.get("analysis", "No structured lead generation funnel is in place.")[:200],
            "score": conversion.get("score", 25),
        },
    ]


def generate_findings_without_audit(company: str) -> list[dict]:
    """Generate generic but plausible findings when no audit data exists."""
    prompt = f"""Generate 4 marketing audit findings for a company called "{company}" that we haven't audited yet.
These should be common issues most businesses face, written as if we've done a preliminary review of their public presence.

Return ONLY valid JSON — an array of 4 objects, each with:
- "title": short finding title (5-8 words)
- "text": 1-2 sentence description
- "score": integer 0-100 (keep scores moderate: 30-55 range)

The 4 findings must cover these areas IN ORDER:
1. Website & SEO
2. Social Presence
3. Content Strategy
4. Lead Generation

Be specific to {company}. Return raw JSON only, no markdown fences."""

    raw = generate(prompt, max_tokens=1024, temperature=0.5)

    try:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        findings = json.loads(cleaned)
        if isinstance(findings, list) and len(findings) == 4:
            return findings
    except (json.JSONDecodeError, ValueError):
        pass

    # Hard fallback
    return [
        {"title": "Website visibility needs improvement", "text": f"{company}'s website likely underperforms on search rankings and messaging clarity, leaving revenue on the table.", "score": 40},
        {"title": "Social presence is underutilized", "text": "Most businesses in this segment post inconsistently and miss engagement opportunities across key platforms.", "score": 35},
        {"title": "Content strategy is ad-hoc", "text": "Without a structured content calendar and SEO-driven blog strategy, organic growth stalls.", "score": 30},
        {"title": "No lead generation system", "text": "Inbound and outbound lead pipelines are likely nonexistent, leaving growth dependent on referrals.", "score": 25},
    ]


# ── Template Rendering ────────────────────────────────────────────────────

def render_proposal(
    company: str,
    package_key: str,
    findings: list[dict],
    executive_summary: str,
) -> str:
    """Load the HTML template and fill in all placeholders."""
    template_path = PROJECT_ROOT / "tools" / "templates" / "proposal.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Proposal template not found at {template_path}")

    html = template_path.read_text()
    pkg = PACKAGES[package_key]

    # Build replacement map
    replacements = {
        "{{COMPANY_NAME}}": company,
        "{{DATE}}": datetime.now().strftime("%B %d, %Y"),
        "{{EXECUTIVE_SUMMARY}}": executive_summary,
        "{{PACKAGE_NAME}}": pkg["name"],
        "{{PACKAGE_PRICE}}": pkg["price"],
        "{{SETUP_FEE}}": pkg["setup_fee"],
        "{{DELIVERABLES}}": render_deliverables(pkg["deliverables"]),
    }

    # Findings
    for i, finding in enumerate(findings[:4], start=1):
        replacements[f"{{{{FINDING_{i}_TITLE}}}}"] = finding.get("title", "Under Review")
        replacements[f"{{{{FINDING_{i}_TEXT}}}}"] = finding.get("text", "Detailed analysis pending.")
        replacements[f"{{{{FINDING_{i}_SCORE}}}}"] = str(finding.get("score", 40))

    # Apply all replacements
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # Warn about any remaining placeholders
    remaining = re.findall(r"\{\{[A-Z_0-9]+\}\}", html)
    if remaining:
        print(f"  [WARN] Unfilled placeholders: {remaining}")

    return html


# ── PDF Export ────────────────────────────────────────────────────────────

async def export_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Export the rendered HTML to PDF using Playwright if available."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("  [INFO] Playwright not installed — skipping PDF export.")
        print("         Install with: pip install playwright && playwright install chromium")
        return False

    print("  [PDF] Launching Playwright...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1400, "height": 900})

            file_url = f"file://{html_path}"
            await page.goto(file_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)  # Wait for fonts

            await page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )

            await browser.close()

        pdf_size_kb = pdf_path.stat().st_size / 1024
        print(f"  [PDF] Exported: {pdf_path.name} ({pdf_size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  [PDF] Export failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AUROS AI — Generate a branded marketing proposal"
    )
    parser.add_argument(
        "--company",
        required=True,
        help="Client company name (e.g., 'Zukerino')",
    )
    parser.add_argument(
        "--package",
        choices=["starter", "growth", "scale"],
        default="growth",
        help="Package tier (default: growth)",
    )
    parser.add_argument(
        "--findings",
        default=None,
        help="Optional path to a JSON file with pre-computed audit findings",
    )

    args = parser.parse_args()

    company = args.company
    package_key = args.package
    slug = slugify(company)

    print(f"\n{'='*60}")
    print(f"  AUROS AI — Proposal Generator")
    print(f"  Company:  {company}")
    print(f"  Package:  {PACKAGES[package_key]['name']} (${PACKAGES[package_key]['price']}/mo)")
    print(f"  Slug:     {slug}")
    print(f"{'='*60}\n")

    # ── Step 1: Resolve audit/findings data ────────────────────────────
    audit_data = None
    findings_data = None

    # Check for explicit findings file first
    if args.findings:
        print("[1/5] Loading findings from provided file...")
        findings_data = load_findings_file(args.findings)
        if findings_data:
            # If the file is a full audit, treat it as audit data
            if "website_analysis" in findings_data:
                audit_data = findings_data
                findings_data = None
            # If it's a list of findings, use directly
            elif isinstance(findings_data, list):
                pass
            # If it has a "findings" key, extract it
            elif "findings" in findings_data:
                findings_data = findings_data["findings"]
            else:
                audit_data = findings_data
                findings_data = None

    # Try loading from portfolio directory
    if not audit_data and not findings_data:
        print("[1/5] Searching for existing audit data...")
        client_dir = PORTFOLIO_DIR / f"client_{slug}"
        if client_dir.is_dir():
            audit_data = load_audit_data(client_dir)
        else:
            print(f"  [INFO] No client directory found at client_{slug}")

    # ── Step 2: Generate findings ──────────────────────────────────────
    if findings_data and isinstance(findings_data, list) and len(findings_data) >= 4:
        print("[2/5] Using provided findings...")
        findings = findings_data[:4]
    elif audit_data:
        print("[2/5] Generating findings from audit data (Claude API)...")
        findings = generate_findings_from_audit(company, audit_data)
    else:
        print("[2/5] No audit data found — generating preliminary findings (Claude API)...")
        findings = generate_findings_without_audit(company)

    for i, f in enumerate(findings, 1):
        print(f"  Finding {i}: {f['title']} (score: {f['score']})")

    # ── Step 3: Generate executive summary ─────────────────────────────
    print("[3/5] Generating executive summary (Claude API)...")
    executive_summary = generate_executive_summary(company, PACKAGES[package_key]["name"], audit_data)
    print(f"  Summary generated ({len(executive_summary)} chars)")

    # ── Step 4: Render template ────────────────────────────────────────
    print("[4/5] Rendering proposal template...")
    html = render_proposal(company, package_key, findings, executive_summary)

    # Ensure output directory exists
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    deliverables_dir = client_dir / "04_deliverables"
    deliverables_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"proposal_{slug}.html"
    output_path = deliverables_dir / output_filename
    output_path.write_text(html)

    html_size_kb = output_path.stat().st_size / 1024
    print(f"  HTML saved: {output_path} ({html_size_kb:.0f} KB)")

    # ── Step 5: PDF export ─────────────────────────────────────────────
    print("[5/5] Attempting PDF export...")
    pdf_path = deliverables_dir / f"proposal_{slug}.pdf"
    asyncio.run(export_to_pdf(output_path, pdf_path))

    # ── Done ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Proposal generated successfully!")
    print(f"  HTML: {output_path}")
    if pdf_path.exists():
        print(f"  PDF:  {pdf_path}")
    print(f"{'='*60}\n")

    return str(output_path)


if __name__ == "__main__":
    main()
