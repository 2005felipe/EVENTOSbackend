import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.passwords import hash_password, verificar_password
from app.repositories.auth_repository import AuthRepository, normalizar_nombre


load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "eventos-escolares-api"
JWT_ACCESS_MINUTES = int(os.getenv("JWT_ACCESS_MINUTES", "30"))

if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY debe existir y tener al menos 32 caracteres.")

auth_repository = AuthRepository()
bearer_scheme = HTTPBearer(auto_error=False)

# Hash de relleno: cuando el correo no existe se verifica igualmente una contraseña,
# para que el tiempo de respuesta no revele qué correos están registrados.
_HASH_RELLENO = hash_password("relleno-contra-enumeracion")

MAX_INTENTOS_LOGIN = int(os.getenv("LOGIN_MAX_INTENTOS", "5"))
VENTANA_LOGIN_SEGUNDOS = int(os.getenv("LOGIN_VENTANA_SEGUNDOS", "900"))


class LimitadorIntentosLogin:
    """Limita los intentos fallidos por (IP, correo) en memoria.

    Es por proceso: con varios workers cada uno cuenta aparte. Suficiente para frenar
    la fuerza bruta básica; para algo más estricto usa un almacén compartido (Redis).
    """

    def __init__(self, maximo: int, ventana: int):
        self.maximo = maximo
        self.ventana = ventana
        self._fallos: dict[tuple[str, str], deque] = {}
        self._lock = threading.Lock()

    def _purgar(self, clave, ahora):
        fallos = self._fallos.get(clave)
        if fallos is None:
            return None
        while fallos and ahora - fallos[0] > self.ventana:
            fallos.popleft()
        if not fallos:
            del self._fallos[clave]
            return None
        return fallos

    def segundos_de_espera(self, clave) -> int:
        """0 si puede intentar; si no, los segundos que faltan para el próximo intento."""
        with self._lock:
            ahora = time.monotonic()
            fallos = self._purgar(clave, ahora)
            if fallos is None or len(fallos) < self.maximo:
                return 0
            return max(1, int(self.ventana - (ahora - fallos[0])))

    def registrar_fallo(self, clave):
        with self._lock:
            ahora = time.monotonic()
            self._purgar(clave, ahora)
            self._fallos.setdefault(clave, deque()).append(ahora)
            if len(self._fallos) > 10_000:  # tope de memoria: descarta lo ya vencido
                for otra in list(self._fallos):
                    self._purgar(otra, ahora)

    def limpiar(self, clave):
        with self._lock:
            self._fallos.pop(clave, None)


limitador_login = LimitadorIntentosLogin(MAX_INTENTOS_LOGIN, VENTANA_LOGIN_SEGUNDOS)


def crear_token_acceso(usuario_id: int, rol_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    claims = {
        "sub": str(usuario_id),
        "rol_id": int(rol_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=JWT_ACCESS_MINUTES),
        "iss": JWT_ISSUER,
    }
    return jwt.encode(claims, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _no_autorizado():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="La sesión no es válida o ya venció.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def obtener_usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _no_autorizado()

    try:
        claims = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["sub", "rol_id", "iat", "exp", "iss"]},
        )
        usuario_id = int(claims["sub"])
        rol_id = int(claims["rol_id"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise _no_autorizado()

    usuario = auth_repository.obtener_principal(usuario_id)
    if (
        not usuario
        or not usuario["estado"]
        or not usuario["rol_estado"]
        or int(usuario["rol_id"]) != rol_id
    ):
        raise _no_autorizado()
    return usuario


def exigir_modulo(
    *nombres_modulo: str,
    modulos_escritura: tuple[str, ...] | None = None,
    roles_lectura: tuple[str, ...] | None = None,
    roles_escritura: tuple[str, ...] | None = None,
):
    def verificar_permiso(
        request: Request,
        usuario: dict = Depends(obtener_usuario_actual),
    ):
        rol = normalizar_nombre(usuario["rol_nombre"])
        ruta = request.url.path.rstrip("/") or "/"
        partes_ruta = ruta.split("/")
        recurso = normalizar_nombre(partes_ruta[1] if len(partes_ruta) > 1 else "")
        es_lectura = request.method in {"GET", "HEAD", "OPTIONS"}

        inscripcion_propia = recurso == "inscripciones" and (
            (request.method == "POST" and ruta == "/inscripciones/propias")
            or (request.method == "DELETE" and ruta.startswith("/inscripciones/propias/"))
        )
        inscripcion_acudido = recurso == "inscripciones" and (
            (request.method == "POST" and ruta == "/inscripciones/acudidos")
            or (request.method == "DELETE" and ruta.startswith("/inscripciones/acudidos/"))
        )

        if rol == "estudiante" and recurso in {"actividades", "inscripciones"} and not es_lectura and not inscripcion_propia:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este perfil solo puede consultar estos registros.")

        if rol in {"acudiente", "padre o acudiente"} and recurso in {"actividades", "inscripciones"} and not es_lectura and not inscripcion_acudido:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este perfil solo puede consultar actividades e inscripciones vinculadas.")

        if rol in {"docente", "profesor", "entrenador"} and recurso in {"actividades", "inscripciones"} and not es_lectura:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El personal docente registra asistencia y retroalimentación; no modifica el catálogo ni las inscripciones.")

        modulos_requeridos = nombres_modulo
        if not es_lectura and modulos_escritura is not None:
            modulos_requeridos = modulos_escritura

        if not auth_repository.tiene_modulo_activo(int(usuario["rol_id"]), modulos_requeridos):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu rol no tiene permiso para este módulo.")
        roles_permitidos = roles_lectura if es_lectura else roles_escritura
        if roles_permitidos is not None and rol not in {normalizar_nombre(nombre) for nombre in roles_permitidos}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu rol no tiene permiso para esta acción.")
        return usuario

    return verificar_permiso


def autenticar_credenciales(correo: str, password: str, rol_id: int):
    usuario = auth_repository.buscar_usuario_para_login(correo, rol_id)
    if not usuario or not usuario["estado"] or not usuario["rol_estado"]:
        verificar_password(password, _HASH_RELLENO)  # igualar el tiempo de respuesta
        return None

    valido, hash_actualizado = verificar_password(password, str(usuario["password"] or ""))
    if not valido:
        return None
    if hash_actualizado:
        auth_repository.actualizar_password(
            int(usuario["id"]),
            hash_actualizado,
            str(usuario["password"]),
        )

    return usuario
