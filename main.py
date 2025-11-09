import os
import requests
import time
import datetime
from flask import Flask
from threading import Thread
from telegram import Bot

# === CONFIGURACIÓN ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

UMBRAL_BAJO = 0.45
UMBRAL_PRECAUCION = 0.75

# Flask app para mantener activo Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot del Arroyo Gambado funcionando 🌊"

def obtener_nivel():
    try:
        import random
        nivel = round(random.uniform(0.3, 1.2), 2)
        tendencia = "subiendo" if random.choice([True, False]) else "bajando"
        return nivel, tendencia
    except Exception as e:
        print("Error al obtener nivel:", e)
        return None, None

def evaluar_navegabilidad(nivel):
    if nivel < UMBRAL_BAJO:
        return "🔴 Nivel muy bajo. No navegues."
    elif UMBRAL_BAJO <= nivel < UMBRAL_PRECAUCION:
        return "🟡 Nivel bajo-medio. Navegable con precaución."
    else:
        return "🟢 Nivel óptimo. Marea favorable."

def enviar_mensaje(texto):
    try:
        bot.send_message(chat_id=CHAT_ID, text=texto)
    except Exception as e:
        print("Error al enviar mensaje:", e)

def bucle_principal():
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
                enviar_mensaje(mensaje)
                ultimo_estado = estado
        time.sleep(3600)  # cada hora

def iniciar_bot():
    enviar_mensaje("🤖 Bot del Arroyo Gambado iniciado correctamente.")
    bucle_principal()

if __name__ == "__main__":
    Thread(target=iniciar_bot).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
