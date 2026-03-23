"""
AUROS AI — Learning Module
Self-reflection and improvement loop for agents.
Each agent periodically reviews its performance and updates its operating guidelines.
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

from system.db import get_recent_tasks, recall_all, remember
from system.agents.base_agent import BaseAgent

logger = logging.getLogger("auros.learning")


def run_self_reflection(agent: BaseAgent) -> str:
    """Run a self-reflection session for an agent.
    Reviews recent tasks and outcomes, then updates operating guidelines."""

    # Gather recent task history for this agent
    recent = get_recent_tasks(limit=50)
    my_tasks = [t for t in recent if t.get("to_agent") == agent.name or t.get("from_agent") == agent.name]

    # Gather current memories
    memories = agent.recall_all()

    # Build reflection prompt
    task_summary = []
    for t in my_tasks[:20]:
        task_summary.append({
            "type": t.get("task_type"),
            "status": t.get("status"),
            "error": t.get("error", "")[:100] if t.get("error") else None,
        })

    prompt = f"""Self-Reflection Session for {agent.name}

## Your Current Memories
{json.dumps(memories, indent=2)[:3000]}

## Recent Task History (last 20)
{json.dumps(task_summary, indent=2)}

## Reflection Questions
1. What patterns do you see in your recent work?
2. What went well? What should you keep doing?
3. What failed or could be improved?
4. Are there any recurring issues that need a systemic fix?
5. What new capabilities or knowledge would make you more effective?

## Output Format
Respond with JSON:
{{
    "insights": ["list of key insights"],
    "keep_doing": ["things that are working well"],
    "improve": ["things to do differently"],
    "new_guidelines": ["updated operating guidelines for yourself"],
    "needs_from_leo": ["anything you need Leo's input on"]
}}"""

    try:
        result = agent.think_json(
            prompt,
            system=f"You are {agent.name} conducting a self-reflection. Be honest and specific.",
            max_tokens=2048,
        )

        # Store reflection results
        agent.remember("last_reflection", {
            "date": datetime.now().isoformat(),
            "insights": result.get("insights", []),
            "guidelines": result.get("new_guidelines", []),
        })

        # Store updated guidelines for future system prompts
        existing_guidelines = agent.recall("operating_guidelines") or []
        new_guidelines = result.get("new_guidelines", [])
        if new_guidelines:
            combined = list(set(existing_guidelines + new_guidelines))[:10]  # Keep top 10
            agent.remember("operating_guidelines", combined)

        summary = f"*{agent.name} Self-Reflection — {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        summary += "**Insights:**\n"
        for insight in result.get("insights", [])[:5]:
            summary += f"- {insight}\n"
        summary += "\n**Keep Doing:**\n"
        for item in result.get("keep_doing", [])[:3]:
            summary += f"- {item}\n"
        summary += "\n**Improve:**\n"
        for item in result.get("improve", [])[:3]:
            summary += f"- {item}\n"

        if result.get("needs_from_leo"):
            summary += "\n**Needs from Leo:**\n"
            for item in result["needs_from_leo"][:3]:
                summary += f"- {item}\n"

        logger.info(f"Self-reflection completed for {agent.name}")
        return summary

    except Exception as e:
        logger.error(f"Self-reflection failed for {agent.name}: {e}")
        return f"Self-reflection failed: {str(e)[:200]}"


def run_all_reflections(agents: dict[str, BaseAgent]) -> str:
    """Run self-reflection for all agents."""
    results = []
    for name, agent in agents.items():
        if name == "ATLAS":  # ATLAS doesn't need self-reflection
            continue
        result = run_self_reflection(agent)
        results.append(result)

    return "\n---\n".join(results)
