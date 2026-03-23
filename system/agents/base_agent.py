"""
AUROS AI — Base Agent
Abstract base class for all department head agents.
Each agent gets: a persona, domain knowledge, tool access, memory, and notification ability.
"""

from __future__ import annotations

import sys
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.shared.config import ANTHROPIC_API_KEY, BRAND
from agents.shared.knowledge import get_frameworks_summary, get_benchmarks

import anthropic

from system.db import (
    create_task,
    get_task,
    update_task_status,
    remember,
    recall,
    recall_all,
    save_conversation,
    get_recent_conversations,
)

logger = logging.getLogger("auros.agents")


class BaseAgent(ABC):
    """Abstract base class for AUROS department head agents."""

    name: str = "UNNAMED"
    description: str = ""
    persona: str = ""
    knowledge_categories: list[str] = []

    def __init__(self, notifier=None):
        """
        Args:
            notifier: Callable(message, level) to send Telegram notifications.
                      level is 'urgent', 'info', or 'approval'.
        """
        self.notifier = notifier
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ------------------------------------------------------------------
    # Abstract methods — each agent must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle a direct message from Leo (routed via ATLAS).
        Returns the response text."""
        ...

    @abstractmethod
    def handle_task(self, task: dict) -> dict:
        """Handle a task from the task queue.
        Returns a result dict."""
        ...

    @abstractmethod
    def get_tools(self) -> dict[str, str]:
        """Return a dict of tool_name -> description for this agent's capabilities."""
        ...

    # ------------------------------------------------------------------
    # System prompt construction
    # ------------------------------------------------------------------

    def get_system_prompt(self, extra_context: str = "") -> str:
        """Build the full system prompt with persona + knowledge + memory."""
        parts = [
            f"You are {self.name}, {self.description}",
            "",
            "## Your Role",
            self.persona,
            "",
            f"## AUROS Brand Voice",
            f"Tagline: {BRAND.get('tagline', '')}",
            f"Voice traits: {', '.join(BRAND.get('voice', {}).get('traits', []))}",
        ]

        voice_rules = BRAND.get("voice", {}).get("rules", [])
        if voice_rules:
            parts.append("Rules:")
            for rule in voice_rules:
                parts.append(f"- {rule}")

        # Domain knowledge
        if self.knowledge_categories:
            kb = get_frameworks_summary(self.knowledge_categories)
            if kb.strip():
                parts.extend(["", "## Your Domain Knowledge", kb])

            benchmarks = get_benchmarks(
                [c for c in self.knowledge_categories if c in ("social_media", "paid_media", "analytics")]
            )
            if benchmarks.strip():
                parts.extend(["", "## Industry Benchmarks", benchmarks])

        # Agent memory (learned insights)
        memories = recall_all(self.name)
        if memories:
            parts.extend(["", "## Your Learned Insights (from past experience)"])
            for key, value in list(memories.items())[:15]:
                if isinstance(value, str):
                    parts.append(f"- **{key}**: {value}")
                else:
                    parts.append(f"- **{key}**: {json.dumps(value)[:200]}")

        # Extra context (e.g., current client data, recent tasks)
        if extra_context:
            parts.extend(["", "## Current Context", extra_context])

        # Operating guidelines
        parts.extend([
            "",
            "## Operating Guidelines",
            "- Be direct and concise. Every sentence earns its place.",
            "- If you need Leo's decision, say so clearly and explain what you need.",
            "- If a task will cost money (API calls, renders), flag it before proceeding.",
            "- When you're unsure, say so rather than guessing.",
            f"- Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ])

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # LLM calls
    # ------------------------------------------------------------------

    def think(
        self,
        prompt: str,
        system: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call Claude with the agent's system prompt."""
        message = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or self.get_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def think_json(
        self,
        prompt: str,
        system: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> dict:
        """Call Claude and parse JSON response."""
        raw = self.think(prompt, system=system, model=model, max_tokens=max_tokens, temperature=0.3)
        # Extract JSON from markdown code blocks if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw.strip())

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def remember(self, key: str, value: Any) -> None:
        """Store a memory for this agent."""
        remember(self.name, key, value)

    def recall(self, key: str) -> Any | None:
        """Recall a specific memory."""
        return recall(self.name, key)

    def recall_all(self) -> dict[str, Any]:
        """Recall all memories."""
        return recall_all(self.name)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def notify(self, message: str, level: str = "info") -> None:
        """Send a notification to Leo via Telegram.
        Levels: 'urgent' (immediate), 'info' (batched), 'approval' (with buttons).
        """
        if self.notifier:
            self.notifier(f"[{self.name}] {message}", level)
        else:
            logger.info(f"[{self.name}] NOTIFY ({level}): {message}")

    # ------------------------------------------------------------------
    # Task delegation
    # ------------------------------------------------------------------

    def delegate(
        self,
        to_agent: str,
        task_type: str,
        payload: dict | None = None,
        priority: int = 5,
    ) -> str:
        """Delegate a task to another agent via the task queue.
        Returns the task ID."""
        task_id = create_task(
            from_agent=self.name,
            to_agent=to_agent,
            task_type=task_type,
            payload=payload,
            priority=priority,
        )
        logger.info(f"[{self.name}] Delegated {task_type} to {to_agent} (task: {task_id})")
        return task_id

    def request_approval(self, description: str, payload: dict | None = None) -> str:
        """Request Leo's approval for an action.
        Creates a task with 'awaiting_approval' status and sends a Telegram notification.
        Returns the task ID."""
        task_id = create_task(
            from_agent=self.name,
            to_agent="LEO",
            task_type="approval_request",
            payload={"description": description, **(payload or {})},
            priority=1,
        )
        update_task_status(task_id, "awaiting_approval")
        self.notify(f"Need your approval: {description}\n/approve {task_id}", level="approval")
        return task_id

    # ------------------------------------------------------------------
    # Conversation context
    # ------------------------------------------------------------------

    def get_conversation_context(self, limit: int = 5) -> str:
        """Get recent conversation history for context."""
        convos = get_recent_conversations(agent=self.name, limit=limit)
        if not convos:
            return ""
        lines = ["## Recent Conversation History"]
        for c in reversed(convos):
            lines.append(f"Leo: {c['user_message']}")
            lines.append(f"{self.name}: {c['agent_response'][:300]}")
            lines.append("")
        return "\n".join(lines)

    def save_conversation(self, user_message: str, response: str, telegram_msg_id: int | None = None) -> None:
        """Save a conversation exchange."""
        save_conversation(
            agent=self.name,
            user_message=user_message,
            agent_response=response,
            telegram_message_id=telegram_msg_id,
        )
