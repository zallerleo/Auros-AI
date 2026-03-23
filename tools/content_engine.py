"""
AUROS AI — Content Engine
Master orchestrator that runs the full content production pipeline end-to-end.

Usage:
    python tools/content_engine.py --exhibition cabinet_of_curiosities
    python tools/content_engine.py --exhibition all
    python tools/content_engine.py --exhibition all --skip-clips  # Use existing clips
    python tools/content_engine.py --exhibition all --dry-run
    python tools/content_engine.py --status  # Show what's been generated
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_utils import CAMPAIGN_COLORS, PROJECT_ROOT

# ── Directories ──────────────────────────────────────────────────────────
CLIPS_DIR = PROJECT_ROOT / ".tmp" / "motion_clips"
VIDEO_OUTPUT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team" / "04_deliverables" / "video_ads_v2"
SOCIAL_OUTPUT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team" / "04_deliverables" / "social_posts_rendered"
LOGS_DIR = PROJECT_ROOT / "logs" / "content_engine"


def show_status():
    """Show current state of all generated content."""
    print(f"\n{'='*60}")
    print(f"  📊 AUROS AI — Content Engine Status")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    total_clips = 0
    total_videos = 0
    total_social = 0

    for exhibition, config in CAMPAIGN_COLORS.items():
        print(f"  🎪 {config['name']}")

        # Motion clips
        clips_path = CLIPS_DIR / exhibition
        clips = list(clips_path.glob("*.mp4")) if clips_path.exists() else []
        total_clips += len(clips)
        print(f"     🎬 Motion clips: {len(clips)}")
        for c in clips:
            size_mb = c.stat().st_size / (1024 * 1024)
            print(f"        - {c.name} ({size_mb:.1f}MB)")

        # Composed videos
        vids_path = VIDEO_OUTPUT_DIR / exhibition
        vids = list(vids_path.glob("*.mp4")) if vids_path.exists() else []
        total_videos += len(vids)
        print(f"     📹 Video ads: {len(vids)}")
        for v in vids:
            size_mb = v.stat().st_size / (1024 * 1024)
            print(f"        - {v.name} ({size_mb:.1f}MB)")

        # Social posts
        social_path = SOCIAL_OUTPUT_DIR / exhibition
        posts = list(social_path.glob("*.png")) if social_path.exists() else []
        total_social += len(posts)
        print(f"     📱 Social posts: {len(posts)}")
        print()

    print(f"  ──────────────────────────────")
    print(f"  Total motion clips: {total_clips}")
    print(f"  Total video ads:    {total_videos}")
    print(f"  Total social posts: {total_social}")
    print(f"{'='*60}\n")


def run_pipeline(
    exhibition: str,
    max_clips: int = 5,
    clip_duration: str = "5",
    video_durations: list[int] = None,
    skip_clips: bool = False,
    skip_compose: bool = False,
    skip_social: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Run the full content production pipeline for one exhibition.

    Steps:
        1. Generate motion clips (fal.ai Kling)
        2. Compose video ads (MoviePy)
        3. Generate social posts (Playwright) — optional
    """
    if video_durations is None:
        video_durations = [15]

    result = {
        "exhibition": exhibition,
        "started_at": datetime.now().isoformat(),
        "steps": {},
        "success": True,
    }

    config = CAMPAIGN_COLORS.get(exhibition)
    if not config:
        print(f"  ❌ Unknown exhibition: {exhibition}")
        return {"exhibition": exhibition, "success": False, "error": "Unknown exhibition"}

    print(f"\n{'='*60}")
    print(f"  🚀 AUROS AI — Content Engine")
    print(f"  Exhibition: {config['name']}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    print(f"{'='*60}\n")

    # ── Step 1: Generate Motion Clips ────────────────────────────────────
    if not skip_clips:
        print(f"  ━━━ Step 1/3: Generate Motion Clips ━━━\n")

        # Check if clips already exist
        clips_dir = CLIPS_DIR / exhibition
        existing_clips = list(clips_dir.glob("*.mp4")) if clips_dir.exists() else []

        if existing_clips and not dry_run:
            print(f"  ℹ️ Found {len(existing_clips)} existing clips. Skipping generation.")
            print(f"     (Use --force-clips to regenerate)")
            result["steps"]["motion_clips"] = {
                "status": "skipped",
                "reason": "clips already exist",
                "count": len(existing_clips),
            }
        else:
            from generate_motion_clips import generate_clips_for_exhibition

            clip_result = generate_clips_for_exhibition(
                exhibition=exhibition,
                max_clips=max_clips,
                duration=clip_duration,
                dry_run=dry_run,
            )

            clips_generated = sum(
                1 for c in clip_result.get("clips", [])
                if c.get("success") or c.get("dry_run")
            )

            result["steps"]["motion_clips"] = {
                "status": "success" if clips_generated > 0 else "failed",
                "count": clips_generated,
                "cost": clip_result.get("total_cost", 0),
            }

            if clips_generated == 0 and not dry_run:
                print(f"\n  ❌ No clips generated. Cannot proceed to composition.")
                result["success"] = False
                return result
    else:
        print(f"  ⏭️ Skipping clip generation (--skip-clips)")
        result["steps"]["motion_clips"] = {"status": "skipped", "reason": "user flag"}

    # ── Step 2: Compose Video Ads ────────────────────────────────────────
    if not skip_compose and not dry_run:
        print(f"\n  ━━━ Step 2/3: Compose Video Ads ━━━\n")

        from compose_video_ad import compose_video_ad

        compose_results = {}
        for duration in video_durations:
            vid_result = compose_video_ad(exhibition, duration)
            compose_results[f"{duration}s"] = vid_result

            if not vid_result.get("success"):
                print(f"  ⚠️ {duration}s video composition failed")

        successful_videos = sum(1 for r in compose_results.values() if r.get("success"))

        result["steps"]["video_composition"] = {
            "status": "success" if successful_videos > 0 else "failed",
            "count": successful_videos,
            "details": compose_results,
        }
    elif dry_run:
        print(f"\n  ⏭️ [DRY RUN] Would compose videos: {video_durations}")
        result["steps"]["video_composition"] = {"status": "dry_run"}
    else:
        print(f"\n  ⏭️ Skipping composition (--skip-compose)")
        result["steps"]["video_composition"] = {"status": "skipped"}

    # ── Step 3: Social Posts ─────────────────────────────────────────────
    if not skip_social and not dry_run:
        print(f"\n  ━━━ Step 3/3: Generate Social Posts ━━━\n")

        # Check if render_social_posts.py exists and is functional
        social_script = PROJECT_ROOT / "tools" / "render_social_posts.py"
        if social_script.exists():
            try:
                import subprocess
                proc = subprocess.run(
                    [sys.executable, str(social_script)],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT),
                )
                if proc.returncode == 0:
                    result["steps"]["social_posts"] = {"status": "success"}
                    print(f"  ✅ Social posts rendered")
                else:
                    result["steps"]["social_posts"] = {
                        "status": "warning",
                        "error": proc.stderr[:200] if proc.stderr else "Unknown error",
                    }
                    print(f"  ⚠️ Social posts had issues (non-critical)")
            except Exception as e:
                result["steps"]["social_posts"] = {"status": "error", "error": str(e)}
                print(f"  ⚠️ Social posts failed: {e}")
        else:
            print(f"  ℹ️ Social post renderer not found (not critical)")
            result["steps"]["social_posts"] = {"status": "skipped", "reason": "script not found"}
    else:
        result["steps"]["social_posts"] = {"status": "skipped"}

    # ── Summary ──────────────────────────────────────────────────────────
    result["completed_at"] = datetime.now().isoformat()

    print(f"\n{'='*60}")
    print(f"  ✅ Pipeline complete for {config['name']}")
    for step_name, step_data in result["steps"].items():
        status_icon = {"success": "✅", "failed": "❌", "skipped": "⏭️",
                       "warning": "⚠️", "dry_run": "🔍"}.get(step_data.get("status"), "❓")
        print(f"     {status_icon} {step_name}: {step_data.get('status')}")
    print(f"{'='*60}\n")

    # Save run log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"{exhibition}_{ts}.json"
    log_path.write_text(json.dumps(result, indent=2, default=str))

    return result


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AUROS AI Content Engine")
    parser.add_argument("--exhibition", type=str, default="cabinet_of_curiosities",
                       help="Exhibition name or 'all'")
    parser.add_argument("--max-clips", type=int, default=5,
                       help="Max motion clips per exhibition (default: 5)")
    parser.add_argument("--clip-duration", type=str, default="5", choices=["5", "10"],
                       help="Motion clip duration (default: 5s)")
    parser.add_argument("--video-durations", type=str, default="15",
                       help="Video ad durations, comma-separated (default: 15)")
    parser.add_argument("--skip-clips", action="store_true",
                       help="Skip motion clip generation (use existing)")
    parser.add_argument("--skip-compose", action="store_true",
                       help="Skip video composition")
    parser.add_argument("--skip-social", action="store_true",
                       help="Skip social post generation")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would happen without calling APIs")
    parser.add_argument("--status", action="store_true",
                       help="Show current status of generated content")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    video_durations = [int(d.strip()) for d in args.video_durations.split(",")]
    exhibitions = list(CAMPAIGN_COLORS.keys()) if args.exhibition == "all" else [args.exhibition]

    all_results = {}
    for exhibition in exhibitions:
        r = run_pipeline(
            exhibition=exhibition,
            max_clips=args.max_clips,
            clip_duration=args.clip_duration,
            video_durations=video_durations,
            skip_clips=args.skip_clips,
            skip_compose=args.skip_compose,
            skip_social=args.skip_social,
            dry_run=args.dry_run,
        )
        all_results[exhibition] = r

    # Final report
    print(f"\n{'='*60}")
    print(f"  📊 CONTENT ENGINE — Final Report")
    print(f"{'='*60}")
    total_cost = 0
    for ex, r in all_results.items():
        success = "✅" if r.get("success") else "❌"
        cost = r.get("steps", {}).get("motion_clips", {}).get("cost", 0)
        total_cost += cost
        print(f"  {success} {CAMPAIGN_COLORS.get(ex, {}).get('name', ex)}")
    print(f"\n  💰 Total API cost: ${total_cost:.2f}")
    print(f"{'='*60}\n")

    return all_results


if __name__ == "__main__":
    main()
