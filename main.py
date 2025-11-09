import os
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

# --- RUTA PRINCIPAL ---
@app.route("/")
def home():
    return "✅ Bot de niveles de agua corriendo y escuchando en Telegram."

# --- HANDLERS DE TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌊 Bot activo. Te avisaré si el nivel de agua no permite navegar.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Podés usar /start para activar las alertas automáticas.")

# --- FUNCIÓN DEL BOT ---
async def iniciar_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_cmd))
    print("🤖 Bot escuchando en Telegram...")
    await app_telegram.run_polling()

# --- EJECUCIÓN PARALELA ---
def run_asyncio_bot():
    asyncio.run(iniciar_bot())

if __name__ == "__main__":
    # Hilo separado para el bot
    bot_thread = threading.Thread(target=run_asyncio_bot)
    bot_thread.start()

    # Mantiene Flask vivo para Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
