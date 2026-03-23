"""
AUROS AI — Visual Identity Analyzer
Extracts colors, fonts, and visual elements from a website.
"""

from __future__ import annotations

import re
import requests
from bs4 import BeautifulSoup


def extract_visual_identity(url: str) -> dict:
    """Extract visual identity elements from a website."""
    result = {
        "url": url,
        "colors_found": [],
        "fonts_found": [],
        "logo_indicators": [],
        "css_variables": [],
        "meta_theme_color": None,
        "favicon": None,
        "og_image": None,
        "page_text_samples": [],
    }

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        html_text = resp.text

        # Extract colors from inline styles and CSS
        hex_pattern = r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b'
        rgb_pattern = r'rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)'

        hex_colors = re.findall(hex_pattern, html_text)
        rgb_colors = re.findall(rgb_pattern, html_text)

        # Count frequency and deduplicate
        color_freq = {}
        for c in hex_colors:
            c_upper = c.upper()
            color_freq[c_upper] = color_freq.get(c_upper, 0) + 1

        # Sort by frequency, take top 15
        sorted_colors = sorted(color_freq.items(), key=lambda x: x[1], reverse=True)
        result["colors_found"] = [
            {"hex": c, "frequency": f} for c, f in sorted_colors[:15]
        ]

        # Extract CSS custom properties (brand tokens)
        css_var_pattern = r'--[\w-]+:\s*([^;]+)'
        css_vars = re.findall(css_var_pattern, html_text)
        result["css_variables"] = list(set(css_vars))[:20]

        # Extract fonts from CSS and Google Fonts imports
        font_pattern = r'font-family:\s*["\']?([^;"\']+)'
        fonts = re.findall(font_pattern, html_text)
        google_fonts = re.findall(r'fonts\.googleapis\.com/css2?\?family=([^&"\']+)', html_text)

        all_fonts = set()
        for f in fonts:
            cleaned = f.strip().split(",")[0].strip("'\" ")
            if cleaned and len(cleaned) > 1:
                all_fonts.add(cleaned)
        for f in google_fonts:
            all_fonts.add(f.replace("+", " ").split(":")[0])

        result["fonts_found"] = list(all_fonts)

        # Logo detection
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            class_name = " ".join(img.get("class", []))
            if any(kw in (src + alt + class_name).lower() for kw in ["logo", "brand", "mark"]):
                result["logo_indicators"].append({
                    "src": src[:200],
                    "alt": alt,
                    "class": class_name,
                })

        # SVG logos
        for svg in soup.find_all("svg"):
            parent_classes = " ".join(svg.parent.get("class", [])) if svg.parent else ""
            if "logo" in parent_classes.lower() or "brand" in parent_classes.lower():
                result["logo_indicators"].append({
                    "type": "svg",
                    "parent_class": parent_classes,
                })

        # Meta theme color
        theme_meta = soup.find("meta", attrs={"name": "theme-color"})
        if theme_meta:
            result["meta_theme_color"] = theme_meta.get("content")

        # Favicon
        favicon = soup.find("link", rel=lambda x: x and "icon" in x)
        if favicon:
            result["favicon"] = favicon.get("href")

        # OG image
        og_img = soup.find("meta", property="og:image")
        if og_img:
            result["og_image"] = og_img.get("content")

        # Sample text for tone analysis (headings + first paragraphs)
        for tag in ["h1", "h2", "p"]:
            for el in soup.find_all(tag)[:5]:
                text = el.get_text(strip=True)
                if text and len(text) > 10:
                    result["page_text_samples"].append(text[:300])

    except Exception as e:
        result["error"] = str(e)
        print(f"[AUROS] Visual extraction failed: {url} — {e}")

    return result
