#!/usr/bin/env python3
"""
AUROS AI — Daily Newsletter Agent
Researches AI + Marketing news and delivers a branded morning briefing.

Usage:
    python -m agents.newsletter.newsletter_agent          # run once
    python -m agents.newsletter.newsletter_agent --dry-run # preview without sending
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import NEWSLETTER_DIR, LOGS_DIR
from agents.shared.llm import generate
from agents.newsletter.research import research_ai_marketing_news
from agents.newsletter.formatter import render_newsletter, render_markdown
from agents.newsletter.sender import send_newsletter


NEWSLETTER_PROMPT = """You are the editor of the AUROS daily AI Marketing Intelligence newsletter.

Given the following research results about AI and marketing news from the last 48 hours, create a newsletter with:

1. **Subject line**: Compelling, under 60 characters, no clickbait. Lead with the most impactful news.
2. **Intro**: 2-3 sentences setting the scene for today's intelligence. Direct, no fluff.
3. **3-5 news items**: Each with:
   - headline (bold, concise)
   - summary (2-3 sentences with AUROS commentary — what this means for marketers)
   - source (publication name)
   - url (from the research)
4. **Tool of the Day**: One AI tool relevant to marketers, with name, description (2-3 sentences on what it does and why it matters), and url.
5. **Actionable tip**: One specific thing a marketer can do today based on these trends. Be concrete.

Voice: Direct. Knowledgeable. No buzzwords without proof. Short sentences. Lead with numbers when possible.

Return your response as valid JSON with this exact structure:
{{
  "subject": "...",
  "intro": "...",
  "news_items": [
    {{"headline": "...", "summary": "...", "source": "...", "url": "..."}}
  ],
  "tool_of_the_day": {{"name": "...", "description": "...", "url": "..."}},
  "actionable_tip": "..."
}}

Here are today's research results:
{research_data}
"""


def run(dry_run: bool = False) -> dict:
    """Execute the full newsletter pipeline."""
    today = datetime.now().strftime("%B %d, %Y")
    print(f"[AUROS] Newsletter agent starting — {today}")

    # Step 1: Research
    print("[AUROS] Researching AI marketing news...")
    results = research_ai_marketing_news()
    print(f"[AUROS] Found {len(results)} relevant articles")

    if not results:
        print("[AUROS] No research results found. Skipping newsletter.")
        return {"status": "skipped", "reason": "no_results"}

    # Step 2: Generate newsletter content via Claude
    print("[AUROS] Generating newsletter content...")
    research_text = json.dumps(results, indent=2)
    prompt = NEWSLETTER_PROMPT.format(research_data=research_text)

    raw_response = generate(prompt, temperature=0.6)

    # Parse JSON from response (handle markdown code blocks)
    json_str = raw_response.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    newsletter_data = json.loads(json_str)
    newsletter_data["date"] = today

    # Step 3: Render HTML and Markdown
    print("[AUROS] Rendering newsletter...")
    html_content = render_newsletter(newsletter_data)
    md_content = render_markdown(newsletter_data)

    # Step 4: Archive
    archive_dir = NEWSLETTER_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    date_slug = datetime.now().strftime("%Y-%m-%d")

    html_path = archive_dir / f"{date_slug}.html"
    md_path = archive_dir / f"{date_slug}.md"
    html_path.write_text(html_content)
    md_path.write_text(md_content)
    print(f"[AUROS] Archived to {html_path}")

    # Step 5: Send
    if dry_run:
        print("[AUROS] DRY RUN — newsletter not sent. Preview saved to archive.")
        return {"status": "dry_run", "archive": str(html_path), "data": newsletter_data}

    print("[AUROS] Sending newsletter...")
    send_result = send_newsletter(
        subject=f"AUROS Intelligence — {newsletter_data['subject']}",
        html_content=html_content,
    )

    # Log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "date": date_slug,
        "subject": newsletter_data["subject"],
        "articles": len(newsletter_data.get("news_items", [])),
        "send_status": send_result.get("status"),
    }
    log_path = LOGS_DIR / "newsletter.log"
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"[AUROS] Newsletter complete — {send_result.get('status')}")
    return {"status": "complete", "send": send_result, "data": newsletter_data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Daily Newsletter Agent")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
