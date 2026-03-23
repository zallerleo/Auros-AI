#!/usr/bin/env python3
"""
AUROS AI — Telegram Bot
Leo's mobile interface to the agent team.
All messages go through ATLAS for routing.

Setup:
1. Talk to @BotFather on Telegram, create a new bot, get the token
2. Get your Telegram user ID (message @userinfobot)
3. Add to .env:
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_USER_ID=your_numeric_id

Run:
    python -m system.telegram_bot
"""

from __future__ import annotations

import sys
import os
import logging
import asyncio
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from system.db import init_db, get_awaiting_approval, update_task_status, get_task
from system.agents.atlas import Atlas, register_agent, get_all_agents

# Import department heads
from system.agents.scout import Scout
from system.agents.forge import Forge
from system.agents.apollo import Apollo
from system.agents.hermes import Hermes
from system.agents.sentinel import Sentinel
from system.agents.prospector import Prospector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "telegram_bot.log"),
    ],
)
logger = logging.getLogger("auros.telegram")

# Config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))

# The bot instance (for sending proactive messages)
_app: Application | None = None


# ---------------------------------------------------------------------------
# Notification callback (used by agents to message Leo)
# ---------------------------------------------------------------------------

async def _send_notification_async(message: str, level: str = "info") -> None:
    """Send a notification to Leo via Telegram."""
    if not _app or not ALLOWED_USER_ID:
        logger.warning(f"Cannot send notification (no app/user): {message}")
        return

    try:
        if level == "approval":
            # Send with inline buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Approve", callback_data="approve_latest"),
                    InlineKeyboardButton("Reject", callback_data="reject_latest"),
                ]
            ])
            await _app.bot.send_message(
                chat_id=ALLOWED_USER_ID,
                text=message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            await _app.bot.send_message(
                chat_id=ALLOWED_USER_ID,
                text=message,
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def send_notification(message: str, level: str = "info") -> None:
    """Sync wrapper for sending notifications (called by agents)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send_notification_async(message, level))
    except RuntimeError:
        # No running loop — create one
        asyncio.run(_send_notification_async(message, level))


# ---------------------------------------------------------------------------
# Security: only Leo can talk to the bot
# ---------------------------------------------------------------------------

def authorized(func):
    """Decorator to restrict bot access to Leo only."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else 0
        if user_id != ALLOWED_USER_ID:
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            if update.message:
                await update.message.reply_text("Access denied. This bot is private.")
            return
        return await func(update, context)
    return wrapper


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any text message or command from Leo — route through ATLAS."""
    if not update.message or not update.message.text:
        return

    message = update.message.text
    logger.info(f"Leo: {message}")

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        atlas = get_all_agents().get("ATLAS")
        if not atlas:
            await update.message.reply_text("ATLAS is not initialized. System error.")
            return

        response = atlas.handle_message(message, context={"source": "telegram"})

        # Save conversation
        atlas.save_conversation(message, response, telegram_msg_id=update.message.message_id)

        # Send response — try Markdown first, fall back to plain text
        await _send_response(update, response)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(f"Something went wrong: {str(e)[:200]}")


async def _send_response(update: Update, response: str) -> None:
    """Send a response, splitting long messages and handling Markdown errors."""
    chunks = [response[i:i+4000] for i in range(0, len(response), 4000)] if len(response) > 4000 else [response]

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            # Markdown parse failed — send as plain text
            await update.message.reply_text(chunk)


@authorized
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "*Welcome back, Leo.*\n\n"
        "Your AUROS agent team is online.\n\n"
        "Commands:\n"
        "/status — System overview\n"
        "/brief — Daily briefing\n"
        "/approve — Pending approvals\n"
        "/agents — Agent roster\n\n"
        "Or just message me naturally — I'll route it to the right agent.",
        parse_mode="Markdown",
    )


@authorized
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses (approve/reject)."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("approve_"):
        task_id = data.replace("approve_", "")
        if task_id == "latest":
            # Find the most recent awaiting approval
            approvals = get_awaiting_approval()
            if approvals:
                task_id = approvals[0]["id"]
            else:
                await query.edit_message_text("No pending approvals.")
                return

        task = get_task(task_id)
        if task and task["status"] == "awaiting_approval":
            update_task_status(task_id, "pending")  # Re-queue for execution
            payload = task.get("payload", {})
            desc = payload.get("description", task["task_type"]) if isinstance(payload, dict) else task["task_type"]
            await query.edit_message_text(f"Approved: {desc}\nQueued for execution.")
        else:
            await query.edit_message_text(f"Task {task_id} not found or already handled.")

    elif data.startswith("reject_"):
        task_id = data.replace("reject_", "")
        if task_id == "latest":
            approvals = get_awaiting_approval()
            if approvals:
                task_id = approvals[0]["id"]
            else:
                await query.edit_message_text("No pending approvals.")
                return

        task = get_task(task_id)
        if task:
            update_task_status(task_id, "rejected")
            await query.edit_message_text(f"Rejected: {task['task_type']}")
        else:
            await query.edit_message_text(f"Task {task_id} not found.")


# ---------------------------------------------------------------------------
# Bot initialization
# ---------------------------------------------------------------------------

def init_agents() -> None:
    """Initialize and register all department head agents."""
    notifier = send_notification

    atlas = Atlas(notifier=notifier)
    scout = Scout(notifier=notifier)
    forge = Forge(notifier=notifier)
    apollo = Apollo(notifier=notifier)
    hermes = Hermes(notifier=notifier)
    sentinel = Sentinel(notifier=notifier)
    prospector = Prospector(notifier=notifier)

    register_agent(atlas)
    register_agent(scout)
    register_agent(forge)
    register_agent(apollo)
    register_agent(hermes)
    register_agent(sentinel)
    register_agent(prospector)

    logger.info(f"Initialized {len(get_all_agents())} agents: {', '.join(get_all_agents().keys())}")


def main() -> None:
    """Start the Telegram bot."""
    global _app

    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("1. Talk to @BotFather on Telegram")
        print("2. Create a new bot")
        print("3. Add TELEGRAM_BOT_TOKEN=<token> to your .env file")
        sys.exit(1)

    if not ALLOWED_USER_ID:
        print("ERROR: TELEGRAM_USER_ID not set in .env")
        print("1. Message @userinfobot on Telegram")
        print("2. It will tell you your numeric user ID")
        print("3. Add TELEGRAM_USER_ID=<id> to your .env file")
        sys.exit(1)

    # Initialize database
    init_db()

    # Initialize agents
    init_agents()

    # Build the bot
    _app = Application.builder().token(BOT_TOKEN).build()

    # Register handlers — commands and general messages all route through ATLAS
    _app.add_handler(CommandHandler("start", handle_start))
    _app.add_handler(CommandHandler("status", handle_message))
    _app.add_handler(CommandHandler("brief", handle_message))
    _app.add_handler(CommandHandler("approve", handle_message))
    _app.add_handler(CommandHandler("reject", handle_message))
    _app.add_handler(CommandHandler("agents", handle_message))
    _app.add_handler(CallbackQueryHandler(handle_callback))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("AUROS Telegram Bot starting...")
    logger.info(f"Authorized user: {ALLOWED_USER_ID}")
    print(f"AUROS Agent Team online. Authorized user: {ALLOWED_USER_ID}")

    # Run the bot
    _app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
