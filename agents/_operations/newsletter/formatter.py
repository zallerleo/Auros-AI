"""
AUROS AI — Newsletter Formatter
Renders newsletter content into AUROS-branded HTML email using Jinja2.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_newsletter(newsletter_data: dict) -> str:
    """
    Render newsletter data into AUROS-branded HTML.

    newsletter_data should contain:
    - subject: str
    - intro: str
    - news_items: list of {headline, summary, source, url}
    - tool_of_the_day: {name, description, url}
    - actionable_tip: str
    - date: str
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("email.html")
    return template.render(**newsletter_data)


def render_markdown(newsletter_data: dict) -> str:
    """Render newsletter as markdown for archiving and blog repurposing."""
    lines = [
        f"# AUROS AI Marketing Intelligence — {newsletter_data['date']}",
        "",
        f"*{newsletter_data['intro']}*",
        "",
        "---",
        "",
    ]

    for i, item in enumerate(newsletter_data.get("news_items", []), 1):
        lines.append(f"## {i}. {item['headline']}")
        lines.append("")
        lines.append(item["summary"])
        lines.append(f"\n*Source: [{item['source']}]({item['url']})*")
        lines.append("")

    tool = newsletter_data.get("tool_of_the_day", {})
    if tool:
        lines.append("---")
        lines.append("")
        lines.append(f"## Tool of the Day: {tool['name']}")
        lines.append("")
        lines.append(tool["description"])
        if tool.get("url"):
            lines.append(f"\n[Check it out]({tool['url']})")
        lines.append("")

    tip = newsletter_data.get("actionable_tip", "")
    if tip:
        lines.append("---")
        lines.append("")
        lines.append("## Actionable Tip")
        lines.append("")
        lines.append(tip)
        lines.append("")

    lines.append("---")
    lines.append("*AUROS — Intelligence, Elevated.*")

    return "\n".join(lines)
