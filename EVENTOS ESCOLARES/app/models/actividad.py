from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from typing import Optional
from datetime import date, datetime, time

class Actividad(BaseRequestModel):
    id: Optional[int] = None
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: Optional[str] = None
    fecha: date
    hora: time
    lugar: str = Field(min_length=1, max_length=150)
    cupo: int = Field(ge=1)
    categoria_id: int = Field(ge=1)
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool


class ActividadAsociacionesUpdate(BaseRequestModel):
    docente_ids: list[int] = Field(default_factory=list)
    estudiante_ids: list[int] = Field(default_factory=list)
