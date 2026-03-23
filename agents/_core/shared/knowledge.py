"""
AUROS AI — Knowledge Base Loader
Loads marketing knowledge base entries for agent enrichment.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.shared.config import PROJECT_ROOT

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"


def load_category(category: str) -> dict:
    """Load a single knowledge base category."""
    path = KNOWLEDGE_DIR / f"kb_{category}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def load_all() -> dict[str, dict]:
    """Load all knowledge base categories."""
    categories = [
        "copywriting", "psychology", "social_media", "video_marketing",
        "paid_media", "analytics", "branding", "content_strategy",
    ]
    return {cat: load_category(cat) for cat in categories if load_category(cat)}


def get_frameworks_summary(categories: list[str] | None = None) -> str:
    """Get a condensed summary of frameworks for prompt injection."""
    target = categories or [
        "copywriting", "psychology", "social_media", "video_marketing",
        "paid_media", "analytics", "branding", "content_strategy",
    ]
    lines = []
    for cat in target:
        data = load_category(cat)
        if not data:
            continue
        frameworks = data.get("frameworks", [])
        tactics = data.get("tactics", [])
        templates = data.get("templates", [])
        lines.append(f"\n### {cat.replace('_', ' ').title()}")
        for fw in frameworks[:3]:
            name = fw.get("name", "")
            desc = fw.get("description", "")[:120]
            when = fw.get("when_to_use", "")[:80]
            lines.append(f"- **{name}**: {desc} | Use when: {when}")
        for tac in tactics[:2]:
            lines.append(f"- Tactic: {tac.get('tactic', '')} ({tac.get('platform', 'all')}): {tac.get('description', '')[:100]}")
        for tmpl in templates[:1]:
            lines.append(f"- Template: {tmpl.get('name', '')}: {tmpl.get('template', '')[:120]}")
    return "\n".join(lines)


def get_benchmarks(categories: list[str] | None = None) -> str:
    """Get industry benchmarks for analysis."""
    target = categories or ["social_media", "paid_media", "analytics"]
    lines = []
    for cat in target:
        data = load_category(cat)
        if not data:
            continue
        benchmarks = data.get("benchmarks", [])
        if benchmarks:
            lines.append(f"\n### {cat.replace('_', ' ').title()} Benchmarks")
            for b in benchmarks[:3]:
                lines.append(f"- {b.get('metric', '')}: avg {b.get('industry_average', '')} | top {b.get('top_performer', '')}")
    return "\n".join(lines)


def get_audit_knowledge() -> str:
    """Get knowledge relevant for marketing audits."""
    parts = [
        "## MARKETING INTELLIGENCE (use this to enrich your analysis)\n",
        get_benchmarks(["social_media", "paid_media", "analytics"]),
        get_frameworks_summary(["analytics", "social_media"]),
    ]
    return "\n".join(parts)


def get_plan_knowledge() -> str:
    """Get knowledge relevant for marketing plan building."""
    parts = [
        "## MARKETING INTELLIGENCE (use these frameworks and tactics in your plan)\n",
        get_frameworks_summary([
            "content_strategy", "copywriting", "social_media",
            "video_marketing", "paid_media", "branding",
        ]),
        get_benchmarks(["social_media", "paid_media", "analytics"]),
    ]
    return "\n".join(parts)


def get_proposal_knowledge() -> str:
    """Get knowledge relevant for proposal generation."""
    parts = [
        "## MARKETING INTELLIGENCE (reference these to demonstrate expertise)\n",
        get_frameworks_summary([
            "copywriting", "psychology", "content_strategy",
            "video_marketing", "paid_media",
        ]),
        get_benchmarks(),
    ]
    return "\n".join(parts)
