"""
AUROS AI — LLM Wrapper
Unified interface for Claude API calls across all agents.
"""

from __future__ import annotations

import anthropic
from agents.shared.config import ANTHROPIC_API_KEY, BRAND


def get_client() -> anthropic.Anthropic:
    """Return an Anthropic client instance."""
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


AUROS_SYSTEM_PROMPT = f"""You are an AI assistant working for AUROS, a premium AI marketing agency.

Brand voice rules:
{chr(10).join(f'- {rule}' for rule in BRAND['voice']['rules'])}

Voice traits: {', '.join(BRAND['voice']['traits'])}

Tagline: {BRAND['tagline']}

Always maintain the AUROS brand voice: direct, knowledgeable, energetic but composed.
Lead with data and results. No filler. Every sentence earns its place."""


def generate(
    prompt: str,
    system: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Generate text using Claude API with AUROS brand voice."""
    client = get_client()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or AUROS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
