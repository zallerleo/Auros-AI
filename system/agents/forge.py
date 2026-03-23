"""
AUROS AI — FORGE: Strategy & Client Director
Owns the full client pipeline: onboarding, strategy, positioning, proposals, delivery.
The architect who turns research into action plans.
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

logger = logging.getLogger("auros.forge")


class Forge(BaseAgent):
    """Strategy & Client Director."""

    name = "FORGE"
    description = "Strategy & Client Director. Client onboarding, marketing strategy, positioning, proposals, and pipeline management."
    persona = """You are FORGE, the Strategy & Client Director at AUROS AI.

You are a senior strategist who builds frameworks and translates research into action. You have deep expertise in:
- Marketing strategy development (90-day plans, quarterly reviews)
- Brand positioning (unique angles, competitive differentiation)
- Client onboarding workflows (from first contact to active client)
- Proposal generation (tiered pricing, ROI projections)
- Audience segmentation and persona development
- Marketing audit methodology
- Content calendar architecture
- Quality assurance and brand compliance

You own the full 13-stage client delivery pipeline:
1. Research → 2. Audit → 3. Brand → 4. Positioning → 5. Plan →
6. Vision → 7. Trend → 8. Content → 9. Calendar → 10. Proposal →
11. Quality → 12. Compliance → 13. GEO

Your decisions are grounded in data (from SCOUT) and result in actionable deliverables (executed by APOLLO and HERMES).

When onboarding a new client:
1. Gather basic info (company, website, social channels, goals)
2. Request approval from Leo before starting the pipeline
3. Run pipeline stages in order, tracking progress
4. Hand content briefs to APOLLO, outreach to HERMES
5. Generate proposal with tiered pricing
6. Quality-check everything before delivery

Always think strategically. Every recommendation should tie back to business outcomes."""

    knowledge_categories = [
        "copywriting", "psychology", "social_media", "video_marketing",
        "paid_media", "analytics", "branding", "content_strategy",
    ]

    def get_tools(self) -> dict[str, str]:
        return {
            "run_pipeline": "Run the full client delivery pipeline",
            "run_stage": "Run a specific pipeline stage",
            "pipeline_status": "Check pipeline progress for a client",
            "create_proposal": "Generate a client proposal",
            "marketing_audit": "Run a marketing audit",
            "brand_analysis": "Extract brand identity",
            "positioning": "Develop positioning angles",
            "marketing_plan": "Build a 90-day marketing plan",
            "list_clients": "List all client portfolios",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle strategy/client requests from Leo."""
        classification = self._classify_request(message)
        action = classification.get("action", "general")
        company = classification.get("company", "")

        if action == "onboard":
            return self._onboard_client(company, message)
        elif action == "pipeline_status":
            return self._pipeline_status(company)
        elif action == "run_stage":
            stage = classification.get("stage", "")
            return self._run_stage(company, stage, message)
        elif action == "proposal":
            return self._create_proposal(company, message)
        elif action == "audit":
            return self._run_audit(company, message)
        elif action == "plan":
            return self._create_plan(company, message)
        elif action == "list_clients":
            return self._list_clients()
        else:
            return self._general_strategy(message)

    def handle_task(self, task: dict) -> dict:
        """Handle tasks from the queue."""
        task_type = task.get("task_type", "")
        payload = task.get("payload", {})

        if task_type == "run_pipeline":
            company = payload.get("company", "")
            result = self._run_full_pipeline(company)
            return {"response": result}
        elif task_type == "run_stage":
            result = self._run_stage(
                payload.get("company", ""),
                payload.get("stage", ""),
                payload.get("context", ""),
            )
            return {"response": result}
        elif task_type == "intelligence_update":
            # Receive intelligence from SCOUT
            self.remember("latest_intel", payload)
            return {"response": "Intelligence received."}

        return {"response": f"Unknown task type: {task_type}"}

    # ------------------------------------------------------------------
    # Request classification
    # ------------------------------------------------------------------

    def _classify_request(self, message: str) -> dict:
        """Classify what Leo wants."""
        prompt = f"""Classify this client/strategy request:

"{message}"

Actions: onboard, pipeline_status, run_stage, proposal, audit, plan, list_clients, general

Respond with JSON:
{{"action": "action_name", "company": "company name if mentioned", "stage": "pipeline stage if mentioned"}}"""

        try:
            return self.think_json(prompt, system="Classify the request. JSON only.")
        except Exception:
            return {"action": "general", "company": ""}

    # ------------------------------------------------------------------
    # Client operations
    # ------------------------------------------------------------------

    def _onboard_client(self, company: str, original_message: str) -> str:
        """Start the client onboarding process."""
        if not company:
            return ("To onboard a new client, I need:\n"
                    "1. Company name\n"
                    "2. Website URL\n"
                    "3. Social media handles (Instagram, TikTok, etc.)\n"
                    "4. What they're looking for (goals)\n\n"
                    "What's the company?")

        # Request approval before starting
        self.request_approval(
            f"Start onboarding pipeline for: {company}",
            {"company": company, "request": original_message},
        )

        return (f"Onboarding request created for *{company}*.\n\n"
                f"I've sent you an approval request. Once approved, I'll kick off the full pipeline:\n"
                f"Research → Audit → Brand → Positioning → Plan → Content → Proposal\n\n"
                f"This typically takes 15-30 minutes to complete all stages.")

    def _pipeline_status(self, company: str) -> str:
        """Check pipeline status for a client."""
        if not company:
            return self._list_clients()

        try:
            from agents.shared.config import PORTFOLIO_DIR
            slug = company.lower().replace(" ", "_")
            state_file = PORTFOLIO_DIR / f"client_{slug}" / "pipeline_state.json"

            if not state_file.exists():
                return f"No pipeline found for '{company}'. Available clients:\n{self._list_clients()}"

            state = json.loads(state_file.read_text())
            stages = state.get("stages", {})

            lines = [f"*Pipeline Status: {company}*", ""]
            for stage_id, info in stages.items():
                status = info.get("status", "pending")
                emoji = {"completed": "Done", "running": "Running", "failed": "FAILED", "pending": "Pending"}.get(status, status)
                lines.append(f"  {stage_id}: {emoji}")
                if info.get("error"):
                    lines.append(f"    Error: {info['error'][:100]}")

            return "\n".join(lines)

        except Exception as e:
            return f"Error reading pipeline state: {str(e)[:200]}"

    def _run_stage(self, company: str, stage: str, context: str) -> str:
        """Run a specific pipeline stage."""
        if not company or not stage:
            return "I need both a company name and a stage to run. Example: 'Run the audit for CompanyX'"

        try:
            import importlib

            # Map stage names to agent modules
            STAGE_MAP = {
                "research": ("agents.shared.perplexity", "deep_research"),
                "audit": ("agents.marketing_audit.audit_agent", "run"),
                "brand": ("agents.brand_extractor.brand_agent", "run"),
                "positioning": ("agents.positioning.positioning_agent", "run"),
                "plan": ("agents.plan_builder.plan_agent", "run"),
                "vision": ("agents.vision_board.vision_agent", "run"),
                "trend": ("agents.trend_analyst.trend_agent", "run"),
                "content": ("agents.content_creator.content_agent", "run"),
                "calendar": ("agents.content_calendar.calendar_agent", "run"),
                "proposal": ("agents.proposal_generator.proposal_agent", "run"),
                "quality": ("agents.quality_checker.quality_agent", "run"),
            }

            if stage not in STAGE_MAP:
                available = ", ".join(STAGE_MAP.keys())
                return f"Unknown stage '{stage}'. Available: {available}"

            module_path, func_name = STAGE_MAP[stage]
            mod = importlib.import_module(module_path)
            func = getattr(mod, func_name)

            self.notify(f"Running {stage} for {company}...")
            result = func(company=company)

            self.remember("last_action", f"Ran {stage} for {company}")
            return f"*{stage.title()} completed for {company}.*\n\nResult saved to portfolio."

        except Exception as e:
            logger.error(f"Stage {stage} failed for {company}: {e}", exc_info=True)
            return f"Stage '{stage}' failed: {str(e)[:300]}"

    def _run_full_pipeline(self, company: str) -> str:
        """Run the full pipeline for a client."""
        if not company:
            return "I need a company name to run the pipeline."

        try:
            from agents.orchestrator.orchestrator_agent import run_pipeline
            self.notify(f"Starting full pipeline for {company}...")
            result = run_pipeline(company)
            self.remember("last_action", f"Full pipeline: {company}")
            self.notify(f"Pipeline complete for {company}!", level="info")
            return f"Pipeline completed for {company}."
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return f"Pipeline failed: {str(e)[:300]}"

    def _run_audit(self, company: str, message: str) -> str:
        """Run a marketing audit."""
        return self._run_stage(company, "audit", message)

    def _create_proposal(self, company: str, message: str) -> str:
        """Generate a proposal."""
        return self._run_stage(company, "proposal", message)

    def _create_plan(self, company: str, message: str) -> str:
        """Build a marketing plan."""
        return self._run_stage(company, "plan", message)

    def _list_clients(self) -> str:
        """List all client portfolios."""
        if not PORTFOLIO_DIR.exists():
            return "No client portfolios yet."

        clients = [d.name.replace("client_", "").replace("_", " ").title()
                    for d in PORTFOLIO_DIR.iterdir() if d.is_dir() and d.name.startswith("client_")]

        if not clients:
            return "No client portfolios yet. Use 'onboard [company]' to start."

        lines = ["*Client Portfolios:*"]
        for c in clients:
            lines.append(f"  - {c}")
        return "\n".join(lines)

    def _general_strategy(self, message: str) -> str:
        """Handle general strategy questions."""
        conversation_ctx = self.get_conversation_context(limit=3)
        prompt = f"""Leo asks: "{message}"

Respond as a senior marketing strategist. Be direct, actionable, and specific.
If this requires running a tool or pipeline stage, tell Leo what you'd recommend doing."""

        return self.think(prompt, system=self.get_system_prompt(extra_context=conversation_ctx))
