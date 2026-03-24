# AUROS AI — AI Automation Agency for Local Businesses

AI automation systems for small/local businesses ($2-10M revenue). We install workflow automation, productivity tracking, and continuous improvement systems on a monthly retainer.

**Status: Pivoting from marketing agency to automation agency.** Core infrastructure retained, marketing agents removed.

## What We Do

- **Workflow Analysis** — Map existing business processes, identify bottlenecks and manual steps
- **Productivity Tracking** — Monitor team output, flag inefficiencies, surface patterns
- **Automation Building** — Build and deploy automations that eliminate repetitive work
- **Continuous Improvement** — Monthly retainer for maintenance, monitoring, and new automations

## Directory Structure

```
AUROS AI/
├── agents/
│   └── _core/
│       ├── shared/         ← Core infra (config, LLM client, Perplexity, browser)
│       └── orchestrator/   ← Pipeline coordinator
│
├── system/
│   ├── agents/             ← System-level agents
│   │   ├── base_agent.py   ← Agent base class
│   │   ├── atlas.py        ← Research/mapping agent
│   │   ├── prospector.py   ← Lead prospecting
│   │   ├── sentinel.py     ← Monitoring agent
│   │   └── learning.py     ← Self-improvement loop
│   ├── api.py              ← API layer
│   ├── db.py               ← SQLite database
│   ├── scheduler.py        ← Task scheduling
│   ├── task_worker.py      ← Background task execution
│   ├── telegram_bot.py     ← Telegram notifications
│   └── dashboard/          ← Web UI
│
├── tools/
│   ├── lead_scraper.py     ← Google Maps / directory scraping
│   ├── lead_enricher.py    ← Business data enrichment
│   ├── batch_lead_runner.py← Bulk lead processing
│   ├── generate_proposal.py← Auto proposal generation
│   ├── website_generator.py← Client-facing site builder
│   ├── deploy_website.py   ← Site deployment
│   └── templates/          ← Proposal/report templates
│
├── workflows/              ← Markdown SOPs (WAT framework)
├── brand/                  ← AUROS brand assets
├── docs/                   ← Agency docs, pricing
├── portfolio/              ← Client deliverables
├── logs/                   ← Execution logs
├── .tmp/                   ← Temporary processing files
└── .env                    ← API keys (never commit)
```

## Agents To Build

| Agent | Purpose | Priority |
|-------|---------|----------|
| **Workflow Analyzer** | Map client processes, detect manual/repetitive steps, score automation potential | High |
| **Productivity Tracker** | Track employee task completion, time allocation, output metrics | High |
| **Automation Builder** | Generate and deploy Make.com/n8n workflows from analyzed processes | High |
| **Integration Engine** | Connect client tools (CRMs, spreadsheets, email, POS systems) | Medium |

## Tech Stack

- **Core:** Python 3.9 + Claude API (claude-sonnet-4-20250514)
- **Automation platforms:** Make.com / n8n integration
- **Research:** Tavily (web) + Perplexity (deep research)
- **Browser automation:** Playwright + BeautifulSoup fallback
- **Database:** SQLite (auros.db)
- **Notifications:** Telegram bot
- **Templating:** Jinja2

## Architecture

Follows the **WAT framework** (Workflows, Agents, Tools):
- **Workflows** — Markdown SOPs in `workflows/` defining what to do
- **Agents** — AI decision-makers that read workflows and call tools
- **Tools** — Deterministic Python scripts that execute the work

## Quick Start

```bash
source venv/bin/activate
python -m system.api        # Start API
python -m system.scheduler  # Start task scheduler
```
