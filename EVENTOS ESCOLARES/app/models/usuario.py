from app.models.base import BaseRequestModel
import re

from pydantic import Field, StrictBool, field_validator
from datetime import datetime
from typing import Optional


_CORREO_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar_correo(valor: str) -> str:
    """Los correos se guardan en minúscula y sin espacios para que no existan duplicados por mayúsculas."""
    correo = valor.strip().lower()
    if not _CORREO_VALIDO.match(correo):
        raise ValueError("Escribe un correo electrónico válido.")
    return correo


class UsuarioCreate(BaseRequestModel):
    nombre: str = Field(min_length=1, max_length=150)
    correo: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    rol_id: int = Field(ge=1)
    estado: StrictBool
    grado: Optional[str] = Field(default=None, max_length=30)
    documento: Optional[str] = Field(default=None, max_length=30)
    telefono: Optional[str] = Field(default=None, max_length=30)
    parentesco: Optional[str] = Field(default=None, max_length=50)

    _normalizar_correo = field_validator("correo")(lambda cls, v: _normalizar_correo(v))


class UsuarioUpdate(BaseRequestModel):
    nombre: str = Field(min_length=1, max_length=150)
    correo: str = Field(min_length=3, max_length=254)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    rol_id: int = Field(ge=1)
    estado: StrictBool

    _normalizar_correo = field_validator("correo")(lambda cls, v: _normalizar_correo(v))


class UsuarioPublic(BaseRequestModel):
    id: int
    nombre: str
    correo: str
    rol_id: int
    rol_nombre: str
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool
