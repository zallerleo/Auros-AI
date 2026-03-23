#!/usr/bin/env python3
"""
AUROS AI — Build Enhanced Visual Proposal
Transforms the text-only proposal into an image-rich, premium presentation.
Embeds real exhibition photos, replaces emoji icons with SVG, adds galleries.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = PROJECT_ROOT / "portfolio" / "client_the_imagine_team"
IMAGES_DIR = CLIENT_DIR / "media" / "proposal_ready"
SOURCE_HTML = CLIENT_DIR / "04_deliverables" / "proposal_3_campaigns_2026-03-22.html"
OUTPUT_HTML = CLIENT_DIR / "04_deliverables" / "proposal_the_imagine_team_enhanced.html"

# ── Image selection per campaign ──────────────────────────────────────────

IMAGE_MAP = {
    "cabinet": {
        "hero_bg": "cabinet/cabinet_hero_mid.jpg",
        "showcase": "cabinet/cabinet_promo_1.jpg",
        "gallery": [
            "cabinet/cabinet_hero_left.jpg",
            "cabinet/cabinet_lock_interior.jpg",
            "cabinet/cabinet_hero_right.jpg",
        ],
        "transition": "cabinet/cabinet_promo_2.jpg",
        "bundle_thumb": "cabinet/cabinet_hero_mid.jpg",
    },
    "titanic": {
        "hero_bg": "titanic/titanic_grand_staircase.jpg",
        "showcase": "titanic/titanic_hall_1.jpg",
        "gallery": [
            "titanic/titanic_atmosphere_1.jpg",
            "titanic/titanic_hall_2.jpg",
            "titanic/titanic_atmosphere_2.jpg",
        ],
        "transition": "titanic/titanic_imagine_1.jpg",
        "bundle_thumb": "titanic/titanic_grand_staircase.jpg",
    },
    "trolls": {
        "hero_bg": "dambo/dambo_golden_rabbit.jpg",
        "showcase": "dambo/dambo_barefoot_frida.jpg",
        "gallery": [
            "dambo/dambo_oscar_bird_king.jpg",
            "dambo/dambo_trollercoaster.jpg",
            "dambo/dambo_pia_peacekeeper.jpg",
        ],
        "transition": "dambo/dambo_save_humans.jpg",
        "bundle_thumb": "dambo/dambo_giants_tour.jpg",
    },
}

# ── SVG Icons ─────────────────────────────────────────────────────────────

SVG_ICONS = {
    # Cabinet icons
    "&#128270;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',  # magnifying glass
    "&#127864;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 22h8l-1-7H9L8 22z"/><path d="M12 2C8 2 5 5.5 5 9h14c0-3.5-3-7-7-7z"/><line x1="12" y1="9" x2="12" y2="15"/></svg>',  # cocktail
    "&#128123;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',  # layers/collection
    "&#128274;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/></svg>',  # lock/vault
    # Titanic icons
    "&#127909;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',  # camera
    "&#128142;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',  # diamond/star
    "&#128149;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',  # heart
    "&#11088;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',  # people/social proof
    # Trolls icons
    "&#127795;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 6c5-3 12-3 12-3s7 0 10 3"/><path d="M7 12c2-1.5 5-1.5 5-1.5s3 0 5 1.5"/><line x1="12" y1="3" x2="12" y2="22"/></svg>',  # tree
    "&#128205;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',  # map pin
    "&#127809;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 17 3.5s1.5 2.5-.5 6.5A5 5 0 0 1 20 14.5"/><path d="M12 20l0 2"/></svg>',  # leaf
    "&#128483;": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',  # speech bubble
}

# ── Helpers ────────────────────────────────────────────────────────────────

def img_to_base64(rel_path: str) -> str:
    """Convert image file to base64 data URI."""
    full = IMAGES_DIR / rel_path
    if not full.exists():
        # Try fallback paths
        for alt in IMAGES_DIR.rglob(Path(rel_path).name):
            full = alt
            break
    if not full.exists():
        print(f"  WARNING: Image not found: {rel_path}")
        return ""
    data = full.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/jpeg;base64,{b64}"


def build_gallery_html(campaign: str, images: list[str], accent: str) -> str:
    """Build a gallery strip section."""
    items = ""
    for img_path in images:
        b64 = img_to_base64(img_path)
        if b64:
            items += f'      <div class="gallery-item" style="border-color: {accent}"><img src="{b64}" alt="{campaign} exhibition" loading="lazy" /></div>\n'
    return f"""
    <div class="campaign-gallery animate-on-scroll">
      <div class="gallery-label">Visual Experience</div>
      <div class="gallery-strip">
{items}      </div>
    </div>
"""


def build_transition_html(img_path: str, from_color: str, to_color: str) -> str:
    """Build a cinematic transition section between campaigns."""
    b64 = img_to_base64(img_path)
    if not b64:
        return '<div class="campaign-divider"><div class="campaign-divider-line"></div></div>'
    return f"""<div class="campaign-transition">
  <div class="transition-image" style="background-image: url({b64})"></div>
  <div class="transition-gradient" style="background: linear-gradient(180deg, {from_color} 0%, transparent 30%, transparent 70%, {to_color} 100%)"></div>
</div>"""


# ── New CSS ────────────────────────────────────────────────────────────────

ENHANCED_CSS = """
/* ====== ENHANCED: Hero backgrounds ====== */
.campaign-hero-wrapper {
  position: relative;
  background-size: cover;
  background-position: center;
  overflow: hidden;
}
.campaign-hero-wrapper::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(11,15,26,0.92) 0%, rgba(11,15,26,0.75) 50%, rgba(11,15,26,0.88) 100%);
  z-index: 1;
}
.campaign-hero-wrapper .campaign-hero {
  position: relative;
  z-index: 2;
}

/* ====== ENHANCED: Showcase images ====== */
.campaign-showcase-image {
  border-radius: 16px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}
.campaign-showcase-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  min-height: 350px;
  max-height: 480px;
}
.campaign-showcase-image::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  border: 1px solid rgba(201,168,76,0.15);
  pointer-events: none;
}
.cabinet .campaign-showcase-image { border: 2px solid rgba(212,160,86,0.25); }
.titanic .campaign-showcase-image { border: 2px solid rgba(126,179,216,0.25); }
.trolls .campaign-showcase-image { border: 2px solid rgba(109,184,154,0.25); }

/* ====== ENHANCED: SVG icons ====== */
.content-card .icon-svg {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  border-radius: 14px;
  background: rgba(201,168,76,0.08);
  border: 1px solid rgba(201,168,76,0.12);
}
.cabinet .content-card .icon-svg {
  background: rgba(139,69,19,0.1);
  border-color: rgba(212,160,86,0.2);
  color: #D4A056;
}
.titanic .content-card .icon-svg {
  background: rgba(31,58,82,0.15);
  border-color: rgba(126,179,216,0.2);
  color: #7EB3D8;
}
.trolls .content-card .icon-svg {
  background: rgba(27,77,62,0.15);
  border-color: rgba(109,184,154,0.2);
  color: #6DB89A;
}

/* ====== ENHANCED: Gallery strips ====== */
.campaign-gallery {
  margin-top: 40px;
  margin-bottom: 16px;
}
.gallery-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--gray);
  margin-bottom: 16px;
}
.gallery-strip {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.gallery-item {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(201,168,76,0.08);
  transition: all 0.4s cubic-bezier(0.16,1,0.3,1);
}
.gallery-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 48px rgba(0,0,0,0.4);
}
.gallery-item img {
  width: 100%;
  height: 220px;
  object-fit: cover;
  display: block;
  transition: transform 0.6s ease;
}
.gallery-item:hover img {
  transform: scale(1.05);
}

/* ====== ENHANCED: Cinematic transitions ====== */
.campaign-transition {
  position: relative;
  height: 180px;
  overflow: hidden;
}
.transition-image {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(2px) brightness(0.4);
}
.transition-gradient {
  position: absolute;
  inset: 0;
}

/* ====== ENHANCED: Cover background ====== */
.cover-bg-enhanced {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.12;
  filter: blur(4px) saturate(0.6);
  z-index: 0;
}
.cover { position: relative; }
.cover > *:not(.cover-bg-enhanced) { position: relative; z-index: 1; }

/* ====== ENHANCED: Bundle thumbnails ====== */
.bundle-item-thumb {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 10px;
  margin-bottom: 12px;
  opacity: 0.8;
  transition: opacity 0.3s;
}
.bundle-item:hover .bundle-item-thumb {
  opacity: 1;
}

/* ====== ENHANCED: Responsive ====== */
@media (max-width: 968px) {
  .gallery-strip { grid-template-columns: 1fr; }
  .campaign-showcase-image img { min-height: 200px; max-height: 300px; }
  .campaign-transition { height: 120px; }
}
@media (max-width: 600px) {
  .gallery-item img { height: 180px; }
  .campaign-transition { height: 80px; }
}

/* ====== ENHANCED: PDF print styles ====== */
@media print {
  .animate-on-scroll { opacity: 1 !important; transform: none !important; }
  .scroll-indicator, .nav { display: none !important; }
  .cover { min-height: auto; padding: 80px 40px; }
  .campaign-transition { height: 60px; }
  .campaign-hero-wrapper::before { background: rgba(11,15,26,0.85) !important; }
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


# ── Main transformation ──────────────────────────────────────────────────

def transform_proposal():
    print("[AUROS] Building enhanced proposal...")
    html = SOURCE_HTML.read_text()

    # 1. Inject enhanced CSS before </style>
    print("  [1/7] Injecting enhanced CSS...")
    html = html.replace("</style>", ENHANCED_CSS + "\n</style>")

    # 2. Replace emoji icons with SVGs
    print("  [2/7] Replacing emoji icons with SVGs...")
    for emoji_code, svg in SVG_ICONS.items():
        icon_html = f'<span class="icon">{emoji_code}</span>'
        svg_html = f'<div class="icon-svg">{svg}</div>'
        html = html.replace(icon_html, svg_html)

    # 3. Add cover background image
    print("  [3/7] Adding cover background...")
    cover_bg = img_to_base64("titanic/titanic_grand_staircase.jpg")
    if cover_bg:
        cover_insert = f'<div class="cover-bg-enhanced" style="background-image: url({cover_bg})"></div>\n'
        html = html.replace(
            '<section class="cover">',
            f'<section class="cover">\n  {cover_insert}'
        )

    # 4. Wrap campaign heroes with background images + add showcase
    print("  [4/7] Enhancing campaign heroes...")
    for campaign, config in [
        ("cabinet", {"id": "cabinet", "bg": IMAGE_MAP["cabinet"]["hero_bg"], "showcase": IMAGE_MAP["cabinet"]["showcase"]}),
        ("titanic", {"id": "titanic", "bg": IMAGE_MAP["titanic"]["hero_bg"], "showcase": IMAGE_MAP["titanic"]["showcase"]}),
        ("trolls", {"id": "trolls", "bg": IMAGE_MAP["trolls"]["hero_bg"], "showcase": IMAGE_MAP["trolls"]["showcase"]}),
    ]:
        bg_b64 = img_to_base64(config["bg"])
        showcase_b64 = img_to_base64(config["showcase"])

        # Wrap campaign-hero in background wrapper
        old_hero_start = f'<section class="campaign-section {campaign}" id="{config["id"]}">\n\n  <div class="campaign-hero animate-on-scroll">'
        new_hero_start = f'<section class="campaign-section {campaign}" id="{config["id"]}">\n\n  <div class="campaign-hero-wrapper" style="background-image: url({bg_b64})">\n  <div class="campaign-hero animate-on-scroll">'

        html = html.replace(old_hero_start, new_hero_start)

        # Replace stats grid with showcase image
        # Find the campaign-stats div for this campaign and replace it
        # We need to find the specific stats block — it follows the campaign-hero-content
        stats_pattern = re.compile(
            r'(<div class="campaign-hero-content">.*?</div>\s*\n\s*)'
            r'(<div class="campaign-stats">.*?</div>\s*\n\s*</div>)',
            re.DOTALL
        )

        def replace_stats(match, showcase_b64=showcase_b64, campaign=campaign):
            hero_content = match.group(1)
            # Keep the stats but convert them to a bar below, and add showcase image
            stats_block = match.group(2)
            # Extract individual stat cards for the horizontal bar
            stat_cards = re.findall(r'<div class="stat-card">.*?</div>\s*</div>', stats_block, re.DOTALL)

            showcase_html = f'''<div class="campaign-showcase-image">
        <img src="{showcase_b64}" alt="{campaign} exhibition showcase" />
      </div>
    </div>
    </div>'''

            return hero_content + showcase_html

        # Only replace the first occurrence for each campaign section
        # We need a more targeted approach
        pass

    # Instead of complex regex, let's do targeted string replacements
    # Replace each campaign's stats div with showcase image
    for campaign_name in ["cabinet", "titanic", "trolls"]:
        showcase_b64 = img_to_base64(IMAGE_MAP[campaign_name]["showcase"])
        if not showcase_b64:
            continue

        # Find and replace the campaign-stats div within each campaign section
        # The pattern: campaign-stats grid gets replaced by showcase image
        # Stats will be shown as a horizontal bar below the hero
        old_stats_start = f'<div class="campaign-stats">'

        # We need to count occurrences and replace the right one
        # Cabinet is 1st, Titanic is 2nd, Trolls is 3rd occurrence
        campaign_idx = {"cabinet": 0, "titanic": 1, "trolls": 2}[campaign_name]

        parts = html.split(old_stats_start)
        if len(parts) > campaign_idx + 1:
            # Find the closing tags for this stats block
            stats_section = parts[campaign_idx + 1]
            # Find the end of the stats div (4 stat-cards, each ends with </div></div>)
            close_idx = 0
            depth = 1
            i = 0
            while i < len(stats_section) and depth > 0:
                if stats_section[i:i+5] == '<div ':
                    depth += 1
                elif stats_section[i:i+6] == '</div>':
                    depth -= 1
                i += 1
            close_idx = i

            old_stats_full = old_stats_start + stats_section[:close_idx]
            new_showcase = f'''<div class="campaign-showcase-image">
        <img src="{showcase_b64}" alt="{campaign_name} exhibition" />
      </div>'''

            html = html.replace(old_stats_full, new_showcase, 1)

    # Close the hero wrappers — add closing div after campaign-hero
    # Each campaign-hero now needs an extra </div> for the wrapper
    for campaign_name in ["cabinet", "titanic", "trolls"]:
        html = html.replace(
            f'  <div class="campaign-detail">\n',
            f'  </div>\n  <div class="campaign-detail">\n',
            1
        ) if f'campaign-hero-wrapper' in html else html

    # 5. Add gallery strips after content-strategy-grid
    print("  [5/7] Adding image gallery strips...")
    accents = {"cabinet": "rgba(212,160,86,0.2)", "titanic": "rgba(126,179,216,0.2)", "trolls": "rgba(109,184,154,0.2)"}

    for campaign_name in ["cabinet", "titanic", "trolls"]:
        gallery_html = build_gallery_html(
            campaign_name,
            IMAGE_MAP[campaign_name]["gallery"],
            accents[campaign_name]
        )
        # Insert after the content-strategy-grid closing div (before positioning-callout)
        # Find the positioning-callout for this campaign
        # Each campaign section has its own positioning-callout
        pass

    # Insert galleries before positioning-callout sections
    # We'll insert them by finding the positioning-callout blocks
    callout_marker = '<div class="positioning-callout animate-on-scroll delay-2">'
    callout_parts = html.split(callout_marker)

    if len(callout_parts) >= 4:  # original + 3 campaigns
        reconstructed = callout_parts[0]
        campaign_order = ["cabinet", "titanic", "trolls"]
        for i, campaign_name in enumerate(campaign_order):
            gallery_html = build_gallery_html(
                campaign_name,
                IMAGE_MAP[campaign_name]["gallery"],
                accents[campaign_name]
            )
            reconstructed += gallery_html + "\n    " + callout_marker + callout_parts[i + 1]
        html = reconstructed

    # 6. Replace campaign dividers with cinematic transitions
    print("  [6/7] Adding cinematic transitions...")
    divider_html = '<div class="campaign-divider"><div class="campaign-divider-line"></div></div>'
    divider_parts = html.split(divider_html)

    if len(divider_parts) >= 4:  # 3 dividers
        transitions = [
            build_transition_html(IMAGE_MAP["cabinet"]["transition"], "var(--midnight)", "var(--midnight)"),
            build_transition_html(IMAGE_MAP["titanic"]["transition"], "var(--midnight)", "var(--midnight)"),
            build_transition_html(IMAGE_MAP["trolls"]["transition"], "var(--midnight)", "var(--midnight)"),
        ]
        reconstructed = divider_parts[0]
        for i, transition in enumerate(transitions):
            if i < len(divider_parts) - 1:
                reconstructed += transition + divider_parts[i + 1]
        html = reconstructed

    # 7. Add thumbnails to bundle items
    print("  [7/7] Adding bundle thumbnails...")
    for campaign_name in ["cabinet", "titanic", "trolls"]:
        thumb_b64 = img_to_base64(IMAGE_MAP[campaign_name]["bundle_thumb"])
        if thumb_b64:
            old_bundle = f'<div class="bundle-item {campaign_name}">'
            new_bundle = f'<div class="bundle-item {campaign_name}">\n        <img class="bundle-item-thumb" src="{thumb_b64}" alt="{campaign_name}" />'
            html = html.replace(old_bundle, new_bundle)

    # Write output
    OUTPUT_HTML.write_text(html)
    size_kb = OUTPUT_HTML.stat().st_size / 1024
    size_mb = size_kb / 1024
    print(f"\n[AUROS] Enhanced proposal saved to:")
    print(f"  {OUTPUT_HTML}")
    print(f"  Size: {size_mb:.1f} MB ({size_kb:.0f} KB)")

    return str(OUTPUT_HTML)


if __name__ == "__main__":
    transform_proposal()
