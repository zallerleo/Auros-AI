"""
AUROS AI — Opus Clip Video Repurposing Agent
Takes long-form exhibition walkthrough videos and generates short-form clips
with captions, hooks, and platform-optimized formatting.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from agents.shared.config import PROJECT_ROOT, PORTFOLIO_DIR
from agents.shared.llm import generate


def generate_clip_plan(
    video_description: str,
    exhibition: str,
    duration_seconds: int = 300,
    num_clips: int = 10,
) -> dict:
    """
    Generate a clip plan from a long-form video description.
    Since we may not have Opus Clip API access, this generates clip specifications
    that can be used with any clipping tool (Opus Clip, CapCut, manual editing).

    Args:
        video_description: Description of the long-form video content
        exhibition: Exhibition name
        duration_seconds: Total video duration in seconds
        num_clips: Number of short clips to generate

    Returns:
        Dict with clip specifications
    """
    prompt = f"""You are a viral content strategist specializing in exhibition marketing.

Given this long-form exhibition video, generate {num_clips} short-form clip specifications
designed to go viral on TikTok, Instagram Reels, and YouTube Shorts.

EXHIBITION: {exhibition}
VIDEO DESCRIPTION: {video_description}
VIDEO DURATION: {duration_seconds} seconds

For each clip, provide:
1. clip_number (1-{num_clips})
2. title — catchy, scroll-stopping title
3. start_time — estimated start time in the source video (format: "MM:SS")
4. end_time — estimated end time (clips should be 15-60 seconds)
5. duration — clip length in seconds
6. hook — first 3 seconds text overlay or voiceover
7. caption — social media caption (include hashtags)
8. platform — primary platform (tiktok/reels/shorts)
9. format — vertical (9:16) or square (1:1)
10. text_overlays — array of text to overlay at specific times
11. music_suggestion — trending audio or music style
12. predicted_engagement — low/medium/high/viral potential
13. clip_type — one of: reaction, walkthrough, detail, pov, before_after, challenge, fact

Prioritize:
- Clips that create FOMO and drive ticket purchases
- POV moments ("POV: you just walked into...")
- Reaction-worthy reveals
- Specific details that showcase the experience
- Facts and numbers that surprise

Return as a JSON object with key "clips" containing an array.
"""

    raw = generate(prompt, max_tokens=8000, temperature=0.7)

    # Parse JSON
    import re
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            clip_plan = json.loads(match.group())
        except json.JSONDecodeError:
            clip_plan = {"clips": [], "raw_output": raw}
    else:
        clip_plan = {"clips": [], "raw_output": raw}

    clip_plan["exhibition"] = exhibition
    clip_plan["source_duration"] = duration_seconds
    clip_plan["generated_at"] = datetime.now().isoformat()

    return clip_plan


def generate_repurposing_matrix(
    clip_plan: dict,
    platforms: list[str] | None = None,
) -> dict:
    """
    Generate a platform-specific repurposing matrix from clip plan.
    Shows how each clip adapts across platforms.
    """
    if platforms is None:
        platforms = ["tiktok", "instagram_reels", "instagram_feed", "youtube_shorts", "facebook"]

    matrix = {
        "exhibition": clip_plan.get("exhibition", ""),
        "platforms": platforms,
        "clips": [],
    }

    for clip in clip_plan.get("clips", []):
        adaptations = {}
        for platform in platforms:
            if platform == "tiktok":
                adaptations[platform] = {
                    "format": "9:16 vertical",
                    "max_duration": 60,
                    "caption_style": "casual, emoji-heavy, trending hashtags",
                    "music": "trending audio",
                    "text_style": "bold, centered, appearing word-by-word",
                }
            elif platform == "instagram_reels":
                adaptations[platform] = {
                    "format": "9:16 vertical",
                    "max_duration": 90,
                    "caption_style": "polished, fewer emojis, niche hashtags",
                    "music": "original or trending",
                    "text_style": "clean sans-serif, lower-third",
                }
            elif platform == "instagram_feed":
                adaptations[platform] = {
                    "format": "1:1 square or 4:5",
                    "max_duration": 60,
                    "caption_style": "longer, storytelling, CTA in caption",
                    "music": "subtle background",
                    "text_style": "minimal, brand-consistent",
                }
            elif platform == "youtube_shorts":
                adaptations[platform] = {
                    "format": "9:16 vertical",
                    "max_duration": 60,
                    "caption_style": "SEO-optimized title, descriptive",
                    "music": "royalty-free",
                    "text_style": "clear, readable, keyword-rich",
                }
            elif platform == "facebook":
                adaptations[platform] = {
                    "format": "1:1 square or 16:9",
                    "max_duration": 120,
                    "caption_style": "conversational, link in description",
                    "music": "optional",
                    "text_style": "subtitles always on (85% watch muted)",
                }

        matrix["clips"].append({
            "clip": clip,
            "adaptations": adaptations,
        })

    return matrix


def run(
    company: str = "The Imagine Team",
    exhibition: str = "Harry Potter: The Exhibition",
    video_description: str | None = None,
) -> dict:
    """Run the full video repurposing workflow."""
    slug = company.lower().replace(" ", "_")
    client_dir = PORTFOLIO_DIR / f"client_{slug}"
    output_dir = client_dir / "content" / "repurposed_clips"
    output_dir.mkdir(parents=True, exist_ok=True)

    if video_description is None:
        video_description = f"""A 5-minute cinematic walkthrough of {exhibition}.
The video shows visitors entering the exhibition, moving through themed rooms,
interacting with exhibits, reacting with awe, taking photos, and experiencing
the highlight moments. Includes wide establishing shots, close-up details of
props and artifacts, crowd reactions, and the grand finale experience."""

    print(f"[AUROS] Generating clip plan for {exhibition}...")
    clip_plan = generate_clip_plan(video_description, exhibition)

    # Save clip plan
    date_str = datetime.now().strftime("%Y-%m-%d")
    plan_file = output_dir / f"clip_plan_{date_str}.json"
    with open(plan_file, "w") as f:
        json.dump(clip_plan, f, indent=2)
    print(f"[AUROS] Clip plan saved — {len(clip_plan.get('clips', []))} clips")

    # Generate repurposing matrix
    print(f"[AUROS] Generating platform repurposing matrix...")
    matrix = generate_repurposing_matrix(clip_plan)
    matrix_file = output_dir / f"repurposing_matrix_{date_str}.json"
    with open(matrix_file, "w") as f:
        json.dump(matrix, f, indent=2)
    print(f"[AUROS] Matrix saved — {len(matrix.get('platforms', []))} platforms")

    return {
        "clip_plan": clip_plan,
        "repurposing_matrix": matrix,
        "files": [str(plan_file), str(matrix_file)],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AUROS Opus Clip Video Repurposer")
    parser.add_argument("--company", default="The Imagine Team")
    parser.add_argument("--exhibition", default="Harry Potter: The Exhibition")
    parser.add_argument("--video-desc", help="Description of source video")
    args = parser.parse_args()

    result = run(
        company=args.company,
        exhibition=args.exhibition,
        video_description=args.video_desc,
    )
    print(f"\n[AUROS] Video repurposing complete")
    print(f"[AUROS] {len(result['clip_plan'].get('clips', []))} clips planned")
    print(f"[AUROS] Files: {result['files']}")
