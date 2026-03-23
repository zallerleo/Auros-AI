#!/usr/bin/env python3
"""
AUROS AI — Website Generator
Generates beautiful static HTML/CSS websites for local businesses.
Claude creates the content, Jinja2 injects it into templates.

Usage:
    python tools/website_generator.py --lead-id abc123
    python tools/website_generator.py --business "Joe's Pizza" --category restaurant --city Atlanta --state GA
"""

from __future__ import annotations

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.shared.config import ANTHROPIC_API_KEY
import anthropic

logger = logging.getLogger("auros.website_gen")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "websites"
OUTPUT_DIR = PROJECT_ROOT / "portfolio" / "websites"


# Category → template mapping
CATEGORY_MAP = {
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "bar": "restaurant",
    "bakery": "restaurant",
    "pizza": "restaurant",
    "salon": "salon",
    "hair": "salon",
    "barber": "salon",
    "spa": "salon",
    "nail": "salon",
    "beauty": "salon",
    "gym": "gym",
    "fitness": "gym",
    "yoga": "gym",
    "crossfit": "gym",
    "dentist": "dental",
    "dental": "dental",
    "orthodont": "dental",
    "plumber": "professional",
    "electric": "professional",
    "hvac": "professional",
    "roofing": "professional",
    "landscap": "professional",
    "cleaning": "professional",
    "lawyer": "professional",
    "account": "professional",
    "consult": "professional",
}


def detect_template(category: str) -> str:
    """Detect the best template based on business category."""
    cat_lower = category.lower()
    for keyword, template in CATEGORY_MAP.items():
        if keyword in cat_lower:
            return template
    return "professional"  # Default fallback


def generate_content(
    business_name: str,
    category: str,
    city: str,
    state: str,
    rating: float = 0,
    review_count: int = 0,
    phone: str = "",
    address: str = "",
) -> dict:
    """Use Claude to generate all website content from business data."""
    template_type = detect_template(category)

    prompt = f"""Generate website content for a local business. Return ONLY valid JSON.

Business: {business_name}
Category: {category}
Template: {template_type}
Location: {city}, {state}
Rating: {rating} stars ({review_count} reviews)
Phone: {phone}
Address: {address}

Generate this JSON structure:
{{
    "tagline": "A compelling 5-8 word tagline",
    "hero_headline": "Main headline for the hero section (8-12 words)",
    "hero_subtext": "Supporting text under the headline (15-25 words)",
    "about_title": "About section title",
    "about_text": "2-3 sentences about this type of business, written as if the owner wrote it. Warm, professional, local.",
    "services": [
        {{"name": "Service 1", "description": "Brief description (10-15 words)"}},
        {{"name": "Service 2", "description": "Brief description"}},
        {{"name": "Service 3", "description": "Brief description"}},
        {{"name": "Service 4", "description": "Brief description"}},
        {{"name": "Service 5", "description": "Brief description"}},
        {{"name": "Service 6", "description": "Brief description"}}
    ],
    "cta_text": "Call-to-action button text (2-4 words)",
    "cta_subtext": "Text near the CTA (10-15 words)",
    "hours": "Mon-Fri: 9am-6pm, Sat: 10am-4pm, Sun: Closed",
    "meta_description": "SEO meta description (150-160 chars)",
    "primary_color": "A hex color that fits the business category (e.g., #D4380D for pizza, #2E7D32 for landscaping)",
    "accent_color": "A complementary accent hex color"
}}

Make the content feel authentic — like a real local business, not generic AI text.
Use the city name naturally. Reference the community."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    return json.loads(raw.strip())


def generate_website(
    business_name: str,
    category: str,
    city: str = "",
    state: str = "",
    rating: float = 0,
    review_count: int = 0,
    phone: str = "",
    address: str = "",
    lead_id: str = "",
    template: str = "auto",
) -> dict:
    """
    Generate a complete static website for a business.
    Returns: {html_path, template, business_name}
    """
    # Detect template
    if template == "auto":
        template = detect_template(category)

    # Generate content via Claude
    logger.info(f"Generating content for: {business_name} ({template})")
    content = generate_content(
        business_name, category, city, state,
        rating, review_count, phone, address,
    )

    # Build the HTML
    html = _build_html(
        template=template,
        business_name=business_name,
        category=category,
        city=city,
        state=state,
        rating=rating,
        review_count=review_count,
        phone=phone,
        address=address,
        content=content,
    )

    # Save to output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = business_name.lower().replace(" ", "-").replace("'", "")[:50]
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{slug}_{timestamp}"
    html_path = OUTPUT_DIR / f"{filename}.html"
    html_path.write_text(html, encoding="utf-8")

    logger.info(f"Website saved: {html_path}")

    return {
        "html_path": str(html_path),
        "template": template,
        "business_name": business_name,
        "slug": slug,
    }


def _build_html(
    template: str,
    business_name: str,
    category: str,
    city: str,
    state: str,
    rating: float,
    review_count: int,
    phone: str,
    address: str,
    content: dict,
) -> str:
    """Build the full HTML from template + content."""
    primary = content.get("primary_color", "#1a1a2e")
    accent = content.get("accent_color", "#e94560")
    tagline = content.get("tagline", f"Quality {category} in {city}")
    hero_headline = content.get("hero_headline", f"Welcome to {business_name}")
    hero_subtext = content.get("hero_subtext", f"Serving {city}, {state} with excellence")
    about_title = content.get("about_title", f"About {business_name}")
    about_text = content.get("about_text", "")
    services = content.get("services", [])
    cta_text = content.get("cta_text", "Contact Us")
    cta_subtext = content.get("cta_subtext", "")
    hours = content.get("hours", "")
    meta_desc = content.get("meta_description", f"{business_name} - {category} in {city}, {state}")

    # Star rating HTML
    stars_html = ""
    if rating:
        full_stars = int(rating)
        half_star = rating - full_stars >= 0.3
        stars_html = "★" * full_stars + ("½" if half_star else "") + f" {rating}"

    # Services grid HTML
    services_html = ""
    for svc in services[:6]:
        services_html += f"""
            <div class="service-card">
                <h3>{svc.get('name', '')}</h3>
                <p>{svc.get('description', '')}</p>
            </div>"""

    # Phone link
    phone_digits = "".join(c for c in phone if c.isdigit()) if phone else ""
    phone_link = f"tel:+1{phone_digits}" if phone_digits else "#"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name} — {tagline}</title>
    <meta name="description" content="{meta_desc}">
    <meta property="og:title" content="{business_name}">
    <meta property="og:description" content="{meta_desc}">
    <meta property="og:type" content="website">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@400;600;700&display=swap" rel="stylesheet">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "{business_name}",
        "address": {{ "@type": "PostalAddress", "streetAddress": "{address}", "addressLocality": "{city}", "addressRegion": "{state}" }},
        "telephone": "{phone}",
        "aggregateRating": {{ "@type": "AggregateRating", "ratingValue": "{rating}", "reviewCount": "{review_count}" }}
    }}
    </script>
    <style>
        :root {{
            --primary: {primary};
            --accent: {accent};
            --bg: #fafafa;
            --text: #1a1a1a;
            --text-light: #666;
            --white: #fff;
            --shadow: 0 4px 24px rgba(0,0,0,0.08);
            --shadow-hover: 0 8px 40px rgba(0,0,0,0.12);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', system-ui, sans-serif;
            color: var(--text);
            background: var(--bg);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}

        /* Navigation */
        nav {{
            position: fixed; top: 0; width: 100%; z-index: 100;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(0,0,0,0.06);
            padding: 16px 0;
        }}
        nav .container {{
            display: flex; align-items: center; justify-content: space-between;
        }}
        nav .logo {{
            font-family: 'Playfair Display', serif;
            font-size: 22px; font-weight: 700; color: var(--primary);
            text-decoration: none;
        }}
        nav .nav-links {{ display: flex; gap: 32px; list-style: none; }}
        nav .nav-links a {{
            text-decoration: none; color: var(--text-light);
            font-size: 14px; font-weight: 500;
            transition: color 0.2s;
        }}
        nav .nav-links a:hover {{ color: var(--primary); }}
        .nav-cta {{
            background: var(--primary); color: var(--white) !important;
            padding: 10px 24px; border-radius: 8px;
            font-weight: 600; transition: transform 0.2s, box-shadow 0.2s;
        }}
        .nav-cta:hover {{ transform: translateY(-1px); box-shadow: var(--shadow); }}

        /* Hero */
        .hero {{
            padding: 160px 0 100px;
            text-align: center;
            background: linear-gradient(135deg, var(--primary) 0%, color-mix(in srgb, var(--primary), black 30%) 100%);
            color: var(--white);
        }}
        .hero h1 {{
            font-family: 'Playfair Display', serif;
            font-size: clamp(36px, 5vw, 64px);
            font-weight: 700; line-height: 1.1;
            max-width: 800px; margin: 0 auto 20px;
        }}
        .hero p {{
            font-size: 18px; opacity: 0.9;
            max-width: 600px; margin: 0 auto 32px;
        }}
        .hero .rating {{
            font-size: 20px; margin-bottom: 24px;
            color: #FFD700;
        }}
        .hero .review-count {{ font-size: 14px; opacity: 0.8; color: var(--white); }}
        .hero-cta {{
            display: inline-block;
            background: var(--accent); color: var(--white);
            padding: 16px 40px; border-radius: 12px;
            font-size: 16px; font-weight: 700;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .hero-cta:hover {{ transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.3); }}

        /* About */
        .about {{
            padding: 100px 0;
            text-align: center;
        }}
        .about h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 36px; margin-bottom: 20px;
        }}
        .about p {{
            font-size: 18px; color: var(--text-light);
            max-width: 700px; margin: 0 auto;
            line-height: 1.8;
        }}

        /* Services */
        .services {{
            padding: 80px 0;
            background: var(--white);
        }}
        .services h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 36px; text-align: center;
            margin-bottom: 48px;
        }}
        .services-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }}
        .service-card {{
            padding: 32px; border-radius: 16px;
            background: var(--bg);
            border: 1px solid rgba(0,0,0,0.06);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .service-card:hover {{
            transform: translateY(-4px);
            box-shadow: var(--shadow-hover);
        }}
        .service-card h3 {{
            font-size: 18px; font-weight: 700;
            margin-bottom: 8px; color: var(--primary);
        }}
        .service-card p {{ font-size: 14px; color: var(--text-light); }}

        /* CTA Section */
        .cta-section {{
            padding: 100px 0;
            text-align: center;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            color: var(--white);
        }}
        .cta-section h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 42px; margin-bottom: 16px;
        }}
        .cta-section p {{ font-size: 18px; opacity: 0.9; margin-bottom: 32px; }}
        .cta-btn {{
            display: inline-block;
            background: var(--white); color: var(--primary);
            padding: 18px 48px; border-radius: 12px;
            font-size: 18px; font-weight: 700;
            text-decoration: none;
            transition: transform 0.2s;
        }}
        .cta-btn:hover {{ transform: translateY(-2px); }}

        /* Contact */
        .contact {{
            padding: 80px 0;
        }}
        .contact h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 36px; text-align: center;
            margin-bottom: 48px;
        }}
        .contact-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 32px; text-align: center;
        }}
        .contact-item h3 {{ font-size: 16px; font-weight: 700; margin-bottom: 8px; color: var(--primary); }}
        .contact-item p {{ font-size: 15px; color: var(--text-light); }}
        .contact-item a {{ color: var(--primary); text-decoration: none; }}

        /* Footer */
        footer {{
            padding: 40px 0;
            text-align: center;
            border-top: 1px solid rgba(0,0,0,0.06);
            font-size: 13px; color: var(--text-light);
        }}
        footer a {{ color: var(--text-light); text-decoration: none; }}

        /* Mobile */
        @media (max-width: 768px) {{
            nav .nav-links {{ display: none; }}
            .hero {{ padding: 120px 20px 80px; }}
            .services-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>

<nav>
    <div class="container">
        <a href="#" class="logo">{business_name}</a>
        <ul class="nav-links">
            <li><a href="#about">About</a></li>
            <li><a href="#services">Services</a></li>
            <li><a href="#contact">Contact</a></li>
            <li><a href="{phone_link}" class="nav-cta">{cta_text}</a></li>
        </ul>
    </div>
</nav>

<section class="hero">
    <div class="container">
        {"<div class='rating'>" + stars_html + " <span class='review-count'>(" + str(review_count) + " reviews)</span></div>" if stars_html else ""}
        <h1>{hero_headline}</h1>
        <p>{hero_subtext}</p>
        <a href="{phone_link}" class="hero-cta">{cta_text}</a>
    </div>
</section>

<section class="about" id="about">
    <div class="container">
        <h2>{about_title}</h2>
        <p>{about_text}</p>
    </div>
</section>

<section class="services" id="services">
    <div class="container">
        <h2>What We Offer</h2>
        <div class="services-grid">
            {services_html}
        </div>
    </div>
</section>

<section class="cta-section">
    <div class="container">
        <h2>Ready to Get Started?</h2>
        <p>{cta_subtext}</p>
        <a href="{phone_link}" class="cta-btn">{cta_text}</a>
    </div>
</section>

<section class="contact" id="contact">
    <div class="container">
        <h2>Get In Touch</h2>
        <div class="contact-grid">
            {"<div class='contact-item'><h3>Phone</h3><p><a href='" + phone_link + "'>" + phone + "</a></p></div>" if phone else ""}
            {"<div class='contact-item'><h3>Address</h3><p>" + address + "</p></div>" if address else ""}
            {"<div class='contact-item'><h3>Hours</h3><p>" + hours + "</p></div>" if hours else ""}
        </div>
    </div>
</section>

<footer>
    <div class="container">
        <p>&copy; {datetime.now().year} {business_name}. All rights reserved.</p>
    </div>
</footer>

</body>
</html>"""


def generate_from_lead(lead_id: str) -> dict:
    """Generate a website from a lead in the database."""
    from system.db import get_lead, update_lead, create_website_record

    lead = get_lead(lead_id)
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    result = generate_website(
        business_name=lead["business_name"],
        category=lead.get("category", ""),
        city=lead.get("city", ""),
        state=lead.get("state", ""),
        rating=lead.get("rating", 0),
        review_count=lead.get("review_count", 0),
        phone=lead.get("phone", ""),
        address=lead.get("address", ""),
        lead_id=lead_id,
    )

    # Update lead and create website record
    update_lead(lead_id, website_generated=1, site_template=result["template"])
    create_website_record(
        lead_id=lead_id,
        business_name=lead["business_name"],
        category=lead.get("category", ""),
        template=result["template"],
        html_path=result["html_path"],
    )

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="AUROS Website Generator")
    parser.add_argument("--lead-id", type=str, help="Generate from a lead ID")
    parser.add_argument("--business", type=str, help="Business name")
    parser.add_argument("--category", type=str, default="restaurant", help="Category")
    parser.add_argument("--city", type=str, default="Atlanta", help="City")
    parser.add_argument("--state", type=str, default="GA", help="State")

    args = parser.parse_args()

    if args.lead_id:
        result = generate_from_lead(args.lead_id)
    else:
        result = generate_website(
            business_name=args.business or "Test Business",
            category=args.category,
            city=args.city,
            state=args.state,
            rating=4.7,
            review_count=120,
        )

    print(f"\nResult: {json.dumps(result, indent=2)}")
