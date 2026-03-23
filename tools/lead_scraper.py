#!/usr/bin/env python3
"""
AUROS AI — Lead Scraper
Finds local businesses using Google Places API.
Targets businesses with good reviews but no website.

Setup:
    1. Enable "Places API" in Google Cloud Console
    2. Create an API key
    3. Add GOOGLE_PLACES_API_KEY=<key> to .env

Usage:
    python tools/lead_scraper.py --category restaurant --city Atlanta --state GA
    python tools/lead_scraper.py --query "hair salon Atlanta GA" --max 50
"""

from __future__ import annotations

import sys
import json
import argparse
import logging
import os
import time
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

logger = logging.getLogger("auros.scraper")

PLACES_TEXT_SEARCH = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"


def search_businesses(
    query: str,
    max_results: int = 60,
    min_rating: float = 4.0,
    min_reviews: int = 15,
    filter_no_website: bool = True,
) -> list[dict]:
    """
    Search for businesses using Google Places Text Search API.
    Returns list of business dicts with details.
    """
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_PLACES_API_KEY not set in .env")
        return []

    all_results = []
    next_page_token = None

    # Text Search returns up to 20 results per page, 3 pages max (60 total)
    for page in range(3):
        if len(all_results) >= max_results:
            break

        params = {"key": GOOGLE_API_KEY}
        if next_page_token:
            params["pagetoken"] = next_page_token
            time.sleep(2)  # Google requires delay between page token requests
        else:
            params["query"] = query
            params["type"] = "establishment"

        resp = requests.get(PLACES_TEXT_SEARCH, params=params, timeout=15)
        if resp.status_code != 200:
            logger.error(f"Places API error: {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        if data.get("status") != "OK":
            logger.warning(f"Places API status: {data.get('status')} - {data.get('error_message', '')}")
            break

        results = data.get("results", [])
        logger.info(f"Page {page + 1}: {len(results)} results")

        for place in results:
            rating = place.get("rating", 0)
            review_count = place.get("user_ratings_total", 0)

            # Basic filter before detail lookup
            if rating < min_rating or review_count < min_reviews:
                continue

            all_results.append(place)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

    # Now get details for each qualifying result
    businesses = []
    for place in all_results[:max_results]:
        details = _get_place_details(place["place_id"])
        if not details:
            continue

        has_website = bool(details.get("website"))

        if filter_no_website and has_website:
            logger.debug(f"Skipping {details.get('name')} — has website")
            continue

        biz = _format_business(place, details)
        businesses.append(biz)
        logger.info(
            f"[{len(businesses)}] {biz['business_name']} | "
            f"{biz.get('rating', 0)}★ {biz.get('review_count', 0)} reviews | "
            f"{'HAS' if has_website else 'NO'} website"
        )

    logger.info(f"Found {len(businesses)} qualifying businesses (no website, good reviews)")
    return businesses


def _get_place_details(place_id: str) -> dict | None:
    """Get detailed info about a place."""
    params = {
        "place_id": place_id,
        "key": GOOGLE_API_KEY,
        "fields": "name,formatted_address,formatted_phone_number,website,url,rating,user_ratings_total,types,business_status,opening_hours",
    }

    try:
        resp = requests.get(PLACES_DETAILS, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                return data.get("result", {})
    except Exception as e:
        logger.debug(f"Details error for {place_id}: {e}")

    return None


def _format_business(place: dict, details: dict) -> dict:
    """Format place data into our standard business dict."""
    address = details.get("formatted_address", place.get("formatted_address", ""))

    # Extract city and state from address
    city, state = "", ""
    parts = address.split(",")
    if len(parts) >= 3:
        city = parts[-3].strip() if len(parts) >= 3 else ""
        state_zip = parts[-2].strip() if len(parts) >= 2 else ""
        # Extract state abbreviation (e.g., "GA 30301" → "GA")
        state_parts = state_zip.split()
        if state_parts:
            state = state_parts[0]

    # Detect social media from website URL
    website = details.get("website", "")
    social_links = {}
    has_social = False
    if website:
        lower_url = website.lower()
        if "instagram.com" in lower_url:
            social_links["instagram"] = website
            has_social = True
        elif "facebook.com" in lower_url:
            social_links["facebook"] = website
            has_social = True

    return {
        "business_name": details.get("name", place.get("name", "")),
        "category": ", ".join(details.get("types", [])[:3]),
        "address": address,
        "city": city,
        "state": state,
        "phone": details.get("formatted_phone_number", ""),
        "google_maps_url": details.get("url", ""),
        "place_id": place.get("place_id", ""),
        "rating": place.get("rating", 0),
        "review_count": place.get("user_ratings_total", 0),
        "has_website": bool(details.get("website")),
        "website_url": details.get("website", ""),
        "has_social_media": has_social,
        "social_links": social_links,
    }


def scrape_and_store(
    query: str,
    city: str = "",
    state: str = "",
    max_results: int = 60,
    min_rating: float = 4.0,
    min_reviews: int = 15,
) -> dict:
    """Search for leads and store them in the database. Returns summary stats."""
    from system.db import create_lead

    businesses = search_businesses(
        query, max_results, min_rating, min_reviews, filter_no_website=True,
    )

    created = 0
    skipped = 0

    for biz in businesses:
        if city and not biz.get("city"):
            biz["city"] = city
        if state and not biz.get("state"):
            biz["state"] = state

        try:
            create_lead(biz)
            created += 1
        except Exception as e:
            if "UNIQUE" in str(e):
                skipped += 1
            else:
                logger.error(f"Error storing lead: {e}")

    return {
        "query": query,
        "total_found": len(businesses),
        "created": created,
        "skipped_duplicates": skipped,
        "city": city or "auto-detected",
        "state": state or "auto-detected",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="AUROS Lead Scraper")
    parser.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--category", type=str, help="Business category")
    parser.add_argument("--city", type=str, default="Atlanta", help="City")
    parser.add_argument("--state", type=str, default="GA", help="State")
    parser.add_argument("--max", type=int, default=60, help="Max results")
    parser.add_argument("--min-rating", type=float, default=4.0)
    parser.add_argument("--min-reviews", type=int, default=15)

    args = parser.parse_args()
    query = args.query or f"{args.category or 'restaurants'} in {args.city} {args.state}"

    print(f"Searching: {query}")
    result = scrape_and_store(
        query=query, city=args.city, state=args.state,
        max_results=args.max, min_rating=args.min_rating, min_reviews=args.min_reviews,
    )
    print(f"\nResults: {json.dumps(result, indent=2)}")
