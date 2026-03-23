#!/usr/bin/env python3
"""
AUROS AI — Task Worker
Processes the task queue: picks up pending tasks, runs the target agent,
handles retries, and updates task status.

Run:
    python -m system.task_worker
"""

from __future__ import annotations

import sys
import time
import json
import logging
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system.db import (
    init_db,
    get_pending_tasks,
    update_task_status,
    get_task,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "task_worker.log"),
    ],
)
logger = logging.getLogger("auros.worker")

# Max retries for failed tasks
MAX_RETRIES = 3
# Poll interval (seconds)
POLL_INTERVAL = 10


def get_agent_instance(agent_name: str):
    """Get an agent instance by name. Lazy import to avoid circular deps."""
    from system.agents.atlas import get_agent
    return get_agent(agent_name)


def init_agents():
    """Initialize all agents (same as telegram_bot)."""
    from system.agents.atlas import register_agent
    from system.agents.scout import Scout
    from system.agents.forge import Forge
    from system.agents.apollo import Apollo
    from system.agents.hermes import Hermes
    from system.agents.sentinel import Sentinel
    from system.agents.atlas import Atlas

    for AgentClass in [Atlas, Scout, Forge, Apollo, Hermes, Sentinel]:
        register_agent(AgentClass())

    logger.info("All agents initialized for task worker.")


def process_task(task: dict) -> None:
    """Process a single task."""
    task_id = task["id"]
    to_agent = task["to_agent"]
    task_type = task["task_type"]

    # Skip approval requests (these wait for Leo)
    if to_agent == "LEO" or task.get("status") == "awaiting_approval":
        return

    logger.info(f"Processing task {task_id}: {task_type} -> {to_agent}")
    update_task_status(task_id, "running")

    agent = get_agent_instance(to_agent)
    if not agent:
        logger.error(f"Agent {to_agent} not found for task {task_id}")
        update_task_status(task_id, "failed", error=f"Agent {to_agent} not found")
        return

    try:
        result = agent.handle_task(task)
        update_task_status(task_id, "completed", result=result)
        logger.info(f"Task {task_id} completed: {task_type}")

        # Update agent memory
        agent.remember("last_action", f"Task: {task_type} (completed)")

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        retry_count = task.get("retry_count", 0)

        if retry_count < MAX_RETRIES:
            logger.warning(f"Task {task_id} failed (attempt {retry_count + 1}/{MAX_RETRIES}): {e}")
            # Re-queue with incremented retry count
            from system.db import get_connection
            conn = get_connection()
            conn.execute(
                "UPDATE tasks SET status = 'pending', retry_count = ?, error = ? WHERE id = ?",
                (retry_count + 1, str(e)[:500], task_id),
            )
            conn.commit()
            conn.close()
        else:
            logger.error(f"Task {task_id} failed permanently: {e}")
            update_task_status(task_id, "failed", error=error_msg[:1000])

            # Notify about permanent failure
            agent.notify(f"Task failed after {MAX_RETRIES} attempts: {task_type}\nError: {str(e)[:200]}", level="urgent")


def run_worker():
    """Main worker loop — polls for pending tasks."""
    logger.info("AUROS Task Worker starting...")
    init_db()
    init_agents()

    print("AUROS Task Worker online. Polling for tasks...")

    while True:
        try:
            pending = get_pending_tasks()
            if pending:
                for task in pending:
                    # Skip approval-related tasks
                    if task.get("to_agent") == "LEO":
                        continue
                    process_task(task)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Task Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            time.sleep(30)  # Back off on errors


if __name__ == "__main__":
    run_worker()
