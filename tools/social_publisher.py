#!/usr/bin/env python3
"""
AUROS AI — Social Media Publisher
Publishes and schedules social media posts via the Buffer API.

Usage:
    python tools/social_publisher.py --profiles
    python tools/social_publisher.py --post "Hello world" --profile-id abc123
    python tools/social_publisher.py --post "Hello world" --profile-id abc123 --image /path/to/image.jpg
    python tools/social_publisher.py --post "Hello world" --profile-id abc123 --schedule-at "2026-04-01T10:00:00Z"
    python tools/social_publisher.py --schedule calendar.json --profile-id abc123
    python tools/social_publisher.py --schedule calendar.json --profile-id abc123 --dry-run
    python tools/social_publisher.py --pending --profile-id abc123
    python tools/social_publisher.py --sent --profile-id abc123
"""

from __future__ import annotations

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import requests

# ── Project setup ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.shared.config import PORTFOLIO_DIR

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "")
BUFFER_BASE_URL = "https://api.bufferapp.com/1/"

logger = logging.getLogger("auros.social_publisher")

# ── Timezone mapping for calendar optimal_time parsing ───────────────────────

_TZ_OFFSETS = {
    "EST": "-05:00", "EDT": "-04:00",
    "CST": "-06:00", "CDT": "-05:00",
    "MST": "-07:00", "MDT": "-06:00",
    "PST": "-08:00", "PDT": "-07:00",
    "UTC": "+00:00", "GMT": "+00:00",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_token() -> str:
    """Return the Buffer access token, raising if missing."""
    token = BUFFER_ACCESS_TOKEN
    if not token:
        raise EnvironmentError(
            "BUFFER_ACCESS_TOKEN is not set. "
            "Add it to your .env file (get one at https://bufferapp.com/developers/apps)."
        )
    return token


def _api_get(endpoint: str, params: dict | None = None) -> dict | list:
    """Make an authenticated GET request to Buffer API."""
    token = _get_token()
    url = f"{BUFFER_BASE_URL}{endpoint}"
    params = params or {}
    params["access_token"] = token

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _api_post(endpoint: str, data: dict | None = None) -> dict:
    """Make an authenticated POST request to Buffer API."""
    token = _get_token()
    url = f"{BUFFER_BASE_URL}{endpoint}"
    data = data or {}
    data["access_token"] = token

    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_optimal_time(date_str: str, time_str: str) -> str:
    """
    Parse a calendar date + optimal_time string into an ISO 8601 timestamp.

    Examples:
        date_str="2026-04-01", time_str="10:00 AM EST"  ->  "2026-04-01T10:00:00-05:00"
        date_str="2026-04-01", time_str="7:00 PM EDT"   ->  "2026-04-01T19:00:00-04:00"
    """
    parts = time_str.strip().split()
    if len(parts) < 2:
        # Fallback: assume noon UTC
        return f"{date_str}T12:00:00+00:00"

    time_part = parts[0]          # "10:00"
    ampm = parts[1].upper()       # "AM" or "PM"
    tz_abbr = parts[2].upper() if len(parts) > 2 else "EST"

    hour, minute = map(int, time_part.split(":"))
    if ampm == "PM" and hour != 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0

    tz_offset = _TZ_OFFSETS.get(tz_abbr, "-05:00")
    return f"{date_str}T{hour:02d}:{minute:02d}:00{tz_offset}"


def _upload_image(image_path: str) -> dict:
    """
    Upload an image to Buffer's media endpoint.
    Returns the media dict with 'picture' and 'thumbnail' URLs.
    """
    token = _get_token()
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Determine MIME type from extension
    ext = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/jpeg")

    # Buffer accepts media as a URL or via their upload flow.
    # For local files, we use the updates/create endpoint with media[photo] directly.
    # The actual upload is handled inline during post creation.
    return {"local_path": str(path), "mime": mime}


# ── Core Functions ───────────────────────────────────────────────────────────

def get_profiles() -> list[dict]:
    """
    List all connected social media profiles on the Buffer account.
    Returns a list of profile dicts with id, service, formatted_username, etc.
    """
    profiles = _api_get("profiles.json")
    return profiles


def create_post(
    profile_ids: list[str],
    text: str,
    media_urls: list[str] | None = None,
    scheduled_at: str | None = None,
    image_path: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Create or schedule a post via Buffer.

    Args:
        profile_ids: List of Buffer profile IDs to post to.
        text: The post text/caption.
        media_urls: Optional list of public image URLs to attach.
        scheduled_at: ISO 8601 timestamp for scheduling. If None, adds to queue.
        image_path: Optional local image path to attach via photo upload.
        dry_run: If True, print what would happen without posting.

    Returns:
        Buffer API response dict.
    """
    data = {
        "text": text,
        "profile_ids[]": profile_ids,
    }

    # Attach media URLs
    if media_urls:
        for i, url in enumerate(media_urls):
            data[f"media[photo]"] = media_urls[0]  # Buffer v1 supports one photo
            if len(media_urls) > 1:
                data[f"media[thumbnail]"] = media_urls[1]

    # Attach local image via photo parameter
    if image_path:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        data["media[photo]"] = f"file://{p.resolve()}"
        logger.info(f"Attaching image: {image_path}")

    # Schedule or add to queue
    if scheduled_at:
        data["scheduled_at"] = scheduled_at
        data["now"] = "false"
    else:
        data["now"] = "false"  # Add to queue (Buffer decides timing)

    if dry_run:
        return {
            "dry_run": True,
            "action": "schedule" if scheduled_at else "queue",
            "profiles": profile_ids,
            "text": text[:100] + ("..." if len(text) > 100 else ""),
            "scheduled_at": scheduled_at,
            "media_urls": media_urls,
            "image_path": image_path,
        }

    result = _api_post("updates/create.json", data)

    if not result.get("success"):
        error_msg = result.get("message", "Unknown error from Buffer API")
        raise RuntimeError(f"Buffer API error: {error_msg}")

    logger.info(f"Post created: {result.get('updates', [{}])[0].get('id', 'N/A')}")
    return result


def create_posts_from_calendar(
    calendar_json_path: str,
    profile_ids: list[str],
    platform_filter: str | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Bulk schedule posts from a content calendar JSON file.

    The calendar JSON is expected to follow the AUROS content calendar format:
    {
        "company": "...",
        "month": "2026-04",
        "calendar": [
            {
                "date": "2026-04-01",
                "platform": "instagram",
                "caption": "...",
                "hashtags": ["#tag1", "#tag2"],
                "optimal_time": "10:00 AM EST",
                "image_path": "/path/to/image.jpg"  (optional)
            },
            ...
        ]
    }

    Args:
        calendar_json_path: Path to the content calendar JSON file.
        profile_ids: List of Buffer profile IDs to post to.
        platform_filter: Optional platform name to filter posts (e.g., "instagram").
        dry_run: If True, print what would happen without posting.

    Returns:
        List of results for each scheduled post.
    """
    cal_path = Path(calendar_json_path)
    if not cal_path.exists():
        raise FileNotFoundError(f"Calendar file not found: {calendar_json_path}")

    with open(cal_path) as f:
        calendar_data = json.load(f)

    posts = calendar_data.get("calendar", [])
    if not posts:
        logger.warning("No posts found in calendar file.")
        return []

    results = []
    success_count = 0
    error_count = 0

    print(f"\n{'='*60}")
    print(f"  AUROS Social Publisher — Bulk Schedule")
    print(f"  Calendar: {cal_path.name}")
    print(f"  Company:  {calendar_data.get('company', 'Unknown')}")
    print(f"  Month:    {calendar_data.get('month', 'Unknown')}")
    print(f"  Posts:    {len(posts)}")
    if platform_filter:
        print(f"  Filter:   {platform_filter}")
    if dry_run:
        print(f"  Mode:     DRY RUN")
    print(f"{'='*60}\n")

    for i, post in enumerate(posts, 1):
        # Apply platform filter
        platform = post.get("platform", "").lower()
        if platform_filter and platform != platform_filter.lower():
            continue

        date = post.get("date", "")
        caption = post.get("caption", "")
        hashtags = post.get("hashtags", [])
        optimal_time = post.get("optimal_time", "12:00 PM EST")
        image_path = post.get("image_path")

        # Build full post text: caption + hashtags
        hashtag_str = " ".join(hashtags) if hashtags else ""
        full_text = f"{caption}\n\n{hashtag_str}".strip() if hashtag_str else caption

        # Parse schedule time
        scheduled_at = _parse_optimal_time(date, optimal_time)

        # Status line
        status_prefix = "[DRY RUN] " if dry_run else ""
        print(f"  {status_prefix}[{i}/{len(posts)}] {date} | {platform:10s} | {optimal_time:14s} | {caption[:50]}...")

        try:
            result = create_post(
                profile_ids=profile_ids,
                text=full_text,
                scheduled_at=scheduled_at,
                image_path=image_path,
                dry_run=dry_run,
            )
            results.append({"date": date, "platform": platform, "status": "ok", "result": result})
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to schedule post for {date}: {error_msg}")
            print(f"    ERROR: {error_msg}")
            results.append({"date": date, "platform": platform, "status": "error", "error": error_msg})
            error_count += 1

    print(f"\n{'='*60}")
    print(f"  Results: {success_count} scheduled, {error_count} errors")
    print(f"{'='*60}\n")

    return results


def get_pending_posts(profile_id: str) -> list[dict]:
    """
    Get all pending (queued) posts for a profile.

    Args:
        profile_id: Buffer profile ID.

    Returns:
        List of pending update dicts.
    """
    result = _api_get(f"profiles/{profile_id}/updates/pending.json")
    return result.get("updates", [])


def get_sent_posts(profile_id: str, page: int = 1, count: int = 20) -> list[dict]:
    """
    Get sent (published) posts for a profile.

    Args:
        profile_id: Buffer profile ID.
        page: Page number for pagination.
        count: Number of posts per page.

    Returns:
        List of sent update dicts.
    """
    result = _api_get(
        f"profiles/{profile_id}/updates/sent.json",
        params={"page": page, "count": count},
    )
    return result.get("updates", [])


# ── Display Helpers ──────────────────────────────────────────────────────────

def _display_profiles(profiles: list[dict]) -> None:
    """Pretty-print connected profiles."""
    print(f"\n{'='*60}")
    print(f"  Buffer Connected Profiles")
    print(f"{'='*60}\n")

    if not profiles:
        print("  No profiles found. Connect accounts at https://buffer.com")
        return

    for p in profiles:
        status = "active" if not p.get("paused", False) else "PAUSED"
        print(f"  [{status:6s}] {p.get('formatted_service', 'unknown'):12s} | "
              f"@{p.get('formatted_username', 'N/A'):20s} | "
              f"ID: {p.get('id', 'N/A')}")

    print(f"\n  Total: {len(profiles)} profiles\n")


def _display_updates(updates: list[dict], label: str) -> None:
    """Pretty-print a list of Buffer updates."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}\n")

    if not updates:
        print("  No posts found.\n")
        return

    for u in updates:
        text_preview = u.get("text", "")[:60]
        if len(u.get("text", "")) > 60:
            text_preview += "..."
        scheduled = u.get("scheduled_at") or u.get("sent_at") or "N/A"
        if isinstance(scheduled, (int, float)):
            scheduled = datetime.fromtimestamp(scheduled, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        status = u.get("status", "unknown")
        print(f"  [{status:8s}] {scheduled:22s} | {text_preview}")
        print(f"             ID: {u.get('id', 'N/A')}")

    print(f"\n  Total: {len(updates)} posts\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AUROS AI — Social Media Publisher (Buffer API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --profiles
  %(prog)s --post "Hello world!" --profile-id abc123
  %(prog)s --post "Check this out" --profile-id abc123 --image photo.jpg
  %(prog)s --post "Scheduled post" --profile-id abc123 --schedule-at "2026-04-01T10:00:00-05:00"
  %(prog)s --schedule calendar.json --profile-id abc123
  %(prog)s --schedule calendar.json --profile-id abc123 --dry-run
  %(prog)s --pending --profile-id abc123
  %(prog)s --sent --profile-id abc123
        """,
    )

    # Actions (mutually exclusive)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--profiles", action="store_true", help="List connected social media profiles")
    action.add_argument("--post", type=str, metavar="TEXT", help="Create a post with the given text")
    action.add_argument("--schedule", type=str, metavar="CALENDAR_JSON", help="Bulk schedule from content calendar JSON")
    action.add_argument("--pending", action="store_true", help="Show pending/queued posts")
    action.add_argument("--sent", action="store_true", help="Show sent/published posts")

    # Options
    parser.add_argument("--profile-id", type=str, action="append", dest="profile_ids",
                        help="Buffer profile ID (can specify multiple times)")
    parser.add_argument("--image", type=str, help="Local image path to attach to a post")
    parser.add_argument("--media-url", type=str, action="append", dest="media_urls",
                        help="Public image URL to attach (can specify multiple)")
    parser.add_argument("--schedule-at", type=str, help="ISO 8601 timestamp for scheduling a single post")
    parser.add_argument("--platform", type=str, help="Filter calendar posts by platform (e.g., instagram)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without posting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="[AUROS] %(levelname)s: %(message)s")

    try:
        # ── List profiles ────────────────────────────────────────────
        if args.profiles:
            profiles = get_profiles()
            _display_profiles(profiles)

        # ── Create single post ───────────────────────────────────────
        elif args.post:
            if not args.profile_ids:
                parser.error("--post requires at least one --profile-id")

            result = create_post(
                profile_ids=args.profile_ids,
                text=args.post,
                media_urls=args.media_urls,
                scheduled_at=args.schedule_at,
                image_path=args.image,
                dry_run=args.dry_run,
            )

            if args.dry_run:
                print(f"\n[DRY RUN] Would create post:")
                print(json.dumps(result, indent=2))
            else:
                print(f"\nPost created successfully!")
                updates = result.get("updates", [])
                if updates:
                    for u in updates:
                        print(f"  ID: {u.get('id')}")
                        print(f"  Status: {u.get('status')}")
                        if u.get('scheduled_at'):
                            sched = datetime.fromtimestamp(
                                u['scheduled_at'], tz=timezone.utc
                            ).strftime("%Y-%m-%d %H:%M UTC")
                            print(f"  Scheduled: {sched}")

        # ── Bulk schedule from calendar ──────────────────────────────
        elif args.schedule:
            if not args.profile_ids:
                parser.error("--schedule requires at least one --profile-id")

            results = create_posts_from_calendar(
                calendar_json_path=args.schedule,
                profile_ids=args.profile_ids,
                platform_filter=args.platform,
                dry_run=args.dry_run,
            )

            # Save results log
            log_dir = PROJECT_ROOT / "logs" / "social_publisher"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"schedule_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_path, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "calendar": args.schedule,
                    "profile_ids": args.profile_ids,
                    "dry_run": args.dry_run,
                    "results": results,
                }, f, indent=2)
            print(f"  Log saved: {log_path}")

        # ── Pending posts ────────────────────────────────────────────
        elif args.pending:
            if not args.profile_ids:
                parser.error("--pending requires at least one --profile-id")
            for pid in args.profile_ids:
                updates = get_pending_posts(pid)
                _display_updates(updates, f"Pending Posts — Profile {pid}")

        # ── Sent posts ───────────────────────────────────────────────
        elif args.sent:
            if not args.profile_ids:
                parser.error("--sent requires at least one --profile-id")
            for pid in args.profile_ids:
                updates = get_sent_posts(pid)
                _display_updates(updates, f"Sent Posts — Profile {pid}")

    except EnvironmentError as e:
        print(f"\n[ERROR] Configuration issue: {e}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "N/A"
        body = ""
        if e.response is not None:
            try:
                body = e.response.json().get("message", e.response.text[:200])
            except Exception:
                body = e.response.text[:200]
        print(f"\n[ERROR] Buffer API returned HTTP {status}: {body}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
