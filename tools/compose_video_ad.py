"""
AUROS AI — Video Ad Compositor
Assembles motion clips + text overlays + transitions into finished video ads using MoviePy.

Usage:
    python tools/compose_video_ad.py --exhibition cabinet_of_curiosities --duration 15
    python tools/compose_video_ad.py --exhibition all --duration 15,30
    python tools/compose_video_ad.py --test  # Test with available clips
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import math
from pathlib import Path
from datetime import datetime

from moviepy import (
    VideoFileClip, TextClip, CompositeVideoClip, ColorClip,
    concatenate_videoclips, ImageClip,
)
from moviepy.video.fx import CrossFadeIn, CrossFadeOut, FadeIn, FadeOut
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ── Project imports ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_utils import (
    load_video_scripts, CAMPAIGN_COLORS, BRAND_COLORS, PROJECT_ROOT,
)

# ── Configuration ────────────────────────────────────────────────────────

CLIPS_DIR = PROJECT_ROOT / ".tmp" / "motion_clips"
OUTPUT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team" / "04_deliverables" / "video_ads_v2"

# Video specs
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 24

# Transition settings
CROSSFADE_DURATION = 0.5  # seconds

# Text styling
FONT_HOOK = "Arial-Bold"
FONT_BODY = "Arial"
FONT_CTA = "Arial-Bold"
FONT_SIZE_HOOK = 64
FONT_SIZE_BODY = 42
FONT_SIZE_CTA = 52
FONT_SIZE_BRAND = 28
TEXT_COLOR = "white"
TEXT_SHADOW_COLOR = (0, 0, 0, 180)

# Brand
BRAND_NAME = "AUROS AI"
WATERMARK_OPACITY = 0.6


# ── Utility Functions ────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_gradient_overlay(width: int, height: int, color: tuple = (0, 0, 0),
                            start_opacity: float = 0.0, end_opacity: float = 0.85,
                            start_position: float = 0.4) -> np.ndarray:
    """Create a vertical gradient overlay (transparent top → dark bottom)."""
    frame = np.zeros((height, width, 4), dtype=np.uint8)
    start_row = int(height * start_position)

    for y in range(start_row, height):
        progress = (y - start_row) / (height - start_row)
        alpha = int((start_opacity + (end_opacity - start_opacity) * progress) * 255)
        frame[y, :, :3] = color
        frame[y, :, 3] = alpha

    return frame


def create_text_with_shadow(text: str, font_size: int, color: str = "white",
                            font: str = "Arial-Bold", max_width: int = 900) -> ImageClip:
    """Create a text clip with shadow effect using PIL for better control."""
    # Create text clip
    try:
        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            color=color,
            font=font,
            method="caption",
            size=(max_width, None),
            text_align="center",
        )
    except Exception:
        # Fallback if font not found
        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            color=color,
            method="caption",
            size=(max_width, None),
            text_align="center",
        )
    return txt_clip


def create_accent_bar(width: int, height: int = 6, color: tuple = (201, 168, 76)) -> ImageClip:
    """Create a colored accent bar."""
    bar = np.zeros((height, width, 3), dtype=np.uint8)
    bar[:, :] = color
    return ImageClip(bar)


def create_cta_card(text: str, accent_color: tuple, width: int = 900, height: int = 200) -> ImageClip:
    """Create a CTA card with accent color background and text."""
    # Background with rounded feel
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    padding = 20
    draw.rounded_rectangle(
        [padding, padding, width - padding, height - padding],
        radius=20,
        fill=(*accent_color, 230),
    )

    # Add text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (width - text_w) // 2
    text_y = (height - text_h) // 2
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

    return ImageClip(np.array(img)).with_duration(1)


# ── Scene Builders ───────────────────────────────────────────────────────

def build_scene_from_clip(
    clip_path: Path,
    text_overlay: str,
    scene_duration: float,
    accent_color: tuple,
    is_first: bool = False,
    is_last: bool = False,
) -> CompositeVideoClip:
    """
    Build a single scene: motion clip + gradient overlay + text.
    """
    # Load and prepare motion clip
    video = VideoFileClip(str(clip_path))

    # Resize to fit our canvas if needed
    if video.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
        # Scale to fill, then crop
        scale_w = VIDEO_WIDTH / video.size[0]
        scale_h = VIDEO_HEIGHT / video.size[1]
        scale = max(scale_w, scale_h)
        video = video.resized(scale)

        # Center crop
        w, h = video.size
        x_offset = (w - VIDEO_WIDTH) // 2
        y_offset = (h - VIDEO_HEIGHT) // 2
        video = video.cropped(
            x1=x_offset, y1=y_offset,
            x2=x_offset + VIDEO_WIDTH, y2=y_offset + VIDEO_HEIGHT,
        )

    # Trim or loop to scene duration
    if video.duration >= scene_duration:
        video = video.subclipped(0, scene_duration)
    else:
        # Loop the clip to fill duration
        loops_needed = math.ceil(scene_duration / video.duration)
        video = concatenate_videoclips([video] * loops_needed).subclipped(0, scene_duration)

    # Create gradient overlay for text readability
    gradient = create_gradient_overlay(VIDEO_WIDTH, VIDEO_HEIGHT)
    gradient_clip = ImageClip(gradient).with_duration(scene_duration)

    # Create text overlay
    layers = [video, gradient_clip]

    if text_overlay:
        txt = create_text_with_shadow(
            text=text_overlay,
            font_size=FONT_SIZE_HOOK if len(text_overlay) < 40 else FONT_SIZE_BODY,
            max_width=int(VIDEO_WIDTH * 0.85),
        )
        txt = txt.with_duration(scene_duration)

        # Fade text in
        txt = txt.with_effects([FadeIn(0.4)])

        # Position in lower third
        txt = txt.with_position(("center", VIDEO_HEIGHT * 0.72))
        layers.append(txt)

    # Accent bar at bottom
    bar = create_accent_bar(VIDEO_WIDTH, height=4, color=accent_color)
    bar = bar.with_duration(scene_duration).with_position(("center", VIDEO_HEIGHT - 4))
    layers.append(bar)

    scene = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    return scene


def build_cta_scene(
    cta_text: str,
    exhibition_name: str,
    accent_color: tuple,
    duration: float = 3.0,
) -> CompositeVideoClip:
    """Build the final CTA scene with brand card."""
    # Dark background
    bg = ColorClip(
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        color=hex_to_rgb(BRAND_COLORS["midnight"]),
    ).with_duration(duration)

    layers = [bg]

    # Exhibition name
    title = create_text_with_shadow(
        text=exhibition_name,
        font_size=FONT_SIZE_HOOK,
        color="#" + "".join(f"{c:02x}" for c in accent_color),
        max_width=int(VIDEO_WIDTH * 0.85),
    )
    title = title.with_duration(duration).with_position(("center", VIDEO_HEIGHT * 0.35))
    title = title.with_effects([FadeIn(0.3)])
    layers.append(title)

    # CTA text
    cta = create_text_with_shadow(
        text=cta_text,
        font_size=FONT_SIZE_CTA,
        max_width=int(VIDEO_WIDTH * 0.8),
    )
    cta = cta.with_duration(duration).with_position(("center", VIDEO_HEIGHT * 0.5))
    cta = cta.with_effects([FadeIn(0.5)])
    layers.append(cta)

    # Brand watermark
    brand = create_text_with_shadow(
        text=BRAND_NAME,
        font_size=FONT_SIZE_BRAND,
        color=BRAND_COLORS["gold"],
    )
    brand = brand.with_duration(duration).with_position(("center", VIDEO_HEIGHT * 0.88))
    brand = brand.with_effects([FadeIn(0.6)])
    layers.append(brand)

    # Accent bar
    bar = create_accent_bar(VIDEO_WIDTH, height=6, color=accent_color)
    bar = bar.with_duration(duration).with_position(("center", VIDEO_HEIGHT * 0.32))
    layers.append(bar)

    return CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))


# ── Main Composition ─────────────────────────────────────────────────────

def compose_video_ad(
    exhibition: str,
    target_duration: int = 15,
) -> dict:
    """
    Compose a full video ad from motion clips + video scripts.

    Args:
        exhibition: Exhibition name
        target_duration: Target duration in seconds (15, 30, 60)

    Returns:
        dict with success, output_path, details
    """
    result = {
        "success": False,
        "exhibition": exhibition,
        "target_duration": target_duration,
        "output_path": None,
        "error": None,
    }

    print(f"\n{'='*60}")
    print(f"  🎬 AUROS AI — Video Ad Compositor")
    print(f"  Exhibition: {CAMPAIGN_COLORS.get(exhibition, {}).get('name', exhibition)}")
    print(f"  Target: {target_duration}s")
    print(f"{'='*60}\n")

    # Get campaign config
    campaign = CAMPAIGN_COLORS.get(exhibition)
    if not campaign:
        result["error"] = f"Unknown exhibition: {exhibition}"
        print(f"  ❌ {result['error']}")
        return result

    accent_color = hex_to_rgb(campaign["accent"])

    # Load motion clips
    clips_dir = CLIPS_DIR / exhibition
    if not clips_dir.exists():
        result["error"] = f"No motion clips found at {clips_dir}"
        print(f"  ❌ {result['error']}")
        print(f"  💡 Run: python tools/generate_motion_clips.py --exhibition {exhibition}")
        return result

    clip_files = sorted(clips_dir.glob("*.mp4"))
    if not clip_files:
        result["error"] = "No .mp4 clips found in clips directory"
        print(f"  ❌ {result['error']}")
        return result

    print(f"  ℹ️ Found {len(clip_files)} motion clips")

    # Load video scripts for text overlays
    scripts = load_video_scripts(exhibition)
    target_script = None
    for s in scripts:
        if s["duration_seconds"] == target_duration:
            target_script = s
            break
    if not target_script and scripts:
        target_script = scripts[0]  # Use first available

    # Plan scenes
    cta_duration = 3.0
    content_duration = target_duration - cta_duration
    num_content_scenes = min(len(clip_files), max(2, target_duration // 5))
    scene_duration = content_duration / num_content_scenes

    print(f"  ℹ️ Planning {num_content_scenes} content scenes + CTA ({cta_duration}s)")
    print(f"  ℹ️ Each scene: {scene_duration:.1f}s")

    # Build scenes
    scenes = []
    for i in range(num_content_scenes):
        clip_path = clip_files[i % len(clip_files)]

        # Get text overlay from script
        text = ""
        if target_script and i < len(target_script["shots"]):
            text = target_script["shots"][i].get("text_overlay", "")

        print(f"  🎞️ Scene {i+1}: {clip_path.name} | \"{text[:50]}\"")

        try:
            scene = build_scene_from_clip(
                clip_path=clip_path,
                text_overlay=text,
                scene_duration=scene_duration,
                accent_color=accent_color,
                is_first=(i == 0),
                is_last=False,
            )
            scenes.append(scene)
        except Exception as e:
            print(f"  ⚠️ Scene {i+1} failed: {str(e)}")
            # Create a fallback solid color scene
            fallback = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=hex_to_rgb(BRAND_COLORS["navy"]),
            ).with_duration(scene_duration)
            scenes.append(fallback)

    # Build CTA scene
    cta_text = target_script.get("cta", "Visit Today") if target_script else "Visit Today"
    print(f"  🎯 CTA: \"{cta_text}\"")

    cta_scene = build_cta_scene(
        cta_text=cta_text,
        exhibition_name=campaign["name"],
        accent_color=accent_color,
        duration=cta_duration,
    )
    scenes.append(cta_scene)

    # Concatenate with crossfades
    print(f"\n  ⚙️ Compositing {len(scenes)} scenes...")

    try:
        if len(scenes) > 1 and CROSSFADE_DURATION > 0:
            # Apply crossfade transitions
            processed_scenes = [scenes[0]]
            for i in range(1, len(scenes)):
                scene = scenes[i].with_effects([CrossFadeIn(CROSSFADE_DURATION)])
                processed_scenes.append(scene)

            final = concatenate_videoclips(
                processed_scenes,
                method="compose",
                padding=-CROSSFADE_DURATION,
            )
        else:
            final = concatenate_videoclips(scenes, method="compose")

        # Ensure exact duration
        if final.duration > target_duration + 0.5:
            final = final.subclipped(0, target_duration)

        # Output
        output_dir = OUTPUT_DIR / exhibition
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")
        output_path = output_dir / f"{exhibition}_{target_duration}s_{ts}.mp4"

        print(f"  📹 Rendering to {output_path.name}...")
        print(f"     Resolution: {VIDEO_WIDTH}x{VIDEO_HEIGHT} | FPS: {FPS}")

        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio=False,  # No audio for now (Phase 2)
            preset="medium",
            bitrate="8M",
            logger=None,  # Suppress moviepy progress bar noise
        )

        # Validate output
        probe = VideoFileClip(str(output_path))
        actual_duration = probe.duration
        actual_size = output_path.stat().st_size
        probe.close()

        print(f"\n  ✅ Video rendered successfully!")
        print(f"     Duration: {actual_duration:.1f}s")
        print(f"     File size: {actual_size // 1024}KB ({actual_size // (1024*1024)}MB)")
        print(f"     Output: {output_path.relative_to(PROJECT_ROOT)}")

        result["success"] = True
        result["output_path"] = str(output_path)
        result["actual_duration"] = actual_duration
        result["file_size_kb"] = actual_size // 1024

        # Cleanup
        final.close()
        for scene in scenes:
            try:
                scene.close()
            except Exception:
                pass

    except Exception as e:
        result["error"] = str(e)
        print(f"\n  ❌ Composition failed: {str(e)}")
        import traceback
        traceback.print_exc()

    return result


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AUROS AI Video Ad Compositor")
    parser.add_argument("--exhibition", type=str, default="cabinet_of_curiosities",
                       help="Exhibition name or 'all'")
    parser.add_argument("--duration", type=str, default="15",
                       help="Target duration(s), comma-separated (e.g., '15,30')")
    parser.add_argument("--test", action="store_true",
                       help="Test with whatever clips are available")

    args = parser.parse_args()

    if args.test:
        # Find any exhibition that has clips
        for ex in CAMPAIGN_COLORS:
            clips_dir = CLIPS_DIR / ex
            if clips_dir.exists() and list(clips_dir.glob("*.mp4")):
                print(f"  🧪 TEST MODE — composing with {ex} clips\n")
                return compose_video_ad(ex, 15)
        print("  ❌ No motion clips found. Run generate_motion_clips.py first.")
        return

    durations = [int(d.strip()) for d in args.duration.split(",")]
    exhibitions = list(CAMPAIGN_COLORS.keys()) if args.exhibition == "all" else [args.exhibition]

    results = {}
    for exhibition in exhibitions:
        for duration in durations:
            key = f"{exhibition}_{duration}s"
            results[key] = compose_video_ad(exhibition, duration)

    # Final summary
    print(f"\n{'='*60}")
    print(f"  📊 Batch Composition Summary")
    for key, r in results.items():
        status = "✅" if r.get("success") else "❌"
        print(f"  {status} {key}: {r.get('output_path', r.get('error', 'unknown'))}")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    main()
