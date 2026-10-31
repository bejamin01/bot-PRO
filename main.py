import os
import re
import sys
import time
import unicodedata
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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
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

INFO_FECHAS = (
    "Calendario y Fechas Importantes UTM 2026:\n\n"
    "- Inscripciones / Postulacion: 24 enero al 01 febrero\n"
    "- Aceptacion de cupos: 03 al 06 de abril (desde las 10:00)\n"
    "- Matriculas S1-2026 (SGU): Segun cronograma por carrera en sgu.utm.edu.ec\n"
    "- Modalidad: 100% en linea y gratuita\n\n"
    f"Consultas WhatsApp:\n{CONTACTO_WHATSAPP}\n"
    f"Horario: {HORARIO_ATENCION}"
)

REGLAS_GRUPO = (
    "Reglas Oficiales - Grupo de Estudio UTM:\n\n"
    "1. Prohibido enviar enlaces externos (solo administradores).\n"
    "2. Prohibido enviar imagenes no autorizadas (solo administradores).\n"
    "3. Prohibido el spam, ventas o publicidad ('hago tareas', 'paso examenes', etc.).\n"
    "4. Mantener el respeto mutuo entre companeros.\n\n"
    "Sistema de Sanciones:\n"
    "- 1ra falta: Advertencia 1/3\n"
    "- 2da falta: Silenciado por 1 hora (Advertencia 2/3)\n"
    "- 3ra falta: Expulsion definitiva del grupo (3/3)"
)

FAQ_ITEMS = {
    "faq_clave": (
        "Olvide mi contrasena del SGU:\n\n"
        "1. Ingresa a https://sgu.utm.edu.ec/auth/login\n"
        "2. Haz clic en 'Olvide mi contrasena'.\n"
        "3. Si eres estudiante nuevo, recuerda que tu contrasena inicial es tu numero de cedula completo (10 digitos).\n"
        "4. Si sigue sin permitirte el acceso, escribe a soporte por WhatsApp: 0986616388 / 0999304713."
    ),
    "faq_correo": (
        "Como saber mi Usuario y Correo Institucional UTM:\n\n"
        "- Formato: inicial de tu primer nombre + primer apellido + ultimos 4 digitos de tu cedula.\n"
        "- Ejemplo: Juan Perez con cedula 1312345678 -> usuario: jperez5678\n"
        "- Correo institucional: jperez5678@utm.edu.ec\n\n"
        "Tip: Usa el comando /miusuario Nombre Apellido Cedula para que el bot lo calcule por ti."
    ),
    "faq_docs": (
        "Documentos requeridos para Matricula en el SGU:\n\n"
        "1. Foto tamaño carnet con fondo blanco (formato imagen).\n"
        "2. Cedula de identidad (anverso y reverso en un solo archivo PDF).\n"
        "3. Certificado de votacion vigente (PDF).\n"
        "4. Titulo de Bachiller o Acta de Grado refrendada (PDF)."
    ),
    "faq_horario": (
        "Donde revisar mi horario de clases:\n\n"
        "1. Entra a https://sgu.utm.edu.ec/auth/login\n"
        "2. Dirigete al modulo Pregrado > Matricula / Inscripcion a Semestre.\n"
        "3. Al seleccionar tus asignaturas y paralelo, podras visualizar y descargar tu horario y comprobante de matricula."
    ),
}

def _limpiar_texto_ascii(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.strip().lower())
    return "".join(c for c in normalizado if c.isalnum())

def calcular_credenciales_sgu(nombre: str, apellido: str, cedula: str):
    digitos = re.sub(r"\D", "", cedula or "")
    nombre_limpio = _limpiar_texto_ascii(nombre)
    apellido_limpio = _limpiar_texto_ascii(apellido)
    if not nombre_limpio or not apellido_limpio or len(digitos) < 4:
        return None
    usuario = f"{nombre_limpio[0]}{apellido_limpio}{digitos[-4:]}"
    correo = f"{usuario}@utm.edu.ec"
    return {
        "usuario": usuario,
        "correo": correo,
        "contrasena": digitos,
    }

def filtrar_carreras_modalidad(modalidad: str) -> str:
    lineas = [l.strip() for l in (obtener_info("carreras_web") or INFO_CARRERAS).splitlines() if l.strip()]
    if modalidad == "online":
        filtradas = [l for l in lineas if "en linea" in l.lower()]
        titulo = "Carreras UTM - Modalidad En Linea"
    elif modalidad == "hibrida":
        filtradas = [l for l in lineas if "hibrida" in l.lower()]
        titulo = "Carreras UTM - Modalidad Hibrida"
    elif modalidad == "presencial":
        filtradas = [l for l in lineas if "en linea" not in l.lower() and "hibrida" not in l.lower()]
        titulo = "Carreras UTM - Modalidad Presencial"
    else:
        filtradas = lineas
        titulo = "Todas las Carreras UTM"
    listado = "\n".join(f"- {c}" for c in filtradas)
    return f"{titulo} ({len(filtradas)}):\n\n{listado}\n\n{AVISO_WEB_UTM}"

INFO_BASE = {
    "admisiones": INFO_ADMISIONES,
    "matricula": INFO_MATRICULA,
    "carreras_web": INFO_CARRERAS,
}

SYNC_VERSION = "2026-08-04-v8"
BOT_VERSION = "2026-08-04-v8"
MSG_TTL_SEG = 18000  # 5 horas (5 * 3600 segundos)
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

PATRON_SPAM_ESTAFAS = re.compile(
    r"(?i)\b(?:"
    r"hago\s+tareas|hacemos\s+tareas|resuelvo\s+examenes|paso\s+examenes|"
    r"ayuda\s+en\s+examenes|gana\s+dinero\s+desde\s+casa|venta\s+de\s+cupos|"
    r"aseguro\s+tu\s+cupo|cupos\s+garantizados|hackear\s+sgu|cambio\s+de\s+notas"
    r")\b"
)

def mensaje_tiene_spam(message) -> bool:
    if not message:
        return False
    texto_total = f"{message.text or ''} {message.caption or ''}".strip()
    if not texto_total:
        return False
    normalizado = unicodedata.normalize("NFKD", texto_total).encode("ascii", "ignore").decode("ascii")
    return bool(PATRON_SPAM_ESTAFAS.search(normalizado))

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

def perdonar_usuario_db(user_id):
    _advertencias_local[user_id] = 0
    if not DB_DISPONIBLE:
        return
    try:
        conn = get_conn()
        conn.execute("UPDATE usuarios SET advertencias = 0 WHERE telegram_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error al perdonar usuario: {e}")

async def aplicar_sancion_gradual(chat, user, context, motivo_corto, detalle_regla):
    """Aplica sancion en 3 niveles: 1=Advertencia, 2=Silencio 1 hora, 3=Ban definitivo."""
    adv = advertir_usuario(user.id)
    if adv >= 3:
        try:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id)
            await enviar_temporal(
                chat, context,
                f"🚫 {user.first_name} fue expulsado del grupo (Advertencia 3/3) por {motivo_corto}.",
            )
        except Exception as e:
            logger.error(f"No se pudo banear por {motivo_corto}: {e}")
    elif adv == 2:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=int(time.time()) + 3600,
            )
            await enviar_temporal(
                chat, context,
                f"🔇 Advertencia 2/3 para {user.first_name}: Has sido silenciado por 1 hora ({detalle_regla}). La proxima falta sera expulsion.",
            )
        except Exception as e:
            logger.error(f"No se pudo silenciar a {user.id}: {e}")
            await enviar_temporal(
                chat, context,
                f"⚠️ Advertencia 2/3 para {user.first_name}: {detalle_regla}.",
            )
    else:
        await enviar_temporal(
            chat, context,
            f"⚠️ Advertencia {adv}/3 para {user.first_name}: {detalle_regla}.",
        )

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

def markup_botones(botones=None, incluir_volver=True):
    filas = []
    if botones:
        filas.append([InlineKeyboardButton(texto, url=url) for texto, url in botones])
    if incluir_volver:
        filas.append([InlineKeyboardButton("⬅️ Volver al Menu Principal", callback_data="menu_volver")])
    return InlineKeyboardMarkup(filas)

def markup_carreras():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏫 Presenciales", callback_data="carreras_presencial"),
            InlineKeyboardButton("🔄 Hibridas",     callback_data="carreras_hibrida"),
        ],
        [
            InlineKeyboardButton("💻 En Linea",     callback_data="carreras_online"),
            InlineKeyboardButton("📋 Ver Todas",    callback_data="carreras_todas"),
        ],
        [
            InlineKeyboardButton("📝 Portal Postulacion", url=URL_POSTULACION),
        ],
        [
            InlineKeyboardButton("⬅️ Volver al Menu Principal", callback_data="menu_volver"),
        ],
    ])

def markup_faq():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Olvide mi clave del SGU", callback_data="faq_clave")],
        [InlineKeyboardButton("📧 Como saber mi usuario/correo", callback_data="faq_correo")],
        [InlineKeyboardButton("📄 Documentos para matricula", callback_data="faq_docs")],
        [InlineKeyboardButton("🕒 Donde veo mi horario", callback_data="faq_horario")],
        [InlineKeyboardButton("⬅️ Volver al Menu Principal", callback_data="menu_volver")],
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
    teclado = markup_carreras() if seccion == "carreras" else markup_botones(botones)
    await responder(
        message, context,
        f"{titulo}\n\n{info}{footer}",
        reply_markup=teclado,
    )

def menu_principal():
    teclado = [
        [
            InlineKeyboardButton("📅 Admisiones", callback_data="admision"),
            InlineKeyboardButton("🧾 Matricula",  callback_data="matricula"),
        ],
        [
            InlineKeyboardButton("🎓 Carreras",   callback_data="carreras"),
            InlineKeyboardButton("🔑 Usuario SGU", callback_data="calc_sgu"),
        ],
        [
            InlineKeyboardButton("📆 Fechas 2026", callback_data="fechas"),
            InlineKeyboardButton("❓ Preguntas FAQ", callback_data="faq_menu"),
        ],
        [
            InlineKeyboardButton("💰 Costos",     callback_data="costo"),
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
        "- Admisiones, matricula y fechas 2026\n"
        "- Carreras (Presenciales, Hibridas y En Linea)\n"
        "- Calculo de tu Usuario y Correo SGU (/miusuario)\n"
        "- Preguntas frecuentes, horarios, costos y contacto\n\n"
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
        "/matricula - Como matricularse en el SGU\n"
        "/carreras - Carreras por modalidad\n"
        "/miusuario - Calcular tu usuario y correo SGU\n"
        "/fechas - Calendario de fechas importantes\n"
        "/faq - Preguntas frecuentes\n"
        "/contacto - Datos de contacto\n"
        "/horarios - Horarios de atencion\n"
        "/reglas - Reglas del grupo\n\n"
        "Comandos para Administradores:\n"
        "/perdonar - Quitar advertencias (respondiendo a un usuario)\n"
        "/anuncio <texto> - Publicar y fijar comunicado oficial",
        reply_markup=menu_principal(),
    )

async def cmd_miid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        f"Tu ID de Telegram es: {update.effective_user.id}",
        reply_markup=markup_botones(),
    )

async def cmd_admisiones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, context, "admision")

async def cmd_matricula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, context, "matricula")

async def cmd_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        "Selecciona la modalidad de carrera que deseas consultar:",
        reply_markup=markup_carreras(),
    )

async def cmd_fechas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        INFO_FECHAS,
        reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
    )

async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        "Preguntas Frecuentes (FAQ) UTM:\nSelecciona tu duda:",
        reply_markup=markup_faq(),
    )

async def cmd_reglas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder(
        update.message, context,
        REGLAS_GRUPO,
        reply_markup=markup_botones(),
    )

async def cmd_miusuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if len(args) < 3:
        await responder(
            update.message, context,
            "🔑 Calculador de Usuario y Correo SGU:\n\n"
            "Escribe el comando seguido de tu Primer Nombre, Primer Apellido y tu Cedula.\n\n"
            "Ejemplo:\n"
            "/miusuario Juan Perez 1312345678",
            reply_markup=markup_botones([("Ir al SGU", URL_SGU)]),
        )
        return

    nombre = args[0]
    apellido = args[1]
    cedula = args[-1]
    datos = calcular_credenciales_sgu(nombre, apellido, cedula)
    if not datos:
        await responder(
            update.message, context,
            "Datos invalidos. Asegurate de escribir: /miusuario PrimerNombre PrimerApellido Cedula (minimo 4 digitos).\n"
            "Ejemplo: /miusuario Juan Perez 1312345678",
            reply_markup=markup_botones([("Ir al SGU", URL_SGU)]),
        )
        return

    await responder(
        update.message, context,
        "✅ Tus credenciales estimadas para el SGU son:\n\n"
        f"👤 Usuario SGU: {datos['usuario']}\n"
        f"📧 Correo institucional: {datos['correo']}\n"
        f"🔐 Contrasena inicial: {datos['contrasena']}\n\n"
        "Nota: Si ya cambiaste tu contrasena antes o no te permite ingresar, usa la opcion 'Olvide mi contrasena' en sgu.utm.edu.ec.",
        reply_markup=markup_botones([("Ingresar al SGU", URL_SGU)]),
    )

async def cmd_perdonar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    user = update.effective_user
    if es_grupo(chat) and not await es_usuario_admin(chat, user, update.message, context):
        await enviar_temporal(chat, context, "Solo los administradores pueden usar /perdonar.")
        return

    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target_user:
        await responder(
            update.message, context,
            "Para perdonar a un usuario, responde a uno de sus mensajes con el comando /perdonar.",
        )
        return

    perdonar_usuario_db(target_user.id)
    if es_grupo(chat):
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=target_user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=False,
                ),
            )
        except Exception:
            pass
    await responder(
        update.message, context,
        f"✅ Se han borrado las advertencias de {target_user.first_name} y puede volver a escribir.",
    )

async def cmd_anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    user = update.effective_user
    if es_grupo(chat) and not await es_usuario_admin(chat, user, update.message, context):
        await enviar_temporal(chat, context, "Solo los administradores pueden publicar anuncios.")
        return

    texto_anuncio = " ".join(context.args or []).strip()
    if not texto_anuncio and update.message.reply_to_message:
        texto_anuncio = update.message.reply_to_message.text or ""
    if not texto_anuncio:
        await responder(
            update.message, context,
            "Uso: /anuncioEscribe aqui el comunicado oficial para el grupo.",
        )
        return

    enviado = await context.bot.send_message(
        chat_id=chat.id,
        text=f"📢 COMUNICADO OFICIAL UTM\n\n{texto_anuncio}",
        reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)], incluir_volver=False),
    )
    if es_grupo(chat):
        try:
            await context.bot.pin_chat_message(chat_id=chat.id, message_id=enviado.message_id)
        except Exception:
            pass

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
        reply_markup=markup_botones(),
    )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dato = query.data

    if dato == "menu_volver":
        await responder_callback(
            query, context,
            "Menu Principal UTM - Elige una opcion o escribe tu pregunta:",
            reply_markup=menu_principal(),
        )
    elif dato == "carreras":
        await responder_callback(
            query, context,
            "🎓 Carreras UTM\nSelecciona la modalidad que deseas consultar:",
            reply_markup=markup_carreras(),
        )
    elif dato in ("carreras_presencial", "carreras_hibrida", "carreras_online", "carreras_todas"):
        mod = dato.replace("carreras_", "")
        await responder_callback(
            query, context,
            filtrar_carreras_modalidad(mod),
            reply_markup=markup_carreras(),
        )
    elif dato in SECCIONES_DB:
        await enviar_seccion_db(query.message, context, dato)
    elif dato == "calc_sgu":
        await responder_callback(
            query, context,
            "🔑 Calculador de Usuario y Correo SGU:\n\n"
            "Envia en el chat el comando:\n"
            "/miusuario PrimerNombre PrimerApellido Cedula\n\n"
            "Ejemplo:\n"
            "/miusuario Juan Perez 1312345678",
            reply_markup=markup_botones([("Ir al SGU", URL_SGU)]),
        )
    elif dato == "fechas":
        await responder_callback(
            query, context,
            INFO_FECHAS,
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
        )
    elif dato == "faq_menu":
        await responder_callback(
            query, context,
            "❓ Preguntas Frecuentes (FAQ) UTM:\nSelecciona una pregunta:",
            reply_markup=markup_faq(),
        )
    elif dato in FAQ_ITEMS:
        await responder_callback(
            query, context,
            FAQ_ITEMS[dato],
            reply_markup=markup_faq(),
        )
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
            reply_markup=markup_botones(),
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

    if es_grupo and (mensaje_tiene_enlace(update.message) or mensaje_tiene_spam(update.message)):
        if not await es_usuario_admin(update.effective_chat, user, update.message, context):
            es_enlace = mensaje_tiene_enlace(update.message)
            try:
                await update.message.delete()
            except Exception:
                pass
            await aplicar_sancion_gradual(
                update.effective_chat,
                user,
                context,
                motivo_corto="enviar enlaces" if es_enlace else "enviar spam",
                detalle_regla="Solo los administradores pueden enviar enlaces" if es_enlace else "No se permite spam ni publicidad en el grupo",
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
        await responder(
            update.message, context,
            "🎓 Carreras UTM\nSelecciona la modalidad que deseas consultar:",
            reply_markup=markup_carreras(),
        )
        return

    if any(p in texto_lower for p in ["fecha", "calendario", "cronograma", "cuando empieza"]):
        await responder(
            update.message, context,
            INFO_FECHAS,
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION), ("Ir al SGU", URL_SGU)]),
        )
        return

    if any(p in texto_lower for p in ["olvide mi contrasena", "olvidé mi contraseña", "recuperar clave", "mi usuario", "correo institucional"]):
        await responder(
            update.message, context,
            "❓ Preguntas Frecuentes (FAQ) UTM:\nSelecciona tu consulta o usa /miusuario Nombre Apellido Cedula:",
            reply_markup=markup_faq(),
        )
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
            reply_markup=markup_botones(),
        )
        return

    if any(p in texto_lower for p in ["costo", "precio", "gratis", "gratuito", "pagar"]):
        await responder(
            update.message, context,
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo.",
            reply_markup=markup_botones([("Postulacion UTM", URL_POSTULACION)]),
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

    await aplicar_sancion_gradual(
        chat,
        user,
        context,
        motivo_corto="enviar imagenes",
        detalle_regla="Solo los administradores o el propietario pueden enviar imagenes al grupo",
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

    if not (mensaje_tiene_enlace(update.message) or mensaje_tiene_spam(update.message)):
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

    await aplicar_sancion_gradual(
        chat,
        user,
        context,
        motivo_corto="enviar enlaces",
        detalle_regla="Solo los administradores o el propietario pueden enviar enlaces al grupo",
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
        ("carreras", "Carreras por modalidad"),
        ("miusuario", "Calcular usuario y correo SGU"),
        ("fechas", "Calendario de fechas 2026"),
        ("faq", "Preguntas frecuentes"),
        ("contacto", "Datos de contacto"),
        ("horarios", "Horarios de atencion"),
        ("reglas", "Reglas del grupo"),
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
    app.add_handler(CommandHandler("miusuario",  cmd_miusuario))
    app.add_handler(CommandHandler("fechas",     cmd_fechas))
    app.add_handler(CommandHandler("faq",        cmd_faq))
    app.add_handler(CommandHandler("reglas",     cmd_reglas))
    app.add_handler(CommandHandler("perdonar",   cmd_perdonar))
    app.add_handler(CommandHandler("anuncio",    cmd_anuncio))
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