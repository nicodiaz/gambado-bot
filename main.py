import os
import asyncio
import threading
import nest_asyncio
import requests
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

# --- CONFIGURACIÓN ---
UMBRAL_BAJO = 0.45   # metros - nivel mínimo para navegar
UMBRAL_ALTO = 0.75   # metros - nivel alto (opcional)
URL_SHN = "https://www.hidro.gov.ar/oceanografia/alturashorarias.asp"

@app.route("/")
def home():
    return "✅ Bot de niveles de agua corriendo y monitoreando el Arroyo Gambado (San Fernando)."

# --- FUNCIÓN PARA OBTENER NIVEL ACTUAL ---
def obtener_nivel_san_fernando():
    try:
        response = requests.get(URL_SHN, timeout=10)
        response.raise_for_status()
        texto = response.text

        # Buscamos el valor de San Fernando en la tabla HTML
        # La página del SHN tiene el formato "San Fernando" seguido de valores horarios
        if "San Fernando" in texto:
            seccion = texto.split("San Fernando")[1][:300]  # corto cerca de 300 chars después
            # Busco números tipo 1.23 o 0.56 (altura en metros)
            import re
            match = re.search(r"(\d+\.\d+)", seccion)
            if match:
                return float(match.group(1))
        return None
    except Exception as e:
        print(f"⚠️ Error obteniendo nivel: {e}")
        return None

# --- COMANDOS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌊 Bot activo.\nTe avisaré si el nivel del agua está demasiado bajo para navegar."
    )

async def nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nivel_actual = obtener_nivel_san_fernando()
    if nivel_actual is None:
        await update.message.reply_text("⚠️ No pude obtener el nivel actual del agua.")
    else:
        mensaje = f"📍 Nivel actual San Fernando: {nivel_actual:.2f} m"
        if nivel_actual < UMBRAL_BAJO:
            mensaje += "\n🚨 Nivel bajo, no se recomienda navegar."
        elif nivel_actual > UMBRAL_ALTO:
            mensaje += "\n🌊 Nivel alto, precaución."
        else:
            mensaje += "\n✅ Nivel normal, navegación posible."
        await update.message.reply_text(mensaje)

# --- ALERTAS AUTOMÁTICAS ---
async def verificar_nivel_periodicamente(bot):
    while True:
        try:
            nivel_actual = obtener_nivel_san_fernando()
            if nivel_actual is not None:
                print(f"[{datetime.now().strftime('%H:%M')}] Nivel: {nivel_actual} m")
                if nivel_actual < UMBRAL_BAJO:
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"🚨 Nivel bajo detectado ({nivel_actual:.2f} m). No conviene salir 🚤"
                    )
            await asyncio.sleep(3600)  # verifica cada 1 hora
        except Exception as e:
            print(f"Error en verificación: {e}")
            await asyncio.sleep(600)  # si hay error, reintenta en 10 min

# --- INICIO DEL BOT ---
async def iniciar_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("nivel", nivel))

    # Tarea paralela de monitoreo
    asyncio.create_task(verificar_nivel_periodicamente(app_telegram.bot))

    print("🤖 Bot escuchando en Telegram y monitoreando niveles...")
    await app_telegram.run_polling(stop_signals=None)

def run_bot():
    asyncio.run(iniciar_bot())

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
