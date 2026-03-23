"""
AUROS AI — HERMES: Outreach & Communications Director
Cold outreach, email campaigns, newsletter, follow-up sequences, client communication.
The master networker who personalizes at scale.
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

logger = logging.getLogger("auros.hermes")


class Hermes(BaseAgent):
    """Outreach & Communications Director."""

    name = "HERMES"
    description = "Outreach & Communications Director. Cold outreach, email campaigns, newsletters, follow-ups, and client communication."
    persona = """You are HERMES, the Outreach & Communications Director at AUROS AI.

You are a master networker who makes every message feel handwritten, even at scale. You have deep expertise in:
- Cold outreach strategy (email, LinkedIn, DM)
- Email sequence design (welcome, nurture, re-engagement, winback)
- Newsletter production and optimization
- Follow-up psychology (timing, frequency, escalation)
- Personalization at scale (variables, triggers, segmentation)
- Deliverability optimization (SPF, DKIM, warm-up, sender reputation)
- Response handling and conversation management

Your communication principles:
1. Every message has ONE clear objective
2. Personalization is not just {first_name} — it's showing you understand their world
3. Follow-up is where deals are made — most people quit too early
4. The subject line is 80% of the battle
5. Short > long. Specific > generic. Value > pitch.

You have access to:
- Resend email API (primary sender)
- Gmail OAuth (fallback/personal sends)
- Newsletter production system
- Outreach templates and sequences
- Response tracking

CRITICAL: You NEVER send outreach without Leo's explicit approval. Draft it, show it, wait for approval.
The only autonomous sends are: pre-approved newsletter (daily), and pre-approved follow-up sequences."""

    knowledge_categories = ["copywriting", "psychology"]

    def get_tools(self) -> dict[str, str]:
        return {
            "draft_outreach": "Draft a cold outreach email/message",
            "draft_sequence": "Design a multi-step email sequence",
            "send_newsletter": "Produce and send the daily newsletter",
            "draft_followup": "Draft a follow-up message",
            "review_outreach": "Review and improve outreach copy",
            "outreach_strategy": "Design an outreach campaign strategy",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle outreach/communication requests."""
        classification = self._classify_request(message)
        action = classification.get("action", "general")

        if action == "draft_outreach":
            return self._draft_outreach(message, classification)
        elif action == "draft_sequence":
            return self._draft_sequence(message, classification)
        elif action == "newsletter":
            return self._handle_newsletter(message)
        elif action == "draft_followup":
            return self._draft_followup(message, classification)
        elif action == "review":
            return self._review_outreach(message)
        elif action == "strategy":
            return self._outreach_strategy(message)
        else:
            return self._general_comms(message)

    def handle_task(self, task: dict) -> dict:
        """Handle tasks from the queue."""
        task_type = task.get("task_type", "")
        payload = task.get("payload", {})

        if task_type == "send_newsletter":
            result = self._produce_newsletter()
            return {"response": result}
        elif task_type == "distribute_content":
            # Content from APOLLO ready for distribution
            result = self._distribute_content(payload)
            return {"response": result}
        elif task_type == "send_approved_outreach":
            result = self._send_outreach(payload)
            return {"response": result}

        return {"response": f"Unknown task type: {task_type}"}

    def _classify_request(self, message: str) -> dict:
        prompt = f"""Classify this outreach/communication request:

"{message}"

Actions: draft_outreach, draft_sequence, newsletter, draft_followup, review, strategy, general

JSON: {{"action": "name", "target": "who/company if mentioned", "channel": "email/linkedin/dm if mentioned"}}"""

        try:
            return self.think_json(prompt, system="Classify. JSON only.")
        except Exception:
            return {"action": "general"}

    def _draft_outreach(self, message: str, classification: dict) -> str:
        """Draft cold outreach — NEVER auto-sends."""
        target = classification.get("target", "")

        prompt = f"""Draft a cold outreach message.

Context: "{message}"
Target: {target or 'Not specified'}

Create 3 versions:
1. **Direct approach** — Get straight to the value
2. **Curiosity approach** — Lead with an intriguing insight
3. **Social proof approach** — Lead with results/credibility

For each version include:
- Subject line (email) or opening hook (DM)
- Full message body
- Clear CTA
- Suggested follow-up timing

Keep each under 150 words. Personalization placeholders: {{company}}, {{name}}, {{specific_detail}}.

IMPORTANT: These are drafts for Leo's review. Mark clearly: "DRAFT — Requires Leo's approval before sending." """

        response = self.think(prompt)
        self.remember("last_action", f"Drafted outreach: {target or message[:50]}")

        return f"{response}\n\n---\n*These are drafts. Reply with which version to send (or edits), and I'll queue it for delivery.*"

    def _draft_sequence(self, message: str, classification: dict) -> str:
        """Design a multi-step email sequence."""
        prompt = f"""Design an email sequence based on: "{message}"

Create a 5-email sequence:
1. **Day 0: Introduction** — First touch, establish relevance
2. **Day 3: Value add** — Share something useful, no ask
3. **Day 7: Case study** — Social proof, specific results
4. **Day 14: Direct ask** — Clear CTA with urgency
5. **Day 21: Breakup** — Last chance, friendly close

For each email:
- Subject line (with A/B variant)
- Preview text
- Body (under 100 words)
- CTA
- Notes on personalization

Include timing rationale for each touchpoint."""

        response = self.think(prompt)
        self.remember("last_action", f"Drafted sequence: {message[:50]}")
        return response

    def _draft_followup(self, message: str, classification: dict) -> str:
        """Draft a follow-up message."""
        prompt = f"""Draft a follow-up message based on: "{message}"

Create 2 versions:
1. **Gentle nudge** — Soft, helpful, reference value
2. **Direct follow-up** — Clear, specific, time-bound

Keep each under 80 words. Every follow-up must add new value — never just "checking in."

DRAFT — Requires Leo's approval."""

        response = self.think(prompt, max_tokens=1024)
        self.remember("last_action", f"Drafted follow-up: {message[:50]}")
        return response

    def _review_outreach(self, message: str) -> str:
        """Review and improve outreach copy."""
        prompt = f"""Review this outreach copy and suggest improvements:

{message}

Evaluate:
1. Subject line effectiveness (1-10)
2. Hook strength (1-10)
3. Clarity of value proposition (1-10)
4. CTA clarity (1-10)
5. Length appropriateness (1-10)
6. Personalization level (1-10)

Provide:
- Overall score
- Top 3 specific improvements
- Rewritten version incorporating all improvements"""

        return self.think(prompt)

    def _outreach_strategy(self, message: str) -> str:
        """Design an outreach campaign strategy."""
        prompt = f"""Design an outreach strategy based on: "{message}"

Cover:
1. **Target Definition** — Who exactly are we reaching?
2. **Channel Mix** — Which channels and why (email, LinkedIn, DM, calls)
3. **Messaging Framework** — Core angles and value props
4. **Sequence Design** — Touchpoint cadence
5. **Personalization Strategy** — How to personalize at scale
6. **Expected Metrics** — Open rate, reply rate, conversion targets
7. **Tools Needed** — What we need to execute
8. **Timeline** — When to start, key milestones"""

        response = self.think(prompt)
        self.remember("last_action", f"Outreach strategy: {message[:50]}")
        return response

    def _handle_newsletter(self, message: str) -> str:
        """Handle newsletter-related requests."""
        if "send" in message.lower() or "produce" in message.lower():
            return self._produce_newsletter()
        return self._general_comms(message)

    def _produce_newsletter(self) -> str:
        """Produce and send the daily newsletter."""
        try:
            import importlib
            mod = importlib.import_module("agents.newsletter.newsletter_agent")
            result = mod.run()
            self.remember("last_action", f"Newsletter sent: {datetime.now().strftime('%Y-%m-%d')}")
            return "Newsletter produced and sent successfully."
        except Exception as e:
            logger.error(f"Newsletter failed: {e}", exc_info=True)
            return f"Newsletter failed: {str(e)[:200]}"

    def _distribute_content(self, payload: dict) -> str:
        """Handle content distribution from APOLLO."""
        # For now, this creates a draft for review
        content_type = payload.get("type", "content")
        self.remember("pending_distribution", payload)
        self.notify(f"Content ready for distribution: {content_type}. Review and approve.")
        return f"Content queued for distribution. Awaiting approval."

    def _send_outreach(self, payload: dict) -> str:
        """Send approved outreach."""
        try:
            from agents.shared.config import RESEND_API_KEY
            import resend

            resend.api_key = RESEND_API_KEY
            result = resend.Emails.send({
                "from": payload.get("from", "leo@auros.ai"),
                "to": payload.get("to", ""),
                "subject": payload.get("subject", ""),
                "html": payload.get("body", ""),
            })
            self.remember("last_action", f"Sent outreach to: {payload.get('to', 'unknown')}")
            return f"Outreach sent to {payload.get('to', 'unknown')}."
        except Exception as e:
            return f"Send failed: {str(e)[:200]}"

    def _general_comms(self, message: str) -> str:
        """Handle general communication questions."""
        conversation_ctx = self.get_conversation_context(limit=3)
        return self.think(
            f'Leo asks: "{message}"\n\nRespond as an outreach expert.',
            system=self.get_system_prompt(extra_context=conversation_ctx),
        )
