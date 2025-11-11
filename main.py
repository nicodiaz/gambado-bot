import os
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]  # envía logs al output de Render
)
logger = logging.getLogger(__name__)

# --- Configuración segura ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))  # configurado en Render como variable de entorno
PORT = int(os.getenv("PORT", 10000))

# --- Estación SHN San Fernando ---
# código de mareógrafo que encontraste: SFER
MAREOGRAFO = "SFER"

# --- Umbral de alerta (ajustá a tu lancha) ---
ALERTA_UMBRAL = float(os.getenv("ALERTA_UMBRAL"))  # metros aprox

# --- Flask (para Render) ---
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot de nivel del Gambado corriendo correctamente."

# --------------------------------------------------------------------------
# 1) OBTENER NIVEL DESDE SHN
# --------------------------------------------------------------------------
async def obtener_nivel():
    """
    Llama a la API del SHN:
    https://www.hidro.gob.ar/api/v1/AlturasHorarias/SFER/YYYYMMDDHHMM
    Devuelve (nivel_en_m, fecha_datetime) o (None, None)
    """
    ahora_ar = datetime.utcnow() - timedelta(hours=3)
    fecha_str = ahora_ar.strftime("%Y%m%d%H%M")
    url = f"https://www.hidro.gob.ar/api/v1/AlturasHorarias/{MAREOGRAFO}/{fecha_str}"

    for intento in range(2):  # reintenta una vez
        try:
            timeout = aiohttp.ClientTimeout(total=35)  # ⏱️ más margen
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, ssl=False) as response:
                    logger.info(f"[{intento+1}] Llamando a {url} ... status={response.status}")

                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} en intento {intento+1}")
                        if intento == 0:
                            # reintento 30 min antes por si la hora exacta no tiene lectura
                            ahora_ar -= timedelta(minutes=30)
                            fecha_str = ahora_ar.strftime("%Y%m%d%H%M")
                            url = f"https://www.hidro.gob.ar/api/v1/AlturasHorarias/{MAREOGRAFO}/{fecha_str}"
                        await asyncio.sleep(2)
                        continue

                    # leemos como texto y parseamos JSON manualmente (más robusto)
                    text = await response.text()
                    data = await asyncio.to_thread(lambda: __import__('json').loads(text))

                    lecturas = data.get("lecturas", [])
                    if not lecturas:
                        logger.warning("Respuesta sin lecturas.")
                        return None, None

                    ultima = lecturas[-1]
                    nivel = ultima.get("altura")
                    fecha_str_json = ultima.get("fecha")
                    fecha_dt = datetime.fromisoformat(fecha_str_json)

                    logger.info(f"Nivel obtenido: {nivel} m a las {fecha_dt}")
                    return float(nivel), fecha_dt

        except asyncio.TimeoutError:
            logger.warning(f"Timeout al consultar {url} (intento {intento+1})")
            await asyncio.sleep(2)
        except Exception as e:
            logger.exception(f"Error obteniendo nivel desde SHN (intento {intento+1}): {e}")
            await asyncio.sleep(2)

    logger.error("No se pudo obtener el nivel del agua tras varios intentos.")
    return None, None

# --------------------------------------------------------------------------
# 2) INTERPRETAR NIVEL
# --------------------------------------------------------------------------
def interpretar_nivel(nivel: float) -> str:
    # podés ajustar estos umbrales a tu realidad del Gambado
    if nivel < 0.60:
        return "🚫 Nivel muy bajo — salir es riesgoso."
    elif nivel < 0.80:
        return "⚠️ Nivel bajo — posible dificultad para navegar el Gambado."
    elif nivel < 1.20:
        return "🚤 Navegable con precaución."
    else:
        return "🌊 Nivel normal — navegación sin problemas."

# --------------------------------------------------------------------------
# 3) COMANDO /nivel
# --------------------------------------------------------------------------
async def comando_nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nivel, fecha = await obtener_nivel()
    if nivel is None:
        await update.message.reply_text("No pude obtener el nivel actual del agua 😔")
        return

    info = interpretar_nivel(nivel)

    if fecha is not None:
        # pasar a horario ARG
        fecha_local = (fecha - timedelta(hours=0)).astimezone(timezone(timedelta(hours=-3)))
        fecha_str = fecha_local.strftime("%d/%m/%Y %H:%M")
    else:
        fecha_str = "sin fecha"

    mensaje = (
        f"📍 *San Fernando (SHN – {MAREOGRAFO})*\n"
        f"Nivel actual: *{nivel:.2f} m*\n"
        f"{info}\n"
        f"Última lectura: {fecha_str}"
    )
    await update.message.reply_markdown(mensaje)

# --------------------------------------------------------------------------
# 4) TAREA AUTOMÁTICA (cada 30 minutos)
# --------------------------------------------------------------------------
async def monitorear_nivel(app):
    # mensaje de arranque
    await app.bot.send_message(
        chat_id=CHAT_ID,
        text="🤖 Bot del Gambado iniciado. Monitoreo cada 30 minutos."
    )
    while True:
        nivel, fecha = await obtener_nivel()
        if nivel is not None and nivel < ALERTA_UMBRAL:
            info = interpretar_nivel(nivel)
            if fecha is not None:
                fecha_local = fecha.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
            else:
                fecha_local = "sin fecha"
            mensaje = (
                f"🚨 *Alerta de nivel bajo (San Fernando)*\n"
                f"Nivel actual: *{nivel:.2f} m*\n"
                f"{info}\n"
                f"Hora: {fecha_local}"
            )
            await app.bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="Markdown")

        # espera 30 minutos
        await asyncio.sleep(1800)

# --------------------------------------------------------------------------
# 5) ARRANQUE DEL BOT
# --------------------------------------------------------------------------
async def main():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("nivel", comando_nivel))

    # tarea en paralelo
    asyncio.create_task(monitorear_nivel(app_telegram))

    await app_telegram.run_polling()

# --------------------------------------------------------------------------
# 6) EJECUCIÓN (Render-friendly)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    # levantamos Flask en un hilo para que Render tenga un puerto abierto
    import threading
    threading.Thread(
        target=lambda: app_flask.run(host="0.0.0.0", port=PORT),
        daemon=True
    ).start()

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
