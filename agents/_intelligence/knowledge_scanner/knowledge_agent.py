#!/usr/bin/env python3
"""
AUROS AI — Agent 12: Marketing Knowledge & Skills Scanner
Self-improving agent that:
1. Scans for Claude Code skills, MCP servers, and AI tools to enhance our capabilities
2. Builds a comprehensive marketing knowledge base (frameworks, tactics, psychology)
3. Keeps the entire agent network updated with the latest marketing intelligence

Usage:
    python -m agents.knowledge_scanner.knowledge_agent --mode "skills"     # Find new tools/skills
    python -m agents.knowledge_scanner.knowledge_agent --mode "knowledge"  # Build marketing knowledge base
    python -m agents.knowledge_scanner.knowledge_agent --mode "full"       # Both
"""

from __future__ import annotations

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PROJECT_ROOT, LOGS_DIR
from agents.shared.llm import generate
from tavily import TavilyClient
from agents.shared.config import TAVILY_API_KEY

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"


# ─── SKILLS & TOOLS SCANNER ───

SKILLS_QUERIES = [
    "Claude Code custom skills marketing automation",
    "MCP server marketing social media tools",
    "Claude Code skills content creation",
    "AI marketing automation tools API 2026",
    "Claude AI agent marketing workflows",
    "MCP servers image generation video editing",
    "Claude Code hooks automation workflows",
    "AI tools social media scheduling API",
    "generative AI marketing stack tools",
    "Claude agent SDK marketing applications",
]

SKILLS_ANALYSIS_PROMPT = """You are the AUROS technology scout. Analyze the following research about AI tools, Claude Code skills, and MCP servers that could enhance an AI marketing agency's capabilities.

For each tool/skill found, evaluate:
- **Relevance**: How useful is this for AI-powered marketing content creation?
- **Integration effort**: How hard is it to integrate with our Python agent stack?
- **Cost**: Free, freemium, or paid?
- **Priority**: Must-have, nice-to-have, or future consideration?

Return as valid JSON:
{{
  "scan_date": "...",
  "tools_found": [
    {{
      "name": "...",
      "type": "claude_skill/mcp_server/api/tool",
      "description": "...",
      "marketing_use_case": "...",
      "integration_effort": "low/medium/high",
      "cost": "free/freemium/paid",
      "priority": "must-have/nice-to-have/future",
      "url": "...",
      "how_to_integrate": "..."
    }}
  ],
  "recommended_stack_additions": [
    {{
      "tool": "...",
      "reason": "...",
      "expected_impact": "..."
    }}
  ],
  "gaps_identified": ["Areas where we still need better tools"]
}}

RESEARCH DATA:
{research_data}
"""


# ─── MARKETING KNOWLEDGE BASE ───

KNOWLEDGE_CATEGORIES = {
    "copywriting": [
        "best copywriting frameworks formulas marketing",
        "AIDA PAS BAB copywriting frameworks examples",
        "direct response copywriting techniques proven",
        "social media copywriting hooks engagement",
        "email marketing copy best practices conversion",
    ],
    "psychology": [
        "marketing psychology principles consumer behavior",
        "persuasion techniques advertising Robert Cialdini",
        "color psychology branding marketing",
        "cognitive biases marketing advertising",
        "emotional triggers advertising conversion",
    ],
    "social_media": [
        "Instagram algorithm 2026 how it works",
        "TikTok algorithm ranking factors 2026",
        "LinkedIn algorithm content visibility 2026",
        "YouTube algorithm watch time optimization",
        "social media engagement rate benchmarks by industry",
    ],
    "video_marketing": [
        "short form video marketing best practices hooks",
        "video ad structure framework proven",
        "video content retention techniques",
        "UGC video marketing strategy brands",
        "AI video generation marketing workflow",
    ],
    "paid_media": [
        "Meta ads best practices 2026 targeting",
        "Google ads performance max campaigns",
        "TikTok ads creative best practices",
        "LinkedIn ads B2B targeting strategies",
        "retargeting strategy funnel marketing",
    ],
    "analytics": [
        "marketing analytics KPIs metrics tracking",
        "attribution modeling marketing channels",
        "A/B testing marketing campaigns methodology",
        "customer lifetime value calculation marketing",
        "marketing ROI measurement frameworks",
    ],
    "branding": [
        "brand positioning strategy framework",
        "brand voice development guidelines",
        "visual identity design principles",
        "brand storytelling techniques",
        "brand differentiation competitive strategy",
    ],
    "content_strategy": [
        "content marketing strategy framework 2026",
        "content pillar strategy social media",
        "content repurposing workflow efficiency",
        "SEO content strategy keyword planning",
        "content calendar planning best practices",
    ],
}

KNOWLEDGE_PROMPT = """You are the AUROS master marketing educator. Compile the most comprehensive, actionable marketing knowledge base entry for the category: {category}.

This knowledge base will be used by AI agents to produce world-class marketing content. Every piece of information must be:
- Specific and actionable (not vague advice)
- Data-backed where possible
- Immediately applicable to content creation

Return as valid JSON:
{{
  "category": "{category}",
  "last_updated": "...",
  "frameworks": [
    {{
      "name": "...",
      "description": "...",
      "when_to_use": "...",
      "steps": ["..."],
      "example": "..."
    }}
  ],
  "key_principles": [
    {{
      "principle": "...",
      "explanation": "...",
      "application": "How to apply this in marketing content"
    }}
  ],
  "tactics": [
    {{
      "tactic": "...",
      "platform": "all/instagram/tiktok/linkedin/etc",
      "description": "...",
      "expected_result": "..."
    }}
  ],
  "benchmarks": [
    {{
      "metric": "...",
      "industry_average": "...",
      "top_performer": "...",
      "source": "..."
    }}
  ],
  "templates": [
    {{
      "name": "...",
      "template": "A fill-in-the-blank template that agents can use",
      "use_case": "..."
    }}
  ],
  "common_mistakes": ["..."],
  "pro_tips": ["Advanced tips that separate good from great"]
}}

RESEARCH DATA:
{research_data}
"""


def scan_skills() -> dict:
    """Scan for new tools, skills, and MCP servers for marketing."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    all_results = []
    seen = set()

    print("[AUROS] Scanning for marketing tools and skills...")
    for query in SKILLS_QUERIES:
        try:
            response = client.search(query=query, search_depth="advanced", max_results=5, days=30)
            for r in response.get("results", []):
                url = r.get("url", "")
                if url not in seen:
                    seen.add(url)
                    all_results.append({
                        "title": r.get("title", ""),
                        "content": r.get("content", "")[:600],
                        "url": url,
                    })
        except Exception as e:
            print(f"[AUROS] Skills scan query failed: {query} — {e}")

    print(f"[AUROS] Found {len(all_results)} potential tools/skills")

    # Analyze with Claude
    prompt = SKILLS_ANALYSIS_PROMPT.format(research_data=json.dumps(all_results, indent=2)[:10000])
    raw = generate(prompt, temperature=0.3, max_tokens=4096)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    analysis = json.loads(json_str)

    # Save
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    path = KNOWLEDGE_DIR / f"skills_scan_{today}.json"
    path.write_text(json.dumps(analysis, indent=2))
    print(f"[AUROS] Skills scan saved to {path}")

    # Print highlights
    must_haves = [t for t in analysis.get("tools_found", []) if t.get("priority") == "must-have"]
    if must_haves:
        print(f"[AUROS] Found {len(must_haves)} must-have tools:")
        for t in must_haves:
            print(f"  → {t['name']}: {t['marketing_use_case']}")

    return analysis


def build_knowledge_base(categories: list[str] | None = None) -> dict:
    """Build comprehensive marketing knowledge base."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    target_categories = categories or list(KNOWLEDGE_CATEGORIES.keys())
    results = {}

    for category in target_categories:
        queries = KNOWLEDGE_CATEGORIES.get(category, [])
        if not queries:
            continue

        print(f"[AUROS] Building knowledge: {category}...")
        research = []
        for query in queries:
            try:
                response = client.search(query=query, search_depth="advanced", max_results=5, days=90)
                for r in response.get("results", []):
                    research.append({
                        "title": r.get("title", ""),
                        "content": r.get("content", "")[:800],
                        "url": r.get("url", ""),
                    })
            except Exception as e:
                print(f"[AUROS] Knowledge query failed: {query} — {e}")

        # Generate knowledge base entry
        prompt = KNOWLEDGE_PROMPT.format(
            category=category,
            research_data=json.dumps(research, indent=2)[:10000],
        )
        raw = generate(prompt, temperature=0.3, max_tokens=6000)

        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1]
            json_str = json_str.rsplit("```", 1)[0]

        kb_entry = json.loads(json_str)
        results[category] = kb_entry

        # Save individual category
        cat_path = KNOWLEDGE_DIR / f"kb_{category}.json"
        cat_path.write_text(json.dumps(kb_entry, indent=2))
        print(f"[AUROS] Knowledge base entry saved: {category} ({len(kb_entry.get('frameworks', []))} frameworks, {len(kb_entry.get('tactics', []))} tactics)")

    # Save master index
    index = {
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "categories": list(results.keys()),
        "total_frameworks": sum(len(v.get("frameworks", [])) for v in results.values()),
        "total_tactics": sum(len(v.get("tactics", [])) for v in results.values()),
        "total_templates": sum(len(v.get("templates", [])) for v in results.values()),
    }
    index_path = KNOWLEDGE_DIR / "kb_index.json"
    index_path.write_text(json.dumps(index, indent=2))

    print(f"[AUROS] Knowledge base complete — {index['total_frameworks']} frameworks, {index['total_tactics']} tactics, {index['total_templates']} templates")
    return results


def run(mode: str = "full", categories: list[str] | None = None) -> dict:
    """Run the knowledge scanner."""
    print(f"[AUROS] Knowledge Scanner starting — Mode: {mode}")
    result = {}

    if mode in ("skills", "full"):
        result["skills"] = scan_skills()

    if mode in ("knowledge", "full"):
        result["knowledge"] = build_knowledge_base(categories)

    print("[AUROS] Knowledge Scanner complete")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Marketing Knowledge & Skills Scanner")
    parser.add_argument("--mode", default="full", choices=["skills", "knowledge", "full"])
    parser.add_argument("--categories", nargs="+", help="Specific knowledge categories to build")
    args = parser.parse_args()
    run(mode=args.mode, categories=args.categories)
