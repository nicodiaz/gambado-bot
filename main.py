import os
import requests
import time
import datetime
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIGURACIÓN ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

UMBRAL_BAJO = 0.45
UMBRAL_PRECAUCION = 0.75

# === Flask para mantener Render activo ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot del Arroyo Gambado funcionando 🌊"

# === Lógica de mareas (simulada por ahora) ===
def obtener_nivel():
    import random
    nivel = round(random.uniform(0.3, 1.2), 2)
    tendencia = "subiendo" if random.choice([True, False]) else "bajando"
    return nivel, tendencia

def evaluar_navegabilidad(nivel):
    if nivel < UMBRAL_BAJO:
        return "🔴 Nivel muy bajo. No navegues."
    elif UMBRAL_BAJO <= nivel < UMBRAL_PRECAUCION:
        return "🟡 Nivel bajo-medio. Navegable con precaución."
    else:
        return "🟢 Nivel óptimo. Marea favorable."

async def enviar_mensaje(app, texto):
    try:
        await app.bot.send_message(chat_id=CHAT_ID, text=texto)
    except Exception as e:
        print("Error al enviar mensaje:", e)

async def bucle_mareas(app):
    ultimo_estado = None
    while True:
        nivel, tendencia = obtener_nivel()
        if nivel:
            estado = evaluar_navegabilidad(nivel)
            ahora = datetime.datetime.now().strftime("%H:%M")
            mensaje = (
                f"🌊 Arroyo Gambado – {ahora}\n"
                f"Nivel San Fernando: {nivel} m {'📈' if tendencia == 'subiendo' else '📉'} ({tendencia})\n"
                f"Estado: {estado}"
            )
            if estado != ultimo_estado or datetime.datetime.now().hour % 3 == 0:
                await enviar_mensaje(app, mensaje)
                ultimo_estado = estado
        await asyncio.sleep(3600)  # cada hora

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

# === Iniciar bot ===
import asyncio

async def iniciar_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("nivel", nivel_command))
    await enviar_mensaje(app_telegram, "🤖 Bot del Arroyo Gambado iniciado correctamente.")
    asyncio.create_task(bucle_mareas(app_telegram))
    await app_telegram.run_polling()

def run_asyncio_bot():
    asyncio.run(iniciar_bot())

if __name__ == "__main__":
    Thread(target=run_asyncio_bot).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
