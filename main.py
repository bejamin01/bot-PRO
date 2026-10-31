import os
import re
import sys
import time
import subprocess
import threading
import asyncio
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import quote, urlparse

def _asegurar_dependencias_kerit():
    """Instala requirements.txt automaticamente en Kerit Cloud si faltan librerias."""
    try:
        import psycopg
        import dotenv
        import telegram
        from google import genai
    except ImportError:
        req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
        if os.path.exists(req_file):
            print("[Kerit Cloud] Instalando dependencias desde requirements.txt...", flush=True)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])

_asegurar_dependencias_kerit()

import psycopg
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from google import genai

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
os.environ.pop("GOOGLE_API_KEY", None)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = (os.getenv("TELEGRAM_TOKEN") or "").strip()
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
BOT_USERNAME   = (os.getenv("BOT_USERNAME", "@utm_help_bot") or "").strip().lower()

def _parse_admins():
    raw = os.getenv("ADMIN_IDS", "5504260343,6501594656")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]

ADMINS = _parse_admins()

CONTACTO_WHATSAPP = (
    "0986616388\n"
    "0999304713\n"
    "0969238552\n"
    "0990181188"
)
HORARIO_ATENCION = "08:00-12:00 y 14:00-18:00"

URL_POSTULACION = "https://postulacion.utm.edu.ec"
URL_SGU = "https://sgu.utm.edu.ec/auth/login"
AVISO_WEB_UTM = (
    "Nota: www.utm.edu.ec esta en mantenimiento.\n"
    "Usa postulacion.utm.edu.ec (admisiones) o sgu.utm.edu.ec (matricula)."
)

INFO_ADMISIONES = (
    "Admisiones UTM 2026:\n"
    "- Inscripciones: 24 enero - 01 febrero\n"
    "- Aceptacion de cupos: 03 al 06 de abril (desde las 10:00)\n"
    "- Plataforma: postulacion.utm.edu.ec\n\n"
    "WhatsApp UTM:\n"
    "- 0986616388\n"
    "- 0999304713\n"
    "- 0969238552\n"
    "- 0990181188\n"
    f"Horario: {HORARIO_ATENCION}"
)

INFO_MATRICULA = (
    "Matricula UTM - SGU (S1-2026):\n"
    "La UTM utiliza el Sistema de Gestion Universitaria (SGU). El antiguo SGA ya no esta en uso.\n"
    "Acceso: https://sgu.utm.edu.ec/auth/login\n\n"
    "Pasos:\n"
    "1. Ingresa al SGU\n"
    "   - Ve a sgu.utm.edu.ec/auth/login\n"
    "   - Usuario: inicial del primer nombre + primer apellido completo + ultimos 4 digitos de cedula\n"
    "     Ejemplo: Juan Perez 1234567890 -> jperez7890\n"
    "   - Correo institucional: jperez7890@utm.edu.ec\n"
    "   - Contrasena: numero de cedula completo\n"
    "   - Si olvidaste tu contrasena, usa 'Olvide mi contrasena' en el SGU\n"
    "   - Escoge Rol: Aspirante (nuevos) o Estudiante (ya matriculados antes)\n\n"
    "2. Completa tus datos personales\n"
    "   - Foto tipo carnet (fondo blanco)\n"
    "   - PDF cedula (anverso y reverso en un solo archivo)\n"
    "   - Certificado de votacion vigente\n"
    "   - Titulo de Bachiller en PDF\n\n"
    "3. Selecciona la matricula\n"
    "   - Ve a: Pregrado > Matricula / Inscripcion a Semestre\n"
    "   - Elige carrera, modalidad y periodo S1-2026\n"
    "   - Revisa y confirma tu horario de clases\n\n"
    "4. Genera tu comprobante\n"
    "   - Descarga o imprime el comprobante de matricula\n\n"
    "El proceso es 100% gratuito y en linea.\n"
    f"Soporte WhatsApp: {CONTACTO_WHATSAPP.replace(chr(10), ' / ')}\n"
    f"Horario: {HORARIO_ATENCION}"
)

INFO_CARRERAS = (
    "Ingenieria Civil\n"
    "Ingenieria Industrial\n"
    "Ingenieria Quimica\n"
    "Electronica y Automatizacion\n"
    "Electricidad\n"
    "Biotecnologia\n"
    "Geologia\n"
    "Mecatronica\n"
    "Biologia\n"
    "Quimica\n"
    "Fisica\n"
    "Medicina\n"
    "Enfermeria\n"
    "Odontologia\n"
    "Nutricion y Dietetica\n"
    "Bioquimica y Farmacia\n"
    "Medicina Veterinaria\n"
    "Agroindustria\n"
    "Agronegocios (Modalidad Hibrida)\n"
    "Biodiversidad y Recursos Geneticos\n"
    "Sistemas de Informacion\n"
    "Tecnologias de la Informacion\n"
    "Tecnologias de la Informacion (En Linea)\n"
    "Realidad Virtual y Videojuegos (Hibrida)\n"
    "Economia (Hibrida)\n"
    "Economia (En Linea)\n"
    "Contabilidad y Auditoria (Hibrida)\n"
    "Administracion de Empresas (Hibrida)\n"
    "Administracion de Empresas (En Linea)\n"
    "Turismo (Hibrida)\n"
    "Turismo (En Linea)\n"
    "Negocios Digitales (En Linea)\n"
    "Logistica y Transporte\n"
    "Gastronomia\n"
    "Educacion Basica (En Linea)\n"
    "Educacion Inicial (En Linea)\n"
    "Pedagogia de los Idiomas Nacionales y Extranjeros\n"
    "Pedagogia de las Ciencias Experimentales (Quimica y Biologia)\n"
    "Pedagogia de las Ciencias Experimentales (Matematicas y Fisica)\n"
    "Pedagogia de Actividad Fisica y Deporte\n"
    "Pedagogia de la Lengua y Literatura\n"
    "Entrenamiento Deportivo\n"
    "Psicologia (En Linea)\n"
    "Trabajo Social\n"
    "Derecho (Hibrida)\n"
    "Derecho (En Linea)\n"
    "Sociologia (Hibrida)\n"
    "Tecnologias Geoespaciales"
)

INFO_BASE = {
    "admisiones": INFO_ADMISIONES,
    "matricula": INFO_MATRICULA,
    "carreras_web": INFO_CARRERAS,
}

SYNC_VERSION = "2026-08-04-v8"
BOT_VERSION = "2026-08-04-v8"
MSG_TTL_SEG = 600
_usuarios_vistos_local = set()
_advertencias_local = {}
_media_groups_vistos = set()
_ultimos_avisos_imagen = {}

SECCIONES_DB = {
    "admision": ("Admisiones UTM", "admisiones", [("Postulacion UTM", URL_POSTULACION)]),
    "matricula": ("Matricula UTM - SGU", "matricula", [("Ir al SGU", URL_SGU)]),
    "carreras": ("Carreras UTM", "carreras_web", [("Portal postulacion", URL_POSTULACION)]),
}

def _normalize_db_url(url):
    if not url:
        return url
    if "sslmode=" not in url and "proxy.rlwy.net" in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

def _db_host(url):
    if "@" not in url:
        return "desconocido"
    return url.split("@", 1)[1].split("/", 1)[0]

def _parsed_database_url():
    return urlparse(os.getenv("DATABASE_URL", ""))

def _compose_db_url(user, password, host, port, database):
    if not all([user, password, host, port, database]):
        return None
    safe_user = quote(user, safe="")
    safe_password = quote(password, safe="")
    return f"postgresql://{safe_user}:{safe_password}@{host}:{port}/{database}"

def _build_tcp_proxy_url():
    domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    if not domain or not port:
        return None

    parsed = _parsed_database_url()
    user = os.getenv("PGUSER") or parsed.username or "postgres"
    password = os.getenv("PGPASSWORD") or parsed.password
    database = os.getenv("PGDATABASE") or (parsed.path.lstrip("/") if parsed.path else "railway")
    return _compose_db_url(user, password, domain, port, database)

def _build_pg_url():
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER") or "postgres"
    password = os.getenv("PGPASSWORD")
    database = os.getenv("PGDATABASE") or "railway"
    if not host or "railway.internal" in host:
        return None
    return _compose_db_url(user, password, host, port, database)

def database_url_candidates():
    private = os.getenv("DATABASE_URL", "")
    public = os.getenv("DATABASE_PUBLIC_URL", "")
    tcp_proxy = _build_tcp_proxy_url()
    pg_url = _build_pg_url()
    ordered = []

    if "railway.internal" in private:
        ordered.extend([public, tcp_proxy, pg_url, private])
    else:
        ordered.extend([private, public, tcp_proxy, pg_url])

    seen = set()
    candidates = []
    for url in ordered:
        normalized = _normalize_db_url(url)
        if not normalized or "railway.internal" in normalized:
            continue
        if normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
    return candidates

DATABASE_URLS = database_url_candidates()

for var_name, var_val in [("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
                           ("GEMINI_API_KEY", GEMINI_API_KEY)]:
    if not var_val:
        raise EnvironmentError(f"Falta la variable de entorno: {var_name}")

DB_DISPONIBLE = bool(DATABASE_URLS)
if not DB_DISPONIBLE:
    logger.warning("Sin DATABASE_URL: el bot usara info local sin persistencia")

client = genai.Client(api_key=GEMINI_API_KEY)

_conn = None
_active_db_url = None

def connect_db():
    global _conn, _active_db_url
    if not DATABASE_URLS:
        raise psycopg.OperationalError("DATABASE_URL no configurada")
    errors = []
    for url in database_url_candidates():
        try:
            conn = psycopg.connect(url)
            _conn = conn
            _active_db_url = url
            logger.info("Conectado a PostgreSQL (%s)", _db_host(url))
            return conn
        except Exception as exc:
            host = _db_host(url)
            logger.warning("Fallo conexion %s: %s", host, exc)
            errors.append(f"{host}: {exc}")
    raise psycopg.OperationalError("; ".join(errors))

def get_conn():
    global _conn
    if not DB_DISPONIBLE:
        raise psycopg.OperationalError("Base de datos no disponible")
    try:
        if _conn is None or _conn.closed:
            raise Exception("Conexion cerrada")
        _conn.execute("SELECT 1")
    except Exception:
        logger.warning("Reconectando a PostgreSQL...")
        connect_db()
    return _conn

def bootstrap_db(max_attempts=3, delay=2):
    global DB_DISPONIBLE
    if not DATABASE_URLS:
        DB_DISPONIBLE = False
        return False

    for attempt in range(1, max_attempts + 1):
        try:
            init_db()
            sync_info_utm()
            DB_DISPONIBLE = True
            return True
        except Exception as exc:
            logger.error("Intento %d/%d de conexion a BD: %s", attempt, max_attempts, exc)
            if attempt < max_attempts:
                time.sleep(delay)

    DB_DISPONIBLE = False
    logger.warning("Bot iniciara sin base de datos. Usando info local.")
    return False

def reintentar_db_en_background():
    if not DATABASE_URLS:
        logger.warning("Sin URL publica de BD. Agrega DATABASE_PUBLIC_URL en Railway.")
        return

    def _loop():
        global DB_DISPONIBLE
        while not DB_DISPONIBLE:
            time.sleep(30)
            try:
                init_db()
                sync_info_utm()
                DB_DISPONIBLE = True
                logger.info("Base de datos conectada en segundo plano")
                return
            except Exception as exc:
                logger.warning("Reintento de BD fallido: %s", exc)

    threading.Thread(target=_loop, daemon=True).start()

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            nombre TEXT,
            advertencias INT DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS info_utm (
            clave TEXT PRIMARY KEY,
            valor TEXT,
            actualizado TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()

    for clave, valor in INFO_BASE.items():
        conn.execute("""
            INSERT INTO info_utm (clave, valor, actualizado)
            VALUES (%s, %s, NOW())
            ON CONFLICT (clave) DO NOTHING
        """, (clave, valor))
    conn.commit()
    logger.info("Tablas e info base listas")

def sync_info_utm():
    """Actualiza info_utm cuando cambia SYNC_VERSION (una vez por deploy)."""
    conn = get_conn()
    actual = conn.execute(
        "SELECT valor FROM info_utm WHERE clave = '_sync_version'"
    ).fetchone()
    if actual and actual[0] == SYNC_VERSION:
        return

    for clave, valor in INFO_BASE.items():
        conn.execute("""
            INSERT INTO info_utm (clave, valor, actualizado)
            VALUES (%s, %s, NOW())
            ON CONFLICT (clave) DO UPDATE
            SET valor = EXCLUDED.valor, actualizado = NOW()
        """, (clave, valor))
    conn.execute("""
        INSERT INTO info_utm (clave, valor, actualizado)
        VALUES ('_sync_version', %s, NOW())
        ON CONFLICT (clave) DO UPDATE
        SET valor = EXCLUDED.valor, actualizado = NOW()
    """, (SYNC_VERSION,))
    conn.commit()
    logger.info("Info UTM sincronizada (version %s)", SYNC_VERSION)

def es_grupo(chat):
    return chat.type in ("group", "supergroup")

async def es_usuario_admin(chat, user, message=None, context=None) -> bool:
    if not es_grupo(chat):
        return False
    if message and message.sender_chat and message.sender_chat.id == chat.id:
        return True
    if not user:
        return False
    if user.id == 1087968824:
        return True
    if user.id in ADMINS:
        return True
    try:
        member = await chat.get_member(user.id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

def mensaje_tiene_enlace(message) -> bool:
    if not message:
        return False

    entidades = list(message.entities or []) + list(message.caption_entities or [])
    for ent in entidades:
        if ent.type in ("url", "text_link"):
            return True

    texto_total = f"{message.text or ''} {message.caption or ''}".strip()
    if not texto_total:
        return False

    patron_enlaces = re.compile(
        r"(?i)\b(?:https?://|ftp://|www\.)[^\s]+"
        r"|\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|edu|ec|io|me|info|biz|xyz|site|online|top|app|dev|link|vip|pro)\b(?:/[^\s]*)?"
        r"|\b(?:t\.me|telegram\.me)/[^\s]+"
    )
    return bool(patron_enlaces.search(texto_total))

def usuario_existe(telegram_id):
    if telegram_id in _usuarios_vistos_local:
        return True
    if not DB_DISPONIBLE:
        return False
    try:
        conn = get_conn()
        return conn.execute(
            "SELECT 1 FROM usuarios WHERE telegram_id = %s", (telegram_id,)
        ).fetchone() is not None
    except Exception as e:
        logger.error(f"Error al consultar usuario: {e}")
        return telegram_id in _usuarios_vistos_local

def guardar_usuario(user):
    _usuarios_vistos_local.add(user.id)
    if not DB_DISPONIBLE:
        return
    try:
        conn = get_conn()
        conn.execute("""
            INSERT INTO usuarios (telegram_id, nombre)
            VALUES (%s, %s)
            ON CONFLICT (telegram_id) DO NOTHING
        """, (user.id, user.first_name))
        conn.commit()
    except Exception as e:
        logger.error(f"Error al guardar usuario: {e}")

async def _borrar_mensajes_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    for msg_id in data.get("message_ids", []):
        try:
            await context.bot.delete_message(chat_id=data["chat_id"], message_id=msg_id)
        except Exception:
            pass

def programar_borrado(context, chat_id, message_ids):
    if not context.job_queue:
        return
    ids = [mid for mid in message_ids if mid]
    if not ids:
        return
    context.job_queue.run_once(
        _borrar_mensajes_job,
        when=MSG_TTL_SEG,
        data={"chat_id": chat_id, "message_ids": ids},
    )

async def responder(message, context, texto, reply_markup=None, borrar_origen=True):
    try:
        enviado = await message.reply_text(texto, reply_markup=reply_markup)
    except Exception:
        enviado = await context.bot.send_message(
            chat_id=message.chat_id, text=texto, reply_markup=reply_markup
        )
    if es_grupo(message.chat):
        ids = [enviado.message_id]
        if borrar_origen and message.message_id:
            ids.append(message.message_id)
        programar_borrado(context, message.chat_id, ids)
    return enviado

async def responder_callback(query, context, texto, reply_markup=None):
    try:
        enviado = await query.message.reply_text(texto, reply_markup=reply_markup)
    except Exception:
        enviado = await context.bot.send_message(
            chat_id=query.message.chat_id, text=texto, reply_markup=reply_markup
        )
    if es_grupo(query.message.chat):
        ids = [enviado.message_id]
        if query.message.message_id:
            ids.append(query.message.message_id)
        programar_borrado(context, query.message.chat_id, ids)
    return enviado

async def enviar_temporal(chat, context, texto, reply_markup=None, extra_ids=None):
    enviado = await context.bot.send_message(
        chat.id, texto, reply_markup=reply_markup
    )
    if es_grupo(chat):
        ids = [enviado.message_id] + list(extra_ids or [])
        programar_borrado(context, chat.id, ids)
    return enviado

def advertir_usuario(user_id):
    _advertencias_local[user_id] = _advertencias_local.get(user_id, 0) + 1
    if not DB_DISPONIBLE:
        return _advertencias_local[user_id]
    try:
        conn = get_conn()
        result = conn.execute("""
            UPDATE usuarios
            SET advertencias = advertencias + 1
            WHERE telegram_id = %s
            RETURNING advertencias
        """, (user_id,)).fetchone()
        conn.commit()
        return result[0] if result else _advertencias_local[user_id]
    except Exception as e:
        logger.error(f"Error al advertir: {e}")
        return _advertencias_local[user_id]

def obtener_info(clave):
    if not DB_DISPONIBLE:
        return INFO_BASE.get(clave)
    try:
        conn = get_conn()
        result = conn.execute(
            "SELECT valor FROM info_utm WHERE clave = %s", (clave,)
        ).fetchone()
        return result[0] if result else INFO_BASE.get(clave)
    except Exception as e:
        logger.error(f"Error al obtener info: {e}")
        return INFO_BASE.get(clave)

def markup_botones(botones):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(texto, url=url) for texto, url in botones]
    ])

def texto_contacto(completo=False):
    texto = (
        "Contacto UTM\n\n"
        f"{AVISO_WEB_UTM}\n\n"
        "Email: info@utm.edu.ec\n"
    )
    if completo:
        texto += "Direccion: Av. Urbina y Che Guevara, Portoviejo, Manabi\n\n"
    else:
        texto += "Portoviejo, Manabi\n\n"
    texto += (
        f"WhatsApp:\n{CONTACTO_WHATSAPP}\n"
        f"Horario: {HORARIO_ATENCION}"
    )
    if completo:
        texto += (
            "\n\nRedes sociales:\n"
            "Twitter: @UTMManabi\n"
            "Instagram: @utm_manabi\n"
            "Facebook: utmmanabi\n"
            "TikTok: @utm_manabi"
        )
    return texto

async def enviar_seccion_db(message, context, seccion, footer=""):
    titulo, clave, botones = SECCIONES_DB[seccion]
    info = obtener_info(clave) or f"Informacion no disponible. {AVISO_WEB_UTM}"
    await responder(
        message, context,
        f"{titulo}\n\n{info}{footer}",
        reply_markup=markup_botones(botones),
    )

def menu_principal():
    teclado = [
        [
            InlineKeyboardButton("📅 Admisiones", callback_data="admision"),
            InlineKeyboardButton("🧾 Matricula",  callback_data="matricula"),
        ],
        [
            InlineKeyboardButton("🎓 Carreras",   callback_data="carreras"),
            InlineKeyboardButton("💰 Costos",     callback_data="costo"),
        ],
        [
            InlineKeyboardButton("🕐 Horarios",   callback_data="horario"),
            InlineKeyboardButton("📍 Ubicacion",  callback_data="ubicacion"),
        ],
        [
            InlineKeyboardButton("📞 Contacto",   callback_data="contacto"),
            InlineKeyboardButton("📝 Postulacion", url=URL_POSTULACION),
            InlineKeyboardButton("🎓 SGU",         url=URL_SGU),
        ],
    ]
    return InlineKeyboardMarkup(teclado)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guardar_usuario(update.effective_user)
    await responder(
        update.message, context,
        "Hola! Soy el asistente virtual de la UTM\n\n"
        "Puedo ayudarte con informacion sobre:\n"
        "Admisiones y matricula\n"
        "Carreras disponibles\n"
        "Horarios y costos\n"
        "Contacto\n\n"
        "Elige una opcion o escribe tu pregunta:",
        reply_markup=menu_principal(),
    )

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        "Comandos disponibles:\n\n"
        "/start - Menu principal\n"
        "/ayuda - Ver esta ayuda\n"
        "/admisiones - Info de admisiones 2026\n"
        "/matricula - Como matricularse\n"
        "/carreras - Lista de carreras\n"
        "/contacto - Datos de contacto\n"
        "/horarios - Horarios de atencion\n"
        "Tambien puedes escribir tu pregunta directamente.",
        reply_markup=menu_principal(),
    )

async def cmd_miid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        f"Tu ID de Telegram es: {update.effective_user.id}",
    )

async def cmd_admisiones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, context, "admision")

async def cmd_matricula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, context, "matricula")

async def cmd_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, context, "carreras", footer=f"\n\n{AVISO_WEB_UTM}")

async def cmd_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        texto_contacto(completo=True),
        reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
    )

async def cmd_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        "Horarios UTM\n\n"
        "Lunes a viernes 08h00 - 17h00",
    )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dato = query.data

    if dato in SECCIONES_DB:
        await enviar_seccion_db(query.message, context, dato)
    elif dato == "costo":
        await responder_callback(
            query, context,
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo.",
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION)]),
        )
    elif dato == "horario":
        await responder_callback(
            query, context,
            "Horarios UTM\n\n"
            "Lunes a viernes 08h00 - 17h00\n"
            "Telefono: (593 5) 263-2677",
        )
    elif dato == "ubicacion":
        await responder_callback(
            query, context,
            "Ubicacion UTM\n\n"
            "Av. Urbina y Che Guevara\n"
            "Portoviejo, Manabi, Ecuador",
            reply_markup=markup_botones([("Ver en Google Maps", "https://maps.google.com/?q=Universidad+Tecnica+de+Manabi+Portoviejo")]),
        )
    elif dato == "contacto":
        await responder_callback(
            query, context,
            texto_contacto(),
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
        )

async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:
        if user.is_bot:
            continue

        es_regreso = usuario_existe(user.id)
        guardar_usuario(user)
        saludo = "Bienvenido de nuevo" if es_regreso else "Bienvenido"

        await responder(
            update.message, context,
            f"{saludo} {user.first_name}!\n\n"
            "Grupo de estudio UTM\n\n"
            f"Escribe {BOT_USERNAME} seguido de tu pregunta\n"
            "o usa /start para ver el menu.\n\n"
            "Reglas:\n"
            "No spam\n"
            "No enlaces\n"
            "Respeto mutuo",
            borrar_origen=True,
        )

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto    = update.message.text
    user     = update.effective_user
    es_grupo = update.effective_chat.type in ["group", "supergroup"]

    guardar_usuario(user)

    if es_grupo and mensaje_tiene_enlace(update.message):
        if not await es_usuario_admin(update.effective_chat, user, update.message, context):
            adv = advertir_usuario(user.id)
            try:
                await update.message.delete()
            except Exception:
                pass
            if adv >= 2:
                try:
                    await context.bot.ban_chat_member(
                        chat_id=update.effective_chat.id,
                        user_id=user.id
                    )
                    await enviar_temporal(
                        update.effective_chat, context,
                        f"{user.first_name} fue baneado por enviar enlaces.",
                    )
                except Exception as e:
                    logger.error(f"No se pudo banear: {e}")
            else:
                await enviar_temporal(
                    update.effective_chat, context,
                    f"Advertencia {adv}/2 para {user.first_name}: Solo los administradores o el propietario pueden enviar enlaces al grupo.",
                )
            return

    if es_grupo and BOT_USERNAME not in texto.lower():
        return

    texto_lower = texto.lower()

    if any(p in texto_lower for p in ["admis", "inscripci", "ingreso", "postula"]):
        await enviar_seccion_db(update.message, context, "admision")
        return

    if any(p in texto_lower for p in ["matricula", "matrícula", "materias", "paralelo", "sgu", "sga", "sistema de gestion", "como matricul"]):
        await enviar_seccion_db(update.message, context, "matricula")
        return

    if any(p in texto_lower for p in ["carrera", "facultad", "oferta"]):
        await enviar_seccion_db(update.message, context, "carreras")
        return

    if any(p in texto_lower for p in ["contacto", "whatsapp", "telefono", "teléfono"]):
        await responder(
            update.message, context,
            texto_contacto(),
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
        )
        return

    if any(p in texto_lower for p in ["horario", "atencion", "atención"]):
        await responder(
            update.message, context,
            "Horarios UTM\n\n"
            "Lunes a viernes 08h00 - 17h00\n"
            "Telefono: (593 5) 263-2677",
        )
        return

    if any(p in texto_lower for p in ["costo", "precio", "gratis", "gratuito", "pagar"]):
        await responder(
            update.message, context,
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo.",
        )
        return

    if any(p in texto_lower for p in ["ubicacion", "ubicación", "donde", "dónde", "direccion"]):
        await responder(
            update.message, context,
            "Ubicacion UTM\n\n"
            "Av. Urbina y Che Guevara\n"
            "Portoviejo, Manabi, Ecuador",
            reply_markup=markup_botones([("Ver en Google Maps", "https://maps.google.com/?q=Universidad+Tecnica+de+Manabi+Portoviejo")]),
        )
        return

    if any(p in texto_lower for p in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "saludos", "menu", "menú", "opciones", "ayuda", "help"]):
        await responder(
            update.message, context,
            "Hola! Soy el asistente virtual de la UTM.\nElige una opcion o escribe tu consulta:",
            reply_markup=menu_principal(),
        )
        return

    try:
        admisiones = obtener_info("admisiones") or ""
        matricula  = obtener_info("matricula")  or ""
        carreras   = obtener_info("carreras_web") or ""

        prompt = (
            "Eres un asistente oficial de la Universidad Tecnica de Manabi (UTM). "
            "Respondes de forma clara, corta y precisa en espanol. "
            "IMPORTANTE: La UTM ya NO usa el SGA (Sistema de Gestion Academica). "
            "Ahora usa el SGU (Sistema de Gestion Universitaria) en sgu.utm.edu.ec. "
            "Si alguien pregunta por el SGA, corrigelo y dirige al SGU. "
            "No inventes informacion. Si no sabes algo, sugiere postulacion.utm.edu.ec o sgu.utm.edu.ec. "
            "www.utm.edu.ec esta en mantenimiento. "
            "o contactar por WhatsApp al 0986616388.\n\n"
            f"Admisiones UTM:\n{admisiones}\n\n"
            f"Matricula UTM (SGU):\n{matricula}\n\n"
            f"Carreras UTM:\n{carreras}\n\n"
            f"Usuario: {texto}"
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt
        )
        respuesta = response.text or f"No pude generar una respuesta. {AVISO_WEB_UTM}"
        await responder(
            update.message, context,
            respuesta,
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
        )

    except Exception as e:
        logger.error(f"Error Gemini: {e}")
        await responder(
            update.message, context,
            "No pude procesar tu pregunta.\n"
            f"{AVISO_WEB_UTM}\nContactanos por WhatsApp al 0986616388.",
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
        )

async def bloquear_imagenes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.effective_chat
    user = update.effective_user

    if not chat or not es_grupo(chat):
        return

    if user and user.is_bot:
        return

    if await es_usuario_admin(chat, user, update.message, context):
        return

    # Borrar la imagen de inmediato
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"No se pudo borrar imagen en el grupo: {e}")

    if not user:
        return

    guardar_usuario(user)

    # Evitar advertencias duplicadas si envian un album o varias imagenes en rafaga
    ahora = time.time()
    mg_id = update.message.media_group_id
    if mg_id:
        if mg_id in _media_groups_vistos:
            return
        _media_groups_vistos.add(mg_id)
        if len(_media_groups_vistos) > 1000:
            _media_groups_vistos.clear()

    ultimo_aviso = _ultimos_avisos_imagen.get(user.id, 0)
    if ahora - ultimo_aviso < 4:
        return
    _ultimos_avisos_imagen[user.id] = ahora

    adv = advertir_usuario(user.id)
    if adv >= 2:
        try:
            await context.bot.ban_chat_member(
                chat_id=chat.id,
                user_id=user.id
            )
            await enviar_temporal(
                chat, context,
                f"{user.first_name} fue baneado por enviar imagenes.",
            )
        except Exception as e:
            logger.error(f"No se pudo banear por enviar imagen: {e}")
    else:
        await enviar_temporal(
            chat, context,
            f"Advertencia {adv}/2 para {user.first_name}: Solo los administradores o el propietario pueden enviar imagenes al grupo.",
        )

async def bloquear_enlaces_en_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.effective_chat
    user = update.effective_user

    if not chat or not es_grupo(chat):
        return

    if user and user.is_bot:
        return

    if not mensaje_tiene_enlace(update.message):
        return

    if await es_usuario_admin(chat, user, update.message, context):
        return

    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"No se pudo borrar enlace en media: {e}")

    if not user:
        return

    guardar_usuario(user)

    adv = advertir_usuario(user.id)
    if adv >= 2:
        try:
            await context.bot.ban_chat_member(
                chat_id=chat.id,
                user_id=user.id
            )
            await enviar_temporal(
                chat, context,
                f"{user.first_name} fue baneado por enviar enlaces.",
            )
        except Exception as e:
            logger.error(f"No se pudo banear por enviar enlace: {e}")
    else:
        await enviar_temporal(
            chat, context,
            f"Advertencia {adv}/2 para {user.first_name}: Solo los administradores o el propietario pueden enviar enlaces al grupo.",
        )

def iniciar_bd_en_background():
    def _tarea():
        if bootstrap_db():
            return
        reintentar_db_en_background()

    threading.Thread(target=_tarea, daemon=True).start()

class _KeritKeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"Bot UTM ({BOT_VERSION}) activo 24/7 en Kerit Cloud".encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

def iniciar_servidor_kerit(puerto_default=8080):
    """Inicia un servidor HTTP ligero en segundo plano para mantener activo el contenedor en Kerit Cloud (Pterodactyl)."""
    raw_port = os.getenv("SERVER_PORT") or os.getenv("PORT") or os.getenv("KERIT_PORT") or str(puerto_default)
    try:
        port = int(raw_port)
    except ValueError:
        port = puerto_default

    def _run_server():
        try:
            HTTPServer.allow_reuse_address = True
            server = HTTPServer(("0.0.0.0", port), _KeritKeepAliveHandler)
            logger.info("Servidor Keep-Alive Kerit Cloud escuchando en 0.0.0.0:%d", port)
            server.serve_forever()
        except Exception as exc:
            logger.warning("No se pudo iniciar servidor Keep-Alive en puerto %d: %s", port, exc)

    def _auto_ping_render():
        """En Render, hace auto-ping a RENDER_EXTERNAL_URL cada 10 minutos para evitar modo sleep."""
        import urllib.request
        while True:
            time.sleep(600)
            url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("KEEPALIVE_URL")
            if url:
                try:
                    urllib.request.urlopen(url, timeout=10).read()
                except Exception:
                    pass

    threading.Thread(target=_run_server, daemon=True).start()
    threading.Thread(target=_auto_ping_render, daemon=True).start()

async def _configurar_comandos_menu(application):
    """Sincroniza el menu de comandos de Telegram (sin becas)."""
    comandos = [
        ("start", "Menu principal"),
        ("ayuda", "Ver ayuda y opciones"),
        ("admisiones", "Info de admisiones 2026"),
        ("matricula", "Como matricularse (SGU)"),
        ("carreras", "Lista de carreras UTM"),
        ("contacto", "Datos de contacto"),
        ("horarios", "Horarios de atencion"),
    ]
    try:
        await application.bot.set_my_commands(comandos)
    except Exception as exc:
        logger.warning("No se pudo actualizar el menu de comandos: %s", exc)

def crear_app():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(_configurar_comandos_menu).build()
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("ayuda",      cmd_ayuda))
    app.add_handler(CommandHandler("help",       cmd_ayuda))
    app.add_handler(CommandHandler("miid",       cmd_miid))
    app.add_handler(CommandHandler("admisiones", cmd_admisiones))
    app.add_handler(CommandHandler("matricula",  cmd_matricula))
    app.add_handler(CommandHandler("carreras",   cmd_carreras))
    app.add_handler(CommandHandler("contacto",   cmd_contacto))
    app.add_handler(CommandHandler("horarios",   cmd_horarios))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))

    filtro_imagenes = (
        filters.PHOTO
        | filters.Document.IMAGE
        | filters.Document.FileExtension("jpg")
        | filters.Document.FileExtension("jpeg")
        | filters.Document.FileExtension("png")
        | filters.Document.FileExtension("webp")
        | filters.Document.FileExtension("gif")
        | filters.Document.FileExtension("bmp")
        | filters.Document.FileExtension("heic")
    )
    app.add_handler(MessageHandler(filtro_imagenes, bloquear_imagenes))
    filtro_media_con_enlace = filters.ChatType.GROUPS & filters.CAPTION
    app.add_handler(MessageHandler(filtro_media_con_enlace, bloquear_enlaces_en_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    return app

if __name__ == "__main__":
    print(f"=== BOT UTM {BOT_VERSION} ===", flush=True)
    print(f"Telegram arranca primero, BD en background ({BOT_VERSION})", flush=True)
    logger.info("Iniciando bot UTM version %s", BOT_VERSION)
    logger.info("Modo: Telegram arranca primero, BD en background")
    logger.info("Candidatos de BD: %s", [_db_host(u) for u in DATABASE_URLS] or ["ninguno - modo local"])

    iniciar_servidor_kerit()
    iniciar_bd_en_background()
    logger.info("Hilo de BD iniciado en segundo plano")
    app = crear_app()

    logger.info("Bot UTM corriendo (polling Telegram)...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)