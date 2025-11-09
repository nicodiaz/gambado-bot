import os
import asyncio
import datetime
import random
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIGURACIÓN ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
UMBRAL_BAJO = 0.45
UMBRAL_PRECAUCION = 0.75

# === Servidor Flask (para mantener activo Render) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot del Arroyo Gambado funcionando 🌊"

# === Funciones de lógica ===
def obtener_nivel():
    nivel = round(random.uniform(0.3, 1.2), 2)
    tendencia = random.choice(["subiendo", "bajando"])
    return nivel, tendencia

def evaluar_navegabilidad(nivel):
    if nivel < UMBRAL_BAJO:
        return "🔴 Nivel muy bajo. No navegues."
    elif nivel < UMBRAL_PRECAUCION:
        return "🟡 Nivel bajo-medio. Navegable con precaución."
    else:
        return "🟢 Nivel óptimo. Marea favorable."

# === Comando manual /nivel ===
async def nivel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nivel, tendencia = obtener_nivel()
    estado = evaluar_navegabilidad(nivel)
    mensaje = (
        f"🌊 Arroyo Gambado\n"
        f"Nivel actual: {nivel} m {'📈' if tendencia == 'subiendo' else '📉'} ({tendencia})\n"
        f"Estado: {estado}"
    )
    await update.message.reply_text(mensaje)

# === Bucle automático ===
async def bucle_mareas(app):
    ultimo_estado = None
    while True:
        nivel, tendencia = obtener_nivel()
        estado = evaluar_navegabilidad(nivel)
        ahora = datetime.datetime.now().strftime("%H:%M")
        mensaje = (
            f"🌊 Arroyo Gambado – {ahora}\n"
            f"Nivel San Fernando: {nivel} m {'📈' if tendencia == 'subiendo' else '📉'} ({tendencia})\n"
            f"Estado: {estado}"
        )
        if estado != ultimo_estado or datetime.datetime.now().hour % 3 == 0:
            await app.bot.send_message(chat_id=CHAT_ID, text=mensaje)
            ultimo_estado = estado
        await asyncio.sleep(3600)  # cada hora

# === Iniciar bot ===
async def iniciar_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("nivel", nivel_command))
    await app_telegram.bot.send_message(chat_id=CHAT_ID, text="🤖 Bot del Arroyo Gambado iniciado correctamente.")
    asyncio.create_task(bucle_mareas(app_telegram))
    await app_telegram.run_polling()

def run_asyncio_bot():
    asyncio.run(iniciar_bot())

if __name__ == "__main__":
    import time
    time.sleep(5)  # espera breve para Render
    Thread(target=run_asyncio_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
