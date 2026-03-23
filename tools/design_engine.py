#!/usr/bin/env python3
"""
AUROS AI — Design Engine
Orchestrates Canva (via MCP) + fal.ai image generation to produce
client-ready marketing visuals: social posts, stories, ads, carousels.

This module is meant to be called by other agents/tools, not Canva MCP directly.
It provides the bridge between AUROS content generation and visual output.

Usage:
    python tools/design_engine.py --company "Zukerino" --type social_feed --topic "Grand opening weekend"
    python tools/design_engine.py --company "The Imagine Team" --type story --topic "Harry Potter exhibition"
    python tools/design_engine.py --type hero --topic "AI marketing agency" --generate-image
"""

from __future__ import annotations

import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.shared.config import PROJECT_ROOT as ROOT, PORTFOLIO_DIR
from agents.shared.llm import generate

logger = logging.getLogger("auros.design_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


# ─── Design Types & Specs ───────────────────────────────────────────────────

DESIGN_SPECS = {
    "social_feed": {
        "canva_type": "instagram_post",
        "size": "1080x1080",
        "fal_style": "social_feed",
        "description": "Square Instagram/Facebook feed post",
    },
    "social_story": {
        "canva_type": "your_story",
        "size": "1080x1920",
        "fal_style": "social_story",
        "description": "Vertical Instagram/Facebook story",
    },
    "facebook_post": {
        "canva_type": "facebook_post",
        "size": "1200x630",
        "fal_style": "ad_landscape",
        "description": "Facebook feed post",
    },
    "twitter_post": {
        "canva_type": "twitter_post",
        "size": "1200x675",
        "fal_style": "ad_landscape",
        "description": "Twitter/X post",
    },
    "ad_portrait": {
        "canva_type": "instagram_post",
        "size": "1080x1350",
        "fal_style": "ad_portrait",
        "description": "Portrait ad (4:5 ratio)",
    },
    "hero": {
        "canva_type": "facebook_cover",
        "size": "1920x1080",
        "fal_style": "hero",
        "description": "Hero/banner image (16:9)",
    },
    "flyer": {
        "canva_type": "flyer",
        "size": "1080x1520",
        "fal_style": "product",
        "description": "Promotional flyer",
    },
    "poster": {
        "canva_type": "poster",
        "size": "1080x1520",
        "fal_style": "hero",
        "description": "Event or promotional poster",
    },
}


# ─── Canva Design Prompt Builder ────────────────────────────────────────────

def build_canva_prompt(
    topic: str,
    design_type: str,
    company_name: str = "",
    brand_colors: dict | None = None,
    tone: str = "",
    extra_context: str = "",
) -> str:
    """Build a detailed Canva generation prompt from inputs."""
    spec = DESIGN_SPECS.get(design_type, DESIGN_SPECS["social_feed"])

    parts = [f"Create a {spec['description']} about: {topic}."]

    if company_name:
        parts.append(f"Brand: {company_name}.")

    if brand_colors:
        color_str = ", ".join(f"{k}: {v}" for k, v in brand_colors.items() if v)
        if color_str:
            parts.append(f"Use these brand colors: {color_str}.")

    if tone:
        parts.append(f"Tone and feel: {tone}.")

    parts.append("Style: modern, professional, high-end. Clean layout with strong visual hierarchy.")
    parts.append("Make text large and readable. Use bold headlines.")

    if extra_context:
        parts.append(extra_context)

    return " ".join(parts)


# ─── Content Brief Generator ────────────────────────────────────────────────

def generate_design_brief(
    topic: str,
    design_type: str,
    company_name: str = "",
    industry: str = "",
    tone: str = "",
) -> dict:
    """Use Claude to generate a creative brief for the design."""
    spec = DESIGN_SPECS.get(design_type, DESIGN_SPECS["social_feed"])

    prompt = f"""You are a creative director at a premium marketing agency.
Generate a design brief for a {spec['description']} about: {topic}

Company: {company_name or 'Not specified'}
Industry: {industry or 'Not specified'}
Tone: {tone or 'Professional, modern'}

Return a JSON object with these fields:
- "headline": Primary text (max 8 words, impactful)
- "subheadline": Supporting text (max 15 words)
- "cta": Call to action text (max 4 words)
- "image_prompt": Description for AI image generation (detailed, visual, no text in image)
- "color_mood": Suggested color mood (e.g., "warm gold and dark", "vibrant blue and white")
- "layout_notes": Brief layout suggestion

Return ONLY valid JSON, no markdown."""

    raw = generate(prompt, temperature=0.7, max_tokens=500)

    try:
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        return {
            "headline": topic[:40],
            "subheadline": f"by {company_name}" if company_name else "",
            "cta": "Learn More",
            "image_prompt": topic,
            "color_mood": "professional dark with gold accents",
            "layout_notes": "Clean, centered layout",
        }


# ─── Image Generation Bridge ────────────────────────────────────────────────

def generate_background_image(
    prompt: str,
    design_type: str,
    output_dir: Path | None = None,
) -> str | None:
    """Generate a background image using fal.ai. Returns file path or None."""
    try:
        from tools.image_generator import generate_image

        spec = DESIGN_SPECS.get(design_type, DESIGN_SPECS["social_feed"])
        style = spec.get("fal_style", "social_feed")

        if output_dir is None:
            output_dir = PORTFOLIO_DIR / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(output_dir / f"{design_type}_{timestamp}.png")

        result = generate_image(
            prompt=prompt,
            style=style,
            output_path=output_path,
        )
        logger.info(f"Generated image: {result}")
        return result
    except ImportError:
        logger.warning("image_generator not available, skipping image generation")
        return None
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return None


# ─── HTML Social Post Renderer ──────────────────────────────────────────────

def render_html_post(
    headline: str,
    subheadline: str = "",
    cta: str = "",
    background_image: str | None = None,
    brand_colors: dict | None = None,
    design_type: str = "social_feed",
    output_path: str | None = None,
) -> str:
    """Render an HTML social post that can be screenshot via Playwright."""
    spec = DESIGN_SPECS.get(design_type, DESIGN_SPECS["social_feed"])
    width, height = spec["size"].split("x")

    primary = (brand_colors or {}).get("primary", "#c9a84c")
    secondary = (brand_colors or {}).get("secondary", "#08080c")
    accent = (brand_colors or {}).get("accent", "#f0ece4")

    bg_style = ""
    if background_image:
        import base64
        try:
            with open(background_image, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = Path(background_image).suffix.lstrip(".")
            bg_style = f"background-image: linear-gradient(rgba(0,0,0,0.45), rgba(0,0,0,0.65)), url('data:image/{ext};base64,{b64}'); background-size: cover; background-position: center;"
        except Exception:
            bg_style = f"background: linear-gradient(135deg, {secondary} 0%, #1a1a2e 100%);"
    else:
        bg_style = f"background: linear-gradient(135deg, {secondary} 0%, #1a1a2e 100%);"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: {width}px; height: {height}px; overflow: hidden; font-family: 'Outfit', sans-serif; }}
.card {{
  width: {width}px; height: {height}px;
  {bg_style}
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: {int(int(width)*0.06)}px;
  position: relative;
}}
.headline {{
  font-size: {int(int(width)*0.065)}px;
  font-weight: 700;
  color: {accent};
  line-height: 1.1;
  margin-bottom: {int(int(width)*0.02)}px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.5);
}}
.subheadline {{
  font-size: {int(int(width)*0.032)}px;
  font-weight: 300;
  color: rgba(255,255,255,0.85);
  margin-bottom: {int(int(width)*0.04)}px;
  text-shadow: 0 1px 10px rgba(0,0,0,0.5);
}}
.cta {{
  display: inline-block;
  font-size: {int(int(width)*0.026)}px;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: {secondary};
  background: {primary};
  padding: {int(int(width)*0.015)}px {int(int(width)*0.04)}px;
  align-self: flex-start;
}}
.brand {{
  position: absolute;
  top: {int(int(width)*0.04)}px;
  right: {int(int(width)*0.04)}px;
  font-size: {int(int(width)*0.02)}px;
  font-weight: 500;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: {primary};
  opacity: 0.8;
}}
</style></head>
<body>
<div class="card">
  <div class="brand">AUROS</div>
  <div class="headline">{headline}</div>
  {"<div class='subheadline'>" + subheadline + "</div>" if subheadline else ""}
  {"<div class='cta'>" + cta + "</div>" if cta else ""}
</div>
</body></html>"""

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PORTFOLIO_DIR / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"post_{design_type}_{timestamp}.html")

    Path(output_path).write_text(html)
    logger.info(f"HTML post saved: {output_path}")
    return output_path


def screenshot_html(html_path: str, output_png: str | None = None) -> str | None:
    """Screenshot an HTML file to PNG using Playwright."""
    try:
        from playwright.sync_api import sync_playwright

        if output_png is None:
            output_png = html_path.replace(".html", ".png")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{Path(html_path).resolve()}")
            page.wait_for_load_state("networkidle")

            # Get the card dimensions
            card = page.query_selector(".card")
            if card:
                box = card.bounding_box()
                page.screenshot(
                    path=output_png,
                    clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]},
                )
            else:
                page.screenshot(path=output_png, full_page=True)

            browser.close()

        logger.info(f"Screenshot saved: {output_png}")
        return output_png
    except ImportError:
        logger.warning("Playwright not available for screenshots")
        return None
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return None


# ─── Main Orchestrator ──────────────────────────────────────────────────────

def create_design(
    topic: str,
    design_type: str = "social_feed",
    company: str = "",
    generate_image: bool = False,
    output_dir: str | None = None,
) -> dict:
    """
    Full design pipeline: brief → image (optional) → HTML render → screenshot.

    Returns dict with paths to generated files.
    """
    result = {"topic": topic, "design_type": design_type, "files": {}}

    # Load client config if company provided
    brand_colors = None
    industry = ""
    tone = ""
    if company:
        try:
            from agents.shared.client_config import load_client_config
            config = load_client_config(company)
            industry = config.get("industry", "")
            tone = config.get("default_tone", "")
            # Use first product's colors as default, or company-level if exists
            products = config.get("products", [])
            if products:
                brand_colors = products[0].get("brand_colors", {})
        except Exception:
            pass

    out = Path(output_dir) if output_dir else PORTFOLIO_DIR / "generated"
    out.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate creative brief
    logger.info(f"Generating design brief for: {topic}")
    brief = generate_design_brief(topic, design_type, company, industry, tone)
    result["brief"] = brief

    brief_path = str(out / f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    Path(brief_path).write_text(json.dumps(brief, indent=2))
    result["files"]["brief"] = brief_path

    # Step 2: Generate background image (optional)
    bg_image = None
    if generate_image:
        logger.info("Generating background image via fal.ai...")
        image_prompt = brief.get("image_prompt", topic)
        bg_image = generate_background_image(image_prompt, design_type, out)
        if bg_image:
            result["files"]["background_image"] = bg_image

    # Step 3: Render HTML post
    logger.info("Rendering HTML design...")
    html_path = render_html_post(
        headline=brief.get("headline", topic),
        subheadline=brief.get("subheadline", ""),
        cta=brief.get("cta", ""),
        background_image=bg_image,
        brand_colors=brand_colors,
        design_type=design_type,
        output_path=str(out / f"design_{design_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"),
    )
    result["files"]["html"] = html_path

    # Step 4: Screenshot to PNG
    png_path = screenshot_html(html_path)
    if png_path:
        result["files"]["png"] = png_path

    # Step 5: Build Canva prompt for MCP generation
    canva_prompt = build_canva_prompt(
        topic=topic,
        design_type=design_type,
        company_name=company,
        brand_colors=brand_colors,
        tone=tone,
        extra_context=f"Headline: {brief.get('headline', '')}. Subtext: {brief.get('subheadline', '')}. CTA: {brief.get('cta', '')}",
    )
    result["canva_prompt"] = canva_prompt
    result["canva_type"] = DESIGN_SPECS.get(design_type, {}).get("canva_type", "instagram_post")

    logger.info(f"Design pipeline complete. Files: {list(result['files'].keys())}")
    return result


# ─── Batch Design Generator ────────────────────────────────────────────────

def batch_designs(
    topics: list[str],
    design_type: str = "social_feed",
    company: str = "",
    generate_images: bool = False,
) -> list[dict]:
    """Generate multiple designs from a list of topics."""
    results = []
    for i, topic in enumerate(topics, 1):
        logger.info(f"[{i}/{len(topics)}] Creating design: {topic}")
        try:
            result = create_design(
                topic=topic,
                design_type=design_type,
                company=company,
                generate_image=generate_images,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to create design for '{topic}': {e}")
            results.append({"topic": topic, "error": str(e)})
    return results


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AUROS AI Design Engine")
    parser.add_argument("--topic", required=True, help="Design topic/description")
    parser.add_argument("--type", default="social_feed", choices=list(DESIGN_SPECS.keys()),
                        help="Design type (default: social_feed)")
    parser.add_argument("--company", default="", help="Client company name")
    parser.add_argument("--generate-image", action="store_true", help="Generate background image via fal.ai")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--batch", nargs="+", help="Multiple topics for batch generation")

    args = parser.parse_args()

    if args.batch:
        results = batch_designs(args.batch, args.type, args.company, args.generate_image)
        for r in results:
            if "error" in r:
                print(f"  FAILED: {r['topic']} — {r['error']}")
            else:
                print(f"  OK: {r['topic']} → {list(r['files'].keys())}")
    else:
        result = create_design(
            topic=args.topic,
            design_type=args.type,
            company=args.company,
            generate_image=args.generate_image,
            output_dir=args.output_dir,
        )
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
