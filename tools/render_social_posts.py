#!/usr/bin/env python3
"""
AUROS AI — Social Post Renderer
Reads social post JSON, renders via Playwright HTML templates → PNG images.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
CLIENT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team"
OUTPUT_DIR = CLIENT_DIR / "04_deliverables" / "social_posts_rendered"

from content_utils import (
    load_social_posts, pick_image, image_to_base64,
    CAMPAIGN_COLORS, MEDIA_FOLDER_MAP,
)

EXHIBITIONS = ["cabinet_of_curiosities", "titanic", "thomas_dambo_trolls"]


def _clean_text(text: str) -> str:
    """Remove hashtags and emojis for clean display text."""
    # Remove hashtag lines
    lines = text.split("\n")
    clean = [l for l in lines if not l.strip().startswith("#")]
    text = "\n".join(clean).strip()
    # Remove emoji unicode (keep basic punctuation)
    text = re.sub(r'[\U0001F300-\U0001F9FF\U00002700-\U000027BF\U0000FE00-\U0000FE0F\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF]', '', text)
    return text.strip()


def _first_line(text: str) -> str:
    """Get first non-empty line."""
    for line in text.split("\n"):
        line = line.strip()
        if line:
            return line
    return text[:80]


def _body_lines(text: str, max_lines: int = 4) -> str:
    """Get body text (skip hook, skip hashtags), limited lines."""
    lines = text.split("\n")
    body = []
    for line in lines[1:]:  # skip hook
        line = line.strip()
        if line.startswith("#"):
            continue
        if line:
            body.append(line)
        if len(body) >= max_lines:
            break
    return "\n".join(body)


async def _inject_content(page, data: dict):
    """Safely inject content into template using Playwright arg passing."""
    # Inject text content first (small payload)
    text_data = {k: v for k, v in data.items() if k != "bgImage"}
    await page.evaluate("""(data) => {
        if (data.accent) document.documentElement.style.setProperty('--accent', data.accent);
        if (data.label) document.getElementById('campaign-label').textContent = data.label;
        if (data.hook) document.getElementById('hook').textContent = data.hook;
        var bodyEl = document.getElementById('body-text');
        if (bodyEl && data.body) bodyEl.textContent = data.body;
        var ctaEl = document.getElementById('cta');
        if (ctaEl && data.cta) ctaEl.textContent = data.cta;
    }""", text_data)

    # Inject background image separately (large base64 payload)
    if data.get("bgImage"):
        await page.evaluate("""(imgSrc) => {
            document.getElementById('bg-image').style.backgroundImage = 'url(' + imgSrc + ')';
        }""", data["bgImage"])


async def render_feed_post(page, post: dict, image_path: Path, output_path: Path):
    """Render a single feed post (1080x1080)."""
    template = TEMPLATES_DIR / "social_feed.html"
    await page.goto(f"file://{template}", wait_until="networkidle")

    colors = CAMPAIGN_COLORS.get(post["exhibition"], CAMPAIGN_COLORS["cabinet_of_curiosities"])
    hook = _clean_text(_first_line(post["hook"]))
    body = _clean_text(_body_lines(post["body"], max_lines=3))
    cta = _clean_text(post["cta"]) or "Learn More"
    img_uri = image_to_base64(image_path)

    if len(hook) > 80:
        hook = hook[:77] + "..."

    await _inject_content(page, {
        "accent": colors["accent"],
        "bgImage": img_uri,
        "label": colors["name"],
        "hook": hook,
        "body": body.replace("\n", " "),
        "cta": cta,
    })

    await page.wait_for_timeout(800)
    await page.screenshot(path=str(output_path))


async def render_story_post(page, post: dict, image_path: Path, output_path: Path):
    """Render a story post (1080x1920)."""
    template = TEMPLATES_DIR / "social_story.html"

    browser = page.context.browser
    context = await browser.new_context(viewport={"width": 1080, "height": 1920})
    story_page = await context.new_page()

    await story_page.goto(f"file://{template}", wait_until="networkidle")

    colors = CAMPAIGN_COLORS.get(post["exhibition"], CAMPAIGN_COLORS["cabinet_of_curiosities"])
    hook = _clean_text(_first_line(post["hook"]))
    body = _clean_text(_body_lines(post["body"], max_lines=2))
    cta = _clean_text(post["cta"]) or "Swipe Up"
    img_uri = image_to_base64(image_path)

    if len(hook) > 60:
        hook = hook[:57] + "..."

    await _inject_content(story_page, {
        "accent": colors["accent"],
        "bgImage": img_uri,
        "label": colors["name"],
        "hook": hook,
        "body": body.replace("\n", " "),
        "cta": cta,
    })

    await story_page.wait_for_timeout(800)
    await story_page.screenshot(path=str(output_path))
    await context.close()


async def render_carousel_slide(page, text: str, slide_num: int, total_slides: int,
                                 exhibition: str, output_path: Path):
    """Render a single carousel slide (1080x1080)."""
    template = TEMPLATES_DIR / "social_carousel.html"
    await page.goto(f"file://{template}", wait_until="networkidle")

    colors = CAMPAIGN_COLORS.get(exhibition, CAMPAIGN_COLORS["cabinet_of_curiosities"])
    clean_text = _clean_text(text)

    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    if len(sentences) > 1:
        main_text = sentences[0]
        sub_text = " ".join(sentences[1:])
    else:
        main_text = clean_text
        sub_text = ""

    await page.evaluate("""(data) => {
        document.documentElement.style.setProperty('--accent', data.accent);
        document.getElementById('campaign-label').textContent = data.label;
        document.getElementById('main-text').textContent = data.mainText;
        document.getElementById('sub-text').textContent = data.subText;
        var indicator = document.getElementById('slide-indicator');
        for (var i = 0; i < data.totalSlides; i++) {
            var dot = document.createElement('div');
            dot.className = 'slide-dot' + (i === data.slideNum ? ' active' : '');
            indicator.appendChild(dot);
        }
    }""", {
        "accent": colors["accent"],
        "label": colors["name"],
        "mainText": main_text,
        "subText": sub_text,
        "slideNum": slide_num,
        "totalSlides": total_slides,
    })

    await page.wait_for_timeout(500)
    await page.screenshot(path=str(output_path))


async def main():
    from playwright.async_api import async_playwright

    print("[AUROS] Social Post Renderer starting...")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Default context for 1080x1080 feed posts
        context = await browser.new_context(viewport={"width": 1080, "height": 1080})
        page = await context.new_page()

        total_rendered = 0

        for exhibition in EXHIBITIONS:
            posts = load_social_posts(exhibition)
            if not posts:
                print(f"  SKIP: No posts for {exhibition}")
                continue

            ex_output = OUTPUT_DIR / exhibition
            ex_output.mkdir(parents=True, exist_ok=True)

            print(f"\n  === {CAMPAIGN_COLORS[exhibition]['name']} ({len(posts)} posts) ===")

            feed_count = 0
            story_count = 0
            carousel_count = 0
            img_idx = 0

            for post in posts:
                fmt = post["format"]
                image = pick_image(exhibition, img_idx)
                img_idx += 1

                if not image:
                    print(f"    SKIP: No images for {exhibition}")
                    continue

                if fmt == "carousel" and post["slides"]:
                    # Render first slide as feed image (with background photo)
                    carousel_count += 1
                    if carousel_count <= 2:  # max 2 carousels per exhibition
                        out = ex_output / f"carousel_{carousel_count}_slide_1.png"
                        await render_feed_post(page, post, image, out)
                        print(f"    OK: carousel_{carousel_count}_slide_1.png (feed cover)")
                        total_rendered += 1

                        # Render text slides
                        for si, slide_text in enumerate(post["slides"][:4], start=2):
                            out = ex_output / f"carousel_{carousel_count}_slide_{si}.png"
                            await render_carousel_slide(
                                page, slide_text, si - 1,
                                min(len(post["slides"]) + 1, 5),
                                exhibition, out
                            )
                            print(f"    OK: carousel_{carousel_count}_slide_{si}.png")
                            total_rendered += 1

                elif fmt == "reel" or fmt == "story":
                    story_count += 1
                    if story_count <= 2:  # max 2 stories per exhibition
                        out = ex_output / f"story_{story_count}.png"
                        await render_story_post(page, post, image, out)
                        print(f"    OK: story_{story_count}.png (1080x1920)")
                        total_rendered += 1

                else:
                    # Feed post
                    feed_count += 1
                    if feed_count <= 3:  # max 3 feed posts per exhibition
                        out = ex_output / f"feed_{feed_count}.png"
                        await render_feed_post(page, post, image, out)
                        print(f"    OK: feed_{feed_count}.png (1080x1080)")
                        total_rendered += 1

        await browser.close()

    # Summary
    print(f"\n[AUROS] Rendering complete!")
    print(f"  Total rendered: {total_rendered}")
    print(f"  Output: {OUTPUT_DIR}")

    # List all files
    for ex_dir in sorted(OUTPUT_DIR.iterdir()):
        if ex_dir.is_dir():
            files = sorted(ex_dir.glob("*.png"))
            total_size = sum(f.stat().st_size for f in files) / 1024
            print(f"  {ex_dir.name}: {len(files)} images ({total_size:.0f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
