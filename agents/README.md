# AUROS AI — Agent Ecosystem

```
agents/
│
├── _core/                          ← INFRASTRUCTURE
│   ├── shared/                     ← Config, LLM, Perplexity, Browser, Knowledge
│   ├── orchestrator/               ← Pipeline coordinator (Agent 0)
│   └── automation/                 ← Workflow configs (Make/Zapier/cron)
│
├── _pipeline/                      ← CLIENT PIPELINE (13 stages)
│   ├── 01_research/                ← Discovery & Analysis
│   │   ├── marketing_audit/        ← Website + social analysis
│   │   ├── brand_extractor/        ← Visual identity extraction
│   │   ├── positioning/            ← 5 angles + scoring
│   │   └── audience_segmentation/  ← Segment generation
│   │
│   ├── 02_strategy/                ← Planning & Direction
│   │   ├── plan_builder/           ← 90-day marketing plans
│   │   ├── vision_board/           ← Creative direction
│   │   ├── content_calendar/       ← Monthly scheduling
│   │   └── trend_analyst/          ← Platform trend research
│   │
│   ├── 03_content/                 ← Production
│   │   ├── content_creator/        ← Exhibition video scripts + social posts
│   │   ├── lead_magnet/            ← Guides, checklists, behind-the-scenes
│   │   ├── video_generator/        ← Remotion programmatic video ads
│   │   ├── video_repurposer/       ← Opus Clip short-form clipping
│   │   └── editor/                 ← FFmpeg + CapCut video specs
│   │
│   └── 04_delivery/                ← Output & Quality
│       ├── proposal_generator/     ← Auto proposals with pricing
│       ├── quality_checker/        ← Brand compliance + EU AI Act
│       ├── outreach/               ← Cold email/DM generation
│       └── client_reports/         ← Monthly branded reports
│
├── _operations/                    ← ALWAYS-ON (cron-scheduled)
│   ├── newsletter/                 ← Daily AI marketing newsletter (7 AM)
│   ├── market_analysis/            ← Sector scanning (M/W/F 8 AM)
│   └── performance_tracker/        ← KPI monitoring
│
├── _intelligence/                  ← MONITORING & LEARNING
│   ├── geo_monitor/                ← AI search visibility tracking
│   └── knowledge_scanner/          ← Marketing framework discovery
│
└── [symlinks]                      ← Backward-compatible import paths
    shared → _core/shared
    orchestrator → _core/orchestrator
    marketing_audit → _pipeline/01_research/marketing_audit
    ... (all old paths still work)
```

## Running Agents

```bash
# Pipeline status
python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --status

# Run next stage
python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --next

# Run specific agent (import paths unchanged)
python -m agents.positioning.positioning_agent --company "The Imagine Team"
python -m agents.geo_monitor.geo_agent --company "The Imagine Team" --city "Barcelona"
```

Note: Symlinks preserve all original import paths (`agents.shared`, `agents.marketing_audit`, etc.)
so no code changes are needed when agents reference each other.
