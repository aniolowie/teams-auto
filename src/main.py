"""
main.py
Entry point. Runs the Telegram bot that orchestrates the full pipeline:
  /start   - Show help
  /check   - Fetch assignments from Teams and process the first new one
  /list    - List all fetched assignments without processing
  /login   - Force a fresh Teams login (clears saved session)
  /status  - Show current pipeline state

Inline keyboard buttons handle Approve and Redo actions.
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from browser import login_to_teams, fetch_assignments, upload_and_turn_in
from ai_agent import complete_assignment
import os

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory state (single-user bot, so this is fine)
# ---------------------------------------------------------------------------
state = {
    "assignments": [],          # List of assignment dicts from Teams
    "current_index": None,      # Index of assignment currently being processed
    "current_file": None,       # Path to the latest generated draft
    "awaiting_redo": False,     # Whether we are waiting for redo instructions
}


def _auth_check(update: Update) -> bool:
    """Only allow messages from the configured chat ID."""
    return str(update.effective_chat.id) == str(TELEGRAM_CHAT_ID)


def _approval_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Approve & Submit", callback_data="approve"),
            InlineKeyboardButton("Redo", callback_data="redo"),
        ]
    ])


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _auth_check(update):
        return
    text = (
        "Teams Assignment Bot\n\n"
        "/check   - Fetch and process next assignment\n"
        "/list    - List all current assignments\n"
        "/login   - Force fresh Teams login\n"
        "/status  - Show pipeline state"
    )
    await update.message.reply_text(text)


async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _auth_check(update):
        return
    state_file = "/app/data/state.json"
    if os.path.exists(state_file):
        os.remove(state_file)
    await update.message.reply_text("Starting fresh Teams login. This may take up to 60 seconds...")
    try:
        await login_to_teams()
        await update.message.reply_text("Login successful. Session saved.")
    except Exception as e:
        await update.message.reply_text(f"Login failed: {e}")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _auth_check(update):
        return
    await update.message.reply_text("Fetching assignments from Teams...")
    try:
        assignments = await fetch_assignments()
        state["assignments"] = assignments
        if not assignments:
            await update.message.reply_text("No active assignments found.")
            return
        lines = [f"{i+1}. [{a['class_name']}] {a['title']} (due {a['due_date']})"
                 for i, a in enumerate(assignments)]
        await update.message.reply_text("Active assignments:\n\n" + "\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error fetching assignments: {e}")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _auth_check(update):
        return
    await update.message.reply_text("Fetching assignments from Teams...")
    try:
        assignments = await fetch_assignments()
        state["assignments"] = assignments
    except Exception as e:
        await update.message.reply_text(f"Error fetching assignments: {e}")
        return

    if not assignments:
        await update.message.reply_text("No active assignments found.")
        return

    # Process the first assignment
    index = 0
    assignment = assignments[index]
    state["current_index"] = index

    await update.message.reply_text(
        f"Found {len(assignments)} assignment(s). Processing:\n\n"
        f"*{assignment['title']}*\n"
        f"Class: {assignment['class_name']}\n"
        f"Due: {assignment['due_date']}",
        parse_mode="Markdown",
    )

    try:
        file_path = await complete_assignment(assignment)
        state["current_file"] = file_path
    except Exception as e:
        await update.message.reply_text(f"AI completion failed: {e}")
        return

    with open(file_path, "rb") as doc:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=doc,
            filename=os.path.basename(file_path),
            caption="Draft complete. Review and choose an action:",
            reply_markup=_approval_keyboard(),
        )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _auth_check(update):
        return
    idx = state["current_index"]
    assignment = state["assignments"][idx] if idx is not None and state["assignments"] else None
    lines = [
        f"Assignments loaded: {len(state['assignments'])}",
        f"Current assignment: {assignment['title'] if assignment else 'None'}",
        f"Draft file: {state['current_file'] or 'None'}",
        f"Awaiting redo: {state['awaiting_redo']}",
    ]
    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Callback query handler (inline buttons)
# ---------------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not _auth_check(update):
        return

    if query.data == "approve":
        await query.edit_message_caption(caption="Approved! Submitting to Teams...")
        try:
            assignment = state["assignments"][state["current_index"]]
            await upload_and_turn_in(state["current_file"], assignment["id"])
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Assignment submitted successfully.",
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Submission failed: {e}",
            )

    elif query.data == "redo":
        state["awaiting_redo"] = True
        await query.edit_message_caption(
            caption="Redo requested. Reply with your specific instructions or feedback."
        )


# ---------------------------------------------------------------------------
# Free-text message handler (for redo instructions)
# ---------------------------------------------------------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _auth_check(update):
        return
    if not state["awaiting_redo"]:
        return

    state["awaiting_redo"] = False
    instructions = update.message.text
    assignment = state["assignments"][state["current_index"]]

    await update.message.reply_text(f"Redoing with your feedback: \"{instructions}\"")

    try:
        file_path = await complete_assignment(assignment, extra_instructions=instructions)
        state["current_file"] = file_path
    except Exception as e:
        await update.message.reply_text(f"AI redo failed: {e}")
        return

    with open(file_path, "rb") as doc:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=doc,
            filename=os.path.basename(file_path),
            caption="Revised draft ready. Review and choose an action:",
            reply_markup=_approval_keyboard(),
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot started. Polling for updates...")
    app.run_polling()


if __name__ == "__main__":
    main()
