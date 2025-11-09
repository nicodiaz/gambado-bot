import os
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask

# --- Configuración segura ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))  # configurado en Render como variable de entorno
PORT = int(os.getenv("PORT", 10000))

# --- Estación INA Puerto de Tigre ---
INA_API_URL = "https://alerta.ina.gob.ar/api/levels/PUERTODETIGRE"

# --- Umbral de alerta ---
ALERTA_UMBRAL = 0.8

# --- Función para obtener el nivel del agua ---
async def obtener_nivel():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(INA_API_URL, timeout=10) as response:
                if response.status != 200:
                    return None, None
                data = await response.json()

                # El valor más reciente está en data["values"][-1]
                valores = data.get("values", [])
                if not valores:
                    return None, None

                ultimo = valores[-1]
                nivel = ultimo.get("value")
                fecha = datetime.fromisoformat(ultimo.get("timestamp").replace("Z", "+00:00"))
                return nivel, fecha
        except Exception as e:
            print(f"Error obteniendo nivel: {e}")
            return None, None

# --- Evaluar nivel ---
def interpretar_nivel(nivel: float) -> str:
    if nivel < 0.8:
        return "🚫 Nivel bajo — posible dificultad para navegar el Gambado."
    elif nivel < 1.2:
        return "🚤 Navegable con precaución."
    else:
        return "🌊 Nivel normal — navegación sin problemas."

# --- Comando /nivel ---
async def comando_nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nivel, fecha = await obtener_nivel()
    if nivel is None:
        await update.message.reply_text("No pude obtener el nivel actual del agua 😔")
        return

    info = interpretar_nivel(nivel)
    fecha_local = fecha.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    mensaje = f"📍 *Puerto de Tigre (INA)*\nNivel actual: *{nivel:.2f} m*\n{info}\nÚltima actualización: {fecha_local}"
    await update.message.reply_markdown(mensaje)

# --- Tarea automática de verificación ---
async def monitorear_nivel(app):
    await app.bot.send_message(chat_id=CHAT_ID, text="🤖 Bot de nivel del Gambado iniciado correctamente.")
    while True:
        nivel, fecha = await obtener_nivel()
        if nivel is not None and nivel < ALERTA_UMBRAL:
            info = interpretar_nivel(nivel)
            fecha_local = fecha.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
            mensaje = f"🚨 *Alerta de nivel bajo*\nNivel actual: *{nivel:.2f} m*\n{info}\nHora: {fecha_local}"
            await app.bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="Markdown")
        await asyncio.sleep(1800)  # cada 30 minutos

# --- Flask (para Render) ---
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot de nivel del Gambado corriendo correctamente."

# --- Iniciar bot ---
async def main():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("nivel", comando_nivel))

    asyncio.create_task(monitorear_nivel(app_telegram))
    await app_telegram.run_polling()

# --- Ejecutar todo ---
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app_flask.run(host="0.0.0.0", port=PORT)).start()
    asyncio.run(main())
