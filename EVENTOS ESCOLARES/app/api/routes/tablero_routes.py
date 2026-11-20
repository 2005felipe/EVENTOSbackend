from typing import Optional
from fastapi import APIRouter, Depends, Query
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
        
@router.get("/resumen")
def obtener_resumen_tablero(
    categoria: Optional[str] = Query(default=None),
    grado: Optional[str] = Query(default=None),
    desde: Optional[str] = Query(default=None),
    hasta: Optional[str] = Query(default=None),
    usuario: dict = Depends(exigir_modulo("tablero", roles_lectura=ROLES_TABLERO)),
):
    """Resumen agregado para los gráficos del tablero."""
    conn = Database().get_connection()
    try:
        cursor = conn.cursor()

        condiciones = []
        parametros = []

        if categoria:
            condiciones.append("categoria = %s")
            parametros.append(categoria)
        if grado:
            condiciones.append("grado = %s")
            parametros.append(grado)
        if desde:
            condiciones.append("fecha_inscripcion::date >= %s::date")
            parametros.append(desde)
        if hasta:
            condiciones.append("fecha_inscripcion::date <= %s::date")
            parametros.append(hasta)

        where_sql = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

        def consultar(sql: str):
            cursor.execute(sql, parametros)
            return cursor.fetchall()

        por_autorizacion = consultar(f"""
            SELECT COALESCE(estado_autorizacion::text, 'Sin estado') AS estado,
                   COUNT(*)::int AS total
            FROM public.vw_tablero_inscripciones
            {where_sql}
            GROUP BY estado
            ORDER BY total DESC;
        """)

        por_categoria = consultar(f"""
            SELECT COALESCE(categoria::text, 'Sin categoría') AS categoria,
                   COUNT(*)::int AS total
            FROM public.vw_tablero_inscripciones
            {where_sql}
            GROUP BY categoria
            ORDER BY total DESC;
        """)

        por_asistencia = consultar(f"""
            SELECT COALESCE(asistencia::text, 'Sin registro') AS estado,
                   COUNT(*)::int AS total
            FROM public.vw_tablero_inscripciones
            {where_sql}
            GROUP BY estado
            ORDER BY total DESC;
        """)

        por_actividad = consultar(f"""
            SELECT COALESCE(actividad::text, 'Sin actividad') AS actividad,
                   COUNT(*)::int AS total
            FROM public.vw_tablero_inscripciones
            {where_sql}
            GROUP BY actividad
            ORDER BY total DESC;
        """)

        por_fecha = consultar(f"""
            SELECT COALESCE(fecha_inscripcion::date::text, 'Sin fecha') AS fecha,
                   COUNT(*)::int AS total
            FROM public.vw_tablero_inscripciones
            {where_sql}
            GROUP BY fecha
            ORDER BY fecha ASC;
        """)

        por_grado = consultar(f"""
            SELECT COALESCE(actividad::text, 'Sin actividad') AS actividad,
                   COALESCE(grado::text, 'Sin grado') AS grado,
                   COUNT(*)::int AS total
            FROM public.vw_tablero_inscripciones
            {where_sql}
            GROUP BY actividad, grado
            ORDER BY actividad ASC, grado ASC;
        """)

        return {
            "por_autorizacion": por_autorizacion,
            "por_categoria": por_categoria,
            "por_asistencia": por_asistencia,
            "por_actividad": por_actividad,
            "por_fecha": por_fecha,
            "por_grado": por_grado,
        }
    finally:
        conn.close()
