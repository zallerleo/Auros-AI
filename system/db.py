"""
AUROS AI — SQLite Database Layer
Central state management for tasks, conversations, agent memory, and schedules.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "auros.db"

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL,
            task_type TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            error TEXT,
            started_at TEXT,
            completed_at TEXT,
            priority INTEGER NOT NULL DEFAULT 5,
            retry_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            telegram_message_id INTEGER,
            telegram_chat_id INTEGER,
            agent TEXT NOT NULL,
            user_message TEXT,
            agent_response TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_memory (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            UNIQUE(agent, key)
        );

        CREATE TABLE IF NOT EXISTS schedule (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            task_type TEXT NOT NULL,
            cron_expression TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run TEXT,
            next_run TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_to_agent ON tasks(to_agent);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority, created_at);
        CREATE INDEX IF NOT EXISTS idx_conversations_agent ON conversations(agent);
        CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent);
        CREATE INDEX IF NOT EXISTS idx_schedule_enabled ON schedule(enabled);

        -- Lead Generation Pipeline
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            business_name TEXT NOT NULL,
            category TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            phone TEXT,
            google_maps_url TEXT,
            place_id TEXT UNIQUE,
            rating REAL,
            review_count INTEGER DEFAULT 0,
            has_website INTEGER DEFAULT 0,
            website_url TEXT,
            has_social_media INTEGER DEFAULT 0,
            social_links TEXT DEFAULT '{}',
            contact_email TEXT,
            email_source TEXT,
            email_confidence REAL,
            owner_name TEXT,
            lead_score INTEGER DEFAULT 0,
            lead_temperature TEXT DEFAULT 'cold',
            status TEXT DEFAULT 'new',
            campaign_id TEXT,
            notes TEXT,
            website_generated INTEGER DEFAULT 0,
            generated_site_url TEXT,
            site_template TEXT
        );

        CREATE TABLE IF NOT EXISTS outreach_campaigns (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            name TEXT NOT NULL,
            target_category TEXT,
            target_city TEXT,
            target_state TEXT,
            status TEXT DEFAULT 'draft',
            total_leads INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            open_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            interested_count INTEGER DEFAULT 0,
            converted_count INTEGER DEFAULT 0,
            sequence_config TEXT DEFAULT '{}',
            email_template_id TEXT
        );

        CREATE TABLE IF NOT EXISTS websites (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            lead_id TEXT,
            business_name TEXT NOT NULL,
            category TEXT,
            template TEXT NOT NULL,
            html_path TEXT,
            deploy_url TEXT,
            deploy_id TEXT,
            status TEXT DEFAULT 'draft',
            config TEXT DEFAULT '{}',
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_category ON leads(category);
        CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score DESC);
        CREATE INDEX IF NOT EXISTS idx_leads_place_id ON leads(place_id);
        CREATE INDEX IF NOT EXISTS idx_campaigns_status ON outreach_campaigns(status);
        CREATE INDEX IF NOT EXISTS idx_websites_lead ON websites(lead_id);
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Task Operations
# ---------------------------------------------------------------------------

def create_task(
    from_agent: str,
    to_agent: str,
    task_type: str,
    payload: dict | None = None,
    priority: int = 5,
) -> str:
    """Create a new task. Returns the task ID."""
    task_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO tasks (id, created_at, from_agent, to_agent, task_type, payload, status, priority)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (task_id, now, from_agent, to_agent, task_type, json.dumps(payload or {}), priority),
    )
    conn.commit()
    conn.close()
    return task_id


def get_task(task_id: str) -> dict | None:
    """Get a single task by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row:
        return _row_to_dict(row)
    return None


def get_pending_tasks(agent: str | None = None) -> list[dict]:
    """Get pending tasks, optionally filtered by target agent."""
    conn = get_connection()
    if agent:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' AND to_agent = ? ORDER BY priority ASC, created_at ASC",
            (agent,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority ASC, created_at ASC"
        ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_awaiting_approval() -> list[dict]:
    """Get all tasks awaiting Leo's approval."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status = 'awaiting_approval' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def update_task_status(task_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    """Update a task's status."""
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    if status == "running":
        conn.execute("UPDATE tasks SET status = ?, started_at = ? WHERE id = ?", (status, now, task_id))
    elif status in ("completed", "failed"):
        conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, result = ?, error = ? WHERE id = ?",
            (status, now, json.dumps(result) if result else None, error, task_id),
        )
    else:
        conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()


def get_recent_tasks(limit: int = 20) -> list[dict]:
    """Get the most recent tasks."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Conversation Operations
# ---------------------------------------------------------------------------

def save_conversation(
    agent: str,
    user_message: str,
    agent_response: str,
    telegram_message_id: int | None = None,
    telegram_chat_id: int | None = None,
) -> str:
    """Save a conversation exchange."""
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO conversations (id, telegram_message_id, telegram_chat_id, agent, user_message, agent_response, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (conv_id, telegram_message_id, telegram_chat_id, agent, user_message, agent_response, now),
    )
    conn.commit()
    conn.close()
    return conv_id


def get_recent_conversations(agent: str | None = None, limit: int = 10) -> list[dict]:
    """Get recent conversations for context."""
    conn = get_connection()
    if agent:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE agent = ? ORDER BY created_at DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Agent Memory Operations
# ---------------------------------------------------------------------------

def remember(agent: str, key: str, value: Any) -> None:
    """Store or update an agent's memory."""
    mem_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO agent_memory (id, agent, key, value, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(agent, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (mem_id, agent, key, json.dumps(value), now),
    )
    conn.commit()
    conn.close()


def recall(agent: str, key: str) -> Any | None:
    """Recall a specific memory."""
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM agent_memory WHERE agent = ? AND key = ?", (agent, key)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return None


def recall_all(agent: str) -> dict[str, Any]:
    """Recall all memories for an agent."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, value FROM agent_memory WHERE agent = ? ORDER BY updated_at DESC", (agent,)
    ).fetchall()
    conn.close()
    return {r["key"]: json.loads(r["value"]) for r in rows}


# ---------------------------------------------------------------------------
# Schedule Operations
# ---------------------------------------------------------------------------

def create_schedule(
    agent: str, task_type: str, cron_expression: str, payload: dict | None = None
) -> str:
    """Create a scheduled recurring task."""
    sched_id = str(uuid.uuid4())[:8]
    conn = get_connection()
    conn.execute(
        """INSERT INTO schedule (id, agent, task_type, cron_expression, payload)
           VALUES (?, ?, ?, ?, ?)""",
        (sched_id, agent, task_type, cron_expression, json.dumps(payload or {})),
    )
    conn.commit()
    conn.close()
    return sched_id


def get_active_schedules() -> list[dict]:
    """Get all enabled schedules."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM schedule WHERE enabled = 1").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a dict, parsing JSON fields."""
    d = dict(row)
    for field in ("payload", "result", "value"):
        if field in d and d[field] and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


# ---------------------------------------------------------------------------
# Lead Operations
# ---------------------------------------------------------------------------

def create_lead(data: dict) -> str:
    """Create a new lead. Returns the lead ID."""
    lead_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO leads (
            id, created_at, updated_at, business_name, category, address, city, state,
            phone, google_maps_url, place_id, rating, review_count,
            has_website, website_url, has_social_media, social_links
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            lead_id, now, now,
            data.get("business_name", ""),
            data.get("category", ""),
            data.get("address", ""),
            data.get("city", ""),
            data.get("state", ""),
            data.get("phone", ""),
            data.get("google_maps_url", ""),
            data.get("place_id", ""),
            data.get("rating"),
            data.get("review_count", 0),
            1 if data.get("has_website") else 0,
            data.get("website_url", ""),
            1 if data.get("has_social_media") else 0,
            json.dumps(data.get("social_links", {})),
        ),
    )
    conn.commit()
    conn.close()
    return lead_id


def update_lead(lead_id: str, **fields) -> None:
    """Update a lead's fields."""
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [lead_id]
    conn = get_connection()
    conn.execute(f"UPDATE leads SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_lead(lead_id: str) -> dict | None:
    """Get a single lead."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def search_leads(
    city: str | None = None,
    state: str | None = None,
    category: str | None = None,
    status: str | None = None,
    min_score: int = 0,
    has_website: bool | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search leads with filters."""
    conn = get_connection()
    query = "SELECT * FROM leads WHERE lead_score >= ?"
    params: list = [min_score]

    if city:
        query += " AND LOWER(city) = LOWER(?)"
        params.append(city)
    if state:
        query += " AND LOWER(state) = LOWER(?)"
        params.append(state)
    if category:
        query += " AND LOWER(category) LIKE LOWER(?)"
        params.append(f"%{category}%")
    if status:
        query += " AND status = ?"
        params.append(status)
    if has_website is not None:
        query += " AND has_website = ?"
        params.append(1 if has_website else 0)

    query += " ORDER BY lead_score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_lead_stats() -> dict:
    """Get lead pipeline statistics."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM leads").fetchone()["c"]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as c FROM leads GROUP BY status").fetchall():
        by_status[row["status"]] = row["c"]
    by_temp = {}
    for row in conn.execute("SELECT lead_temperature, COUNT(*) as c FROM leads GROUP BY lead_temperature").fetchall():
        by_temp[row["lead_temperature"]] = row["c"]
    websites_built = conn.execute("SELECT COUNT(*) as c FROM leads WHERE website_generated = 1").fetchone()["c"]
    conn.close()
    return {"total": total, "by_status": by_status, "by_temperature": by_temp, "websites_built": websites_built}


# ---------------------------------------------------------------------------
# Campaign Operations
# ---------------------------------------------------------------------------

def create_campaign(name: str, target_category: str, target_city: str, target_state: str) -> str:
    """Create an outreach campaign."""
    campaign_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO outreach_campaigns (id, created_at, name, target_category, target_city, target_state) VALUES (?, ?, ?, ?, ?, ?)",
        (campaign_id, now, name, target_category, target_city, target_state),
    )
    conn.commit()
    conn.close()
    return campaign_id


def update_campaign(campaign_id: str, **fields) -> None:
    """Update campaign fields."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [campaign_id]
    conn = get_connection()
    conn.execute(f"UPDATE outreach_campaigns SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_campaigns(status: str | None = None) -> list[dict]:
    """Get campaigns."""
    conn = get_connection()
    if status:
        rows = conn.execute("SELECT * FROM outreach_campaigns WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM outreach_campaigns ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Website Operations
# ---------------------------------------------------------------------------

def create_website_record(lead_id: str, business_name: str, category: str, template: str, html_path: str) -> str:
    """Create a website record."""
    site_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO websites (id, created_at, lead_id, business_name, category, template, html_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (site_id, now, lead_id, business_name, category, template, html_path),
    )
    conn.commit()
    conn.close()
    return site_id


def update_website(site_id: str, **fields) -> None:
    """Update website record."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [site_id]
    conn = get_connection()
    conn.execute(f"UPDATE websites SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


# Auto-initialize on import
init_db()
