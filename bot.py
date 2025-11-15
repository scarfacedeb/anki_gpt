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

def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USER_IDS:
            await update.message.reply_text(f"You are not authorized to use this bot (ID: {user_id}).")
            return

        await func(update, context, *args, **kwargs)
    return wrapper


def generate_word(user_input: str, user_id: int) -> WordList:
    """Generate word definitions using ChatGPT without saving."""
    response = get_definitions(user_input.lower(), user_id)
    return response

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

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().lower()
    user_id = update.effective_user.id

    word_service = WordService()

    # Check if word already exists in database
    existing_word = await asyncio.to_thread(word_service.get, user_input)

    if existing_word:
        # Word found in database - show it without GPT call
        response_text = word_to_html(existing_word)
        await update.message.reply_html(f"📖 Found in database:\n\n{response_text}")
        return

    # Word not found - generate with GPT
    response = generate_word(user_input, user_id)

    if response.context:
        await update.message.reply_text(response.context)

    if not response.words:
        await update.message.reply_text("No words found or could not parse.")
        return

    # Save new words
    for new_word in response.words:
        await asyncio.to_thread(word_service.create, new_word)
        response_text = word_to_html(new_word)
        await update.message.reply_html(f"✅ Added:\n\n{response_text}")

    # Sync with AnkiWeb after processing all words
    await asyncio.to_thread(sync_anki)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_model", set_model))
    app.add_handler(CommandHandler("set_effort", set_effort))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
