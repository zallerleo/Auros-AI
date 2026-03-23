#!/usr/bin/env python3
"""
AUROS AI — Website Deployer
Deploys generated HTML websites to Netlify for instant live URLs.

Usage:
    python tools/deploy_website.py --html portfolio/websites/joes-pizza_20260323.html --name joes-pizza-atlanta
"""

from __future__ import annotations

import sys
import os
import json
import hashlib
import argparse
import logging
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN", "")
NETLIFY_API = "https://api.netlify.com/api/v1"

logger = logging.getLogger("auros.deploy")


def deploy_to_netlify(
    html_path: str,
    site_name: str | None = None,
    site_id: str | None = None,
) -> dict:
    """
    Deploy a single HTML file to Netlify.

    Args:
        html_path: Path to the index.html file
        site_name: Desired subdomain (e.g., "joes-pizza" → joes-pizza.netlify.app)
        site_id: Existing site ID to update (for redeployments)

    Returns: {url, site_id, deploy_id, admin_url}
    """
    if not NETLIFY_TOKEN:
        return {"error": "NETLIFY_TOKEN not set in .env. Get one at https://app.netlify.com/user/applications#personal-access-tokens"}

    headers = {
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
    }

    html_file = Path(html_path)
    if not html_file.exists():
        return {"error": f"HTML file not found: {html_path}"}

    html_content = html_file.read_bytes()
    file_hash = hashlib.sha1(html_content).hexdigest()

    try:
        # Step 1: Create or get the site
        if site_id:
            # Update existing site
            logger.info(f"Updating existing site: {site_id}")
        else:
            # Create new site
            create_data = {}
            if site_name:
                # Clean the name for Netlify
                clean_name = site_name.lower().replace(" ", "-").replace("'", "")
                clean_name = "".join(c for c in clean_name if c.isalnum() or c == "-")
                create_data["name"] = clean_name

            resp = requests.post(
                f"{NETLIFY_API}/sites",
                headers={**headers, "Content-Type": "application/json"},
                json=create_data,
                timeout=30,
            )

            if resp.status_code not in (200, 201):
                # Name might be taken, try without
                if "name already exists" in resp.text.lower() or resp.status_code == 422:
                    logger.info("Site name taken, creating with auto-name")
                    resp = requests.post(
                        f"{NETLIFY_API}/sites",
                        headers={**headers, "Content-Type": "application/json"},
                        json={},
                        timeout=30,
                    )

                if resp.status_code not in (200, 201):
                    return {"error": f"Failed to create site: {resp.status_code} {resp.text[:200]}"}

            site_data = resp.json()
            site_id = site_data["id"]
            logger.info(f"Site created: {site_data.get('url', '')} (id: {site_id})")

        # Step 2: Deploy using file digest
        deploy_payload = {
            "files": {
                "/index.html": file_hash,
            }
        }

        resp = requests.post(
            f"{NETLIFY_API}/sites/{site_id}/deploys",
            headers={**headers, "Content-Type": "application/json"},
            json=deploy_payload,
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            return {"error": f"Deploy creation failed: {resp.status_code} {resp.text[:200]}"}

        deploy_data = resp.json()
        deploy_id = deploy_data["id"]

        # Step 3: Upload the file
        required = deploy_data.get("required", [])
        if file_hash in required or not deploy_data.get("required"):
            resp = requests.put(
                f"{NETLIFY_API}/deploys/{deploy_id}/files/index.html",
                headers={**headers, "Content-Type": "application/octet-stream"},
                data=html_content,
                timeout=30,
            )

            if resp.status_code not in (200, 201):
                return {"error": f"File upload failed: {resp.status_code}"}

        # Get final site info
        resp = requests.get(
            f"{NETLIFY_API}/sites/{site_id}",
            headers=headers,
            timeout=10,
        )
        site_info = resp.json() if resp.status_code == 200 else {}

        result = {
            "url": site_info.get("ssl_url") or site_info.get("url", f"https://{site_id}.netlify.app"),
            "site_id": site_id,
            "deploy_id": deploy_id,
            "admin_url": f"https://app.netlify.com/sites/{site_info.get('name', site_id)}",
        }

        logger.info(f"Deployed: {result['url']}")
        return result

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)[:200]}"}


def deploy_lead_website(lead_id: str) -> dict:
    """Deploy a generated website for a specific lead."""
    from system.db import get_lead, update_lead, update_website, get_connection

    lead = get_lead(lead_id)
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    if not lead.get("website_generated"):
        return {"error": f"No website generated for lead {lead_id}. Run website_generator first."}

    # Find the website record
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM websites WHERE lead_id = ? ORDER BY created_at DESC LIMIT 1", (lead_id,)
    ).fetchone()
    conn.close()

    if not row:
        return {"error": "Website record not found in database"}

    website = dict(row)
    html_path = website.get("html_path", "")

    if not html_path or not Path(html_path).exists():
        return {"error": f"HTML file not found: {html_path}"}

    # Generate site name from business name + city
    biz_name = lead.get("business_name", "site").lower()
    city = lead.get("city", "").lower()
    site_name = f"{biz_name}-{city}".replace(" ", "-").replace("'", "")[:50]

    # Deploy
    result = deploy_to_netlify(html_path, site_name=site_name)

    if result.get("error"):
        return result

    # Update records
    update_website(website["id"], deploy_url=result["url"], deploy_id=result.get("site_id", ""), status="deployed")
    update_lead(lead_id, generated_site_url=result["url"])

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="AUROS Website Deployer")
    parser.add_argument("--html", type=str, help="Path to HTML file")
    parser.add_argument("--name", type=str, help="Desired site name")
    parser.add_argument("--lead-id", type=str, help="Deploy website for a lead")

    args = parser.parse_args()

    if args.lead_id:
        result = deploy_lead_website(args.lead_id)
    elif args.html:
        result = deploy_to_netlify(args.html, site_name=args.name)
    else:
        print("Provide --html <path> or --lead-id <id>")
        sys.exit(1)

    print(f"\nResult: {json.dumps(result, indent=2)}")
