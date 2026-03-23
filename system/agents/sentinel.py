"""
AUROS AI — SENTINEL: Operations & Performance Director
KPI tracking, analytics, anomaly detection, system health, cost monitoring.
The data-obsessed operator who catches problems before they become crises.
"""

from __future__ import annotations

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system.agents.base_agent import BaseAgent
from system.db import get_recent_tasks

logger = logging.getLogger("auros.sentinel")


class Sentinel(BaseAgent):
    """Operations & Performance Director."""

    name = "SENTINEL"
    description = "Operations & Performance Director. KPI tracking, analytics, anomaly detection, system health, and cost monitoring."
    persona = """You are SENTINEL, the Operations & Performance Director at AUROS AI.

You are data-obsessed and catch problems before they become crises. You have deep expertise in:
- Marketing KPIs and performance metrics
- Analytics interpretation (not just numbers — the story behind them)
- Anomaly detection (what changed and why)
- System health monitoring (API uptime, cost tracking, process health)
- Industry benchmarking (are we above or below average?)
- ROI calculation and attribution
- A/B test analysis and statistical significance

Your monitoring domains:
1. **Client Performance** — Campaign metrics, content engagement, funnel conversion
2. **System Health** — API costs, process uptime, error rates, disk space
3. **Business Metrics** — Revenue, pipeline value, client retention, proposal conversion
4. **Agent Performance** — Task completion rates, response times, error rates

You don't just report numbers. You explain:
- What happened (the metric)
- Why it matters (the impact)
- What to do about it (the recommendation)

When you spot an anomaly, you investigate before alerting. False alarms erode trust.

You have access to:
- Performance tracking agents
- System logs and error logs
- API usage data
- Client portfolio data
- Historical performance archives"""

    knowledge_categories = ["analytics", "paid_media"]

    def get_tools(self) -> dict[str, str]:
        return {
            "performance_report": "Generate a performance report",
            "system_health": "Check system health and API status",
            "cost_tracking": "Track API costs and usage",
            "task_analytics": "Analyze task completion and agent performance",
            "anomaly_check": "Check for anomalies in metrics",
            "daily_check": "Run the daily performance check",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle performance/operations requests."""
        classification = self._classify_request(message)
        action = classification.get("action", "general")

        if action == "performance":
            return self._performance_report(message, classification)
        elif action == "system_health":
            return self._system_health()
        elif action == "costs":
            return self._cost_tracking()
        elif action == "task_analytics":
            return self._task_analytics()
        elif action == "anomaly":
            return self._anomaly_check(message)
        else:
            return self._general_ops(message)

    def handle_task(self, task: dict) -> dict:
        """Handle tasks from the queue."""
        task_type = task.get("task_type", "")
        payload = task.get("payload", {})

        if task_type == "daily_check":
            result = self._daily_performance_check()
            return {"response": result}
        elif task_type == "system_health":
            result = self._system_health()
            return {"response": result}
        elif task_type == "cost_alert":
            result = self._cost_tracking()
            return {"response": result}

        return {"response": f"Unknown task type: {task_type}"}

    def _classify_request(self, message: str) -> dict:
        prompt = f"""Classify this operations request:

"{message}"

Actions: performance, system_health, costs, task_analytics, anomaly, general

JSON: {{"action": "name", "timeframe": "today/week/month if mentioned", "client": "if mentioned"}}"""

        try:
            return self.think_json(prompt, system="Classify. JSON only.")
        except Exception:
            return {"action": "general"}

    def _performance_report(self, message: str, classification: dict) -> str:
        """Generate performance report."""
        # Check for existing performance data
        try:
            import importlib
            mod = importlib.import_module("agents.performance_tracker.performance_agent")
            data = mod.get_latest_metrics() if hasattr(mod, "get_latest_metrics") else {}
        except Exception:
            data = {}

        # Analyze recent task history
        recent = get_recent_tasks(limit=50)
        task_summary = self._summarize_tasks(recent)

        prompt = f"""Generate a performance report.

Request: "{message}"

Task Activity (last 50 tasks):
{task_summary}

Performance Data:
{json.dumps(data, indent=2)[:3000] if data else "No performance data available yet."}

Provide:
1. Key metrics summary (tasks completed, success rate, agent utilization)
2. Highlights and wins
3. Issues or concerns
4. Recommendations

If data is limited, say so and explain what tracking needs to be set up."""

        response = self.think(prompt)
        self.remember("last_action", f"Performance report: {datetime.now().strftime('%Y-%m-%d')}")
        return response

    def _system_health(self) -> str:
        """Check system health."""
        health = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        # Check API keys
        from agents.shared.config import (
            ANTHROPIC_API_KEY, TAVILY_API_KEY, PERPLEXITY_API_KEY,
            RESEND_API_KEY, PORTFOLIO_DIR, LOGS_DIR,
        )

        health["checks"]["api_keys"] = {
            "anthropic": "Set" if ANTHROPIC_API_KEY else "MISSING",
            "perplexity": "Set" if PERPLEXITY_API_KEY else "MISSING",
            "tavily": "Set" if TAVILY_API_KEY else "MISSING",
            "resend": "Set" if RESEND_API_KEY else "MISSING",
            "telegram": "Set" if os.getenv("TELEGRAM_BOT_TOKEN") else "MISSING",
        }

        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            health["checks"]["disk"] = {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "usage_pct": round(used / total * 100, 1),
            }
        except Exception:
            health["checks"]["disk"] = "Check failed"

        # Check portfolio directory
        if PORTFOLIO_DIR.exists():
            clients = [d.name for d in PORTFOLIO_DIR.iterdir() if d.is_dir()]
            health["checks"]["portfolio"] = {"clients": len(clients), "names": clients}
        else:
            health["checks"]["portfolio"] = "Directory not found"

        # Check logs directory
        if LOGS_DIR.exists():
            log_files = list(LOGS_DIR.rglob("*.log"))
            total_log_size = sum(f.stat().st_size for f in log_files)
            health["checks"]["logs"] = {
                "files": len(log_files),
                "total_size_mb": round(total_log_size / (1024**2), 1),
            }

        # Check recent tasks
        recent = get_recent_tasks(limit=20)
        failed = [t for t in recent if t["status"] == "failed"]
        health["checks"]["tasks"] = {
            "recent_total": len(recent),
            "recent_failed": len(failed),
            "failure_rate": f"{len(failed)/max(len(recent),1)*100:.0f}%",
        }

        # Format report
        lines = [f"*System Health — {datetime.now().strftime('%Y-%m-%d %H:%M')}*", ""]

        # API Keys
        lines.append("*API Keys:*")
        for key, status in health["checks"]["api_keys"].items():
            indicator = "OK" if status == "Set" else "MISSING"
            lines.append(f"  {key}: {indicator}")

        # Disk
        disk = health["checks"].get("disk", {})
        if isinstance(disk, dict):
            lines.append(f"\n*Disk:* {disk.get('free_gb', '?')}GB free ({disk.get('usage_pct', '?')}% used)")

        # Portfolio
        portfolio = health["checks"].get("portfolio", {})
        if isinstance(portfolio, dict):
            lines.append(f"\n*Clients:* {portfolio.get('clients', 0)} portfolios")

        # Tasks
        tasks = health["checks"].get("tasks", {})
        if isinstance(tasks, dict):
            lines.append(f"\n*Recent Tasks:* {tasks.get('recent_total', 0)} total, {tasks.get('recent_failed', 0)} failed ({tasks.get('failure_rate', '0%')})")

        self.remember("last_action", f"System health: {datetime.now().strftime('%Y-%m-%d')}")
        return "\n".join(lines)

    def _cost_tracking(self) -> str:
        """Track API costs."""
        # This would integrate with Claude API usage tracking
        prompt = """Provide an API cost tracking report.

Currently tracked APIs:
- Anthropic Claude (main LLM — charged per token)
- Perplexity (research — charged per query)
- Resend (email — charged per send)
- FAL.ai (video generation — charged per render)

Note: Direct API usage tracking is not yet implemented. Recommend:
1. Wrapping all API calls with a cost counter
2. Logging token usage per agent per day
3. Setting daily/weekly spend alerts

Provide recommendations for setting up cost tracking."""

        return self.think(prompt, max_tokens=1024)

    def _task_analytics(self) -> str:
        """Analyze task completion and agent performance."""
        recent = get_recent_tasks(limit=100)
        summary = self._summarize_tasks(recent)

        prompt = f"""Analyze this task activity:

{summary}

Provide:
1. Tasks by agent (who's doing the most work?)
2. Success vs failure rates
3. Average task types
4. Any bottlenecks or patterns
5. Recommendations for optimization"""

        response = self.think(prompt, max_tokens=1024)
        self.remember("last_action", "Task analytics")
        return response

    def _anomaly_check(self, message: str) -> str:
        """Check for anomalies."""
        return self.think(
            f'Check for anomalies based on: "{message}"\n\nReport any unusual patterns in recent activity.',
            system=self.get_system_prompt(),
            max_tokens=1024,
        )

    def _daily_performance_check(self) -> str:
        """Daily automated performance check."""
        health = self._system_health()
        tasks = self._summarize_tasks(get_recent_tasks(limit=50))

        summary = f"Daily check completed.\n\n{health}\n\nTask Summary:\n{tasks}"
        self.remember("last_action", f"Daily check: {datetime.now().strftime('%Y-%m-%d')}")
        return summary

    def _general_ops(self, message: str) -> str:
        """Handle general operations questions."""
        conversation_ctx = self.get_conversation_context(limit=3)
        return self.think(
            f'Leo asks: "{message}"\n\nRespond as an operations expert.',
            system=self.get_system_prompt(extra_context=conversation_ctx),
        )

    def _summarize_tasks(self, tasks: list[dict]) -> str:
        """Summarize a list of tasks into a readable format."""
        if not tasks:
            return "No tasks recorded yet."

        by_status = {}
        by_agent = {}
        for t in tasks:
            status = t.get("status", "unknown")
            agent = t.get("to_agent", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            by_agent[agent] = by_agent.get(agent, 0) + 1

        lines = [
            f"Total: {len(tasks)} tasks",
            f"By status: {json.dumps(by_status)}",
            f"By agent: {json.dumps(by_agent)}",
        ]
        return "\n".join(lines)
