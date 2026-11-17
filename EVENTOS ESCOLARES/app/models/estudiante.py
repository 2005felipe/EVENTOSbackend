from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import datetime
from typing import Optional

class Estudiante(BaseRequestModel):
    id: Optional[int] = None
    usuario_id: int
    codigo_estudiante: str = Field(min_length=1, max_length=30)
    grado: str = Field(min_length=1, max_length=30)
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool


class EstudianteAcudienteVinculo(BaseRequestModel):
    acudiente_id: int = Field(ge=1)
    parentesco: Optional[str] = Field(default=None, max_length=50)


class EstudianteAcudientesUpdate(BaseRequestModel):
    vinculos: list[EstudianteAcudienteVinculo] = Field(default_factory=list)
