"""
AUROS AI — PROSPECTOR: Lead Generation & Website Pipeline Director
Scrapes leads, scores prospects, generates websites, manages outreach pipeline.
The growth engine that turns strangers into clients.
"""

from __future__ import annotations

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system.agents.base_agent import BaseAgent
from system.db import (
    get_lead_stats, search_leads, get_lead, update_lead,
    create_campaign, get_campaigns,
)

logger = logging.getLogger("auros.prospector")


class Prospector(BaseAgent):
    """Lead Generation & Website Pipeline Director."""

    name = "PROSPECTOR"
    description = "Lead Generation & Website Pipeline Director. Scrapes local businesses, generates websites, manages outreach pipeline."
    persona = """You are PROSPECTOR, the Lead Generation & Website Pipeline Director at AUROS AI.

You find local businesses that need websites, build them beautiful sites, and coordinate outreach to convert them into paying clients. You have deep expertise in:
- Local business lead generation (Google Maps scraping, business directories)
- Lead scoring and qualification (rating quality, review volume, digital presence gaps)
- Website generation for local businesses (restaurants, salons, gyms, dental, professional services)
- Sales pipeline management (cold → warm → hot → converted)
- Outreach strategy (the website IS the pitch — show, don't tell)

Your pipeline:
1. SCRAPE — Find businesses with great reviews but no website
2. SCORE — Rate leads by conversion potential (rating, reviews, social presence)
3. BUILD — Generate a real, beautiful website for the business
4. DEPLOY — Put it live on Netlify so they can see it immediately
5. OUTREACH — Hand to HERMES with the live URL as the hook
6. TRACK — Monitor responses, follow up, alert Leo for sales calls

Target market: United States, starting with Atlanta, Georgia.
Business categories: restaurants, salons, gyms, dental offices, professional services.

Your value proposition to leads: "We already built your website. Take a look: [live URL]"
This is infinitely more compelling than "Hey, do you want a website?"

When Leo asks you to scrape or find leads:
1. Run the scraper for the specified city/category
2. Score all results
3. Report how many leads found, how many are warm/hot
4. Recommend next steps (generate websites for top leads, launch campaign)

You coordinate with:
- HERMES for sending outreach emails
- APOLLO for custom content if needed
- SENTINEL for tracking conversion metrics
- FORGE for onboarding converted leads into the full marketing pipeline"""

    knowledge_categories = ["psychology"]

    def get_tools(self) -> dict[str, str]:
        return {
            "scrape_leads": "Scrape Google Maps for businesses without websites",
            "enrich_leads": "Find contact emails and score leads",
            "generate_website": "Generate a beautiful website for a lead",
            "deploy_website": "Deploy a website to Netlify (live URL)",
            "pipeline_status": "Show lead pipeline funnel stats",
            "launch_campaign": "Launch an outreach campaign for a city/category",
            "top_leads": "Show the highest-scored leads ready for outreach",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle lead gen / website pipeline requests."""
        classification = self._classify_request(message)
        action = classification.get("action", "general")

        if action == "scrape":
            return self._handle_scrape(message, classification)
        elif action == "enrich":
            return self._handle_enrich(message, classification)
        elif action == "generate_website":
            return self._handle_generate(message, classification)
        elif action == "deploy":
            return self._handle_deploy(message, classification)
        elif action == "pipeline_status":
            return self._pipeline_status()
        elif action == "top_leads":
            return self._top_leads(classification)
        elif action == "launch_campaign":
            return self._handle_campaign(message, classification)
        else:
            return self._general_prospecting(message)

    def handle_task(self, task: dict) -> dict:
        """Handle tasks from the queue."""
        task_type = task.get("task_type", "")
        payload = task.get("payload", {})

        if task_type == "scrape_leads":
            result = self._run_scrape(
                payload.get("city", "Atlanta"),
                payload.get("state", "GA"),
                payload.get("category", "restaurants"),
                payload.get("max_results", 50),
            )
            return {"response": result}
        elif task_type == "enrich_batch":
            result = self._run_enrich()
            return {"response": result}
        elif task_type == "generate_websites":
            result = self._generate_for_top_leads(payload.get("count", 5))
            return {"response": result}

        return {"response": f"Unknown task type: {task_type}"}

    def _classify_request(self, message: str) -> dict:
        prompt = f"""Classify this lead generation request:

"{message}"

Actions: scrape, enrich, generate_website, deploy, pipeline_status, top_leads, launch_campaign, general

JSON: {{"action": "name", "city": "if mentioned", "state": "2-letter state if mentioned", "category": "business type if mentioned", "lead_id": "if a specific lead referenced"}}"""

        try:
            return self.think_json(prompt, system="Classify. JSON only.")
        except Exception:
            return {"action": "general"}

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    def _handle_scrape(self, message: str, classification: dict) -> str:
        """Handle a scrape request."""
        city = classification.get("city", "Atlanta")
        state = classification.get("state", "GA")
        category = classification.get("category", "restaurants")

        # Request approval for scraping (uses API credits)
        self.request_approval(
            f"Scrape {category} in {city}, {state} from Google Maps",
            {"city": city, "state": state, "category": category},
        )

        return (
            f"Scrape request created for *{category}* in *{city}, {state}*.\n\n"
            f"I've sent you an approval request. Once approved, I'll:\n"
            f"1. Scrape Google Maps for businesses with 4+ stars, 15+ reviews, no website\n"
            f"2. Score and rank all leads\n"
            f"3. Report the results\n\n"
            f"This typically takes 5-10 minutes for 50 leads."
        )

    def _run_scrape(self, city: str, state: str, category: str, max_results: int = 50) -> str:
        """Actually run the scraper."""
        try:
            from tools.lead_scraper import scrape_and_store
            query = f"{category} {city} {state}"
            self.notify(f"Scraping {category} in {city}, {state}...")
            result = scrape_and_store(
                query=query,
                city=city,
                state=state,
                max_results=max_results,
            )
            self.remember("last_action", f"Scraped {category} in {city}: {result.get('created', 0)} leads")
            self.notify(
                f"Scraping complete: {result.get('created', 0)} new leads found for {category} in {city}, {state}.\n"
                f"Total scraped: {result.get('scraped', 0)}, Duplicates skipped: {result.get('skipped_duplicates', 0)}",
                level="info",
            )
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Scraping failed: {e}", exc_info=True)
            return f"Scraping failed: {str(e)[:300]}"

    # ------------------------------------------------------------------
    # Enrichment
    # ------------------------------------------------------------------

    def _handle_enrich(self, message: str, classification: dict) -> str:
        """Handle enrichment request."""
        result = self._run_enrich()
        return f"*Enrichment Results:*\n{result}"

    def _run_enrich(self) -> str:
        """Run enrichment on unenriched leads."""
        try:
            from tools.lead_enricher import enrich_leads
            result = enrich_leads(limit=50)
            self.remember("last_action", f"Enriched {result.get('processed', 0)} leads")
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Enrichment failed: {str(e)[:200]}"

    # ------------------------------------------------------------------
    # Website Generation
    # ------------------------------------------------------------------

    def _handle_generate(self, message: str, classification: dict) -> str:
        """Handle website generation request."""
        lead_id = classification.get("lead_id", "")

        if lead_id:
            return self._generate_for_lead(lead_id)
        else:
            # Generate for top leads
            return self._generate_for_top_leads(5)

    def _generate_for_lead(self, lead_id: str) -> str:
        """Generate website for a specific lead."""
        try:
            from tools.website_generator import generate_from_lead
            result = generate_from_lead(lead_id)
            if result.get("error"):
                return f"Error: {result['error']}"

            self.remember("last_action", f"Generated website: {result.get('business_name', '')}")
            return (
                f"Website generated for *{result.get('business_name', '')}*\n"
                f"Template: {result.get('template', '')}\n"
                f"File: {result.get('html_path', '')}\n\n"
                f"Ready to deploy. Say 'deploy website for {lead_id}' to put it live."
            )
        except Exception as e:
            return f"Generation failed: {str(e)[:200]}"

    def _generate_for_top_leads(self, count: int = 5) -> str:
        """Generate websites for the top-scored leads without websites."""
        leads = search_leads(min_score=30, has_website=False, limit=count)
        leads = [l for l in leads if not l.get("website_generated")]

        if not leads:
            return "No qualifying leads found. Try scraping more leads first."

        results = []
        for lead in leads[:count]:
            try:
                from tools.website_generator import generate_from_lead
                result = generate_from_lead(lead["id"])
                results.append(f"  {lead['business_name']}: {'Done' if not result.get('error') else result['error']}")
            except Exception as e:
                results.append(f"  {lead['business_name']}: Failed ({str(e)[:50]})")

        self.remember("last_action", f"Generated {len(results)} websites")
        return f"*Generated {len(results)} websites:*\n" + "\n".join(results)

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def _handle_deploy(self, message: str, classification: dict) -> str:
        """Handle deployment request."""
        lead_id = classification.get("lead_id", "")
        if not lead_id:
            return "I need a lead ID to deploy. Use 'top leads' to see available leads."

        try:
            from tools.deploy_website import deploy_lead_website
            result = deploy_lead_website(lead_id)
            if result.get("error"):
                return f"Deploy failed: {result['error']}"

            self.remember("last_action", f"Deployed website: {result.get('url', '')}")
            return (
                f"Website deployed!\n\n"
                f"Live URL: {result.get('url', '')}\n"
                f"Admin: {result.get('admin_url', '')}\n\n"
                f"Ready for outreach. I can hand this to HERMES to send the pitch email."
            )
        except Exception as e:
            return f"Deploy failed: {str(e)[:200]}"

    # ------------------------------------------------------------------
    # Pipeline Status
    # ------------------------------------------------------------------

    def _pipeline_status(self) -> str:
        """Show the full lead pipeline funnel."""
        stats = get_lead_stats()
        campaigns = get_campaigns()

        lines = ["*Lead Pipeline Status*", ""]
        lines.append(f"Total Leads: {stats['total']}")
        lines.append("")

        # Funnel
        lines.append("*Pipeline Funnel:*")
        for status, count in stats.get("by_status", {}).items():
            lines.append(f"  {status.title()}: {count}")

        lines.append("")
        lines.append("*Temperature:*")
        for temp, count in stats.get("by_temperature", {}).items():
            indicator = {"hot": "Hot", "warm": "Warm", "cold": "Cold"}.get(temp, temp)
            lines.append(f"  {indicator}: {count}")

        lines.append(f"\nWebsites Built: {stats.get('websites_built', 0)}")

        if campaigns:
            lines.append(f"\n*Active Campaigns:* {len(campaigns)}")
            for c in campaigns[:3]:
                lines.append(f"  {c.get('name', '')}: {c.get('sent_count', 0)} sent, {c.get('reply_count', 0)} replies")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Top Leads
    # ------------------------------------------------------------------

    def _top_leads(self, classification: dict) -> str:
        """Show top-scored leads."""
        city = classification.get("city")
        category = classification.get("category")

        leads = search_leads(city=city, category=category, min_score=20, has_website=False, limit=10)

        if not leads:
            return "No leads found matching criteria. Try scraping first."

        lines = [f"*Top {len(leads)} Leads:*", ""]
        for lead in leads:
            temp = {"hot": "HOT", "warm": "WARM", "cold": "COLD"}.get(lead.get("lead_temperature", ""), "?")
            has_site = "Built" if lead.get("website_generated") else "Not built"
            lines.append(
                f"  [{lead['id']}] *{lead['business_name']}* ({lead.get('city', '')}, {lead.get('state', '')})\n"
                f"    {lead.get('rating', 0)}★ | {lead.get('review_count', 0)} reviews | "
                f"Score: {lead.get('lead_score', 0)} ({temp}) | Website: {has_site}"
            )
            if lead.get("contact_email"):
                lines.append(f"    Email: {lead['contact_email']}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Campaign
    # ------------------------------------------------------------------

    def _handle_campaign(self, message: str, classification: dict) -> str:
        """Handle campaign launch request."""
        city = classification.get("city", "Atlanta")
        state = classification.get("state", "GA")
        category = classification.get("category", "restaurants")

        # Check we have leads ready
        leads = search_leads(city=city, state=state, category=category, min_score=40, has_website=False, limit=20)
        warm_leads = [l for l in leads if l.get("website_generated") and l.get("contact_email")]

        if not warm_leads:
            return (
                f"Not ready to launch campaign for {category} in {city}, {state}.\n\n"
                f"Need: Leads with generated websites + contact emails.\n"
                f"Found: {len(leads)} leads total, {len(warm_leads)} ready for outreach.\n\n"
                f"Steps needed:\n"
                f"1. Scrape leads (if {len(leads)} < 10)\n"
                f"2. Enrich with emails\n"
                f"3. Generate websites for top leads\n"
                f"4. Then launch campaign"
            )

        self.request_approval(
            f"Launch outreach campaign: {category} in {city}, {state} ({len(warm_leads)} leads)",
            {
                "city": city, "state": state, "category": category,
                "lead_count": len(warm_leads),
                "lead_ids": [l["id"] for l in warm_leads],
            },
        )

        return (
            f"Campaign ready for *{category}* in *{city}, {state}*\n\n"
            f"Leads ready: {len(warm_leads)}\n"
            f"Each will receive a personalized email with their live website demo URL.\n\n"
            f"Approval request sent. Once approved, HERMES will start sending."
        )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------

    def _general_prospecting(self, message: str) -> str:
        """Handle general prospecting questions."""
        stats = get_lead_stats()
        conversation_ctx = self.get_conversation_context(limit=3)
        extra = f"Current pipeline: {json.dumps(stats)}\n{conversation_ctx}"

        return self.think(
            f'Leo asks: "{message}"\n\nRespond as the lead gen expert. Reference current pipeline data.',
            system=self.get_system_prompt(extra_context=extra),
        )
