#!/usr/bin/env python3
"""
AUROS AI — Agent 6: Post-Production Editor
Hybrid editing agent that uses FFmpeg for automated edits (text overlays, cuts,
color grading, music) and generates CapCut project specs for complex edits.

Usage:
    python -m agents.editor.editor_agent --company "Company Name" --task "overlay" --input video.mp4
    python -m agents.editor.editor_agent --company "Company Name" --task "full_edit" --input-dir ./clips/
    python -m agents.editor.editor_agent --company "Company Name" --task "capcut_spec" --input-dir ./clips/
"""

from __future__ import annotations

import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, BRAND
from agents.shared.llm import generate


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def add_text_overlay(
    input_path: str,
    output_path: str,
    text: str,
    font_size: int = 48,
    font_color: str = "C9A84C",
    position: str = "center",
    start_time: float = 0,
    duration: float | None = None,
) -> bool:
    """Add text overlay to a video using FFmpeg."""
    if not check_ffmpeg():
        print("[AUROS] FFmpeg not installed. Run: brew install ffmpeg")
        return False

    # Position mapping
    positions = {
        "center": "x=(w-text_w)/2:y=(h-text_h)/2",
        "bottom_center": "x=(w-text_w)/2:y=h-text_h-60",
        "top_center": "x=(w-text_w)/2:y=60",
        "bottom_left": "x=60:y=h-text_h-60",
        "bottom_right": "x=w-text_w-60:y=h-text_h-60",
    }
    pos = positions.get(position, positions["center"])

    # Build filter
    enable = f":enable='gte(t,{start_time})"
    if duration:
        enable += f"*lte(t,{start_time + duration})'"
    else:
        enable += "'"

    filter_str = (
        f"drawtext=text='{text}':fontsize={font_size}:fontcolor=#{font_color}"
        f":{pos}{enable}"
    )

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", filter_str,
        "-codec:a", "copy",
        "-y", output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[AUROS] Text overlay added: {output_path}")
            return True
        else:
            print(f"[AUROS] FFmpeg error: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("[AUROS] FFmpeg timed out")
        return False


def apply_color_grade(
    input_path: str,
    output_path: str,
    style: str = "auros_gold",
) -> bool:
    """Apply color grading to a video using FFmpeg."""
    if not check_ffmpeg():
        print("[AUROS] FFmpeg not installed. Run: brew install ffmpeg")
        return False

    grades = {
        "auros_gold": "eq=contrast=1.15:brightness=0.02:saturation=0.9,colorbalance=rs=0.05:gs=0.02:bs=-0.03:rh=0.08:gh=0.04:bh=-0.02",
        "cinematic": "eq=contrast=1.2:brightness=-0.02:saturation=0.85,curves=preset=cross_process",
        "warm": "eq=contrast=1.1:brightness=0.03:saturation=1.1,colorbalance=rs=0.06:gs=0.02:bs=-0.04",
        "cold": "eq=contrast=1.15:brightness=0.0:saturation=0.8,colorbalance=rs=-0.03:gs=0.0:bs=0.05",
        "high_contrast": "eq=contrast=1.3:brightness=-0.01:saturation=1.0",
    }

    filter_str = grades.get(style, grades["auros_gold"])

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", filter_str,
        "-codec:a", "copy",
        "-y", output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[AUROS] Color grade applied ({style}): {output_path}")
            return True
        else:
            print(f"[AUROS] FFmpeg error: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("[AUROS] FFmpeg timed out")
        return False


def trim_video(input_path: str, output_path: str, start: float, end: float) -> bool:
    """Trim a video to a specific time range."""
    if not check_ffmpeg():
        return False

    cmd = [
        "ffmpeg", "-i", input_path,
        "-ss", str(start), "-to", str(end),
        "-c", "copy",
        "-y", output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"[AUROS] Trimmed {start}s-{end}s: {output_path}")
            return True
        print(f"[AUROS] Trim error: {result.stderr[:300]}")
        return False
    except subprocess.TimeoutExpired:
        return False


def concatenate_clips(clip_paths: list[str], output_path: str) -> bool:
    """Concatenate multiple video clips into one."""
    if not check_ffmpeg():
        return False

    # Create concat file
    concat_file = Path(output_path).parent / "_concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip}'\n")

    cmd = [
        "ffmpeg",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-y", output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        concat_file.unlink(missing_ok=True)
        if result.returncode == 0:
            print(f"[AUROS] Concatenated {len(clip_paths)} clips: {output_path}")
            return True
        print(f"[AUROS] Concat error: {result.stderr[:300]}")
        return False
    except subprocess.TimeoutExpired:
        concat_file.unlink(missing_ok=True)
        return False


def add_audio_track(
    video_path: str,
    audio_path: str,
    output_path: str,
    audio_volume: float = 0.3,
) -> bool:
    """Add background music to a video."""
    if not check_ffmpeg():
        return False

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[1:a]volume={audio_volume}[music];[0:a][music]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-shortest",
        "-y", output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[AUROS] Audio track added: {output_path}")
            return True
        print(f"[AUROS] Audio error: {result.stderr[:300]}")
        return False
    except subprocess.TimeoutExpired:
        return False


def resize_for_platform(
    input_path: str,
    output_path: str,
    platform: str = "instagram_reel",
) -> bool:
    """Resize video for specific platform dimensions."""
    if not check_ffmpeg():
        return False

    sizes = {
        "instagram_reel": "1080:1920",
        "instagram_feed": "1080:1080",
        "instagram_story": "1080:1920",
        "youtube": "1920:1080",
        "tiktok": "1080:1920",
        "facebook": "1200:628",
        "linkedin": "1920:1080",
    }

    size = sizes.get(platform, sizes["instagram_reel"])
    w, h = size.split(":")

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0B0F1A",
        "-c:a", "copy",
        "-y", output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[AUROS] Resized for {platform}: {output_path}")
            return True
        print(f"[AUROS] Resize error: {result.stderr[:300]}")
        return False
    except subprocess.TimeoutExpired:
        return False


def generate_capcut_spec(
    company: str,
    clips_dir: str | None = None,
    ad_duration: int = 30,
    style: str = "cinematic",
) -> dict:
    """
    Generate a detailed CapCut editing specification that a human editor
    can follow to assemble the final video.
    """
    company_slug = company.lower().replace(" ", "_").replace("'", "")
    client_dir = PORTFOLIO_DIR / f"client_{company_slug}"

    # Load brand data if available
    brand_data = {}
    brand_files = sorted(client_dir.glob("brand_identity_*.json"), reverse=True)
    if brand_files:
        brand_data = json.loads(brand_files[0].read_text())

    # List available clips
    clips_info = []
    if clips_dir:
        clips_path = Path(clips_dir)
        if clips_path.exists():
            for f in clips_path.iterdir():
                if f.suffix.lower() in (".mp4", ".mov", ".avi", ".webm"):
                    clips_info.append(f.name)

    prompt = f"""Generate a detailed CapCut editing specification for a {ad_duration}-second {style} advertisement video.

Company: {company}
Available clips: {json.dumps(clips_info) if clips_info else "Clips to be generated from AI tools (Runway ML, Kling AI)"}
Brand colors: {json.dumps(brand_data.get('colors', BRAND['colors']))}
Brand font: {brand_data.get('typography', {}).get('primary_font', 'Inter')}

Return as valid JSON:
{{
  "project_name": "...",
  "duration_seconds": {ad_duration},
  "aspect_ratio": "9:16",
  "timeline": [
    {{
      "clip_number": 1,
      "start_time": "0:00",
      "end_time": "0:03",
      "source": "clip name or AI generation instruction",
      "motion": "slow zoom in / pan right / static / etc",
      "transition_in": "cut / crossfade / etc",
      "text_overlay": {{
        "text": "...",
        "font": "Inter Bold",
        "size": 48,
        "color": "#C9A84C",
        "position": "center",
        "animation": "fade in"
      }},
      "notes": "..."
    }}
  ],
  "audio": {{
    "music_track": "recommended style and tempo",
    "music_source": "Pixabay / Uppbeat / Artlist",
    "volume_level": "30-40% under visuals",
    "sound_effects": ["..."]
  }},
  "color_grading": {{
    "overall": "...",
    "highlights": "warm gold tones",
    "shadows": "deep blacks",
    "contrast": "high"
  }},
  "export_settings": {{
    "resolution": "1080x1920",
    "fps": 30,
    "format": "MP4 H.264",
    "quality": "High"
  }},
  "platform_versions": [
    {{"platform": "Instagram Reels", "aspect": "9:16", "duration": {ad_duration}}},
    {{"platform": "YouTube", "aspect": "16:9", "duration": {ad_duration}}},
    {{"platform": "Feed", "aspect": "1:1", "duration": {ad_duration}}}
  ]
}}"""

    raw = generate(prompt, temperature=0.5)
    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    spec = json.loads(json_str)

    # Save
    today = datetime.now().strftime("%Y-%m-%d")
    spec_path = client_dir / f"capcut_spec_{ad_duration}s_{today}.json"
    client_dir.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(spec, indent=2))
    print(f"[AUROS] CapCut spec saved to {spec_path}")

    return spec


def run(
    company: str,
    task: str = "capcut_spec",
    input_path: str | None = None,
    input_dir: str | None = None,
    duration: int = 30,
    style: str = "cinematic",
) -> dict:
    """Run the editor agent."""
    print(f"[AUROS] Editor Agent starting — {company} — Task: {task}")

    if task == "capcut_spec":
        spec = generate_capcut_spec(company, input_dir, duration, style)
        print(f"[AUROS] Generated CapCut spec with {len(spec.get('timeline', []))} timeline entries")
        return {"status": "complete", "task": task, "spec": spec}

    elif task == "overlay" and input_path:
        output = str(Path(input_path).with_stem(Path(input_path).stem + "_overlay"))
        success = add_text_overlay(input_path, output, company, position="bottom_center")
        return {"status": "complete" if success else "failed", "task": task, "output": output}

    elif task == "color_grade" and input_path:
        output = str(Path(input_path).with_stem(Path(input_path).stem + f"_{style}"))
        success = apply_color_grade(input_path, output, style)
        return {"status": "complete" if success else "failed", "task": task, "output": output}

    elif task == "resize" and input_path:
        output = str(Path(input_path).with_stem(Path(input_path).stem + f"_{style}"))
        success = resize_for_platform(input_path, output, style)
        return {"status": "complete" if success else "failed", "task": task, "output": output}

    elif task == "full_edit" and input_dir:
        # Full edit: concatenate all clips, add color grade, add text overlay
        clips_path = Path(input_dir)
        clips = sorted([str(f) for f in clips_path.iterdir() if f.suffix.lower() in (".mp4", ".mov")])
        if not clips:
            return {"status": "failed", "reason": "no clips found"}

        company_slug = company.lower().replace(" ", "_").replace("'", "")
        client_dir = PORTFOLIO_DIR / f"client_{company_slug}"
        client_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        concat_out = str(client_dir / f"raw_concat_{today}.mp4")
        graded_out = str(client_dir / f"graded_{today}.mp4")
        final_out = str(client_dir / f"final_{today}.mp4")

        # Step 1: Concatenate
        if not concatenate_clips(clips, concat_out):
            return {"status": "failed", "step": "concatenate"}

        # Step 2: Color grade
        if not apply_color_grade(concat_out, graded_out, "auros_gold"):
            return {"status": "failed", "step": "color_grade"}

        # Step 3: Text overlay
        if not add_text_overlay(graded_out, final_out, company, position="bottom_center", font_size=36):
            return {"status": "failed", "step": "text_overlay"}

        print(f"[AUROS] Full edit complete: {final_out}")
        return {"status": "complete", "task": task, "output": final_out}

    else:
        print(f"[AUROS] Unknown task or missing input: {task}")
        return {"status": "failed", "reason": f"unknown task '{task}' or missing input"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Post-Production Editor")
    parser.add_argument("--company", required=True)
    parser.add_argument("--task", default="capcut_spec",
                        choices=["overlay", "color_grade", "resize", "full_edit", "capcut_spec"])
    parser.add_argument("--input", dest="input_path", help="Input video file")
    parser.add_argument("--input-dir", help="Directory of clips")
    parser.add_argument("--duration", type=int, default=30, help="Ad duration in seconds")
    parser.add_argument("--style", default="cinematic", help="Edit style or platform for resize")
    args = parser.parse_args()
    run(company=args.company, task=args.task, input_path=args.input_path,
        input_dir=args.input_dir, duration=args.duration, style=args.style)
