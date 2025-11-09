import os
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot de niveles de agua corriendo y escuchando en Telegram."

# --- Comandos del bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌊 Bot activo. Te avisaré si el nivel de agua no permite navegar.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usá /start para activar las alertas automáticas.")

# --- Lógica del bot ---
async def iniciar_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_cmd))
    print("🤖 Bot escuchando en Telegram...")
    # 🟢 Evita los errores de 'set_wakeup_fd' en hilo secundario
    await app_telegram.run_polling(stop_signals=None)

# --- Hilo separado para el bot ---
def run_asyncio_bot():
    asyncio.run(iniciar_bot())

if __name__ == "__main__":
    # Inicia el bot en un hilo aparte
    bot_thread = threading.Thread(target=run_asyncio_bot, daemon=True)
    bot_thread.start()

    # Mantiene Flask activo (Render lo necesita)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
