import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import asyncio

from chatgpt import get_definitions
from anki import sync_anki
from word import Word, word_to_html, WordList
from user_settings import get_user_config, set_user_model, set_user_effort, ALLOWED_MODELS, ALLOWED_EFFORTS
from word_service import WordService

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")
ALLOWED_USER_IDS = set(map(int, os.getenv("ALLOWED_USER_IDS", "").split(",")))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

DELETE_WORD_CALLBACK_PREFIX = "delete_word:"
REGENERATE_WORD_CALLBACK_PREFIX = "regenerate_word:"

def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USER_IDS:
            if update.callback_query:
                await update.callback_query.answer(
                    f"You are not authorized to use this bot (ID: {user_id}).",
                    show_alert=True,
                )
            elif update.message:
                await update.message.reply_text(f"You are not authorized to use this bot (ID: {user_id}).")
            return

        await func(update, context, *args, **kwargs)
    return wrapper


def generate_word(user_input: str, user_id: int, effort_override: str | None = None) -> WordList:
    """Generate word definitions using ChatGPT without saving."""
    response = get_definitions(user_input, user_id, effort_override=effort_override)
    return response

def higher_effort(effort: str) -> str:
    """Return the next higher reasoning effort, capped at the maximum."""
    try:
        effort_index = ALLOWED_EFFORTS.index(effort)
    except ValueError:
        effort_index = ALLOWED_EFFORTS.index("medium")

    return ALLOWED_EFFORTS[min(effort_index + 1, len(ALLOWED_EFFORTS) - 1)]

def word_actions_keyboard(word_id: int | None) -> InlineKeyboardMarkup | None:
    """Build inline actions for a saved word."""
    if word_id is None:
        return None

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Regenerate higher", callback_data=f"{REGENERATE_WORD_CALLBACK_PREFIX}{word_id}"),
            InlineKeyboardButton("Delete word", callback_data=f"{DELETE_WORD_CALLBACK_PREFIX}{word_id}"),
        ]
    ])

async def reply_word(update: Update, prefix: str, word: Word, word_id: int | None):
    """Reply with a word definition and its Telegram actions."""
    await reply_word_message(update.message, prefix, word, word_id)


async def reply_word_message(message, prefix: str, word: Word, word_id: int | None):
    """Reply to a Telegram message with a word definition and its actions."""
    response_text = word_to_html(word)
    await message.reply_html(
        f"{prefix}\n\n{response_text}",
        reply_markup=word_actions_keyboard(word_id),
    )

@authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Available commands:\n"
        rf"/set_model - Set OpenAI model\n"
        rf"/set_effort - Set reasoning effort\n"
        rf"/settings - View current settings"
    )

@authorized
async def set_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = get_user_config(user_id)

    keyboard = []
    for model in ALLOWED_MODELS:
        current_marker = "✅ " if model == config.model else ""
        keyboard.append([InlineKeyboardButton(f"{current_marker}{model}", callback_data=f"model_{model}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Current model: {config.model}\n\nSelect a new model:",
        reply_markup=reply_markup
    )

@authorized
async def set_effort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = get_user_config(user_id)

    keyboard = []
    for effort in ALLOWED_EFFORTS:
        current_marker = "✅ " if effort == config.effort else ""
        keyboard.append([InlineKeyboardButton(f"{current_marker}{effort}", callback_data=f"effort_{effort}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Current effort: {config.effort}\n\nSelect a new effort level:",
        reply_markup=reply_markup
    )

@authorized
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = get_user_config(user_id)

    await update.message.reply_text(f"Current settings:\nModel: {config.model}\nEffort: {config.effort}")

@authorized
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if data.startswith("model_"):
        model = data.replace("model_", "")
        if set_user_model(user_id, model):
            await query.edit_message_text(f"✅ Model set to: {model}")
        else:
            await query.edit_message_text(f"❌ Failed to set model")

    elif data.startswith("effort_"):
        effort = data.replace("effort_", "")
        if set_user_effort(user_id, effort):
            await query.edit_message_text(f"✅ Reasoning effort set to: {effort}")
        else:
            await query.edit_message_text(f"❌ Failed to set effort level")

    elif data.startswith(DELETE_WORD_CALLBACK_PREFIX):
        word_id_text = data.removeprefix(DELETE_WORD_CALLBACK_PREFIX)
        try:
            word_id = int(word_id_text)
        except ValueError:
            await query.edit_message_text("❌ Could not delete word: invalid word ID.")
            return

        word_service = WordService()
        word = await asyncio.to_thread(word_service.get_by_id, word_id)
        if not word:
            await query.edit_message_text("Word was already deleted.")
            return

        db_deleted, anki_deleted = await asyncio.to_thread(word_service.delete_by_id, word_id)
        if db_deleted:
            anki_text = ""
            if anki_deleted is True:
                anki_text = " Anki note deleted too."
            elif anki_deleted is False:
                anki_text = " Anki note could not be deleted."
            await query.edit_message_text(f"Deleted word: {word.dutch}.{anki_text}")
        else:
            await query.edit_message_text(f"❌ Failed to delete word: {word.dutch}")

    elif data.startswith(REGENERATE_WORD_CALLBACK_PREFIX):
        word_id_text = data.removeprefix(REGENERATE_WORD_CALLBACK_PREFIX)
        try:
            word_id = int(word_id_text)
        except ValueError:
            await query.edit_message_text("❌ Could not regenerate word: invalid word ID.")
            return

        word_service = WordService()
        existing_word = await asyncio.to_thread(word_service.get_by_id, word_id)
        if not existing_word:
            await query.edit_message_text("Word was already deleted.")
            return

        effort = higher_effort(get_user_config(user_id).effort)
        await query.edit_message_text(f"Regenerating {existing_word.dutch} with {effort} reasoning...")

        response = await asyncio.to_thread(generate_word, existing_word.dutch, user_id, effort)
        if not response.words:
            await query.edit_message_text(f"❌ Could not regenerate word: {existing_word.dutch}")
            return

        regenerated_word = response.words[0]
        await asyncio.to_thread(word_service.update_by_id, word_id, regenerated_word)
        await asyncio.to_thread(sync_anki)

        response_text = word_to_html(regenerated_word)
        await query.edit_message_text(
            f"✅ Regenerated with {effort} reasoning:\n\n{response_text}",
            parse_mode="HTML",
            reply_markup=word_actions_keyboard(word_id),
        )

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    user_id = update.effective_user.id

    word_service = WordService()

    # Check if word already exists in database
    existing_word = await asyncio.to_thread(word_service.get, user_input)

    if existing_word:
        # Word found in database - show it without GPT call
        word_id = await asyncio.to_thread(word_service.get_id, user_input)
        await reply_word(update, "📖 Found in database:", existing_word, word_id)
        return

    status_message = await update.message.reply_text(f"Generating: {user_input}")
    context.application.create_task(
        process_new_word(update.message, status_message, user_input, user_id)
    )


async def process_new_word(message, status_message, user_input: str, user_id: int):
    """Generate, save, and sync a new word after the handler has returned."""
    word_service = WordService()

    try:
        # Word not found - generate with GPT
        response = await asyncio.to_thread(generate_word, user_input, user_id)

        if response.context:
            await message.reply_text(response.context)

        if not response.words:
            await status_message.edit_text("No words found or could not parse.")
            return

        await status_message.edit_text(f"Saving {len(response.words)} word(s)...")

        # Save new words
        for new_word in response.words:
            await asyncio.to_thread(word_service.create, new_word)
            word_id = await asyncio.to_thread(word_service.get_id, new_word.dutch)
            await reply_word_message(message, "✅ Added:", new_word, word_id)

        await status_message.edit_text("Syncing with AnkiWeb...")
        await asyncio.to_thread(sync_anki)
        await status_message.edit_text("Done.")
    except Exception as e:
        logging.exception("Failed to process Telegram word request")
        await status_message.edit_text(f"❌ Failed to process word: {e}")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_model", set_model))
    app.add_handler(CommandHandler("set_effort", set_effort))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
