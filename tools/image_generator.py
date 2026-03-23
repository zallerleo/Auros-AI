#!/usr/bin/env python3
"""
AUROS AI — Marketing Image Generator
Generates marketing images via fal.ai's REST API (Flux Pro / Flux Dev).

Usage (CLI):
    python tools/image_generator.py --prompt "coffee shop interior" --style hero --output output.png
    python tools/image_generator.py --prompt "luxury watch on marble" --style product --size 1080x1080
    python tools/image_generator.py --prompt "team meeting" --style social_story --size 1080x1920

Usage (Python):
    from tools.image_generator import generate_image
    path = generate_image("coffee shop interior, warm lighting", style="hero")
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Resolve project root so we can import the shared config regardless of cwd
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent

# Add project root to sys.path so `agents._core.shared.config` is importable
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents._core.shared.config import FAL_API_KEY, PORTFOLIO_DIR  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("image_generator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODELS = {
    "flux-pro": "fal-ai/flux-pro/v1.1-ultra",
    "flux-dev": "fal-ai/flux/dev",
}

DEFAULT_MODEL = "flux-pro"

# Style presets: (prompt_prefix, default_aspect_ratio)
STYLES = {
    "hero": {
        "prefix": "cinematic wide shot, dramatic lighting, editorial quality, ",
        "aspect_ratio": "16:9",
    },
    "product": {
        "prefix": "professional marketing photograph, high-end brand campaign, studio lighting, 8k resolution, ",
        "aspect_ratio": "1:1",
    },
    "social_feed": {
        "prefix": "modern social media design, clean composition, bold typography space, ",
        "aspect_ratio": "1:1",
    },
    "social_story": {
        "prefix": "modern social media design, clean composition, bold typography space, vertical format, ",
        "aspect_ratio": "9:16",
    },
    "ad_landscape": {
        "prefix": "professional marketing photograph, high-end brand campaign, studio lighting, 8k resolution, ",
        "aspect_ratio": "16:9",
    },
    "ad_portrait": {
        "prefix": "professional marketing photograph, high-end brand campaign, studio lighting, 8k resolution, ",
        "aspect_ratio": "4:5",
    },
}

# Map WxH shorthand to aspect ratios understood by fal.ai
SIZE_TO_ASPECT = {
    "1920x1080": "16:9",
    "1080x1920": "9:16",
    "1080x1080": "1:1",
    "1080x1350": "4:5",
    "1200x628": "16:9",
}

FAL_QUEUE_URL = "https://queue.fal.run"
FAL_STATUS_URL = "https://queue.fal.run"

POLL_INTERVAL = 2  # seconds
MAX_POLL_TIME = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Core API interaction
# ---------------------------------------------------------------------------

def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }


def _submit_request(model_id: str, payload: dict, api_key: str) -> dict:
    """Submit an image generation request to fal.ai's queue."""
    url = f"{FAL_QUEUE_URL}/{model_id}"
    logger.info("Submitting request to %s", url)

    resp = requests.post(url, json=payload, headers=_headers(api_key), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _poll_for_result(model_id: str, request_id: str, api_key: str) -> dict:
    """Poll fal.ai queue until the result is ready or timeout is reached."""
    status_url = f"{FAL_STATUS_URL}/{model_id}/requests/{request_id}/status"
    result_url = f"{FAL_QUEUE_URL}/{model_id}/requests/{request_id}"

    start = time.time()
    while time.time() - start < MAX_POLL_TIME:
        resp = requests.get(status_url, headers=_headers(api_key), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "COMPLETED":
            logger.info("Generation completed. Fetching result.")
            result_resp = requests.get(result_url, headers=_headers(api_key), timeout=30)
            result_resp.raise_for_status()
            return result_resp.json()

        if status in ("FAILED", "CANCELLED"):
            error_msg = data.get("error", "Unknown error from fal.ai")
            raise RuntimeError(f"Image generation {status.lower()}: {error_msg}")

        logger.info("Status: %s — polling again in %ds", status, POLL_INTERVAL)
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Image generation timed out after {MAX_POLL_TIME}s")


def _download_image(image_url: str, output_path: Path) -> Path:
    """Download the generated image to a local file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading image to %s", output_path)

    resp = requests.get(image_url, timeout=60, stream=True)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Saved %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)
    return output_path


# ---------------------------------------------------------------------------
# Prompt engineering
# ---------------------------------------------------------------------------

def _build_prompt(user_prompt: str, style: str) -> str:
    """Wrap the user prompt with marketing-optimized quality boosters."""
    style_cfg = STYLES.get(style)
    if not style_cfg:
        raise ValueError(f"Unknown style '{style}'. Choose from: {', '.join(STYLES)}")
    return style_cfg["prefix"] + user_prompt


def _resolve_aspect_ratio(style: str, size: Optional[str]) -> str:
    """Determine aspect ratio from explicit size or style default."""
    if size:
        ar = SIZE_TO_ASPECT.get(size)
        if ar:
            return ar
        # Try interpreting as direct aspect ratio (e.g. "16:9")
        if ":" in size:
            return size
        raise ValueError(
            f"Unrecognised size '{size}'. Use WxH (e.g. 1080x1080) or ratio (e.g. 16:9). "
            f"Known sizes: {', '.join(SIZE_TO_ASPECT)}"
        )
    return STYLES[style]["aspect_ratio"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_image(
    prompt: str,
    style: str = "hero",
    output_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    size: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """
    Generate a marketing image and return the local file path.

    Args:
        prompt:      Description of the desired image.
        style:       One of hero, product, social_feed, social_story, ad_landscape, ad_portrait.
        output_path: Where to save the image. Auto-generated in portfolio/ if omitted.
        model:       "flux-pro" (default, photorealistic) or "flux-dev" (faster/cheaper).
        size:        Optional WxH string (e.g. "1080x1080") or aspect ratio ("4:5").
        api_key:     fal.ai API key. Falls back to config / env.

    Returns:
        Absolute path to the saved image file.
    """
    # --- Validate inputs ---
    key = api_key or FAL_API_KEY
    if not key:
        raise EnvironmentError(
            "FAL_API_KEY is not set. Add it to your .env file or pass it explicitly."
        )

    if model not in MODELS:
        raise ValueError(f"Unknown model '{model}'. Choose from: {', '.join(MODELS)}")

    if style not in STYLES:
        raise ValueError(f"Unknown style '{style}'. Choose from: {', '.join(STYLES)}")

    model_id = MODELS[model]
    enhanced_prompt = _build_prompt(prompt, style)
    aspect_ratio = _resolve_aspect_ratio(style, size)

    logger.info("Model: %s | Style: %s | Aspect: %s", model, style, aspect_ratio)
    logger.info("Enhanced prompt: %s", enhanced_prompt)

    # --- Build payload ---
    payload = {
        "prompt": enhanced_prompt,
        "num_images": 1,
        "enable_safety_checker": True,
    }

    # flux-pro/v1.1-ultra uses aspect_ratio; flux/dev uses image_size
    if model == "flux-pro":
        payload["aspect_ratio"] = aspect_ratio
    else:
        # flux-dev expects image_size as an object or preset
        _ar_to_size = {
            "16:9": {"width": 1344, "height": 768},
            "9:16": {"width": 768, "height": 1344},
            "1:1":  {"width": 1024, "height": 1024},
            "4:5":  {"width": 896, "height": 1120},
        }
        payload["image_size"] = _ar_to_size.get(aspect_ratio, {"width": 1024, "height": 1024})

    # --- Submit & poll ---
    submit_resp = _submit_request(model_id, payload, key)

    # fal.ai may return the result immediately or give us a request_id to poll
    if "images" in submit_resp:
        result = submit_resp
    elif "request_id" in submit_resp:
        request_id = submit_resp["request_id"]
        logger.info("Queued — request_id: %s", request_id)
        result = _poll_for_result(model_id, request_id, key)
    else:
        raise RuntimeError(f"Unexpected response from fal.ai: {submit_resp}")

    # --- Extract image URL ---
    images = result.get("images", [])
    if not images:
        raise RuntimeError("fal.ai returned no images. Response: " + str(result))

    image_url = images[0].get("url")
    if not image_url:
        raise RuntimeError("No URL in fal.ai image response: " + str(images[0]))

    # --- Determine output path ---
    if output_path:
        dest = Path(output_path).resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c if c.isalnum() or c in " _-" else "" for c in prompt)[:50].strip().replace(" ", "_")
        filename = f"{timestamp}_{style}_{safe_prompt}.png"
        dest = PORTFOLIO_DIR / "generated" / filename

    return str(_download_image(image_url, dest))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AUROS AI — Generate marketing images via fal.ai",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --prompt "coffee shop interior, warm lighting" --style hero --output output.png
  %(prog)s --prompt "luxury watch on marble" --style product --size 1080x1080
  %(prog)s --prompt "team meeting" --style social_story --size 1080x1920
  %(prog)s --prompt "sunset cityscape" --style ad_landscape --model flux-dev
        """,
    )
    parser.add_argument("--prompt", required=True, help="Image description")
    parser.add_argument(
        "--style",
        default="hero",
        choices=list(STYLES.keys()),
        help="Marketing style preset (default: hero)",
    )
    parser.add_argument("--output", default=None, help="Output file path (auto-generated if omitted)")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=list(MODELS.keys()),
        help="fal.ai model (default: flux-pro)",
    )
    parser.add_argument("--size", default=None, help="Image size as WxH (e.g. 1080x1080) or aspect ratio (e.g. 4:5)")
    parser.add_argument("--api-key", default=None, help="fal.ai API key (overrides .env)")

    args = parser.parse_args()

    try:
        path = generate_image(
            prompt=args.prompt,
            style=args.style,
            output_path=args.output,
            model=args.model,
            size=args.size,
            api_key=args.api_key,
        )
        print(f"Image saved: {path}")
    except Exception as e:
        logger.error("Failed to generate image: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
