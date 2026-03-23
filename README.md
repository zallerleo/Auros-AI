# AUROS AI — AI Marketing Agency System

## Quick Start
```bash
source venv/bin/activate
python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --status
```

## Directory Structure

```
AUROS AI/
├── agents/              ← 21 autonomous marketing agents (38 Python files)
│   ├── shared/          ← Core infrastructure (config, LLM, Perplexity, browser)
│   ├── orchestrator/    ← Pipeline coordinator (Agent 0)
│   ├── marketing_audit/ ← Agent 1: Website + social analysis
│   ├── brand_extractor/ ← Agent 2: Visual identity extraction
│   ├── positioning/     ← Agent 3: 5 positioning angles + scoring
│   ├── audience_segmentation/ ← Agent 4: Audience segment generation
│   ├── plan_builder/    ← Agent 5: 90-day marketing plans
│   ├── vision_board/    ← Agent 6: Creative direction
│   ├── trend_analyst/   ← Agent 7: Platform trend research
│   ├── content_creator/ ← Agent 8: Exhibition video scripts + social posts
│   ├── content_calendar/← Agent 9: Monthly content scheduling
│   ├── proposal_generator/ ← Agent 10: Auto proposals with pricing
│   ├── quality_checker/ ← Agent 11: Brand compliance + EU AI Act
│   ├── geo_monitor/     ← Agent 12: AI search visibility tracking
│   ├── lead_magnet/     ← Lead magnet creation (guides, checklists)
│   ├── video_generator/ ← Remotion programmatic video ads
│   ├── video_repurposer/← Opus Clip short-form repurposing
│   ├── editor/          ← FFmpeg + CapCut video specs
│   ├── outreach/        ← Cold email/DM generation
│   ├── performance_tracker/ ← KPI monitoring
│   ├── client_reports/  ← Monthly branded reports
│   ├── newsletter/      ← Daily AI marketing newsletter
│   ├── market_analysis/ ← Sector scanning + competitor tracking
│   ├── knowledge_scanner/ ← Marketing framework discovery
│   └── automation/      ← Workflow configs (Make/Zapier/cron)
│
├── brand/               ← AUROS brand assets + tokens
├── dashboard/           ← Command center UI
├── docs/                ← Agency docs, pricing, content templates
├── knowledge_base/      ← Marketing frameworks (8 categories, 30+ frameworks)
├── logs/                ← Agent execution logs
├── portfolio/           ← Client deliverables
│   └── client_the_imagine_team/
│       ├── 01_research/     ← Audit, brand, positioning, segments
│       ├── 02_strategy/     ← Plans, vision boards, calendars, frameworks
│       ├── 03_content/      ← Video scripts, social posts, lead magnets
│       ├── 04_deliverables/ ← Proposals, summaries
│       └── 05_reports/      ← Pipeline status, performance reports
├── tools/               ← Utility scripts
└── .env                 ← API keys (never commit)
```

## Key Commands

```bash
# Full pipeline status
python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --status

# Run next pipeline stage
python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --next

# Run specific agent
python -m agents.positioning.positioning_agent --company "The Imagine Team"
python -m agents.audience_segmentation.segmentation_agent --company "The Imagine Team" --exhibition "Harry Potter"
python -m agents.geo_monitor.geo_agent --company "The Imagine Team" --city "Barcelona"
python -m agents.lead_magnet.lead_magnet_agent --company "The Imagine Team" --exhibition "Harry Potter"

# Daily operations (cron-scheduled)
python -m agents.newsletter.newsletter_agent
python -m agents.market_analysis.market_agent

# Export workflow automation configs
python -m agents.automation.workflow_config --export
```

## Tech Stack
- Python 3.9 + Claude API (claude-sonnet-4-20250514)
- Tavily (web research) + Perplexity (deep research)
- Playwright (JS page scraping) + BeautifulSoup (fallback)
- Remotion (programmatic video ads)
- Resend (email delivery)
- Jinja2 (HTML templating)

## Current Client
**The Imagine Team** — Exhibition marketing (Harry Potter, Titanic)
- Pipeline: 13/13 stages complete
- Focus: Cinematic content → ticket sales conversion
