#!/usr/bin/env python3
"""
AUROS AI — Lead Enricher
Finds contact emails via Hunter.io and scores leads.

Usage:
    python tools/lead_enricher.py --enrich-all
    python tools/lead_enricher.py --score-all
    python tools/lead_enricher.py --lead-id abc123
"""

from __future__ import annotations

import sys
import json
import argparse
import logging
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.shared.config import PROJECT_ROOT as _PR
from dotenv import load_dotenv
import os

load_dotenv(_PR / ".env", override=True)

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

logger = logging.getLogger("auros.enricher")


# ---------------------------------------------------------------------------
# Email Enrichment (Hunter.io)
# ---------------------------------------------------------------------------

def find_email_hunter(
    business_name: str,
    domain: str | None = None,
    city: str = "",
    state: str = "",
) -> dict:
    """
    Find contact email for a business using Hunter.io.
    Returns: {email, confidence, type, source}
    """
    if not HUNTER_API_KEY:
        logger.warning("HUNTER_API_KEY not set. Skipping email enrichment.")
        return {}

    try:
        # If we have a domain, use domain search
        if domain:
            resp = requests.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails = data.get("emails", [])
                if emails:
                    best = emails[0]
                    return {
                        "email": best.get("value", ""),
                        "confidence": best.get("confidence", 0),
                        "type": best.get("type", ""),
                        "source": "hunter_domain",
                    }

        # Fallback: email finder with company name
        resp = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "company": business_name,
                "api_key": HUNTER_API_KEY,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data.get("email"):
                return {
                    "email": data["email"],
                    "confidence": data.get("score", 0),
                    "type": data.get("type", ""),
                    "source": "hunter_finder",
                }

    except Exception as e:
        logger.error(f"Hunter.io error for {business_name}: {e}")

    return {}


def generate_common_emails(business_name: str, domain: str | None = None) -> list[str]:
    """Generate common email patterns as fallback when Hunter.io has no results."""
    if not domain:
        return []

    # Strip www and extract base domain
    clean = domain.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

    # Common patterns for small businesses
    patterns = [
        f"info@{clean}",
        f"contact@{clean}",
        f"hello@{clean}",
    ]
    return patterns


# ---------------------------------------------------------------------------
# Lead Scoring
# ---------------------------------------------------------------------------

def score_lead(lead: dict) -> tuple[int, str]:
    """
    Score a lead 0-100 and assign temperature.
    Higher = more likely to convert.

    Factors:
    - Rating quality (high ratings = established, cares about quality)
    - Review volume (many reviews = popular, more to gain from a website)
    - No website (the core opportunity)
    - Has social media (digitally aware, more likely to buy)
    - Has email found (we can actually reach them)
    - Email confidence (higher = more likely to land)
    """
    score = 0

    # Rating quality (max 25 points)
    rating = lead.get("rating", 0)
    if rating >= 4.8:
        score += 25
    elif rating >= 4.5:
        score += 20
    elif rating >= 4.0:
        score += 10

    # Review volume (max 25 points)
    reviews = lead.get("review_count", 0)
    if reviews >= 200:
        score += 25
    elif reviews >= 100:
        score += 20
    elif reviews >= 50:
        score += 15
    elif reviews >= 20:
        score += 10

    # No website = opportunity (20 points)
    if not lead.get("has_website"):
        score += 20

    # Has social media = digitally aware (15 points)
    if lead.get("has_social_media"):
        score += 15

    # Has contact email (10 points)
    if lead.get("contact_email"):
        score += 10

    # Email confidence bonus (5 points)
    confidence = lead.get("email_confidence", 0)
    if confidence and confidence > 80:
        score += 5

    # Determine temperature
    if score >= 61:
        temp = "hot"
    elif score >= 31:
        temp = "warm"
    else:
        temp = "cold"

    return score, temp


# ---------------------------------------------------------------------------
# Batch Operations
# ---------------------------------------------------------------------------

def enrich_leads(lead_ids: list[str] | None = None, limit: int = 50) -> dict:
    """Enrich leads with emails and scores. Returns summary."""
    from system.db import search_leads, get_lead, update_lead

    if lead_ids:
        leads = [get_lead(lid) for lid in lead_ids if get_lead(lid)]
    else:
        # Get leads without emails
        leads = search_leads(status="new", limit=limit)

    enriched = 0
    scored = 0
    emails_found = 0

    for lead in leads:
        if not lead:
            continue

        # Try to find email if not already set
        if not lead.get("contact_email"):
            domain = lead.get("website_url", "").strip() or None
            result = find_email_hunter(
                lead["business_name"],
                domain=domain,
                city=lead.get("city", ""),
                state=lead.get("state", ""),
            )
            if result.get("email"):
                update_lead(
                    lead["id"],
                    contact_email=result["email"],
                    email_confidence=result.get("confidence", 0),
                    email_source=result.get("source", ""),
                )
                emails_found += 1
                lead["contact_email"] = result["email"]
                lead["email_confidence"] = result.get("confidence", 0)
            enriched += 1

        # Score the lead
        score, temp = score_lead(lead)
        update_lead(lead["id"], lead_score=score, lead_temperature=temp)
        scored += 1

    return {
        "processed": len(leads),
        "enriched": enriched,
        "emails_found": emails_found,
        "scored": scored,
    }


def score_all_leads() -> dict:
    """Re-score all leads."""
    from system.db import search_leads, update_lead

    leads = search_leads(limit=1000)
    scored = 0
    for lead in leads:
        score, temp = score_lead(lead)
        update_lead(lead["id"], lead_score=score, lead_temperature=temp)
        scored += 1

    return {"scored": scored}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="AUROS Lead Enricher")
    parser.add_argument("--enrich-all", action="store_true", help="Enrich all unenriched leads")
    parser.add_argument("--score-all", action="store_true", help="Re-score all leads")
    parser.add_argument("--lead-id", type=str, help="Enrich a specific lead")
    parser.add_argument("--limit", type=int, default=50, help="Max leads to process")

    args = parser.parse_args()

    if args.lead_id:
        result = enrich_leads([args.lead_id])
    elif args.score_all:
        result = score_all_leads()
    else:
        result = enrich_leads(limit=args.limit)

    print(f"\nResults: {json.dumps(result, indent=2)}")
