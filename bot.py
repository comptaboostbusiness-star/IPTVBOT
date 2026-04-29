from urllib.parse import urlparse, parse_qs
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def parse_m3u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        parsed = urlparse(text)
        query = parse_qs(parsed.query)

        username = query.get("username", [""])[0]
        password = query.get("password", [""])[0]
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        response = f"""Username: {username}
Password: {password}
Host: {host}
Port: {port}
"""
        await update.message.reply_text(response)

    except:
        await update.message.reply_text("Erreur")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, parse_m3u))

app.run_polling()
