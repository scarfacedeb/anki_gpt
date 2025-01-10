import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from chatgpt import get_definitions
from anki import add_notes, sync_anki
from word import Word, word_to_html

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
            await update.message.reply_text("You are not authorized to use this bot (ID: {user_id}.")
            return

        await func(update, context, *args, **kwargs)
    return wrapper


def add_word_to_anki(user_input: str) -> list[Word]:
    words = get_definitions(user_input.lower()).words

    if words:
        add_notes(words)

    sync_anki()

    return words


@authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!"
    )

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    words = add_word_to_anki(user_input)

    if words:
        user = update.effective_user
        for w in words:
            response_text = word_to_html(w)
            await update.message.reply_html(response_text)
    else:
        await update.message.reply_text("No words found or could not parse.")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
