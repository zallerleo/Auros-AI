#!/usr/bin/env python3
"""
AUROS AI — Quality Checker Agent
Verifies content against AUROS brand rules for consistency and quality.

Usage:
    python -m agents.quality_checker.quality_agent <path_to_content>
    python -m agents.quality_checker.quality_agent --text "Some marketing copy"
    python -m agents.quality_checker.quality_agent --image path/to/image.png
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import BRAND, QUALITY_DIR, LOGS_DIR
from agents.shared.llm import generate

# Try to import Pillow for image checking
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


BRAND_RULES = BRAND["voice"]["rules"]
BRAND_COLORS_HEX = [v for v in BRAND["colors"].values()]

QUALITY_PROMPT = """You are the AUROS brand quality checker. Evaluate the following content against AUROS brand rules.

BRAND RULES:
{rules}

CONTENT TO CHECK:
{content}

Evaluate each rule and return valid JSON:
{{
  "overall_score": 0-100,
  "pass": true/false,
  "checks": [
    {{
      "rule": "...",
      "status": "pass" or "fail",
      "issue": "..." or null,
      "fix": "..." or null
    }}
  ],
  "summary": "Brief overall assessment",
  "critical_fixes": ["List of must-fix items before publishing"]
}}

Be strict. AUROS is a premium brand — anything that dilutes that positioning should fail.
Score thresholds: 90+ = publish ready, 70-89 = minor fixes needed, <70 = rewrite required.
"""


def check_text(content: str) -> dict:
    """Check text content against AUROS brand voice rules."""
    rules_text = "\n".join(f"- {rule}" for rule in BRAND_RULES)
    prompt = QUALITY_PROMPT.format(rules=rules_text, content=content)
    raw = generate(prompt, temperature=0.2)

    json_str = raw.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    return json.loads(json_str)


def check_image_colors(image_path: str) -> dict:
    """Check if an image uses AUROS brand colors (approximate matching)."""
    if not HAS_PILLOW:
        return {"status": "skipped", "reason": "Pillow not installed"}

    img = Image.open(image_path).convert("RGB")
    img_small = img.resize((50, 50))  # Downsample for speed
    pixels = list(img_small.getdata())

    # Convert brand colors to RGB
    brand_rgb = []
    for hex_color in BRAND_COLORS_HEX:
        hex_color = hex_color.lstrip("#")
        brand_rgb.append(tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)))

    # Check pixel proximity to brand colors (tolerance of 40)
    on_brand = 0
    tolerance = 40
    for pixel in pixels:
        for brand_color in brand_rgb:
            distance = sum(abs(p - b) for p, b in zip(pixel, brand_color))
            if distance < tolerance * 3:
                on_brand += 1
                break

    compliance = on_brand / len(pixels) * 100

    return {
        "total_pixels_sampled": len(pixels),
        "on_brand_pixels": on_brand,
        "compliance_percentage": round(compliance, 1),
        "pass": compliance > 60,
        "recommendation": (
            "Image uses AUROS brand palette effectively."
            if compliance > 60
            else "Image contains significant off-brand colors. Adjust to use midnight/gold/navy palette."
        ),
    }


def run(
    content: str = None,
    image_path: str = None,
    file_path: str = None,
    company: str = "",
    **kwargs,
) -> dict:
    """Run quality checks on provided content.

    When called by the orchestrator with only ``company``, scans the client
    portfolio directory for deliverables and spot-checks them.
    """
    # If called from orchestrator with just company, scan portfolio
    if company and not content and not file_path:
        from agents.shared.config import PORTFOLIO_DIR
        client_dir = PORTFOLIO_DIR / f"client_{company.lower().replace(' ', '_').replace(chr(39), '')}"
        # Spot-check the proposal and content files
        for candidate in sorted(client_dir.rglob("*.json"))[:5]:
            file_path = str(candidate)
            break

    results = {"checks": []}

    if file_path:
        path = Path(file_path)
        if path.suffix in (".png", ".jpg", ".jpeg", ".webp"):
            image_path = file_path
        else:
            content = path.read_text()

    if content:
        print("[AUROS] Checking text content against brand rules...")
        text_result = check_text(content)
        results["text_quality"] = text_result
        print(f"[AUROS] Text quality score: {text_result.get('overall_score', 'N/A')}/100")

    if image_path:
        print(f"[AUROS] Checking image colors: {image_path}")
        color_result = check_image_colors(image_path)
        results["image_colors"] = color_result
        print(f"[AUROS] Color compliance: {color_result.get('compliance_percentage', 'N/A')}%")

    # Log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "quality_checks.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(results) + "\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUROS Quality Checker Agent")
    parser.add_argument("path", nargs="?", help="Path to file to check")
    parser.add_argument("--text", help="Text content to check")
    parser.add_argument("--image", help="Image path to check")
    args = parser.parse_args()

    result = run(content=args.text, image_path=args.image, file_path=args.path)
    print(json.dumps(result, indent=2))
