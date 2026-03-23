#!/usr/bin/env python3
"""
AUROS AI — Scheduler
Triggers recurring agent tasks on a cron schedule.
Uses APScheduler for reliable, timezone-aware scheduling.

Run:
    python -m system.scheduler
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from system.db import init_db, create_task, get_active_schedules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "scheduler.log"),
    ],
)
logger = logging.getLogger("auros.scheduler")


def queue_task(agent: str, task_type: str, payload: dict | None = None) -> None:
    """Create a task in the queue for the worker to pick up."""
    task_id = create_task(
        from_agent="SCHEDULER",
        to_agent=agent,
        task_type=task_type,
        payload=payload,
        priority=3,  # Scheduled tasks are medium priority
    )
    logger.info(f"Scheduled task queued: {task_type} -> {agent} (id: {task_id})")


def setup_default_schedules(scheduler: BlockingScheduler) -> None:
    """Set up the default AUROS recurring schedules."""

    # SCOUT: Daily intelligence scan — every day at 7:00 AM
    scheduler.add_job(
        queue_task,
        CronTrigger(hour=7, minute=0),
        args=["SCOUT", "daily_scan"],
        id="scout_daily_scan",
        name="SCOUT Daily Intelligence Scan",
        replace_existing=True,
    )

    # HERMES: Daily newsletter — every day at 7:30 AM
    scheduler.add_job(
        queue_task,
        CronTrigger(hour=7, minute=30),
        args=["HERMES", "send_newsletter"],
        id="hermes_newsletter",
        name="HERMES Daily Newsletter",
        replace_existing=True,
    )

    # SCOUT: Market analysis — Mon, Wed, Fri at 8:00 AM
    scheduler.add_job(
        queue_task,
        CronTrigger(day_of_week="mon,wed,fri", hour=8, minute=0),
        args=["SCOUT", "deep_research", {"query": "AI marketing industry latest developments"}],
        id="scout_market_analysis",
        name="SCOUT Market Analysis (M/W/F)",
        replace_existing=True,
    )

    # SENTINEL: Daily performance check — every day at 6:00 PM
    scheduler.add_job(
        queue_task,
        CronTrigger(hour=18, minute=0),
        args=["SENTINEL", "daily_check"],
        id="sentinel_daily_check",
        name="SENTINEL Daily Performance Check",
        replace_existing=True,
    )

    # SENTINEL: System health — every day at 9:00 AM
    scheduler.add_job(
        queue_task,
        CronTrigger(hour=9, minute=0),
        args=["SENTINEL", "system_health"],
        id="sentinel_system_health",
        name="SENTINEL System Health Check",
        replace_existing=True,
    )

    # ATLAS: Daily briefing — every day at 8:30 AM
    scheduler.add_job(
        queue_task,
        CronTrigger(hour=8, minute=30),
        args=["ATLAS", "daily_briefing"],
        id="atlas_daily_briefing",
        name="ATLAS Daily Briefing",
        replace_existing=True,
    )

    logger.info("Default schedules configured.")


def load_custom_schedules(scheduler: BlockingScheduler) -> None:
    """Load any custom schedules from the database."""
    schedules = get_active_schedules()
    for sched in schedules:
        try:
            parts = sched["cron_expression"].split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
                payload = sched.get("payload", {})
                if isinstance(payload, str):
                    import json
                    payload = json.loads(payload)

                scheduler.add_job(
                    queue_task,
                    trigger,
                    args=[sched["agent"], sched["task_type"], payload],
                    id=f"custom_{sched['id']}",
                    name=f"Custom: {sched['agent']} {sched['task_type']}",
                    replace_existing=True,
                )
                logger.info(f"Loaded custom schedule: {sched['agent']} {sched['task_type']} ({sched['cron_expression']})")
        except Exception as e:
            logger.error(f"Failed to load schedule {sched['id']}: {e}")


def main() -> None:
    """Start the scheduler."""
    init_db()

    scheduler = BlockingScheduler()

    # Set up schedules
    setup_default_schedules(scheduler)
    load_custom_schedules(scheduler)

    # List all jobs
    jobs = scheduler.get_jobs()
    print(f"AUROS Scheduler online. {len(jobs)} jobs configured:")
    for job in jobs:
        print(f"  {job.name}: next run at {job.next_run_time}")

    logger.info(f"Scheduler starting with {len(jobs)} jobs")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
