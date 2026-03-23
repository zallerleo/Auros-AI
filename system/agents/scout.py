"""
AUROS AI — SCOUT: Research & Intelligence Director
Deep market research, competitive intelligence, trend analysis, sector scanning.
The eyes and ears of the agency.
"""

from __future__ import annotations

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system.agents.base_agent import BaseAgent

logger = logging.getLogger("auros.scout")


class Scout(BaseAgent):
    """Research & Intelligence Director."""

    name = "SCOUT"
    description = "Research & Intelligence Director. Deep market research, competitive analysis, trends, and sector scanning."
    persona = """You are SCOUT, the Research & Intelligence Director at AUROS AI.

You are an obsessive intelligence analyst who sees patterns others miss. You have deep expertise in:
- Market research methodology (primary and secondary)
- Competitive intelligence frameworks (Porter's Five Forces, SWOT, perceptual mapping)
- Trend analysis and forecasting (macro trends, micro trends, platform-specific)
- Sector scoring and opportunity identification
- AI search visibility (GEO — Generative Engine Optimization)
- Social listening and sentiment analysis

Your research is thorough but actionable. You don't just collect data — you synthesize it into insights that drive decisions. Every research output should answer: "So what? What should we do with this?"

You have access to:
- Perplexity AI (deep web research with citations)
- Tavily (fast web search)
- Playwright browser (scraping and screenshots)
- Market analysis archives
- Competitor tracking database
- GEO monitoring reports

When asked to research something:
1. Define the research question clearly
2. Choose the right tool (Perplexity for deep research, Tavily for quick lookups, browser for live scraping)
3. Synthesize findings into actionable intelligence
4. Flag opportunities and threats
5. Recommend next steps

Always cite your sources. Be direct about confidence levels — if data is thin, say so."""

    knowledge_categories = ["analytics", "content_strategy"]

    def get_tools(self) -> dict[str, str]:
        return {
            "deep_research": "Multi-query deep research via Perplexity AI",
            "quick_search": "Fast web search for specific answers",
            "competitive_analysis": "Full competitive teardown of a company",
            "market_scan": "Sector scanning and scoring",
            "trend_analysis": "Platform and industry trend research",
            "geo_check": "AI search visibility monitoring",
            "scrape_website": "Live website scraping and analysis",
        }

    def handle_message(self, message: str, context: dict | None = None) -> str:
        """Handle a research request from Leo."""
        # Classify the request
        classification = self._classify_request(message)
        tool = classification.get("tool", "deep_research")
        query = classification.get("query", message)

        # Execute the right tool
        if tool == "deep_research":
            return self._deep_research(query, message)
        elif tool == "competitive_analysis":
            company = classification.get("company", query)
            return self._competitive_analysis(company, message)
        elif tool == "quick_search":
            return self._quick_search(query, message)
        elif tool == "market_scan":
            return self._market_scan(query, message)
        elif tool == "scrape_website":
            url = classification.get("url", "")
            return self._scrape_and_analyze(url, message)
        else:
            return self._deep_research(query, message)

    def handle_task(self, task: dict) -> dict:
        """Handle a task from the queue."""
        task_type = task.get("task_type", "")
        payload = task.get("payload", {})

        if task_type == "deep_research":
            result = self._deep_research(
                payload.get("query", ""), payload.get("context", "")
            )
            return {"response": result}
        elif task_type == "competitive_analysis":
            result = self._competitive_analysis(
                payload.get("company", ""), payload.get("context", "")
            )
            return {"response": result}
        elif task_type == "daily_scan":
            result = self._daily_intelligence_scan()
            return {"response": result}
        elif task_type == "intelligence_update":
            # Store incoming intelligence from other agents
            self.remember("latest_intel", payload)
            return {"response": "Intelligence received and stored."}

        return {"response": f"Unknown task type: {task_type}"}

    # ------------------------------------------------------------------
    # Request classification
    # ------------------------------------------------------------------

    def _classify_request(self, message: str) -> dict:
        """Classify what kind of research Leo wants."""
        prompt = f"""Classify this research request and extract key parameters.

Request: "{message}"

Available tools:
- deep_research: Multi-query research on a topic
- competitive_analysis: Analyze a specific company/competitor
- quick_search: Fast lookup for a specific fact or answer
- market_scan: Broad sector/industry scanning
- scrape_website: Analyze a specific URL

Respond with JSON:
{{"tool": "tool_name", "query": "the core research question", "company": "company name if relevant", "url": "URL if mentioned"}}"""

        try:
            return self.think_json(prompt, system="You are a research request classifier. Respond with JSON only.")
        except Exception:
            return {"tool": "deep_research", "query": message}

    # ------------------------------------------------------------------
    # Research tools
    # ------------------------------------------------------------------

    def _deep_research(self, query: str, original_message: str) -> str:
        """Run deep multi-query research via Perplexity."""
        try:
            from agents.shared.perplexity import deep_research
            result = deep_research(queries=[query], context=original_message)

            # Synthesize with Claude
            synthesis_prompt = f"""Research results for: "{query}"

Raw findings:
{json.dumps(result, indent=2)[:6000]}

Synthesize these findings into:
1. Key insights (3-5 bullets)
2. Opportunities or threats identified
3. Recommended next steps
4. Confidence level (high/medium/low) and any gaps

Be direct and actionable."""

            response = self.think(synthesis_prompt)
            self.remember("last_action", f"Deep research: {query[:100]}")
            return response

        except Exception as e:
            logger.error(f"Deep research failed: {e}", exc_info=True)
            return f"Research failed: {str(e)[:200]}. I'll try a different approach."

    def _competitive_analysis(self, company: str, original_message: str) -> str:
        """Run competitive analysis on a company."""
        try:
            from agents.shared.perplexity import competitive_analysis
            result = competitive_analysis(company)

            prompt = f"""Competitive analysis results for: {company}

Data:
{json.dumps(result, indent=2)[:6000]}

Provide:
1. Company overview (what they do, positioning)
2. Strengths and weaknesses
3. Their marketing approach
4. Opportunities for AUROS clients vs this competitor
5. Key takeaways

Be specific — generic analysis is useless."""

            response = self.think(prompt)
            self.remember("last_action", f"Competitive analysis: {company}")
            return response

        except Exception as e:
            logger.error(f"Competitive analysis failed: {e}", exc_info=True)
            return f"Competitive analysis failed: {str(e)[:200]}"

    def _quick_search(self, query: str, original_message: str) -> str:
        """Quick search for a specific answer."""
        try:
            from agents.shared.perplexity import research
            result = research(query, context=original_message)

            prompt = f"""Quick search results for: "{query}"

{json.dumps(result, indent=2)[:4000]}

Give a concise, direct answer. No fluff."""

            response = self.think(prompt, max_tokens=1024)
            self.remember("last_action", f"Quick search: {query[:100]}")
            return response

        except Exception as e:
            return f"Search failed: {str(e)[:200]}"

    def _market_scan(self, query: str, original_message: str) -> str:
        """Broad market/sector scanning."""
        try:
            from agents.shared.perplexity import deep_research
            queries = [
                f"{query} market size trends 2024 2025",
                f"{query} key players competitors landscape",
                f"{query} emerging opportunities threats",
            ]
            result = deep_research(queries=queries, context=f"Market scan for: {query}")

            prompt = f"""Market scan results for: "{query}"

{json.dumps(result, indent=2)[:6000]}

Provide a market intelligence brief:
1. Market overview and size
2. Key players and their positioning
3. Trends (growing, declining, emerging)
4. Opportunities for an AI marketing agency
5. Risks or concerns

Score the sector attractiveness on a 1-10 scale with justification."""

            response = self.think(prompt)
            self.remember("last_action", f"Market scan: {query[:100]}")
            return response

        except Exception as e:
            return f"Market scan failed: {str(e)[:200]}"

    def _scrape_and_analyze(self, url: str, original_message: str) -> str:
        """Scrape and analyze a specific website."""
        if not url:
            return "I need a URL to analyze. Please provide one."

        try:
            from agents.shared.browser import scrape_sync
            data = scrape_sync(url)

            if data.get("error"):
                return f"Couldn't scrape {url}: {data['error']}"

            prompt = f"""Website analysis for: {url}

Title: {data.get('title', 'N/A')}
Meta tags: {json.dumps(data.get('meta_tags', {}))[:500]}
Headings: {json.dumps(data.get('headings', []))[:500]}
Social links: {data.get('social_links', [])}
Colors: {data.get('colors', [])}
Fonts: {data.get('fonts', [])}

Content excerpt:
{data.get('text', '')[:3000]}

Original request: "{original_message}"

Provide a concise analysis focused on what Leo asked about."""

            response = self.think(prompt)
            self.remember("last_action", f"Website analysis: {url}")
            return response

        except Exception as e:
            return f"Scraping failed: {str(e)[:200]}"

    def _daily_intelligence_scan(self) -> str:
        """Daily automated intelligence gathering."""
        try:
            from agents.shared.perplexity import research

            topics = [
                "AI marketing agency industry news today",
                "new AI tools for marketing and content creation this week",
                "Barcelona business and startup ecosystem news",
            ]

            results = []
            for topic in topics:
                try:
                    r = research(topic)
                    results.append({"topic": topic, "result": r})
                except Exception as e:
                    results.append({"topic": topic, "error": str(e)})

            prompt = f"""Daily intelligence scan results:

{json.dumps(results, indent=2)[:6000]}

Compile a brief daily intelligence report:
1. Top 3 most relevant news items for AUROS AI
2. Any emerging trends or opportunities
3. Anything that needs Leo's attention

Keep it concise — this goes in the daily briefing."""

            response = self.think(prompt, max_tokens=1024)
            self.remember("last_action", f"Daily scan: {datetime.now().strftime('%Y-%m-%d')}")
            self.remember("daily_scan", {"date": datetime.now().isoformat(), "summary": response[:500]})
            return response

        except Exception as e:
            return f"Daily scan failed: {str(e)[:200]}"
