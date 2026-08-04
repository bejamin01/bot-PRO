"""Genera la guia de instalacion y configuracion del Bot UTM en formato Word."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from datetime import date

OUTPUT = r"C:\Users\leonel\Documents\bot-utm-pro\Guia_Instalacion_Bot_UTM.docx"


def add_heading(doc, text, level=1):
    return doc.add_heading(text, level=level)


def add_para(doc, text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(11)
    run.font.name = "Arial"
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(text, style="List Bullet")
    for run in p.runs:
        run.font.size = Pt(11)
        run.font.name = "Arial"
    return p


def add_numbered(doc, text):
    p = doc.add_paragraph(text, style="List Number")
    for run in p.runs:
        run.font.size = Pt(11)
        run.font.name = "Arial"
    return p


def add_note(doc, text):
    p = doc.add_paragraph()
    run = p.add_run("Nota: ")
    run.bold = True
    run.font.size = Pt(10)
    run.font.name = "Arial"
    run2 = p.add_run(text)
    run2.italic = True
    run2.font.size = Pt(10)
    run2.font.name = "Arial"
    return p


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(10)
    for ri, row in enumerate(rows):
        cells = table.rows[ri + 1].cells
        for ci, val in enumerate(row):
            cells[ci].text = val
            for p in cells[ci].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    doc.add_paragraph()
    return table


def build():
    doc = Document()

    # Estilos base
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    # Portada
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_run = title.add_run("Guia de Instalacion y Configuracion\nBot UTM Pro")
    t_run.bold = True
    t_run.font.size = Pt(24)
    t_run.font.name = "Arial"
    t_run.font.color.rgb = RGBColor(0, 51, 102)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s_run = sub.add_run(
        "Asistente virtual de Telegram para la Universidad Tecnica de Manabi\n"
        f"Version del documento: {date.today().strftime('%d/%m/%Y')} | Bot v7"
    )
    s_run.font.size = Pt(12)
    s_run.font.name = "Arial"

    doc.add_paragraph()
    repo = doc.add_paragraph()
    repo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_run = repo.add_run("Repositorio: https://github.com/Orion12l/bot-utm-pro")
    r_run.font.size = Pt(10)
    r_run.font.name = "Arial"

    doc.add_page_break()

    # Indice manual
    add_heading(doc, "Indice", 1)
    for item in [
        "1. Introduccion",
        "2. Requisitos previos",
        "3. Instalacion local (paso a paso)",
        "4. Variables de entorno",
        "5. Despliegue en Railway (paso a paso)",
        "6. Configuracion del bot en Telegram",
        "7. Verificar que funciona",
        "8. Solucion de problemas: cuando el bot NO responde",
        "9. Mantenimiento y actualizaciones",
    ]:
        add_para(doc, item)

    doc.add_page_break()

    # 1. Introduccion
    add_heading(doc, "1. Introduccion", 1)
    add_para(
        doc,
        "El Bot UTM Pro es un asistente de Telegram que responde consultas sobre "
        "admisiones, matricula (SGU), carreras, horarios y contacto de la UTM. "
        "Utiliza PostgreSQL para guardar usuarios e informacion, y Google Gemini "
        "para responder preguntas libres."
    )
    add_para(doc, "Funciones principales:", bold=True)
    add_bullet(doc, "Menu interactivo con botones y comandos (/start, /admisiones, etc.)")
    add_bullet(doc, "Moderacion en grupos (bloqueo de enlaces, advertencias)")
    add_bullet(doc, "Auto-borrado de mensajes en grupos a los 10 minutos")
    add_bullet(doc, "Mensaje de bienvenida y 'Bienvenido de nuevo' al reingresar")
    add_bullet(doc, "Arranque rapido: Telegram primero, base de datos en segundo plano")

    # 2. Requisitos
    add_heading(doc, "2. Requisitos previos", 1)
    add_table(
        doc,
        ["Requisito", "Descripcion"],
        [
            ("Cuenta Telegram", "Para crear el bot con @BotFather"),
            ("Token de Telegram", "TELEGRAM_TOKEN del bot"),
            ("API Key Gemini", "Desde Google AI Studio (aistudio.google.com)"),
            ("Python 3.11+", "Para ejecucion local"),
            ("PostgreSQL", "Opcional en local; obligatorio en Railway para persistencia"),
            ("Cuenta Railway", "Para despliegue en la nube (recomendado)"),
            ("Git", "Para clonar el repositorio"),
        ],
    )

    # 3. Instalacion local
    add_heading(doc, "3. Instalacion local (paso a paso)", 1)

    add_heading(doc, "Paso 1: Clonar el repositorio", 2)
    add_para(doc, "Abre PowerShell o terminal y ejecuta:")
    code = doc.add_paragraph("git clone https://github.com/Orion12l/bot-utm-pro.git")
    code.runs[0].font.name = "Consolas"
    code.runs[0].font.size = Pt(10)
    add_para(doc, "cd bot-utm-pro")

    add_heading(doc, "Paso 2: Crear entorno virtual", 2)
    add_numbered(doc, "python -m venv venv")
    add_numbered(doc, "En Windows: .\\venv\\Scripts\\Activate.ps1")
    add_numbered(doc, "En Linux/Mac: source venv/bin/activate")

    add_heading(doc, "Paso 3: Instalar dependencias", 2)
    add_para(doc, "pip install -r requirements.txt")
    add_note(
        doc,
        "El paquete python-telegram-bot incluye job-queue para el auto-borrado de mensajes."
    )

    add_heading(doc, "Paso 4: Configurar variables (.env)", 2)
    add_numbered(doc, "Copia .env.example como .env")
    add_numbered(doc, "Edita .env con tus valores reales (ver seccion 4)")
    add_numbered(doc, "Nunca subas el archivo .env a GitHub")

    add_heading(doc, "Paso 5: Ejecutar el bot", 2)
    add_para(doc, "python main.py")
    add_para(doc, "Debes ver en consola:")
    add_bullet(doc, "=== BOT UTM 2026-06-27-v7 ===")
    add_bullet(doc, "Telegram arranca primero, BD en background (2026-06-27-v7)")
    add_bullet(doc, "Bot UTM corriendo (polling Telegram)...")

    # 4. Variables
    add_heading(doc, "4. Variables de entorno", 1)
    add_table(
        doc,
        ["Variable", "Obligatoria", "Descripcion"],
        [
            ("TELEGRAM_TOKEN", "Si", "Token del bot desde @BotFather"),
            ("GEMINI_API_KEY", "Si", "Clave API de Google Gemini"),
            ("BOT_USERNAME", "Si", "Usuario del bot, ej: @utm_help_bot"),
            ("DATABASE_URL", "Railway", "URL interna de PostgreSQL (Railway la crea sola)"),
            ("DATABASE_PUBLIC_URL", "Si en Railway", "URL publica TCP; evita error railway.internal"),
            ("ADMIN_IDS", "No", "IDs de Telegram de admins separados por coma"),
            ("PGUSER / PGPASSWORD", "Auto", "Railway las inyecta al referenciar Postgres"),
        ],
    )
    add_note(
        doc,
        "Si DATABASE_URL contiene postgres.railway.internal, el bot ignora esa URL "
        "y usa DATABASE_PUBLIC_URL o el proxy TCP de Railway."
    )

    # 5. Railway
    add_heading(doc, "5. Despliegue en Railway (paso a paso)", 1)

    add_heading(doc, "Paso 1: Crear proyecto en Railway", 2)
    add_numbered(doc, "Entra a https://railway.app e inicia sesion")
    add_numbered(doc, "Clic en New Project > Deploy from GitHub repo")
    add_numbered(doc, "Selecciona el repositorio Orion12l/bot-utm-pro")
    add_numbered(doc, "Railway detectara el Dockerfile automaticamente")

    add_heading(doc, "Paso 2: Agregar PostgreSQL", 2)
    add_numbered(doc, "En el proyecto, clic en + New > Database > PostgreSQL")
    add_numbered(doc, "Espera a que el servicio Postgres quede activo")

    add_heading(doc, "Paso 3: Configurar variables del servicio Bot", 2)
    add_numbered(doc, "Abre el servicio del bot (no el de Postgres)")
    add_numbered(doc, "Ve a Variables y agrega manualmente:")
    add_bullet(doc, "TELEGRAM_TOKEN = (tu token)")
    add_bullet(doc, "GEMINI_API_KEY = (tu clave)")
    add_bullet(doc, "BOT_USERNAME = @utm_help_bot")
    add_bullet(doc, "ADMIN_IDS = 5504260343,6501594656 (o tus IDs)")
    add_numbered(doc, "Agrega DATABASE_PUBLIC_URL como Reference:")
    add_bullet(doc, "Clic en + New Variable > Add Reference")
    add_bullet(doc, "Servicio: Postgres > Variable: DATABASE_PUBLIC_URL")

    add_heading(doc, "Paso 4: Desplegar", 2)
    add_numbered(doc, "Railway despliega automaticamente al hacer push a main")
    add_numbered(doc, "O usa Redeploy manual en la pestana Deployments")
    add_numbered(doc, "Revisa los logs: debe aparecer la version v7")

    add_heading(doc, "Paso 5: Obtener tu ID de Telegram (ADMIN_IDS)", 2)
    add_numbered(doc, "Escribe al bot @userinfobot en Telegram")
    add_numbered(doc, "Copia tu Id y agregalo en ADMIN_IDS en Railway")

    # 6. Telegram config
    add_heading(doc, "6. Configuracion del bot en Telegram", 1)

    add_heading(doc, "6.1 Crear el bot (@BotFather)", 2)
    add_numbered(doc, "Abre Telegram y busca @BotFather")
    add_numbered(doc, "Envia /newbot y sigue las instrucciones")
    add_numbered(doc, "Guarda el token en TELEGRAM_TOKEN")
    add_numbered(doc, "Configura el username (debe coincidir con BOT_USERNAME)")

    add_heading(doc, "6.2 Agregar el bot a un grupo", 2)
    add_numbered(doc, "Crea o abre el grupo de estudio UTM")
    add_numbered(doc, "Agrega el bot como miembro")
    add_numbered(doc, "Hazlo administrador con estos permisos:")
    add_bullet(doc, "Eliminar mensajes (necesario para auto-borrado)")
    add_bullet(doc, "Banear usuarios (para moderacion de enlaces)")

    add_heading(doc, "6.3 Como usar el bot en el grupo", 2)
    add_para(doc, "En grupos, el bot solo responde si:")
    add_bullet(doc, "Mencionas al bot: @utm_help_bot admisiones")
    add_bullet(doc, "O usas un comando: /start, /admisiones, /matricula, etc.")
    add_note(doc, "En chat privado responde a cualquier mensaje sin mencionarlo.")

    # 7. Verificacion
    add_heading(doc, "7. Verificar que funciona", 1)
    add_table(
        doc,
        ["Prueba", "Resultado esperado"],
        [
            ("Chat privado: /start", "Muestra menu con botones"),
            ("Grupo: @bot admisiones", "Responde info de admisiones"),
            ("Grupo: usuario nuevo entra", "Mensaje de Bienvenido"),
            ("Grupo: usuario sale y vuelve", "Mensaje de Bienvenido de nuevo"),
            ("Grupo: consulta", "Mensajes se borran a los 10 minutos"),
            ("Logs Railway", "=== BOT UTM 2026-06-27-v7 ==="),
        ],
    )

    # 8. Troubleshooting - MAIN SECTION
    add_heading(doc, "8. Solucion de problemas: cuando el bot NO responde", 1)
    add_para(
        doc,
        "Sigue estos pasos EN ORDEN. No saltes pasos hasta confirmar cada uno."
    )

    add_heading(doc, "Paso 1: Confirmar que el bot esta en linea", 2)
    add_numbered(doc, "Abre Railway > servicio del bot > Deployments")
    add_numbered(doc, "El ultimo deploy debe estar en verde (Success)")
    add_numbered(doc, "Abre Logs y busca: Bot UTM corriendo (polling Telegram)")
    add_para(doc, "Si el servicio esta caido o en crash loop:", bold=True)
    add_bullet(doc, "Revisa que TELEGRAM_TOKEN y GEMINI_API_KEY esten configurados")
    add_bullet(doc, "Haz Redeploy manual")
    add_bullet(doc, "Si ves 'Falta la variable de entorno', agrega la variable faltante")

    add_heading(doc, "Paso 2: Verificar la version desplegada", 2)
    add_numbered(doc, "En los logs debe aparecer: === BOT UTM 2026-06-27-v7 ===")
    add_numbered(doc, "Si ves v5 o v6, Railway tiene codigo viejo")
    add_para(doc, "Solucion:", bold=True)
    add_bullet(doc, "Confirma que GitHub main tiene el ultimo commit")
    add_bullet(doc, "Redeploy en Railway")
    add_bullet(doc, "Verifica que el servicio apunta al repo correcto")

    add_heading(doc, "Paso 3: Probar en chat PRIVADO primero", 2)
    add_numbered(doc, "Abre el bot en privado (no en el grupo)")
    add_numbered(doc, "Envia /start")
    add_para(doc, "Si NO responde en privado:", bold=True)
    add_bullet(doc, "Token incorrecto o revocado: genera uno nuevo en @BotFather")
    add_bullet(doc, "Bot detenido en Railway: revisa logs de error")
    add_bullet(doc, "Error Gemini: revisa GEMINI_API_KEY valida y con cuota")

    add_heading(doc, "Paso 4: Si responde en privado pero NO en el grupo", 2)
    add_para(doc, "Causa mas comun: no mencionaste al bot.", bold=True)
    add_numbered(doc, "Escribe exactamente: @utm_help_bot hola (con el @ del bot)")
    add_numbered(doc, "O usa /start dentro del grupo")
    add_numbered(doc, "Verifica que BOT_USERNAME en Railway coincida con el @ real del bot")
    add_note(
        doc,
        "El bot ignora mensajes en grupo que no lo mencionen ni usen comandos."
    )

    add_heading(doc, "Paso 5: Revisar permisos del bot en el grupo", 2)
    add_numbered(doc, "Grupo > Administradores > selecciona el bot")
    add_numbered(doc, "Activa: Eliminar mensajes y Banear usuarios")
    add_numbered(doc, "Si el bot no es admin, puede responder pero no moderar ni borrar")

    add_heading(doc, "Paso 6: Revisar conexion a la base de datos", 2)
    add_numbered(doc, "En logs busca: Conectado a PostgreSQL o Base de datos conectada en segundo plano")
    add_numbered(doc, "Si ves: Sin DATABASE_URL o Reintento de BD fallido:")
    add_para(doc, "Solucion:", bold=True)
    add_bullet(doc, "Agrega DATABASE_PUBLIC_URL como Reference al servicio Postgres")
    add_bullet(doc, "NO uses solo postgres.railway.internal (no resuelve desde el bot)")
    add_bullet(doc, "Redeploy despues de agregar la variable")
    add_note(
        doc,
        "El bot funciona sin BD usando info local, pero pierde registro de usuarios "
        "y el mensaje 'Bienvenido de nuevo' puede fallar."
    )

    add_heading(doc, "Paso 7: Errores comunes en logs y solucion", 2)
    add_table(
        doc,
        ["Error en logs", "Causa", "Solucion"],
        [
            (
                "Falta la variable de entorno: TELEGRAM_TOKEN",
                "Variable no configurada",
                "Agregar TELEGRAM_TOKEN en Railway Variables",
            ),
            (
                "postgres.railway.internal / no resuelve",
                "URL interna sin acceso",
                "Usar DATABASE_PUBLIC_URL como Reference",
            ),
            (
                "pip: command not found (build)",
                "Build viejo con Nixpacks",
                "Usar Dockerfile (ya incluido en el repo)",
            ),
            (
                "Error Gemini / API key",
                "Clave invalida o sin cuota",
                "Renovar GEMINI_API_KEY en Google AI Studio",
            ),
            (
                "Conflict: terminated by other getUpdates",
                "Dos instancias del bot corriendo",
                "Detener bot local si Railway ya esta activo",
            ),
            (
                "Forbidden: bot is not a member",
                "Bot sacado del grupo",
                "Volver a agregar el bot al grupo",
            ),
        ],
    )

    add_heading(doc, "Paso 8: Reinicio completo (ultimo recurso)", 2)
    add_numbered(doc, "Deten cualquier copia local del bot (Ctrl+C en terminal)")
    add_numbered(doc, "Railway > servicio bot > Settings > Redeploy")
    add_numbered(doc, "Espera 2-3 minutos y revisa logs")
    add_numbered(doc, "Prueba /start en privado, luego en grupo con @bot")
    add_numbered(doc, "Si persiste, crea un servicio nuevo desde GitHub (como en la instalacion inicial)")

    add_heading(doc, "Paso 9: Checklist rapido", 2)
    add_table(
        doc,
        ["#", "Verificacion", "OK?"],
        [
            ("1", "Deploy en verde en Railway", ""),
            ("2", "Logs muestran v7 y polling activo", ""),
            ("3", "TELEGRAM_TOKEN y GEMINI_API_KEY configurados", ""),
            ("4", "DATABASE_PUBLIC_URL referenciada", ""),
            ("5", "/start funciona en chat privado", ""),
            ("6", "En grupo se usa @bot o comando", ""),
            ("7", "Bot es admin con permiso eliminar mensajes", ""),
        ],
    )

    # 9. Mantenimiento
    add_heading(doc, "9. Mantenimiento y actualizaciones", 1)
    add_bullet(doc, "Actualizar codigo: git pull && push a main (Railway redespliega solo)")
    add_bullet(doc, "Cambiar info UTM: editar INFO_* en main.py y subir (SYNC_VERSION actualiza BD)")
    add_bullet(doc, "Ver version: archivo VERSION o logs de arranque")
    add_bullet(doc, "Enlaces activos: postulacion.utm.edu.ec y sgu.utm.edu.ec (www.utm.edu.ec en mantenimiento)")
    add_bullet(doc, "Contacto soporte bot: revisar ADMIN_IDS para moderacion")

    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_run = footer.add_run(
        "Documento generado para Bot UTM Pro | Universidad Tecnica de Manabi"
    )
    f_run.font.size = Pt(9)
    f_run.italic = True

    doc.save(OUTPUT)
    print(f"Guia creada: {OUTPUT}")


if __name__ == "__main__":
    build()