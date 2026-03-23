"""
AUROS AI — Content Production Utilities
Shared helpers for rendering social posts and video ads.
"""
from __future__ import annotations

import json
import base64
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team" / "media" / "proposal_ready"
CONTENT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team" / "03_content"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# ── Brand tokens ──────────────────────────────────────────────────────────

BRAND_COLORS = {
    "midnight": "#0B0F1A",
    "navy": "#111827",
    "gold": "#C9A84C",
    "gold_light": "#E8C96A",
    "white": "#FAFAF8",
    "off_white": "#F0EDE6",
    "gray": "#6B7280",
    "gray_light": "#9CA3AF",
}

CAMPAIGN_COLORS = {
    "cabinet_of_curiosities": {"accent": "#D4A056", "bg": "#8B4513", "name": "Cabinet of Curiosities"},
    "titanic": {"accent": "#7EB3D8", "bg": "#1F3A52", "name": "Titanic: The Exhibition"},
    "thomas_dambo_trolls": {"accent": "#6DB89A", "bg": "#1B4D3E", "name": "Thomas Dambo Trolls"},
}

# Map exhibition folder names to media folder names
MEDIA_FOLDER_MAP = {
    "cabinet_of_curiosities": "cabinet",
    "titanic": "titanic",
    "thomas_dambo_trolls": "dambo",
}

# ── Image selection ───────────────────────────────────────────────────────

def get_images(exhibition: str) -> list[Path]:
    """Get all available images for an exhibition."""
    media_name = MEDIA_FOLDER_MAP.get(exhibition, exhibition)
    img_dir = MEDIA_DIR / media_name
    if not img_dir.exists():
        return []
    return sorted(f for f in img_dir.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png"))


def pick_image(exhibition: str, index: int = 0) -> Path | None:
    """Pick an image for the exhibition by cycling through available images."""
    images = get_images(exhibition)
    if not images:
        return None
    return images[index % len(images)]


def image_to_base64(path: Path) -> str:
    """Convert image to base64 data URI."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/jpeg;base64,{b64}"


def image_to_file_uri(path: Path) -> str:
    """Convert image path to file:// URI."""
    return f"file://{path.resolve()}"


# ── Social post normalizer ────────────────────────────────────────────────

def load_social_posts(exhibition: str) -> list[dict]:
    """Load and normalize social posts from any exhibition JSON schema."""
    path = CONTENT_DIR / exhibition / "social_posts_2026-03-22.json"
    if not path.exists():
        return []

    raw = json.loads(path.read_text())

    # Handle different root structures
    if isinstance(raw, list):
        posts = raw
    elif isinstance(raw, dict):
        posts = raw.get("posts", raw.get("social_posts", []))
    else:
        return []

    normalized = []
    for i, p in enumerate(posts):
        post = {
            "index": i,
            "exhibition": exhibition,
            "platform": p.get("platform", "Instagram"),
            "format": _detect_format(p),
            "hook": _extract_hook(p),
            "body": _extract_body(p),
            "cta": p.get("cta", ""),
            "visual_direction": p.get("visual_description", p.get("visual_direction", "")),
            "hashtags": _extract_hashtags(p),
            "slides": _extract_slides(p),
        }
        normalized.append(post)

    return normalized


def _detect_format(p: dict) -> str:
    fmt = p.get("format", "").lower()
    if "carousel" in fmt:
        return "carousel"
    if "reel" in fmt or "video" in fmt:
        return "reel"
    if "story" in fmt:
        return "story"
    if p.get("slides"):
        return "carousel"
    return "feed"


def _extract_hook(p: dict) -> str:
    if p.get("hook"):
        return p["hook"]
    copy = p.get("copy", p.get("caption", ""))
    # First line is usually the hook
    lines = copy.strip().split("\n")
    return lines[0] if lines else ""


def _extract_body(p: dict) -> str:
    copy = p.get("copy", p.get("caption", ""))
    lines = copy.strip().split("\n")
    # Skip first line (hook) and hashtag lines
    body_lines = [l for l in lines[1:] if not l.strip().startswith("#")]
    return "\n".join(body_lines).strip()


def _extract_hashtags(p: dict) -> list[str]:
    if p.get("hashtags"):
        return p["hashtags"] if isinstance(p["hashtags"], list) else [p["hashtags"]]
    copy = p.get("copy", p.get("caption", ""))
    return re.findall(r"#\w+", copy)


def _extract_slides(p: dict) -> list[str]:
    if p.get("slides"):
        if isinstance(p["slides"], list):
            return [s if isinstance(s, str) else s.get("text", s.get("copy", str(s))) for s in p["slides"]]
    # Try to extract from copy
    copy = p.get("copy", "")
    slide_matches = re.findall(r"Slide \d+:\s*(.+?)(?:\n|$)", copy)
    return slide_matches


# ── Video script normalizer ──────────────────────────────────────────────

def load_video_scripts(exhibition: str) -> list[dict]:
    """Load and normalize video scripts from exhibition JSON."""
    path = CONTENT_DIR / exhibition / "video_scripts_2026-03-22.json"
    if not path.exists():
        return []

    raw = json.loads(path.read_text())

    if isinstance(raw, list):
        scripts = raw
    elif isinstance(raw, dict):
        scripts = raw.get("scripts", raw.get("video_scripts", []))
    else:
        return []

    normalized = []
    for s in scripts:
        duration = s.get("duration", "15s")
        if isinstance(duration, str):
            duration_sec = int(re.sub(r"[^0-9]", "", duration) or "15")
        else:
            duration_sec = int(duration)

        script = {
            "exhibition": exhibition,
            "duration_seconds": duration_sec,
            "title": s.get("title", s.get("name", "")),
            "shots": [],
            "cta": s.get("cta", ""),
        }

        for shot in s.get("shots", []):
            script["shots"].append({
                "text_overlay": shot.get("text_overlay", shot.get("text", "")),
                "visual": shot.get("visual", shot.get("visual_description", "")),
                "duration": shot.get("duration", shot.get("duration_seconds", 3)),
            })

        normalized.append(script)

    return normalized
