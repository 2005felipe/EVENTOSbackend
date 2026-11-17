import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from psycopg2 import errors as pg_errors

from app.core.database import ConexionBaseDatosError

load_dotenv()

from app.api.routes import (
    rol_routes, tablero_routes, usuario_routes, modulo_routes, modulo_rol_routes,
    estudiante_routes, acudiente_routes, categoria_actividad_routes,
    actividad_routes, inscripcion_routes, autorizacion_routes,
    asistencia_routes, actividad_docente_routes,
    auth_routes, notificacion_routes, reportes_routes
)
from app.core.security import exigir_modulo

ORIGENES_CORS_POR_DEFECTO = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
ORIGENES_CORS_CONFIGURADOS = [
    origen.strip().rstrip("/")
    for origen in os.getenv("CORS_ORIGINS", "").split(",")
    if origen.strip()
]

app = FastAPI(
    title="Colegio San Miguel: gestión de eventos y actividades extracurriculares",
    description="API para gestión de actividades extracurriculares con autorización digital - Colegio San Miguel",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger("eventos_escolares")

# Mensajes claros para las restricciones de la base de datos que ninguna ruta atrapó.
MENSAJES_UNICIDAD = {
    "usuario_correo_key": "Ese correo ya está registrado.",
    "usuario_correo_normalizado_key": "Ese correo ya está registrado.",
    "acudiente_documento_key": "Ese documento ya está registrado para otro acudiente.",
    "acudiente_usuario_id_key": "Esta cuenta ya tiene una ficha en el módulo de acudientes.",
    "rol_nombre_key": "Ya existe un rol con ese nombre.",
    "modulo_nombre_key": "Ya existe un módulo con ese nombre.",
    "modulo_rol_rol_id_modulo_id_key": "Ese rol ya tiene asignado ese módulo.",
    "estudiante_usuario_id_key": "Esta cuenta ya está asociada a otro estudiante.",
    "estudiante_codigo_estudiante_key": "Ese código de estudiante ya existe.",
    "actividad_docente_actividad_id_docente_id_key": "Ese docente ya está asignado a la actividad.",
}


@app.exception_handler(pg_errors.UniqueViolation)
async def manejar_unicidad(request: Request, error: pg_errors.UniqueViolation):
    restriccion = getattr(getattr(error, "diag", None), "constraint_name", None) or ""
    return JSONResponse(
        status_code=409,
        content={"detail": MENSAJES_UNICIDAD.get(restriccion, "Ya existe un registro con uno de los datos ingresados.")},
    )


@app.exception_handler(pg_errors.ForeignKeyViolation)
async def manejar_referencia(request: Request, error: pg_errors.ForeignKeyViolation):
    return JSONResponse(
        status_code=409,
        content={"detail": "El registro hace referencia a datos que no existen o está siendo usado por otros registros."},
    )


@app.exception_handler(pg_errors.CheckViolation)
@app.exception_handler(pg_errors.NotNullViolation)
@app.exception_handler(pg_errors.StringDataRightTruncation)
async def manejar_datos_invalidos(request: Request, error: psycopg2.Error):
    return JSONResponse(status_code=400, content={"detail": "Alguno de los datos enviados no es válido."})


@app.exception_handler(psycopg2.Error)
async def manejar_error_de_base_de_datos(request: Request, error: psycopg2.Error):
    logger.error("Error de base de datos en %s %s: %s", request.method, request.url.path, error)
    return JSONResponse(status_code=500, content={"detail": "Error interno al acceder a la base de datos."})


@app.exception_handler(ConexionBaseDatosError)
async def manejar_error_de_conexion(request: Request, error: ConexionBaseDatosError):
    logger.error("Error de configuración o conexión en %s %s: %s", request.method, request.url.path, error)
    return JSONResponse(status_code=503, content={"detail": "El servicio no está disponible en este momento."})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = BASE_DIR / "app" / "static" / "favicon.ico"
    return FileResponse(icon_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_CORS_CONFIGURADOS or ORIGENES_CORS_POR_DEFECTO,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(rol_routes.router, dependencies=[Depends(exigir_modulo("roles", modulos_escritura=("roles",), roles_escritura=("administrador",)))])
app.include_router(usuario_routes.router, dependencies=[Depends(exigir_modulo("usuarios", modulos_escritura=("usuarios",), roles_lectura=("administrador", "secretaria"), roles_escritura=("administrador", "secretaria")))])
app.include_router(modulo_routes.router, dependencies=[Depends(exigir_modulo("roles", modulos_escritura=("roles",), roles_lectura=("administrador",), roles_escritura=("administrador",)))])
app.include_router(modulo_rol_routes.router, dependencies=[Depends(exigir_modulo("roles", "seguridad", modulos_escritura=("roles", "seguridad"), roles_escritura=("administrador",)))])
app.include_router(estudiante_routes.router)
app.include_router(acudiente_routes.router)
app.include_router(categoria_actividad_routes.router, dependencies=[Depends(exigir_modulo("categorias", "actividades", modulos_escritura=("categorias",), roles_escritura=("administrador", "coordinador")))])
app.include_router(actividad_routes.router, dependencies=[Depends(exigir_modulo("actividades", modulos_escritura=("actividades",), roles_escritura=("administrador", "coordinador")))])
app.include_router(inscripcion_routes.router)
app.include_router(autorizacion_routes.router)
app.include_router(asistencia_routes.router)
app.include_router(actividad_docente_routes.router, dependencies=[Depends(exigir_modulo("actividades", modulos_escritura=("actividades",), roles_escritura=("administrador", "coordinador")))])
app.include_router(notificacion_routes.router)
app.include_router(reportes_routes.router)
app.include_router(tablero_routes.router)

@app.get("/")
def root():
    return {
        "Colegio": "Colegio San Miguel",
        "message": "API Gestión de Eventos y Actividades Extracurriculares",
        "docs": "/docs",
        "status": "Funcionando correctamente"
    }
