#!/usr/bin/env python3
"""
AUROS AI -- Agent 0: Orchestrator
Master pipeline coordinator that sequences every agent in the AUROS client
delivery workflow.  Tracks state, handles errors, and generates status reports.

Usage:
    python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --status
    python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --next
    python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --run-all
    python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --stage audit
    python -m agents.orchestrator.orchestrator_agent --company "The Imagine Team" --run-all --start-from brand --stop-at calendar
"""

from __future__ import annotations

import sys
import json
import argparse
import importlib
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.shared.config import PORTFOLIO_DIR, LOGS_DIR, BRAND

# ---------------------------------------------------------------------------
# Pipeline definition
# ---------------------------------------------------------------------------

PIPELINE: list[dict[str, str]] = [
    {
        "id": "research",
        "agent": "agents.shared.perplexity",
        "func": "deep_research",
        "description": "Deep market research",
    },
    {
        "id": "audit",
        "agent": "agents.marketing_audit.audit_agent",
        "func": "run",
        "description": "Marketing audit",
    },
    {
        "id": "brand",
        "agent": "agents.brand_extractor.brand_agent",
        "func": "run",
        "description": "Brand extraction",
    },
    {
        "id": "positioning",
        "agent": "agents.positioning.positioning_agent",
        "func": "run",
        "description": "Positioning analysis",
    },
    {
        "id": "plan",
        "agent": "agents.plan_builder.plan_agent",
        "func": "run",
        "description": "Marketing plan",
    },
    {
        "id": "vision",
        "agent": "agents.vision_board.vision_agent",
        "func": "run",
        "description": "Vision board",
    },
    {
        "id": "trend",
        "agent": "agents.trend_analyst.trend_agent",
        "func": "run",
        "description": "Trend analysis",
    },
    {
        "id": "content",
        "agent": "agents.content_creator.exhibition_content",
        "func": "run",
        "description": "Content creation",
    },
    {
        "id": "calendar",
        "agent": "agents.content_calendar.calendar_agent",
        "func": "run",
        "description": "Content calendar",
    },
    {
        "id": "proposal",
        "agent": "agents.proposal_generator.proposal_agent",
        "func": "run",
        "description": "Proposal generation",
    },
    {
        "id": "quality",
        "agent": "agents.quality_checker.quality_agent",
        "func": "run",
        "description": "Quality check",
    },
    {
        "id": "compliance",
        "agent": "agents.quality_checker.compliance",
        "func": "check_compliance",
        "description": "EU AI Act compliance",
    },
    {
        "id": "geo",
        "agent": "agents.geo_monitor.geo_agent",
        "func": "run",
        "description": "GEO monitoring",
    },
]

# Maps pipeline stage IDs to file-name prefixes produced by each agent.
# Used to detect which stages already have output on disk.
_OUTPUT_PATTERNS: dict[str, list[str]] = {
    "research":   ["research_", "marketing_audit_"],
    "audit":      ["marketing_audit_"],
    "brand":      ["brand_identity_"],
    "positioning": ["positioning_", "strategic_framework_"],
    "plan":       ["marketing_plan_"],
    "vision":     ["vision_board_"],
    "trend":      ["trend_report_"],
    "content":    ["cabinet_of_curiosities/", "titanic/", "van_gogh/", "video_scripts_"],
    "calendar":   ["content_calendar_"],
    "proposal":   ["proposal_"],
    "quality":    ["quality_"],
    "compliance": ["compliance_"],
    "geo":        ["geo_"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _company_slug(company: str) -> str:
    """Normalise company name to a filesystem-safe slug."""
    return company.lower().replace(" ", "_").replace("'", "")


def _client_dir(company: str) -> Path:
    """Return (and create) the portfolio directory for *company*."""
    d = PORTFOLIO_DIR / f"client_{_company_slug(company)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path(company: str) -> Path:
    return _client_dir(company) / "pipeline_state.json"


def _load_state(company: str) -> dict[str, Any]:
    """Load persisted pipeline state, or return a fresh skeleton."""
    path = _state_path(company)
    if path.exists():
        return json.loads(path.read_text())
    return {
        "company": company,
        "created_at": datetime.now().isoformat(),
        "stages": {},
    }


def _save_state(company: str, state: dict[str, Any]) -> None:
    path = _state_path(company)
    state["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(state, indent=2, default=str))


def _has_output_files(company: str, stage_id: str) -> bool:
    """Return True if the portfolio already contains output for *stage_id*."""
    client = _client_dir(company)
    patterns = _OUTPUT_PATTERNS.get(stage_id, [])
    for pattern in patterns:
        if pattern.endswith("/"):
            # Check for a subdirectory with content
            subdir = client / pattern.rstrip("/")
            if subdir.is_dir() and any(subdir.iterdir()):
                return True
        else:
            if list(client.rglob(f"{pattern}*")):
                return True
    return False


def _log(msg: str) -> None:
    """Print a timestamped AUROS log line."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[AUROS {ts}] {msg}")


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def get_pipeline_status(company: str) -> dict[str, Any]:
    """Check which stages have been completed by inspecting output files
    and the persisted pipeline state.

    Returns a dict with a ``stages`` list, each entry containing:
    ``id``, ``description``, ``status``, ``has_output``, and timestamps.
    """
    state = _load_state(company)
    stages_info: list[dict[str, Any]] = []

    for stage in PIPELINE:
        sid = stage["id"]
        saved = state.get("stages", {}).get(sid, {})
        has_output = _has_output_files(company, sid)

        # Derive effective status
        if saved.get("status") == "completed" or has_output:
            status = "completed"
        elif saved.get("status") == "failed":
            status = "failed"
        elif saved.get("status") == "running":
            status = "running"
        else:
            status = "pending"

        stages_info.append({
            "id": sid,
            "description": stage["description"],
            "status": status,
            "has_output": has_output,
            "started_at": saved.get("started_at"),
            "completed_at": saved.get("completed_at"),
            "error": saved.get("error"),
        })

    return {
        "company": company,
        "stages": stages_info,
        "completed": sum(1 for s in stages_info if s["status"] == "completed"),
        "total": len(stages_info),
    }


def get_next_stage(company: str) -> dict[str, str] | None:
    """Return the first pipeline stage that has not yet been completed,
    or ``None`` if every stage is done."""
    status = get_pipeline_status(company)
    for s in status["stages"]:
        if s["status"] not in ("completed",):
            # Return the matching PIPELINE entry
            for p in PIPELINE:
                if p["id"] == s["id"]:
                    return p
            return None
    return None


def run_stage(stage_id: str, company: str, **kwargs: Any) -> dict[str, Any]:
    """Import and execute a single pipeline stage.

    Returns a dict with ``stage_id``, ``status``, ``result`` (or ``error``).
    """
    # Find the stage definition
    stage = None
    for p in PIPELINE:
        if p["id"] == stage_id:
            stage = p
            break
    if stage is None:
        return {"stage_id": stage_id, "status": "error", "error": f"Unknown stage: {stage_id}"}

    state = _load_state(company)
    if "stages" not in state:
        state["stages"] = {}

    # Mark running
    state["stages"][stage_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "output_files": [],
    }
    _save_state(company, state)

    _log(f"Running stage: {stage['description']}...")

    try:
        mod = importlib.import_module(stage["agent"])
        func = getattr(mod, stage["func"])

        # Build call kwargs -- every agent accepts ``company`` at minimum
        call_kwargs: dict[str, Any] = {"company": company}
        call_kwargs.update(kwargs)

        result = func(**call_kwargs)

        # Detect output files created during this run
        output_files = [
            str(f.relative_to(PORTFOLIO_DIR))
            for f in _client_dir(company).rglob("*")
            if f.is_file()
        ]

        state["stages"][stage_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "output_files": output_files,
        })
        _save_state(company, state)

        _log(f"Stage complete: {stage['description']}")
        return {"stage_id": stage_id, "status": "completed", "result": result}

    except Exception as exc:
        tb = traceback.format_exc()
        error_msg = f"{exc.__class__.__name__}: {exc}"

        state["stages"][stage_id].update({
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "error": error_msg,
        })
        _save_state(company, state)

        _log(f"Stage FAILED: {stage['description']} -- {error_msg}")
        _log(f"Traceback:\n{tb}")

        # Log to file
        log_dir = LOGS_DIR / "orchestrator"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"error_{stage_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file.write_text(f"{error_msg}\n\n{tb}")

        return {"stage_id": stage_id, "status": "failed", "error": error_msg}


def run_pipeline(
    company: str,
    start_from: str | None = None,
    stop_at: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run the full pipeline (or a subset from *start_from* to *stop_at*).

    Returns a summary dict with per-stage results.
    """
    _log(f"Pipeline starting for: {company}")
    _log(f"  start_from={start_from or '(beginning)'}  stop_at={stop_at or '(end)'}")

    # Determine stage window
    stage_ids = [s["id"] for s in PIPELINE]

    if start_from:
        if start_from not in stage_ids:
            return {"error": f"Unknown start stage: {start_from}"}
        start_idx = stage_ids.index(start_from)
    else:
        start_idx = 0

    if stop_at:
        if stop_at not in stage_ids:
            return {"error": f"Unknown stop stage: {stop_at}"}
        stop_idx = stage_ids.index(stop_at) + 1  # inclusive
    else:
        stop_idx = len(stage_ids)

    active_stages = PIPELINE[start_idx:stop_idx]

    results: list[dict[str, Any]] = []
    failed = 0

    for stage in active_stages:
        sid = stage["id"]

        # Skip if already completed (unless explicitly re-running)
        if _has_output_files(company, sid):
            _log(f"Skipping (already complete): {stage['description']}")
            results.append({"stage_id": sid, "status": "skipped"})
            continue

        outcome = run_stage(sid, company, **kwargs)
        results.append(outcome)

        if outcome["status"] == "failed":
            failed += 1
            _log(
                f"Stage '{stage['description']}' failed. "
                f"Continuing to next stage..."
            )

    _log(f"Pipeline finished for: {company}")
    _log(f"  Completed: {sum(1 for r in results if r['status'] == 'completed')}")
    _log(f"  Skipped:   {sum(1 for r in results if r['status'] == 'skipped')}")
    _log(f"  Failed:    {failed}")

    return {
        "company": company,
        "stages_run": len(results),
        "results": results,
        "failed": failed,
    }


# ---------------------------------------------------------------------------
# Status report (text + HTML dashboard)
# ---------------------------------------------------------------------------

def generate_status_report(company: str) -> str:
    """Return a formatted plaintext status report."""
    status = get_pipeline_status(company)
    lines = [
        "",
        f"  AUROS Pipeline Status -- {company}",
        f"  {'-' * 50}",
        f"  Progress: {status['completed']}/{status['total']} stages complete",
        "",
    ]

    symbols = {"completed": "+", "running": "~", "failed": "!", "pending": " "}

    for s in status["stages"]:
        sym = symbols.get(s["status"], "?")
        line = f"  [{sym}] {s['id']:<14} {s['description']}"
        if s["status"] == "completed" and s.get("completed_at"):
            line += f"  (done {s['completed_at'][:10]})"
        elif s["status"] == "failed" and s.get("error"):
            line += f"  ERROR: {s['error'][:60]}"
        lines.append(line)

    lines.append("")
    return "\n".join(lines)


def generate_html_dashboard(company: str) -> str:
    """Generate an HTML status dashboard and save it to the client directory."""
    status = get_pipeline_status(company)

    # Brand colours
    gold = BRAND.get("primary", "#C9A84C")
    dark = BRAND.get("background", "#0A0A0A")
    text_color = BRAND.get("text", "#F5F0E8")

    color_map = {
        "completed": "#22c55e",
        "running": "#eab308",
        "failed": "#ef4444",
        "pending": "#6b7280",
    }

    label_map = {
        "completed": "DONE",
        "running": "RUNNING",
        "failed": "FAILED",
        "pending": "PENDING",
    }

    pct = int((status["completed"] / status["total"]) * 100) if status["total"] else 0

    rows = ""
    for s in status["stages"]:
        c = color_map[s["status"]]
        label = label_map[s["status"]]
        detail = ""
        if s["status"] == "completed" and s.get("completed_at"):
            detail = s["completed_at"][:16].replace("T", " ")
        elif s["status"] == "failed" and s.get("error"):
            detail = s["error"][:80]
        rows += f"""
        <tr>
            <td style="padding:10px 16px;border-bottom:1px solid #222;">{s['id']}</td>
            <td style="padding:10px 16px;border-bottom:1px solid #222;">{s['description']}</td>
            <td style="padding:10px 16px;border-bottom:1px solid #222;text-align:center;">
                <span style="background:{c};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;">{label}</span>
            </td>
            <td style="padding:10px 16px;border-bottom:1px solid #222;color:#999;font-size:13px;">{detail}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS Pipeline -- {company}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:{dark}; color:{text_color}; font-family:'Inter','Helvetica Neue',sans-serif; padding:40px; }}
  h1 {{ color:{gold}; font-size:28px; margin-bottom:8px; }}
  .subtitle {{ color:#999; margin-bottom:32px; font-size:14px; }}
  .progress-bar {{ background:#1a1a1a; border-radius:8px; height:16px; margin-bottom:32px; overflow:hidden; }}
  .progress-fill {{ background:linear-gradient(90deg,{gold},#e8c84a); height:100%; border-radius:8px; transition:width .4s ease; }}
  table {{ width:100%; border-collapse:collapse; background:#111; border-radius:12px; overflow:hidden; }}
  th {{ text-align:left; padding:12px 16px; background:#1a1a1a; color:{gold}; font-size:13px; text-transform:uppercase; letter-spacing:0.5px; }}
  .footer {{ margin-top:32px; text-align:center; color:#555; font-size:12px; }}
</style>
</head>
<body>
  <h1>AUROS Pipeline Dashboard</h1>
  <p class="subtitle">{company} &mdash; {status['completed']}/{status['total']} stages complete ({pct}%)</p>

  <div class="progress-bar">
    <div class="progress-fill" style="width:{pct}%"></div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Stage</th>
        <th>Description</th>
        <th style="text-align:center;">Status</th>
        <th>Detail</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <p class="footer">Generated by AUROS AI &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</body>
</html>"""

    # Save
    out = _client_dir(company) / "pipeline_dashboard.html"
    out.write_text(html)
    _log(f"Dashboard saved to {out}")
    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AUROS AI -- Orchestrator Agent (Agent 0)",
    )
    parser.add_argument("--company", required=True, help="Client company name")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--next", action="store_true", dest="run_next", help="Run the next pending stage")
    parser.add_argument("--run-all", action="store_true", help="Run full pipeline")
    parser.add_argument("--stage", type=str, help="Run a specific stage by ID")
    parser.add_argument("--start-from", type=str, help="Start pipeline from this stage (with --run-all)")
    parser.add_argument("--stop-at", type=str, help="Stop pipeline at this stage (with --run-all)")
    parser.add_argument("--dashboard", action="store_true", help="Generate HTML dashboard")

    args = parser.parse_args()
    company = args.company

    if args.status:
        report = generate_status_report(company)
        print(report)
        # Also generate dashboard alongside
        generate_html_dashboard(company)

    elif args.run_next:
        nxt = get_next_stage(company)
        if nxt is None:
            _log("All pipeline stages are complete.")
        else:
            _log(f"Next stage: {nxt['id']} -- {nxt['description']}")
            run_stage(nxt["id"], company)
        generate_html_dashboard(company)

    elif args.run_all:
        run_pipeline(company, start_from=args.start_from, stop_at=args.stop_at)
        generate_html_dashboard(company)

    elif args.stage:
        run_stage(args.stage, company)
        generate_html_dashboard(company)

    elif args.dashboard:
        generate_html_dashboard(company)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
