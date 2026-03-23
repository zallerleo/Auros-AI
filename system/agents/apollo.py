"""
AUROS AI — APOLLO: Creative & Content Director
Content creation, video production, social posts, copywriting, creative direction.
The voice and visual identity of every client.
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
from agents.shared.config import PORTFOLIO_DIR

logger = logging.getLogger("auros.apollo")


class Apollo(BaseAgent):
    """Creative & Content Director."""

    name = "APOLLO"
    description = "Creative & Content Director. Content creation, video scripts, social posts, copywriting, and creative direction."
    persona = """You are APOLLO, the Creative Director at AUROS AI.

You blend data with art — every piece of content has a strategic reason behind it. You have deep expertise in:
- Copywriting frameworks (AIDA, PAS, BAB, Hook-Value-Close, Before-After-Bridge)
- Video script architecture (15s/30s/60s formats, shot-by-shot breakdowns)
- Social media content strategy (platform-specific optimization)
- Visual direction and brand consistency
- Psychology of persuasion (Cialdini's principles, cognitive biases)
- Content calendar execution
- Short-form video trends (TikTok, Reels, Shorts)
- Exhibition and event marketing content

Your creative process:
1. Understand the strategic objective (what are we trying to achieve?)
2. Know the audience (who are we talking to?)
3. Choose the framework (which copywriting/content approach fits?)
4. Create with precision (every word earns its place)
5. Optimize for platform (what works on TikTok ≠ what works on LinkedIn)

You have access to:
- Content creation agents (social posts, video scripts)
- Content engine (rendering pipeline)
- Video generation (Remotion for programmatic video)
- Content calendar system
- Brand tokens and voice guidelines

When creating content, always:
- Start from the brand voice and positioning
- Use proven frameworks (don't just wing it)
- Include platform-specific variations
- Think about the hook first — if the first 3 seconds don't grab, nothing else matters"""

    knowledge_categories = ["copywriting", "psychology", "video_marketing", "social_media", "content_strategy"]

    def get_tools(self) -> dict[str, str]:
        return {
            "create_social_posts": "Generate platform-optimized social media posts",
            "create_video_script": "Write video scripts with shot breakdowns",
            "create_content_batch": "Batch content creation for a content calendar",
            "generate_hooks": "Generate attention-grabbing hooks for any topic",
            "adapt_content": "Adapt content across platforms (TikTok → LinkedIn → Instagram)",
            "content_calendar": "Build or execute a content calendar",
            "creative_brief": "Create a creative brief for a campaign",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle creative/content requests."""
        classification = self._classify_request(message)
        action = classification.get("action", "general")
        company = classification.get("company", "")
        topic = classification.get("topic", message)

        if action == "social_posts":
            return self._create_social_posts(topic, company, message)
        elif action == "video_script":
            return self._create_video_script(topic, company, message)
        elif action == "hooks":
            return self._generate_hooks(topic, message)
        elif action == "content_batch":
            return self._create_content_batch(company, message)
        elif action == "creative_brief":
            return self._creative_brief(topic, message)
        elif action == "adapt":
            return self._adapt_content(topic, message)
        else:
            return self._general_creative(message)

    def handle_task(self, task: dict) -> dict:
        """Handle tasks from the queue."""
        task_type = task.get("task_type", "")
        payload = task.get("payload", {})

        if task_type == "content_brief":
            result = self._create_from_brief(payload)
            return {"response": result}
        elif task_type == "create_social_posts":
            result = self._create_social_posts(
                payload.get("topic", ""), payload.get("company", ""), ""
            )
            return {"response": result}
        elif task_type == "create_video_script":
            result = self._create_video_script(
                payload.get("topic", ""), payload.get("company", ""), ""
            )
            return {"response": result}

        return {"response": f"Unknown task type: {task_type}"}

    def _classify_request(self, message: str) -> dict:
        prompt = f"""Classify this creative request:

"{message}"

Actions: social_posts, video_script, hooks, content_batch, creative_brief, adapt, general

JSON: {{"action": "name", "company": "if mentioned", "topic": "the creative topic"}}"""

        try:
            return self.think_json(prompt, system="Classify. JSON only.")
        except Exception:
            return {"action": "general", "topic": message}

    def _create_social_posts(self, topic: str, company: str, original: str) -> str:
        """Generate social media posts."""
        brand_ctx = self._load_client_context(company) if company else ""

        prompt = f"""Create social media posts for: {topic}

{brand_ctx}

Generate posts for each platform:
1. **Instagram** (carousel or single post — include caption + hashtags)
2. **TikTok** (script for short video — hook + content + CTA)
3. **LinkedIn** (professional angle — thought leadership style)
4. **X/Twitter** (thread of 3-5 tweets — punchy, shareable)

For each post:
- Start with a strong hook
- Use the appropriate copywriting framework
- Include a clear CTA
- Platform-specific formatting and length

Original request: "{original}" """

        response = self.think(prompt)
        self.remember("last_action", f"Social posts: {topic[:100]}")
        return response

    def _create_video_script(self, topic: str, company: str, original: str) -> str:
        """Write video scripts."""
        brand_ctx = self._load_client_context(company) if company else ""

        prompt = f"""Write video scripts for: {topic}

{brand_ctx}

Create 3 video formats:
1. **15-second** (hook + one key message + CTA — for Reels/TikTok)
2. **30-second** (problem + solution + proof + CTA)
3. **60-second** (full story arc — hook, context, value, transformation, CTA)

For each script include:
- Shot-by-shot breakdown with timestamps
- Exact text overlays
- Voiceover script (if applicable)
- Music direction (mood, tempo)
- Visual direction for each shot
- Platform optimization notes"""

        response = self.think(prompt)
        self.remember("last_action", f"Video scripts: {topic[:100]}")
        return response

    def _generate_hooks(self, topic: str, original: str) -> str:
        """Generate attention hooks."""
        prompt = f"""Generate 10 attention-grabbing hooks for: {topic}

Mix these hook types:
- Question hooks ("Did you know...?")
- Contrarian hooks ("Everyone says X. They're wrong.")
- Number hooks ("3 things that...")
- Story hooks ("Last week, something happened...")
- Challenge hooks ("Stop doing X. Here's why.")

For each hook, note:
- Best platform (TikTok, Instagram, LinkedIn, X)
- Why it works (psychological principle)
- Suggested content to follow the hook"""

        response = self.think(prompt, max_tokens=2048)
        self.remember("last_action", f"Hooks: {topic[:100]}")
        return response

    def _create_content_batch(self, company: str, original: str) -> str:
        """Batch content creation for a calendar."""
        if not company:
            return "I need a company name to create a content batch. Which client?"

        try:
            import importlib
            mod = importlib.import_module("agents.content_creator.content_agent")
            result = mod.run(company=company)
            self.remember("last_action", f"Content batch: {company}")
            return f"Content batch created for {company}. Files saved to portfolio."
        except Exception as e:
            return f"Content batch failed: {str(e)[:200]}"

    def _creative_brief(self, topic: str, original: str) -> str:
        """Create a creative brief."""
        prompt = f"""Create a creative brief for: {topic}

Include:
1. **Objective**: What are we trying to achieve?
2. **Target Audience**: Who are we talking to?
3. **Key Message**: One sentence that captures the core idea
4. **Tone & Style**: How should it feel?
5. **Content Formats**: What types of content should we create?
6. **Distribution Channels**: Where does this go?
7. **Success Metrics**: How do we measure success?
8. **Timeline**: Suggested production timeline
9. **References/Inspiration**: Similar campaigns or content to reference"""

        response = self.think(prompt)
        self.remember("last_action", f"Creative brief: {topic[:100]}")
        return response

    def _adapt_content(self, content: str, original: str) -> str:
        """Adapt content across platforms."""
        prompt = f"""Adapt this content for multiple platforms:

Original content:
{content[:2000]}

Create optimized versions for:
1. **Instagram** — visual-first, caption with line breaks, 5-10 hashtags
2. **TikTok** — script format, hook-first, trending audio suggestion
3. **LinkedIn** — professional tone, thought leadership angle, longer form
4. **X/Twitter** — punchy, thread-worthy, max engagement
5. **Email** — subject line + preview text + body snippet

Keep the core message but adapt the format, tone, and length for each platform."""

        return self.think(prompt)

    def _create_from_brief(self, brief: dict) -> str:
        """Create content from a structured brief (from FORGE)."""
        prompt = f"""Create content based on this brief:

{json.dumps(brief, indent=2)[:4000]}

Execute the brief — create the actual content pieces described."""

        return self.think(prompt)

    def _general_creative(self, message: str) -> str:
        """Handle general creative questions."""
        conversation_ctx = self.get_conversation_context(limit=3)
        return self.think(
            f'Leo asks: "{message}"\n\nRespond as a creative director.',
            system=self.get_system_prompt(extra_context=conversation_ctx),
        )

    def _load_client_context(self, company: str) -> str:
        """Load brand and audit context for a client."""
        if not company:
            return ""

        slug = company.lower().replace(" ", "_")
        client_dir = PORTFOLIO_DIR / f"client_{slug}"
        if not client_dir.exists():
            return ""

        context_parts = []
        for prefix in ("brand_identity_", "marketing_audit_", "positioning_"):
            files = sorted(client_dir.glob(f"{prefix}*.json"), reverse=True)
            if files:
                try:
                    data = json.loads(files[0].read_text())
                    context_parts.append(f"## {prefix.replace('_', ' ').title()}\n{json.dumps(data)[:1500]}")
                except Exception:
                    pass

        return "\n\n".join(context_parts)
