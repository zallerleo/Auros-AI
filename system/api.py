#!/usr/bin/env python3
"""
AUROS AI — Dashboard API
FastAPI server that exposes agent, task, and system data for the web dashboard.
Reads from the same auros.db that the agents use.

Run:
    uvicorn system.api:app --host 0.0.0.0 --port 8100 --reload
"""

from __future__ import annotations

import sys
import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from system.db import (
    init_db,
    get_recent_tasks,
    get_pending_tasks,
    get_awaiting_approval,
    update_task_status,
    get_task,
    get_connection,
    recall_all,
)

app = FastAPI(title="AUROS AI Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
init_db()

# ---------------------------------------------------------------------------
# Agent definitions (static metadata)
# ---------------------------------------------------------------------------

AGENTS = {
    "ATLAS": {
        "name": "ATLAS",
        "role": "Chief of Staff",
        "description": "Routes requests, coordinates agents, compiles briefings",
        "icon": "brain",
        "color": "#C9A84C",
        "tools": ["route_message", "daily_briefing", "approval_queue", "system_status"],
    },
    "SCOUT": {
        "name": "SCOUT",
        "role": "Research & Intelligence",
        "description": "Market research, competitive analysis, trends, sector scanning",
        "icon": "search",
        "color": "#3B82F6",
        "tools": ["deep_research", "quick_search", "competitive_analysis", "market_scan", "trend_analysis", "geo_check"],
    },
    "FORGE": {
        "name": "FORGE",
        "role": "Strategy & Clients",
        "description": "Client onboarding, marketing strategy, positioning, proposals",
        "icon": "target",
        "color": "#8B5CF6",
        "tools": ["run_pipeline", "run_stage", "pipeline_status", "create_proposal", "marketing_audit"],
    },
    "APOLLO": {
        "name": "APOLLO",
        "role": "Creative & Content",
        "description": "Content creation, video scripts, social posts, copywriting",
        "icon": "palette",
        "color": "#F59E0B",
        "tools": ["create_social_posts", "create_video_script", "generate_hooks", "content_calendar", "creative_brief"],
    },
    "HERMES": {
        "name": "HERMES",
        "role": "Outreach & Comms",
        "description": "Cold outreach, email campaigns, newsletters, follow-ups",
        "icon": "send",
        "color": "#10B981",
        "tools": ["draft_outreach", "draft_sequence", "send_newsletter", "draft_followup", "outreach_strategy"],
    },
    "SENTINEL": {
        "name": "SENTINEL",
        "role": "Operations & Performance",
        "description": "KPI tracking, analytics, anomaly detection, system health",
        "icon": "shield",
        "color": "#EF4444",
        "tools": ["performance_report", "system_health", "cost_tracking", "task_analytics", "anomaly_check"],
    },
}


# ---------------------------------------------------------------------------
# Dashboard Overview
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def get_dashboard():
    """Main dashboard data: KPIs, agent status, recent activity."""
    conn = get_connection()

    # Task counts
    total_tasks = conn.execute("SELECT COUNT(*) as c FROM tasks").fetchone()["c"]
    completed = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status='completed'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status='failed'").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status='pending'").fetchone()["c"]
    running = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status='running'").fetchone()["c"]
    awaiting = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status='awaiting_approval'").fetchone()["c"]

    # Today's tasks
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_completed = conn.execute(
        "SELECT COUNT(*) as c FROM tasks WHERE status='completed' AND completed_at LIKE ?", (f"{today}%",)
    ).fetchone()["c"]

    # Tasks per agent
    agent_tasks = {}
    for row in conn.execute(
        "SELECT to_agent, COUNT(*) as c FROM tasks GROUP BY to_agent"
    ).fetchall():
        agent_tasks[row["to_agent"]] = row["c"]

    # Completion rate
    completion_rate = round(completed / max(total_tasks, 1) * 100, 1)

    # Uptime (days since first task)
    first_task = conn.execute("SELECT MIN(created_at) as first FROM tasks").fetchone()
    uptime_days = 0
    if first_task and first_task["first"]:
        try:
            first_dt = datetime.fromisoformat(first_task["first"])
            uptime_days = (datetime.utcnow() - first_dt).days
        except Exception:
            pass

    # Performance over time (last 7 days)
    performance_data = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_label = (datetime.utcnow() - timedelta(days=i)).strftime("%a")
        day_completed = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE status='completed' AND completed_at LIKE ?",
            (f"{day}%",),
        ).fetchone()["c"]
        day_failed = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE status='failed' AND completed_at LIKE ?",
            (f"{day}%",),
        ).fetchone()["c"]
        day_total = day_completed + day_failed
        accuracy = round(day_completed / max(day_total, 1) * 100) if day_total > 0 else 100
        performance_data.append({
            "day": day_label,
            "completed": day_completed,
            "failed": day_failed,
            "accuracy": accuracy,
        })

    conn.close()

    # System health
    disk = shutil.disk_usage("/")

    return {
        "kpis": {
            "total_agents": len(AGENTS),
            "active_agents": len(AGENTS),
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "today_completed": today_completed,
            "completion_rate": completion_rate,
            "uptime_days": max(uptime_days, 1),
            "pending_tasks": pending,
            "running_tasks": running,
            "failed_tasks": failed,
            "awaiting_approval": awaiting,
        },
        "performance": performance_data,
        "agent_tasks": agent_tasks,
        "system": {
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_usage_pct": round(disk.used / disk.total * 100, 1),
        },
    }


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@app.get("/api/agents")
def get_agents():
    """Get all agents with their status and recent activity."""
    conn = get_connection()
    result = []

    for name, meta in AGENTS.items():
        # Task stats for this agent
        total = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE to_agent=?", (name,)
        ).fetchone()["c"]
        completed = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE to_agent=? AND status='completed'", (name,)
        ).fetchone()["c"]
        failed = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE to_agent=? AND status='failed'", (name,)
        ).fetchone()["c"]
        running = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE to_agent=? AND status='running'", (name,)
        ).fetchone()["c"]

        # Last activity
        last_task = conn.execute(
            "SELECT * FROM tasks WHERE to_agent=? ORDER BY created_at DESC LIMIT 1", (name,)
        ).fetchone()

        # Agent memory
        memories = recall_all(name)
        last_action = memories.get("last_action", "No activity yet")

        # Determine status
        if running > 0:
            status = "active"
        elif failed > 0 and completed == 0:
            status = "error"
        else:
            status = "online"

        result.append({
            **meta,
            "status": status,
            "stats": {
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "success_rate": round(completed / max(total, 1) * 100, 1),
            },
            "last_action": last_action if isinstance(last_action, str) else json.dumps(last_action)[:150],
            "last_activity": dict(last_task)["created_at"] if last_task else None,
            "memory_count": len(memories),
        })

    conn.close()
    return result


@app.get("/api/agents/{agent_name}")
def get_agent_detail(agent_name: str):
    """Get detailed info about a specific agent."""
    agent_name = agent_name.upper()
    if agent_name not in AGENTS:
        return {"error": f"Agent {agent_name} not found"}

    meta = AGENTS[agent_name]
    conn = get_connection()

    # Recent tasks
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE to_agent=? OR from_agent=? ORDER BY created_at DESC LIMIT 20",
        (agent_name, agent_name),
    ).fetchall()

    # Conversations
    convos = conn.execute(
        "SELECT * FROM conversations WHERE agent=? ORDER BY created_at DESC LIMIT 10",
        (agent_name,),
    ).fetchall()

    # Memory
    memories = recall_all(agent_name)

    conn.close()

    return {
        **meta,
        "tasks": [dict(t) for t in tasks],
        "conversations": [dict(c) for c in convos],
        "memories": memories,
    }


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.get("/api/tasks")
def get_tasks(
    status: str | None = None,
    agent: str | None = None,
    limit: int = Query(default=50, le=200),
):
    """Get tasks with optional filtering."""
    conn = get_connection()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if agent:
        query += " AND (to_agent = ? OR from_agent = ?)"
        params.extend([agent.upper(), agent.upper()])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    tasks = []
    for r in rows:
        d = dict(r)
        for field in ("payload", "result"):
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        tasks.append(d)

    return tasks


@app.get("/api/tasks/approvals")
def get_approvals():
    """Get tasks awaiting approval."""
    return get_awaiting_approval()


@app.post("/api/tasks/{task_id}/approve")
def approve_task(task_id: str):
    """Approve a task."""
    task = get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    update_task_status(task_id, "pending")
    return {"status": "approved", "task_id": task_id}


@app.post("/api/tasks/{task_id}/reject")
def reject_task(task_id: str):
    """Reject a task."""
    task = get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    update_task_status(task_id, "rejected")
    return {"status": "rejected", "task_id": task_id}


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

@app.get("/api/system/health")
def system_health():
    """System health check."""
    from agents.shared.config import (
        ANTHROPIC_API_KEY, TAVILY_API_KEY, PERPLEXITY_API_KEY,
        RESEND_API_KEY, PORTFOLIO_DIR,
    )

    disk = shutil.disk_usage("/")

    clients = []
    if PORTFOLIO_DIR.exists():
        clients = [d.name.replace("client_", "").replace("_", " ").title()
                    for d in PORTFOLIO_DIR.iterdir() if d.is_dir() and d.name.startswith("client_")]

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "api_keys": {
            "anthropic": bool(ANTHROPIC_API_KEY),
            "perplexity": bool(PERPLEXITY_API_KEY),
            "tavily": bool(TAVILY_API_KEY),
            "resend": bool(RESEND_API_KEY),
            "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        },
        "disk": {
            "free_gb": round(disk.free / (1024**3), 1),
            "total_gb": round(disk.total / (1024**3), 1),
            "usage_pct": round(disk.used / disk.total * 100, 1),
        },
        "clients": clients,
        "agents": list(AGENTS.keys()),
    }


@app.get("/api/clients")
def get_clients():
    """Get all client portfolios."""
    from agents.shared.config import PORTFOLIO_DIR

    if not PORTFOLIO_DIR.exists():
        return []

    clients = []
    for d in sorted(PORTFOLIO_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("client_"):
            name = d.name.replace("client_", "").replace("_", " ").title()
            files = list(d.glob("*.json")) + list(d.glob("*.html")) + list(d.glob("*.md"))

            # Check pipeline state
            state_file = d / "pipeline_state.json"
            pipeline = {}
            if state_file.exists():
                try:
                    pipeline = json.loads(state_file.read_text())
                except Exception:
                    pass

            clients.append({
                "name": name,
                "slug": d.name,
                "files": len(files),
                "pipeline": pipeline.get("stages", {}),
                "created": pipeline.get("created_at", "Unknown"),
            })

    return clients


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
