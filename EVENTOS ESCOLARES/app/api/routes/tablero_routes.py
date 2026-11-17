from fastapi import APIRouter, Depends

from app.core.database import Database
from app.core.security import exigir_modulo

router = APIRouter(prefix="/tablero", tags=["Tablero"])

ROLES_TABLERO = ("administrador", "coordinador", "director")


@router.get("/inscripciones")
def obtener_datos_tablero(
    usuario: dict = Depends(exigir_modulo("tablero", roles_lectura=ROLES_TABLERO)),
):
    """Filas de la vista del tablero: sin IDs ni nombres de estudiantes."""
    conn = Database().get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT actividad, categoria, lugar,
                   fecha_actividad::text   AS fecha_actividad,
                   fecha_inscripcion::text AS fecha_inscripcion,
                   grado, estado_autorizacion, asistencia
            FROM public.vw_tablero_inscripciones
            ORDER BY fecha_inscripcion DESC;
        """)
        return cursor.fetchall()
    finally:
        conn.close()