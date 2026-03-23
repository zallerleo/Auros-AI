"""
AUROS AI — Workflow Automation Configuration
Generates Make/Zapier webhook configurations and automation blueprints
for connecting AUROS agents to external tools and scheduling.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from agents.shared.config import PROJECT_ROOT, PORTFOLIO_DIR


# ---------------------------------------------------------------------------
# Workflow definitions
# ---------------------------------------------------------------------------

WORKFLOWS = {
    "monthly_report_cycle": {
        "name": "Monthly Client Report Automation",
        "description": "Auto-generates and delivers monthly client reports on the 1st of each month.",
        "trigger": "Schedule: 1st of month, 9:00 AM",
        "steps": [
            {"order": 1, "action": "Run Performance Tracker", "agent": "agents.performance_tracker.performance_agent", "input": "Previous month data"},
            {"order": 2, "action": "Run Client Report Generator", "agent": "agents.client_reports.report_agent", "input": "Performance data from step 1"},
            {"order": 3, "action": "Run Quality Checker", "agent": "agents.quality_checker.quality_agent", "input": "Report content from step 2"},
            {"order": 4, "action": "Run Compliance Check", "agent": "agents.quality_checker.compliance", "input": "Report content from step 2"},
            {"order": 5, "action": "Send Report via Email", "agent": "agents.shared.sender (Resend)", "input": "Approved report from step 3-4"},
        ],
        "error_handling": "If any step fails, pause workflow and alert via email",
        "make_webhook": "POST /webhook/monthly-report",
    },
    "content_publishing_cycle": {
        "name": "Content Publishing Automation",
        "description": "Auto-generates and queues content based on the content calendar.",
        "trigger": "Daily at 7:00 AM — check content calendar for today's posts",
        "steps": [
            {"order": 1, "action": "Check Content Calendar", "agent": "agents.content_calendar.calendar_agent", "input": "Today's date"},
            {"order": 2, "action": "Generate Content", "agent": "agents.content_creator.exhibition_content", "input": "Calendar entry for today"},
            {"order": 3, "action": "Quality Check", "agent": "agents.quality_checker.quality_agent", "input": "Generated content"},
            {"order": 4, "action": "Queue for Approval", "method": "Email draft to client or Buffer/Later queue"},
        ],
        "error_handling": "Skip today's post if generation fails, alert team",
        "make_webhook": "POST /webhook/daily-content",
    },
    "performance_alert": {
        "name": "Performance Alert System",
        "description": "Monitors campaign performance daily and alerts on significant changes.",
        "trigger": "Daily at 6:00 PM — check today's performance metrics",
        "steps": [
            {"order": 1, "action": "Pull Performance Data", "agent": "agents.performance_tracker.performance_agent", "input": "Today's metrics"},
            {"order": 2, "action": "Compare Against Thresholds", "thresholds": {
                "ctr_drop_alert": "CTR drops >20% from 7-day average",
                "spend_alert": "Daily spend exceeds budget by >10%",
                "conversion_alert": "Zero conversions for 24 hours",
                "engagement_spike": "Engagement >3x average (opportunity alert)",
            }},
            {"order": 3, "action": "Generate Alert", "agent": "agents.shared.llm (Claude)", "input": "Anomaly data + recommendations"},
            {"order": 4, "action": "Send Alert", "method": "Email or Slack webhook"},
        ],
        "error_handling": "If data pull fails, retry in 1 hour",
        "make_webhook": "POST /webhook/performance-alert",
    },
    "new_client_onboarding": {
        "name": "New Client Onboarding Pipeline",
        "description": "Automatically runs the full AUROS pipeline when a new client is added.",
        "trigger": "Manual trigger or webhook when new client data is received",
        "steps": [
            {"order": 1, "action": "Deep Research", "agent": "agents.shared.perplexity", "input": "Client website + industry"},
            {"order": 2, "action": "Marketing Audit", "agent": "agents.marketing_audit.audit_agent", "input": "Client website"},
            {"order": 3, "action": "Brand Extraction", "agent": "agents.brand_extractor.brand_agent", "input": "Client website"},
            {"order": 4, "action": "Positioning Analysis", "agent": "agents.positioning.positioning_agent", "input": "Audit + Brand data"},
            {"order": 5, "action": "Audience Segmentation", "agent": "agents.audience_segmentation.segmentation_agent", "input": "Audit + Brand + Research"},
            {"order": 6, "action": "Marketing Plan", "agent": "agents.plan_builder.plan_agent", "input": "All previous outputs"},
            {"order": 7, "action": "Content Calendar", "agent": "agents.content_calendar.calendar_agent", "input": "Marketing plan"},
            {"order": 8, "action": "Proposal Generation", "agent": "agents.proposal_generator.proposal_agent", "input": "All previous outputs"},
            {"order": 9, "action": "Quality + Compliance Check", "agent": "agents.quality_checker", "input": "All deliverables"},
            {"order": 10, "action": "Deliver to Client", "method": "Email portfolio link"},
        ],
        "error_handling": "Log errors, continue pipeline, flag failed stages for manual review",
        "make_webhook": "POST /webhook/new-client",
    },
    "geo_monitoring": {
        "name": "Weekly GEO Monitoring",
        "description": "Checks client visibility in AI search results weekly.",
        "trigger": "Every Monday at 10:00 AM",
        "steps": [
            {"order": 1, "action": "Run GEO Monitor", "agent": "agents.geo_monitor.geo_agent", "input": "Client name + city"},
            {"order": 2, "action": "Compare with Previous Week", "input": "Previous GEO report"},
            {"order": 3, "action": "Generate Improvement Recommendations", "agent": "agents.shared.llm (Claude)"},
            {"order": 4, "action": "Add to Monthly Report", "method": "Append GEO section"},
        ],
        "error_handling": "If Perplexity API fails, skip and retry next day",
        "make_webhook": "POST /webhook/geo-check",
    },
}


def generate_make_blueprint(workflow_id: str) -> dict:
    """Generate a Make.com scenario blueprint for a workflow."""
    workflow = WORKFLOWS.get(workflow_id)
    if not workflow:
        return {"error": f"Unknown workflow: {workflow_id}"}

    blueprint = {
        "name": f"AUROS — {workflow['name']}",
        "description": workflow["description"],
        "trigger": workflow["trigger"],
        "modules": [],
    }

    for step in workflow["steps"]:
        module = {
            "order": step["order"],
            "type": "webhook" if "agent" in step else "action",
            "action": step["action"],
        }
        if "agent" in step:
            module["webhook_url"] = f"{{{{base_url}}}}/{workflow.get('make_webhook', '/webhook/default')}"
            module["payload"] = {"agent": step["agent"], "input": step.get("input", "")}
        if "method" in step:
            module["method"] = step["method"]

        blueprint["modules"].append(module)

    return blueprint


def generate_cron_schedule() -> dict:
    """Generate crontab entries for all scheduled workflows."""
    project_root = str(PROJECT_ROOT)
    venv_python = f"{project_root}/venv/bin/python"

    cron_entries = {
        "daily_newsletter": {
            "cron": "0 7 * * *",
            "command": f'cd "{project_root}" && {venv_python} -m agents.newsletter.newsletter_agent',
            "description": "Daily AI marketing newsletter at 7 AM",
        },
        "market_analysis": {
            "cron": "0 8 * * 1,3,5",
            "command": f'cd "{project_root}" && {venv_python} -m agents.market_analysis.market_agent',
            "description": "Market analysis Mon/Wed/Fri at 8 AM",
        },
        "performance_check": {
            "cron": "0 18 * * *",
            "command": f'cd "{project_root}" && {venv_python} -m agents.performance_tracker.performance_agent --company "The Imagine Team"',
            "description": "Daily performance check at 6 PM",
        },
        "geo_monitor": {
            "cron": "0 10 * * 1",
            "command": f'cd "{project_root}" && {venv_python} -m agents.geo_monitor.geo_agent --company "The Imagine Team" --city "Barcelona"',
            "description": "Weekly GEO monitoring Mondays at 10 AM",
        },
        "monthly_report": {
            "cron": "0 9 1 * *",
            "command": f'cd "{project_root}" && {venv_python} -m agents.client_reports.report_agent --company "The Imagine Team"',
            "description": "Monthly client report on the 1st at 9 AM",
        },
    }

    return cron_entries


def export_all_configs(output_dir: str | None = None) -> dict:
    """Export all workflow configurations to files."""
    if output_dir is None:
        output_dir = str(PROJECT_ROOT / "agents" / "automation" / "configs")

    os.makedirs(output_dir, exist_ok=True)

    # Save workflow definitions
    with open(os.path.join(output_dir, "workflows.json"), "w") as f:
        json.dump(WORKFLOWS, f, indent=2)

    # Save Make blueprints
    blueprints = {}
    for wf_id in WORKFLOWS:
        blueprints[wf_id] = generate_make_blueprint(wf_id)
    with open(os.path.join(output_dir, "make_blueprints.json"), "w") as f:
        json.dump(blueprints, f, indent=2)

    # Save cron schedule
    crons = generate_cron_schedule()
    with open(os.path.join(output_dir, "cron_schedule.json"), "w") as f:
        json.dump(crons, f, indent=2)

    # Generate crontab file
    crontab_lines = [f"# AUROS AI — Automated Agent Schedule", f"# Generated: {datetime.now().isoformat()}", ""]
    for name, entry in crons.items():
        crontab_lines.append(f"# {entry['description']}")
        crontab_lines.append(f"{entry['cron']} {entry['command']} >> \"{PROJECT_ROOT}/logs/{name}.log\" 2>&1")
        crontab_lines.append("")
    with open(os.path.join(output_dir, "crontab.txt"), "w") as f:
        f.write("\n".join(crontab_lines))

    print(f"[AUROS] Workflow configs exported to {output_dir}")
    return {
        "workflows": len(WORKFLOWS),
        "cron_entries": len(crons),
        "output_dir": output_dir,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AUROS Workflow Automation Config")
    parser.add_argument("--export", action="store_true", help="Export all configs")
    parser.add_argument("--list", action="store_true", help="List all workflows")
    parser.add_argument("--cron", action="store_true", help="Show cron schedule")
    args = parser.parse_args()

    if args.list:
        print("\n=== AUROS WORKFLOWS ===\n")
        for wf_id, wf in WORKFLOWS.items():
            print(f"  {wf_id}")
            print(f"    {wf['name']}")
            print(f"    Trigger: {wf['trigger']}")
            print(f"    Steps: {len(wf['steps'])}")
            print()
    elif args.cron:
        print("\n=== CRON SCHEDULE ===\n")
        for name, entry in generate_cron_schedule().items():
            print(f"  {entry['cron']}  # {entry['description']}")
        print()
    elif args.export:
        result = export_all_configs()
        print(f"\nExported {result['workflows']} workflows, {result['cron_entries']} cron entries")
    else:
        parser.print_help()
