from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from app.core.database import Database
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
import os
import tempfile

router = APIRouter(prefix="/reportes", tags=["Reportes"])

# ==========================================
# CONFIGURACIÓN DEL CORREO
# ==========================================
def obtener_config_correo() -> ConnectionConfig:
    """Se crea al enviar (no al arrancar), así el servidor levanta aunque falte el .env de correo."""
    usuario = os.getenv("MAIL_USERNAME", "").strip()
    clave = os.getenv("MAIL_PASSWORD", "").strip()
    remitente = os.getenv("MAIL_FROM", "").strip() or usuario
    if not usuario or not clave or not remitente:
        raise HTTPException(
            status_code=503,
            detail="El envío de correo no está configurado. Faltan MAIL_USERNAME, MAIL_PASSWORD o MAIL_FROM en el .env.",
        )
    return ConnectionConfig(
        MAIL_USERNAME=usuario,
        MAIL_PASSWORD=clave,
        MAIL_FROM=remitente,
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )

# ==========================================
# FUNCIONES DE APOYO (Para no repetir código)
# ==========================================
def obtener_datos(fecha_inicio, fecha_fin, nombre_estudiante):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            u.nombre AS "Estudiante", 
            a.nombre AS "Actividad", 
            i.fecha_inscripcion AS "Fecha",
            CASE WHEN i.estado THEN 'Activa' ELSE 'Pendiente' END AS "Estado"
        FROM inscripcion i
        JOIN estudiante e ON i.estudiante_id = e.id
        JOIN usuario u ON e.usuario_id = u.id
        JOIN actividad a ON i.actividad_id = a.id
        WHERE 1=1
    """
    params = []
    
    if fecha_inicio and fecha_fin:
        query += " AND i.fecha_inscripcion BETWEEN %s AND %s"
        params.extend([fecha_inicio, fecha_fin])
        
    if nombre_estudiante:
        query += " AND (u.nombre ILIKE %s OR a.nombre ILIKE %s)"
        params.extend([f"%{nombre_estudiante}%", f"%{nombre_estudiante}%"])
        
    query += ' ORDER BY i.fecha_inscripcion DESC'
    try:
        cursor.execute(query, tuple(params))
        datos = cursor.fetchall()
    finally:
        conn.close()
    
    return datos

def formatear_fechas(df):
    """Deja la columna Fecha como dd/mm/aaaa (sin hora ni zona horaria) para que el Excel se vea limpio."""
    if "Fecha" in df.columns:
        fechas = pd.to_datetime(df["Fecha"], errors="coerce", utc=True).dt.tz_localize(None)
        df["Fecha"] = fechas.dt.strftime("%d/%m/%Y").fillna("")
    return df

def estilizar_excel(writer, sheet_name):
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Estilos (Colores azules)
    color_encabezado = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    fuente_encabezado = Font(color="FFFFFF", bold=True, size=12)
    alineacion_centro = Alignment(horizontal="center", vertical="center")
    
    for cell in worksheet[1]:
        cell.fill = color_encabezado
        cell.font = fuente_encabezado
        cell.alignment = alineacion_centro
        
    # Ancho de columnas
    for i, columna in enumerate(worksheet.columns, 1):
        max_longitud = 0
        letra_columna = get_column_letter(i)
        for celda in columna:
            if celda.value:
                max_longitud = max(max_longitud, len(str(celda.value)))
        worksheet.column_dimensions[letra_columna].width = max(max_longitud + 3, 15)
        
    # Bordes
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, min_col=1, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thin_border
            if cell.row > 1: 
                cell.alignment = Alignment(horizontal="left", vertical="center")


# ==========================================
# 1. ENDPOINT PARA DESCARGAR EXCEL
# ==========================================
@router.get("/excel")
def descargar_reporte_excel(
    fecha_inicio: str = Query(None), 
    fecha_fin: str = Query(None),
    nombre_estudiante: str = Query(None),
    nombre_actividad: str = Query(None),
    orden_campo: str = Query('fecha'),
    orden_direccion: str = Query('desc')
):
    datos = obtener_datos(fecha_inicio, fecha_fin, nombre_estudiante)
    
    if not datos:
        raise HTTPException(status_code=404, detail="No hay inscripciones para estos filtros.")

    df = pd.DataFrame(datos)
    
    # Ordenamiento en Pandas
    columna_pd = 'Fecha' if orden_campo == 'fecha' else 'Estudiante' if orden_campo == 'nombre' else 'Actividad'
    df = df.sort_values(by=columna_pd, ascending=(orden_direccion == 'asc'))
    df = formatear_fechas(df)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
        estilizar_excel(writer, 'Reporte')

    output.seek(0)
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_inscripciones.xlsx"}
    )


# ==========================================
# 2. ENDPOINT PARA ENVIAR POR CORREO
# ==========================================
@router.post("/enviar-correo")
async def enviar_reporte_correo(
    correo_destino: EmailStr,
    fecha_inicio: str = Query(None), 
    fecha_fin: str = Query(None),
    nombre_estudiante: str = Query(None)
):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Validar usuario
    try:
        cursor.execute(
            "SELECT id, nombre FROM usuario WHERE LOWER(TRIM(correo)) = LOWER(TRIM(%s))",
            (correo_destino,),
        )
        usuario = cursor.fetchone()
    finally:
        conn.close()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="El correo ingresado no está registrado en la base de datos.")
    
    datos = obtener_datos(fecha_inicio, fecha_fin, nombre_estudiante)
    if not datos:
        raise HTTPException(status_code=404, detail="No hay datos para enviar con estos filtros.")

    df = formatear_fechas(pd.DataFrame(datos))
    
    # Guardar archivo físico temporal (esto evita el error de fastapi-mail)
    config_correo = obtener_config_correo()
    fd, temp_file_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    with pd.ExcelWriter(temp_file_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
        estilizar_excel(writer, 'Reporte')

    message = MessageSchema(
        subject="Reporte de Inscripciones - Colegio San Miguel",
        recipients=[correo_destino],
        body=f"Hola {usuario['nombre']},\n\nAdjunto encontrarás el reporte solicitado generado por el sistema.",
        subtype="plain",
        attachments=[temp_file_path]
    )

    try:
        fm = FastMail(config_correo)
        await fm.send_message(message)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="No se pudo enviar el correo. Revisa MAIL_USERNAME/MAIL_PASSWORD (Gmail requiere contraseña de aplicación).",
        ) from error
    finally:
        # Eliminar el archivo temporal después de enviarlo
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return {"message": f"Reporte enviado exitosamente a {correo_destino}"}