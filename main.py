import os
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

# Ruta base para que Render confirme que está activo
@app.route("/")
def home():
    return "Bot de niveles de agua corriendo ✅"

# Comando /start en Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌊 Bot activo. Te avisaré si el nivel de agua no permite navegar.")

# Notificación de ejemplo
async def enviar_alerta():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    await app_telegram.bot.send_message(
        chat_id=CHAT_ID,
        text="🚤 Alerta automática: el nivel de agua está bajo, no conviene salir."
    )

async def run_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    await app_telegram.run_polling()

def main():
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    main()
