from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.security import (
    auth_repository,
    autenticar_credenciales,
    crear_token_acceso,
    limitador_login,
    obtener_usuario_actual,
)
from app.models.auth import LoginRequest


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.get("/roles")
def obtener_roles_disponibles():
    """Roles activos para el selector; la API valida la relación al autenticar."""
    return auth_repository.obtener_roles_activos()


@router.post("/login")
def iniciar_sesion(datos: LoginRequest, request: Request):
    clave = (request.client.host if request.client else "desconocida", datos.correo)
    espera = limitador_login.segundos_de_espera(clave)
    if espera:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Espera unos minutos antes de volver a intentarlo.",
            headers={"Retry-After": str(espera)},
        )

    usuario = autenticar_credenciales(datos.correo, datos.password, datos.rol_id)
    if not usuario:
        limitador_login.registrar_fallo(clave)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo, contraseña o perfil incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    limitador_login.limpiar(clave)
    perfil = auth_repository.obtener_perfil(int(usuario["id"]))
    if not perfil or not perfil["modulos"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este perfil no tiene módulos activos asignados.")

    return {
        "access_token": crear_token_acceso(int(usuario["id"]), int(usuario["rol_id"])),
        "token_type": "bearer",
        **perfil,
    }


@router.get("/me")
def obtener_perfil_actual(usuario: dict = Depends(obtener_usuario_actual)):
    perfil = auth_repository.obtener_perfil(int(usuario["id"]))
    if not perfil:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La cuenta ya no está disponible.")
    return perfil
