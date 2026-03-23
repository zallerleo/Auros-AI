"""
AUROS AI — ATLAS: Chief of Staff
Routes messages to the right department head, compiles briefings,
manages approvals, and serves as Leo's primary interface.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from system.agents.base_agent import BaseAgent
from system.db import (
    get_awaiting_approval,
    get_recent_tasks,
    update_task_status,
    get_task,
    get_pending_tasks,
)

logger = logging.getLogger("auros.atlas")


# Agent registry — populated at runtime
_AGENTS: dict[str, BaseAgent] = {}


def register_agent(agent: BaseAgent) -> None:
    """Register a department head agent with ATLAS."""
    _AGENTS[agent.name] = agent


def get_agent(name: str) -> BaseAgent | None:
    """Get a registered agent by name."""
    return _AGENTS.get(name)


def get_all_agents() -> dict[str, BaseAgent]:
    """Get all registered agents."""
    return _AGENTS


class Atlas(BaseAgent):
    """Chief of Staff — routes, coordinates, and briefs."""

    name = "ATLAS"
    description = "Chief of Staff at AUROS AI. Routes requests, coordinates agents, compiles briefings."
    persona = """You are the Chief of Staff at AUROS AI. You are Leo's primary point of contact.

Your responsibilities:
1. ROUTE incoming messages to the correct department head agent
2. COMPILE daily briefings from all agents
3. MANAGE the approval queue — present decisions clearly
4. COORDINATE multi-agent workflows (e.g., client onboarding involves FORGE then APOLLO then HERMES)
5. STATUS UPDATES — when Leo asks "what's going on", give a concise summary

You don't do the work yourself. You know who does what:
- SCOUT: Research, competitive intel, market scanning, trends
- FORGE: Strategy, client onboarding, proposals, marketing plans, pipeline management
- APOLLO: Content creation, video scripts, social posts, creative direction
- HERMES: Cold outreach, email campaigns, newsletter, client communication
- SENTINEL: Performance tracking, KPIs, analytics, system health
- PROSPECTOR: Lead scraping, lead scoring, website generation for prospects, outreach pipeline management

Route accurately. Be concise. When in doubt, ask Leo to clarify."""

    knowledge_categories = []  # ATLAS doesn't need domain knowledge

    def get_tools(self) -> dict[str, str]:
        return {
            "route_message": "Route a message to the correct agent",
            "daily_briefing": "Compile a summary from all agents",
            "approval_queue": "Show pending approvals",
            "system_status": "Show system and agent status",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Route a message from Leo to the right agent, or handle it directly."""
        msg_lower = message.strip().lower()

        # Direct commands
        if msg_lower.startswith("/status"):
            return self._system_status()
        if msg_lower.startswith("/brief"):
            return self._daily_briefing()
        if msg_lower.startswith("/approve"):
            parts = message.strip().split()
            if len(parts) >= 2:
                return self._approve_task(parts[1])
            return self._show_approvals()
        if msg_lower.startswith("/reject"):
            parts = message.strip().split()
            if len(parts) >= 2:
                return self._reject_task(parts[1])
            return "Usage: /reject <task_id>"
        if msg_lower.startswith("/agents"):
            return self._agent_roster()

        # Route to the right agent using Claude
        routing = self._route(message)
        target = routing.get("agent", "ATLAS")
        task_type = routing.get("task_type", "general")
        summary = routing.get("summary", message)

        # If ATLAS should handle it directly
        if target == "ATLAS":
            return self._handle_direct(message, context)

        # Route to the target agent
        agent = get_agent(target)
        if not agent:
            return f"Agent {target} is not available. Available agents: {', '.join(_AGENTS.keys())}"

        try:
            response = agent.handle_message(message, context)
            agent.save_conversation(message, response)
            return f"*{target}*:\n\n{response}"
        except Exception as e:
            logger.error(f"Agent {target} failed: {e}", exc_info=True)
            return f"*{target}* encountered an error: {str(e)[:200]}\n\nI'll look into this."

    def handle_task(self, task: dict) -> dict:
        """Handle system-level tasks (approvals, notifications)."""
        task_type = task.get("task_type", "")
        if task_type == "daily_briefing":
            return {"response": self._daily_briefing()}
        if task_type == "system_health":
            return {"response": self._system_status()}
        return {"response": "ATLAS received task but doesn't know how to handle it."}

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route(self, message: str) -> dict:
        """Use Claude to classify and route a message."""
        available = {name: agent.description for name, agent in _AGENTS.items() if name != "ATLAS"}
        agents_desc = "\n".join(f"- {name}: {desc}" for name, desc in available.items())

        prompt = f"""Classify this message and determine which agent should handle it.

Available agents:
{agents_desc}

If the message is a simple greeting, question about the system, or doesn't clearly fit any agent, respond with ATLAS.

Message: "{message}"

Respond with JSON only:
{{"agent": "AGENT_NAME", "task_type": "brief_category", "summary": "one_line_summary"}}"""

        try:
            result = self.think_json(prompt, system="You are a message router. Respond with JSON only.")
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Routing failed, defaulting to ATLAS: {e}")
            return {"agent": "ATLAS", "task_type": "general", "summary": message[:100]}

    # ------------------------------------------------------------------
    # Direct handling (when ATLAS handles the message itself)
    # ------------------------------------------------------------------

    def _handle_direct(self, message: str, context: dict | None = None) -> str:
        """Handle messages that ATLAS answers directly (greetings, status questions, etc.)."""
        conversation_ctx = self.get_conversation_context(limit=3)
        extra = conversation_ctx
        if context:
            extra += f"\nAdditional context: {json.dumps(context)[:500]}"

        prompt = f"""Leo says: "{message}"

Respond naturally as his Chief of Staff. Be concise and helpful.
If he's asking about system status, agents, or tasks, provide what you know.
If he's asking something that should go to a specific agent, tell him you'll route it."""

        return self.think(prompt, system=self.get_system_prompt(extra_context=extra), max_tokens=1024)

    # ------------------------------------------------------------------
    # System commands
    # ------------------------------------------------------------------

    def _system_status(self) -> str:
        """System status overview."""
        pending = get_pending_tasks()
        approvals = get_awaiting_approval()
        recent = get_recent_tasks(limit=5)

        lines = ["*AUROS System Status*", ""]

        # Agent status
        lines.append("*Agents Online:*")
        for name in _AGENTS:
            lines.append(f"  {name}: Active")

        # Pending tasks
        lines.append(f"\n*Task Queue:* {len(pending)} pending")
        for t in pending[:5]:
            lines.append(f"  -> [{t['to_agent']}] {t['task_type']}")

        # Approvals
        if approvals:
            lines.append(f"\n*Awaiting Your Approval:* {len(approvals)}")
            for a in approvals:
                payload = a.get("payload", {})
                desc = payload.get("description", a["task_type"]) if isinstance(payload, dict) else a["task_type"]
                lines.append(f"  [{a['id']}] {desc}")

        # Recent activity
        lines.append("\n*Recent Activity:*")
        for t in recent[:5]:
            status_emoji = {"completed": "Done", "failed": "Failed", "running": "Running", "pending": "Pending"}.get(
                t["status"], t["status"]
            )
            lines.append(f"  {t['from_agent']} -> {t['to_agent']}: {t['task_type']} ({status_emoji})")

        return "\n".join(lines)

    def _daily_briefing(self) -> str:
        """Compile daily briefing from all agents."""
        lines = [f"*AUROS Daily Briefing — {datetime.now().strftime('%B %d, %Y')}*", ""]

        for name, agent in _AGENTS.items():
            if name == "ATLAS":
                continue
            # Check for recent completed tasks by this agent
            memories = agent.recall_all()
            last_action = memories.get("last_action", "No recent activity")
            lines.append(f"*{name}* ({agent.description.split('.')[0]})")
            lines.append(f"  Last: {last_action if isinstance(last_action, str) else json.dumps(last_action)[:150]}")
            lines.append("")

        approvals = get_awaiting_approval()
        if approvals:
            lines.append(f"*{len(approvals)} item(s) awaiting your approval* — use /approve to review")

        return "\n".join(lines)

    def _show_approvals(self) -> str:
        """Show all pending approvals."""
        approvals = get_awaiting_approval()
        if not approvals:
            return "No pending approvals. All clear."

        lines = [f"*{len(approvals)} Pending Approval(s):*", ""]
        for a in approvals:
            payload = a.get("payload", {})
            desc = payload.get("description", a["task_type"]) if isinstance(payload, dict) else a["task_type"]
            lines.append(f"*[{a['id']}]* from {a['from_agent']}")
            lines.append(f"  {desc}")
            lines.append(f"  /approve {a['id']}  |  /reject {a['id']}")
            lines.append("")

        return "\n".join(lines)

    def _approve_task(self, task_id: str) -> str:
        """Approve a pending task."""
        task = get_task(task_id)
        if not task:
            return f"Task {task_id} not found."
        if task["status"] != "awaiting_approval":
            return f"Task {task_id} is not awaiting approval (status: {task['status']})."

        update_task_status(task_id, "approved")
        # Re-queue it as pending for the originating agent to pick up
        update_task_status(task_id, "pending")

        payload = task.get("payload", {})
        desc = payload.get("description", task["task_type"]) if isinstance(payload, dict) else task["task_type"]
        return f"Approved: {desc}\nTask {task_id} has been re-queued for {task['from_agent']} to execute."

    def _reject_task(self, task_id: str) -> str:
        """Reject a pending task."""
        task = get_task(task_id)
        if not task:
            return f"Task {task_id} not found."

        update_task_status(task_id, "rejected")
        payload = task.get("payload", {})
        desc = payload.get("description", task["task_type"]) if isinstance(payload, dict) else task["task_type"]
        return f"Rejected: {desc}\n{task['from_agent']} has been notified."

    def _agent_roster(self) -> str:
        """Show all agents and what they do."""
        lines = ["*AUROS Agent Team:*", ""]
        for name, agent in _AGENTS.items():
            tools = agent.get_tools()
            lines.append(f"*{name}*: {agent.description}")
            if tools:
                lines.append(f"  Tools: {', '.join(tools.keys())}")
            lines.append("")
        return "\n".join(lines)
