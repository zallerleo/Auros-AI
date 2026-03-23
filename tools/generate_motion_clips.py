"""
AUROS AI — Motion Clip Generator
Converts still exhibition photos into cinematic 3-5 second motion clips via fal.ai Kling.

Usage:
    python tools/generate_motion_clips.py --exhibition cabinet_of_curiosities
    python tools/generate_motion_clips.py --exhibition all
    python tools/generate_motion_clips.py --exhibition titanic --max-clips 3 --duration 5
    python tools/generate_motion_clips.py --test  # Single image test run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

# ── Project imports ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_utils import (
    get_images, CAMPAIGN_COLORS, MEDIA_FOLDER_MAP,
    PROJECT_ROOT, MEDIA_DIR,
)

# ── Configuration ────────────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")

FAL_KEY = os.getenv("FAL_KEY", "")
if not FAL_KEY:
    print("[ERROR] FAL_KEY not found in .env")
    sys.exit(1)

# fal.ai Kling model endpoint — v2.6 Pro for highest quality
MODEL_ID = "fal-ai/kling-video/v2.6/pro/image-to-video"

# Output directory for generated clips
CLIPS_DIR = PROJECT_ROOT / ".tmp" / "motion_clips"

# Default settings
DEFAULT_DURATION = "5"       # 5 or 10 seconds
DEFAULT_ASPECT_RATIO = "9:16"  # Vertical for Reels/TikTok
DEFAULT_CFG_SCALE = 0.5
DEFAULT_NEGATIVE_PROMPT = "blur, distort, low quality, watermark, text overlay, shaky"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds between retries

# ══════════════════════════════════════════════════════════════════════════
# STORY-DRIVEN CLIP SEQUENCES
# Each exhibition tells a STORY: Hook → Discovery → Wonder → Connection → CTA
# Every clip has a ROLE in the narrative arc that drives ticket sales.
# ══════════════════════════════════════════════════════════════════════════

STORY_SEQUENCES = {
    "cabinet_of_curiosities": {
        "narrative": "Mystery → Discovery → Secret World → Desire",
        "clips": [
            {
                "role": "HOOK — Mystery & Intrigue",
                "image": "cabinet_hero_mid.jpg",
                "prompt": (
                    "The mysterious cabinet room comes alive — dust particles floating through beams of "
                    "warm golden light, antique oddities on shelves subtly rattling and glowing as if "
                    "possessed by their stories, shadows dancing across walls, atmospheric fog drifting "
                    "through the space, hyper-realistic cinematic quality, 4K, moody speakeasy atmosphere"
                ),
            },
            {
                "role": "DISCOVERY — Finding the Secret",
                "image": "cabinet_lock_interior.jpg",
                "prompt": (
                    "A vintage vault lock mechanism slowly clicking open, golden sparks of light "
                    "emerging from the keyhole, the heavy door beginning to crack open, revealing "
                    "warm amber light spilling from behind, the thrill of discovering a hidden world, "
                    "dramatic tension, hyper-realistic cinematic 4K quality"
                ),
            },
            {
                "role": "WONDER — Inside the Experience",
                "image": "cabinet_hero_left.jpg",
                "prompt": (
                    "Dramatic reveal of the curiosity cabinet interior — a single spotlight slowly "
                    "illuminating row after row of mysterious artifacts and vintage taxidermy, each "
                    "object pulsing with hidden energy, amber and gold tones, the feeling of stepping "
                    "into a world where every object has a forbidden story, cinematic 4K quality"
                ),
            },
            {
                "role": "CONNECTION — The Social Experience",
                "image": "cabinet_happy_hour.png",
                "prompt": (
                    "Elegant cocktails being crafted in the secret speakeasy — amber liquid swirling "
                    "in crystal glasses, ice cracking in slow motion, warm intimate lighting, friends "
                    "sharing the exclusive experience, laughter and clinking glasses in a hidden world "
                    "behind a locked door, cinematic shallow depth of field, 4K quality"
                ),
            },
            {
                "role": "DESIRE — Leave Them Wanting More",
                "image": "cabinet_promo_2.jpg",
                "prompt": (
                    "The vault door slowly swinging closed, the last sliver of golden speakeasy light "
                    "disappearing, a final glimpse of the magical world inside before the secret is "
                    "sealed again, the feeling that you NEED to experience this before it's gone, "
                    "dramatic amber and black, cinematic 4K quality"
                ),
            },
        ],
    },
    "titanic": {
        "narrative": "Awe → History → Emotion → Human Connection → Urgency",
        "clips": [
            {
                "role": "HOOK — Jaw-Dropping Scale",
                "image": "titanic_grand_staircase.jpg",
                "prompt": (
                    "The legendary Titanic grand staircase comes to life — the ornate chandelier "
                    "swaying gently as if on the open ocean, light refracting through crystal and "
                    "casting prismatic patterns across carved oak railings, spectral figures of "
                    "elegant first-class passengers almost visible descending the stairs, haunting "
                    "yet magnificent, cool blue and warm gold lighting, cinematic 4K quality"
                ),
            },
            {
                "role": "DISCOVERY — Stepping Into History",
                "image": "titanic_hall_1.jpg",
                "prompt": (
                    "Walking through the grand Titanic exhibition hall — the camera slowly floating "
                    "forward through the recreated interior, lights flickering to life as if the ship "
                    "is powering up for the first time in a century, the sheer scale of the recreation "
                    "revealed, cool blue atmospheric lighting with warm accents, majestic and haunting, "
                    "cinematic 4K quality"
                ),
            },
            {
                "role": "WONDER — Touching Real History",
                "image": "titanic_02.jpg",
                "prompt": (
                    "Authentic recovered Titanic artifacts dramatically illuminated — water droplets "
                    "slowly condensing and dripping off preserved objects recovered from the ocean "
                    "floor, each item telling a real human story, dramatic spotlight revealing "
                    "textures untouched for over a century, deeply emotional atmosphere, "
                    "cinematic 4K quality"
                ),
            },
            {
                "role": "CONNECTION — Real Human Stories",
                "image": "titanic_atmosphere_1.jpg",
                "prompt": (
                    "Deep underwater atmosphere — ethereal blue light filtering through ocean water, "
                    "illuminating preserved artifacts, bubbles slowly rising past objects that once "
                    "belonged to real passengers with real dreams, the weight of their stories hanging "
                    "in the air, haunting and deeply moving, emotional museum atmosphere, "
                    "cinematic 4K quality"
                ),
            },
            {
                "role": "URGENCY — Experience It Before It's Gone",
                "image": "titanic_atmosphere_2.jpg",
                "prompt": (
                    "A boarding pass slowly emerging from darkness into a dramatic spotlight, the "
                    "paper trembling slightly, names and dates becoming visible, dust particles "
                    "floating like memories, the realization that this is YOUR boarding pass to "
                    "the experience, deep blue and silver atmosphere, cinematic slow motion, 4K quality"
                ),
            },
        ],
    },
    "thomas_dambo_trolls": {
        "narrative": "Adventure → Discovery → Magic → Joy → Wonder",
        "clips": [
            {
                "role": "HOOK — The Call to Adventure",
                "image": "dambo_explorers_sentosa.jpg",
                "prompt": (
                    "Adventurers discovering a hidden giant troll deep in a tropical forest — the "
                    "camera slowly pushing through dense foliage to reveal a MASSIVE wooden sculpture "
                    "towering above the trees, sunbeams breaking through the canopy, exotic birds "
                    "taking flight in surprise, the sense of stumbling upon something ancient and "
                    "magical, warm tropical colors with lush green and golden light, cinematic 4K"
                ),
            },
            {
                "role": "DISCOVERY — Meeting the First Troll",
                "image": "dambo_golden_rabbit.jpg",
                "prompt": (
                    "The Golden Rabbit troll springs to life in the forest — its giant ears twitching, "
                    "nose wiggling as it surveys the woodland, golden sunlight catching its textured "
                    "wooden surface, small rabbits hopping around the base as if called by their giant "
                    "friend, wildflowers swaying, the magic of art becoming alive, enchanted forest "
                    "atmosphere, cinematic 4K quality"
                ),
            },
            {
                "role": "WONDER — The Forest Awakens",
                "image": "dambo_malins_fountain.jpg",
                "prompt": (
                    "The giant troll fountain sculpture awakens — water beginning to flow from its "
                    "cupped wooden hands, wildflowers blooming in timelapse around its enormous feet, "
                    "golden hour sunlight streaming through the forest canopy, butterflies and "
                    "fireflies emerging and circling the massive figure, the entire forest celebrating, "
                    "magical realism, cinematic 4K quality"
                ),
            },
            {
                "role": "CONNECTION — Falling in Love",
                "image": "dambo_barefoot_frida.jpg",
                "prompt": (
                    "Barefoot Frida the troll sits peacefully as the forest comes alive around her — "
                    "mushrooms sprouting in timelapse at her feet, morning mist swirling around her "
                    "giant wooden form, a single butterfly landing on her nose, her expression seeming "
                    "to shift into the gentlest smile, warm earthy tones with dappled golden sunlight, "
                    "Studio Ghibli-like magical realism, cinematic 4K quality"
                ),
            },
            {
                "role": "DESIRE — There Are More to Find",
                "image": "dambo_pia_peacekeeper.jpg",
                "prompt": (
                    "The towering Pia the Peacekeeper troll slowly turns her wooden head toward "
                    "camera, eyes beginning to glow with warm amber light, her massive frame "
                    "breathing with the forest breeze, birds landing on her outstretched arms, "
                    "dappled sunlight creating a halo — she's inviting you to come find her, "
                    "magical whimsical atmosphere, cinematic 4K quality"
                ),
            },
        ],
    },
}

# Fallback prompts if an image doesn't have a specific prompt
FALLBACK_PROMPTS = {
    "cabinet_of_curiosities":
        "Mysterious speakeasy coming alive — warm amber light, dust particles floating, "
        "antique objects glowing with hidden energy, atmospheric fog, cinematic 4K quality",
    "titanic":
        "Grand Titanic exhibition — dramatic museum lighting, artifacts telling human stories, "
        "cool blue and silver atmosphere, emotional and majestic, cinematic 4K quality",
    "thomas_dambo_trolls":
        "Giant wooden troll sculpture awakening in an enchanted forest — eyes glowing warmly, "
        "leaves and butterflies swirling, golden hour sunlight, magical atmosphere, cinematic 4K quality",
}

# ── Logging ──────────────────────────────────────────────────────────────

class Logger:
    """Simple structured logger with file + console output."""

    def __init__(self, exhibition: str):
        self.log_dir = PROJECT_ROOT / "logs" / "motion_clips"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{exhibition}_{ts}.log"
        self.entries = []

    def log(self, level: str, message: str, **data):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **data,
        }
        self.entries.append(entry)
        prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "COST": "💰"}.get(level, "  ")
        print(f"  {prefix} {message}")
        if data:
            for k, v in data.items():
                print(f"       {k}: {v}")

    def save(self):
        self.log_file.write_text(json.dumps(self.entries, indent=2))
        print(f"\n  📝 Log saved: {self.log_file.relative_to(PROJECT_ROOT)}")


# ── Core Functions ───────────────────────────────────────────────────────

def upload_image_to_fal(image_path: Path) -> str:
    """Upload a local image to fal.ai and return the URL."""
    import fal_client
    url = fal_client.upload_file(image_path)
    return url


def generate_single_clip(
    image_path: Path,
    prompt: str,
    duration: str = DEFAULT_DURATION,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    logger: Logger | None = None,
) -> dict:
    """
    Generate a single motion clip from an image via fal.ai Kling.

    Returns:
        dict with keys: success, video_url, output_path, cost_estimate, error
    """
    import fal_client

    result = {
        "success": False,
        "image": image_path.name,
        "video_url": None,
        "output_path": None,
        "cost_estimate": 0.0,
        "error": None,
        "duration_seconds": int(duration),
        "retries": 0,
    }

    # Validate image exists and is readable
    if not image_path.exists():
        result["error"] = f"Image not found: {image_path}"
        if logger:
            logger.log("ERROR", f"Image not found: {image_path.name}")
        return result

    file_size = image_path.stat().st_size
    if file_size < 1000:  # Less than 1KB = probably corrupt
        result["error"] = f"Image too small ({file_size} bytes), likely corrupt"
        if logger:
            logger.log("ERROR", f"Image too small: {image_path.name} ({file_size}B)")
        return result

    # Upload image to fal.ai
    if logger:
        logger.log("INFO", f"Uploading {image_path.name} ({file_size // 1024}KB)...")

    try:
        image_url = upload_image_to_fal(image_path)
    except Exception as e:
        result["error"] = f"Upload failed: {str(e)}"
        if logger:
            logger.log("ERROR", f"Upload failed: {image_path.name}", error=str(e))
        return result

    # Generate motion clip with retries
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if logger:
                logger.log("INFO", f"Generating clip (attempt {attempt}/{MAX_RETRIES})...",
                          model=MODEL_ID, duration=f"{duration}s", aspect_ratio=aspect_ratio)

            start_time = time.time()

            def on_queue_update(update):
                if isinstance(update, fal_client.InProgress):
                    for log_entry in update.logs:
                        if logger:
                            logger.log("INFO", f"  fal.ai: {log_entry.get('message', '')}")

            api_result = fal_client.subscribe(
                MODEL_ID,
                arguments={
                    "prompt": prompt,
                    "image_url": image_url,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                    "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
                    "cfg_scale": DEFAULT_CFG_SCALE,
                },
                with_logs=True,
                on_queue_update=on_queue_update,
            )

            elapsed = time.time() - start_time

            # Extract video URL
            video_url = api_result.get("video", {}).get("url")
            if not video_url:
                raise ValueError(f"No video URL in response: {json.dumps(api_result, indent=2)[:500]}")

            result["video_url"] = video_url
            result["success"] = True
            result["cost_estimate"] = float(duration) * 0.07  # $0.07/second for Kling 2.5 Turbo
            result["retries"] = attempt - 1

            if logger:
                logger.log("OK", f"Clip generated in {elapsed:.1f}s",
                          video_url=video_url[:80] + "...",
                          cost=f"${result['cost_estimate']:.2f}")

            break  # Success — exit retry loop

        except Exception as e:
            result["retries"] = attempt
            error_msg = str(e)

            if logger:
                logger.log("WARN", f"Attempt {attempt} failed: {error_msg[:200]}")

            if attempt < MAX_RETRIES:
                if logger:
                    logger.log("INFO", f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                result["error"] = f"All {MAX_RETRIES} attempts failed. Last error: {error_msg}"
                if logger:
                    logger.log("ERROR", f"All attempts exhausted for {image_path.name}")

    return result


def download_clip(video_url: str, output_path: Path, logger: Logger | None = None) -> bool:
    """Download a generated video clip to disk with validation."""
    try:
        if logger:
            logger.log("INFO", f"Downloading clip to {output_path.name}...")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(video_url, timeout=120, stream=True)
        response.raise_for_status()

        # Stream download for large files
        total_size = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                total_size += len(chunk)

        # Validate downloaded file
        if total_size < 10000:  # Less than 10KB = probably failed
            if logger:
                logger.log("ERROR", f"Downloaded file too small ({total_size}B)")
            output_path.unlink(missing_ok=True)
            return False

        if logger:
            logger.log("OK", f"Downloaded {output_path.name} ({total_size // 1024}KB)")

        return True

    except Exception as e:
        if logger:
            logger.log("ERROR", f"Download failed: {str(e)}")
        output_path.unlink(missing_ok=True)
        return False


def validate_clip(clip_path: Path, logger: Logger | None = None) -> bool:
    """Validate a downloaded clip is a real video file."""
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(str(clip_path))
        duration = clip.duration
        w, h = clip.size
        fps = clip.fps
        clip.close()

        if duration < 1.0:
            if logger:
                logger.log("WARN", f"Clip too short: {duration:.1f}s")
            return False

        if logger:
            logger.log("OK", f"Validated: {duration:.1f}s, {w}x{h}, {fps}fps")

        return True

    except Exception as e:
        if logger:
            logger.log("ERROR", f"Validation failed: {str(e)}")
        return False


# ── Main Pipeline ────────────────────────────────────────────────────────

def generate_clips_for_exhibition(
    exhibition: str,
    max_clips: int = 5,
    duration: str = DEFAULT_DURATION,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    dry_run: bool = False,
) -> dict:
    """
    Generate motion clips for all images in an exhibition.

    Returns summary dict with results for each clip.
    """
    logger = Logger(exhibition)
    print(f"\n{'='*60}")
    print(f"  🎬 AUROS AI — Motion Clip Generator")
    print(f"  Exhibition: {CAMPAIGN_COLORS.get(exhibition, {}).get('name', exhibition)}")
    print(f"  Model: {MODEL_ID}")
    print(f"  Duration: {duration}s | Aspect: {aspect_ratio}")
    print(f"{'='*60}\n")

    # Get story sequence for this exhibition
    story = STORY_SEQUENCES.get(exhibition)
    if not story:
        logger.log("ERROR", f"No story sequence defined for: {exhibition}")
        logger.save()
        return {"exhibition": exhibition, "success": False, "error": "No story sequence"}

    logger.log("INFO", f"Narrative: {story['narrative']}")

    # Resolve image paths from story sequence
    media_name = MEDIA_FOLDER_MAP.get(exhibition, exhibition)
    media_dir = MEDIA_DIR / media_name

    clip_plan = []
    for scene in story["clips"][:max_clips]:
        image_path = media_dir / scene["image"]
        if image_path.exists():
            clip_plan.append({
                "image_path": image_path,
                "prompt": scene["prompt"],
                "role": scene["role"],
            })
        else:
            logger.log("WARN", f"Image not found: {scene['image']} — skipping")

    if not clip_plan:
        logger.log("ERROR", f"No valid images found for exhibition: {exhibition}")
        logger.save()
        return {"exhibition": exhibition, "success": False, "error": "No valid images"}

    logger.log("INFO", f"Story: {len(clip_plan)} scenes planned")

    # Output directory
    output_dir = CLIPS_DIR / exhibition
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate clips in story order
    results = []
    total_cost = 0.0

    for i, scene in enumerate(clip_plan):
        image_path = scene["image_path"]
        full_prompt = scene["prompt"]
        role = scene["role"]

        print(f"\n  ── Scene {i+1}/{len(clip_plan)}: {role} ──")
        print(f"     Image: {image_path.name}")

        if dry_run:
            logger.log("INFO", f"[DRY RUN] {role}: {image_path.name}")
            logger.log("INFO", f"  Prompt: {full_prompt[:100]}...")
            logger.log("COST", f"  Estimated cost: ${float(duration) * 0.07:.2f}")
            results.append({
                "image": image_path.name,
                "role": role,
                "success": True,
                "cost_estimate": float(duration) * 0.07,
                "dry_run": True,
            })
            total_cost += float(duration) * 0.07
            continue

        # Generate
        clip_result = generate_single_clip(
            image_path=image_path,
            prompt=full_prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            logger=logger,
        )

        if clip_result["success"] and clip_result["video_url"]:
            # Download with story-ordered naming (01_hook, 02_discovery, etc.)
            role_slug = role.split("—")[0].strip().lower().replace(" ", "_")
            output_name = f"{i+1:02d}_{role_slug}_{image_path.stem}_{duration}s.mp4"
            output_path = output_dir / output_name

            downloaded = download_clip(clip_result["video_url"], output_path, logger)

            if downloaded:
                # Validate
                valid = validate_clip(output_path, logger)
                clip_result["output_path"] = str(output_path)
                clip_result["role"] = role
                clip_result["valid"] = valid

                if not valid:
                    logger.log("WARN", f"Clip failed validation, keeping file for review")
            else:
                clip_result["success"] = False
                clip_result["error"] = "Download failed"

        clip_result["role"] = role
        results.append(clip_result)
        total_cost += clip_result.get("cost_estimate", 0.0)

        # Brief pause between API calls to avoid rate limits
        if i < len(clip_plan) - 1:
            time.sleep(2)

    # Summary
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful

    print(f"\n{'='*60}")
    print(f"  📊 Results Summary")
    print(f"  ✅ Successful: {successful}/{len(results)}")
    if failed:
        print(f"  ❌ Failed: {failed}")
    print(f"  💰 Total cost: ${total_cost:.2f}")
    print(f"  📁 Output: {output_dir.relative_to(PROJECT_ROOT)}")
    print(f"{'='*60}\n")

    logger.log("COST", f"Total batch cost: ${total_cost:.2f}",
              successful=successful, failed=failed)
    logger.save()

    # Save manifest
    manifest = {
        "exhibition": exhibition,
        "generated_at": datetime.now().isoformat(),
        "model": MODEL_ID,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "total_cost": total_cost,
        "clips": results,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    return manifest


def run_test(duration: str = "5") -> dict:
    """Quick test: generate 1 clip from the first cabinet image."""
    print("\n  🧪 TEST MODE — generating 1 clip to verify pipeline\n")
    images = get_images("cabinet_of_curiosities")
    if not images:
        print("  ❌ No test images found")
        return {"success": False}

    return generate_clips_for_exhibition(
        exhibition="cabinet_of_curiosities",
        max_clips=1,
        duration=duration,
    )


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AUROS AI Motion Clip Generator")
    parser.add_argument("--exhibition", type=str, default="cabinet_of_curiosities",
                       help="Exhibition name or 'all'")
    parser.add_argument("--max-clips", type=int, default=5,
                       help="Max clips to generate per exhibition (default: 5)")
    parser.add_argument("--duration", type=str, default="5", choices=["5", "10"],
                       help="Clip duration in seconds (default: 5)")
    parser.add_argument("--aspect-ratio", type=str, default="9:16",
                       choices=["9:16", "16:9", "1:1"],
                       help="Aspect ratio (default: 9:16 vertical)")
    parser.add_argument("--test", action="store_true",
                       help="Test mode: generate 1 clip only")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run: show what would be generated without calling API")

    args = parser.parse_args()

    if args.test:
        return run_test(args.duration)

    exhibitions = list(CAMPAIGN_COLORS.keys()) if args.exhibition == "all" else [args.exhibition]

    all_results = {}
    for exhibition in exhibitions:
        if exhibition not in CAMPAIGN_COLORS:
            print(f"  ⚠️ Unknown exhibition: {exhibition}")
            print(f"  Available: {', '.join(CAMPAIGN_COLORS.keys())}")
            continue

        result = generate_clips_for_exhibition(
            exhibition=exhibition,
            max_clips=args.max_clips,
            duration=args.duration,
            aspect_ratio=args.aspect_ratio,
            dry_run=args.dry_run,
        )
        all_results[exhibition] = result

    return all_results


if __name__ == "__main__":
    main()
