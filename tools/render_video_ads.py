#!/usr/bin/env python3
"""
AUROS AI — Video Ad Renderer
Reads video script JSON, renders animated HTML via Playwright frame capture → MP4.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
CLIENT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team"
OUTPUT_DIR = CLIENT_DIR / "04_deliverables" / "video_ads_rendered"

from content_utils import (
    load_video_scripts, pick_image, image_to_base64,
    CAMPAIGN_COLORS, get_images,
)

EXHIBITIONS = ["cabinet_of_curiosities", "titanic", "thomas_dambo_trolls"]
FPS = 15  # 15fps is enough for slideshow-style video — keeps render fast
KENBURNS_VARIANTS = ["kenBurnsIn", "kenBurnsOut", "kenBurnsPanRight"]


def _build_scene_js(shots: list[dict], exhibition: str, total_duration: int) -> str:
    """Build JS that injects scenes into the HTML template."""
    images = get_images(exhibition)
    if not images:
        return ""

    # Calculate timing per shot
    num_shots = len(shots)
    cta_duration = 3  # last 3 seconds for CTA
    content_duration = total_duration - cta_duration
    shot_duration = content_duration / max(num_shots, 1)

    scene_blocks = []
    for i, shot in enumerate(shots):
        img = images[i % len(images)]
        img_b64 = image_to_base64(img)
        text = shot.get("text_overlay", "")
        start = i * shot_duration
        ken_burns = KENBURNS_VARIANTS[i % len(KENBURNS_VARIANTS)]

        scene_blocks.append(f"""
        (function() {{
            var scene = document.createElement('div');
            scene.className = 'scene';
            scene.style.animation = 'sceneFadeIn {shot_duration}s linear {start}s forwards';

            var bg = document.createElement('div');
            bg.className = 'bg';
            bg.style.backgroundImage = 'url(' + images[{i}] + ')';
            bg.style.animation = '{ken_burns} {shot_duration + 1}s ease-in-out {start}s forwards';
            scene.appendChild(bg);

            var overlay = document.createElement('div');
            overlay.className = 'overlay';
            scene.appendChild(overlay);

            var textContainer = document.createElement('div');
            textContainer.className = 'text-container';
            var textEl = document.createElement('div');
            textEl.className = 'text-overlay';
            textEl.textContent = texts[{i}];
            textEl.style.animation = 'textFadeInUp 0.6s ease-out {start + 0.3}s forwards';
            textContainer.appendChild(textEl);
            scene.appendChild(textContainer);

            container.appendChild(scene);
        }})();
        """)

    # CTA timing
    cta_start = content_duration

    return "\n".join(scene_blocks), cta_start


async def render_video(exhibition: str, script: dict, output_path: Path):
    """Render a single video ad by capturing frames from animated HTML."""
    from playwright.async_api import async_playwright

    duration = script["duration_seconds"]
    shots = script["shots"]
    colors = CAMPAIGN_COLORS.get(exhibition, CAMPAIGN_COLORS["cabinet_of_curiosities"])
    title = script.get("title", "Ad")

    print(f"    Rendering: {title} ({duration}s, {len(shots)} shots)...")

    # Prepare image data and text data
    images = get_images(exhibition)
    if not images:
        print(f"    SKIP: No images for {exhibition}")
        return False

    img_b64_list = [image_to_base64(images[i % len(images)]) for i in range(len(shots))]
    text_list = [shot.get("text_overlay", "") for shot in shots]
    cta_text = script.get("cta", "Get Tickets Now")

    # Timing
    cta_duration = 3
    content_duration = duration - cta_duration
    shot_duration = content_duration / max(len(shots), 1)
    cta_start = content_duration

    # Create temp dir for frames
    frames_dir = Path(tempfile.mkdtemp(prefix="auros_frames_"))

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={"width": 1080, "height": 1920})
            page = await context.new_page()

            template = TEMPLATES_DIR / "video_15s.html"
            await page.goto(f"file://{template}", wait_until="networkidle")

            # Set accent color and total duration
            await page.evaluate("""(data) => {
                document.documentElement.style.setProperty('--accent', data.accent);
                document.documentElement.style.setProperty('--total-duration', data.duration + 's');
            }""", {"accent": colors["accent"], "duration": duration})

            # Inject all scenes
            await page.evaluate("""(data) => {
                var container = document.getElementById('scenes-container');
                var images = data.images;
                var texts = data.texts;
                var shotDuration = data.shotDuration;
                var kenVariants = ['kenBurnsIn', 'kenBurnsOut', 'kenBurnsPanRight'];

                for (var i = 0; i < texts.length; i++) {
                    var scene = document.createElement('div');
                    scene.className = 'scene';
                    scene.style.animation = 'sceneFadeIn ' + shotDuration + 's linear ' + (i * shotDuration) + 's forwards';

                    var bg = document.createElement('div');
                    bg.className = 'bg';
                    bg.style.backgroundImage = 'url(' + images[i] + ')';
                    bg.style.animation = kenVariants[i % 3] + ' ' + (shotDuration + 1) + 's ease-in-out ' + (i * shotDuration) + 's forwards';
                    scene.appendChild(bg);

                    var overlay = document.createElement('div');
                    overlay.className = 'overlay';
                    scene.appendChild(overlay);

                    var textContainer = document.createElement('div');
                    textContainer.className = 'text-container';
                    var textEl = document.createElement('div');
                    textEl.className = 'text-overlay';
                    textEl.textContent = texts[i];
                    textEl.style.animation = 'textFadeInUp 0.6s ease-out ' + (i * shotDuration + 0.3) + 's forwards';
                    textContainer.appendChild(textEl);
                    scene.appendChild(textContainer);

                    container.appendChild(scene);
                }

                // CTA scene
                var ctaScene = document.getElementById('cta-scene');
                ctaScene.style.animation = 'ctaFadeIn 0.5s ease-out ' + data.ctaStart + 's forwards';
                document.getElementById('cta-text').textContent = data.ctaText;
                var ctaBtn = document.getElementById('cta-button');
                ctaBtn.style.animation = 'ctaButtonIn 0.5s ease-out ' + (data.ctaStart + 0.5) + 's forwards';
            }""", {
                "images": img_b64_list,
                "texts": text_list,
                "shotDuration": shot_duration,
                "ctaStart": cta_start,
                "ctaText": cta_text,
            })

            # Wait for fonts
            await page.wait_for_timeout(1000)

            # Capture frames
            total_frames = duration * FPS
            print(f"    Capturing {total_frames} frames at {FPS}fps...")

            for frame in range(total_frames):
                current_time_ms = (frame / FPS) * 1000

                # Pause all animations at this timestamp
                await page.evaluate("""(time) => {
                    document.getAnimations().forEach(function(a) {
                        a.currentTime = time;
                        a.pause();
                    });
                }""", current_time_ms)

                frame_path = frames_dir / f"frame_{frame:04d}.png"
                await page.screenshot(path=str(frame_path))

                # Progress indicator every 30 frames
                if frame > 0 and frame % (FPS * 3) == 0:
                    print(f"      {frame}/{total_frames} frames...")

            await browser.close()

        # Assemble frames into MP4
        print(f"    Assembling {total_frames} frames into MP4...")
        import imageio.v3 as iio

        frames = []
        for i in range(total_frames):
            frame_path = frames_dir / f"frame_{i:04d}.png"
            frame_data = iio.imread(str(frame_path))
            frames.append(frame_data)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        iio.imwrite(
            str(output_path),
            frames,
            fps=FPS,
            codec="libx264",
            plugin="pyav",
        )

        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"    SAVED: {output_path.name} ({size_mb:.1f} MB)")
        return True

    finally:
        # Clean up frames
        shutil.rmtree(frames_dir, ignore_errors=True)


async def main():
    print("[AUROS] Video Ad Renderer starting...")

    total_rendered = 0

    for exhibition in EXHIBITIONS:
        scripts = load_video_scripts(exhibition)
        if not scripts:
            print(f"  SKIP: No scripts for {exhibition}")
            continue

        colors = CAMPAIGN_COLORS[exhibition]
        print(f"\n  === {colors['name']} ({len(scripts)} scripts) ===")

        # Render only the 15s script (first one)
        for script in scripts:
            if script["duration_seconds"] <= 15:
                slug = exhibition.replace("_", "-")
                out = OUTPUT_DIR / f"{slug}-{script['duration_seconds']}s.mp4"
                success = await render_video(exhibition, script, out)
                if success:
                    total_rendered += 1
                break  # Only one per exhibition for now

    print(f"\n[AUROS] Video rendering complete!")
    print(f"  Total rendered: {total_rendered}")
    print(f"  Output: {OUTPUT_DIR}")

    for f in sorted(OUTPUT_DIR.glob("*.mp4")):
        size = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}: {size:.1f} MB")


if __name__ == "__main__":
    asyncio.run(main())
