"""Strict request and response DTOs for institutional workflows."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


class StrictDTO(BaseModel):
    """Reject undeclared fields and coercion in public contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SugerenciaCreate(StrictDTO):
    categoria: StrictStr = Field(min_length=2, max_length=48)
    titulo: StrictStr | None = Field(default=None, min_length=3, max_length=160)
    detalle: StrictStr = Field(min_length=10, max_length=2000)


class SugerenciaModeracion(StrictDTO):
    categoria: StrictStr | None = Field(default=None, min_length=2, max_length=48)
    estado: Literal["en_revision", "respondida", "cerrada"]
    respuesta_publica: StrictStr | None = Field(default=None, max_length=2000)


class SugerenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    categoria: str
    titulo: str | None
    detalle: str
    estado: str
    respuesta_publica: str | None
    creada_en: datetime


class PlanCreate(StrictDTO):
    titulo: StrictStr = Field(min_length=5, max_length=160)
    objetivo: StrictStr = Field(min_length=10, max_length=2000)
    dimension: StrictStr = Field(min_length=2, max_length=80)
    responsable: StrictStr = Field(min_length=2, max_length=120)
    acciones: list[StrictStr] = Field(min_length=1, max_length=30)
    fecha_inicio: StrictStr = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    fecha_fin: StrictStr = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class PlanUpdate(StrictDTO):
    titulo: StrictStr | None = Field(default=None, min_length=5, max_length=160)
    objetivo: StrictStr | None = Field(default=None, min_length=10, max_length=2000)
    dimension: StrictStr | None = Field(default=None, min_length=2, max_length=80)
    responsable: StrictStr | None = Field(default=None, min_length=2, max_length=120)
    acciones: list[StrictStr] | None = Field(default=None, min_length=1, max_length=30)
    progreso: StrictInt | None = Field(default=None, ge=0, le=100)
    estado: Literal["borrador", "activo", "pausado", "completado"] | None = None
    fecha_inicio: StrictStr | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    fecha_fin: StrictStr | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    objetivo: str
    dimension: str
    responsable: str
    acciones: list[str]
    progreso: int
    estado: str
    fecha_inicio: str
    fecha_fin: str
    creado_en: datetime


class ReconocimientoCreate(StrictDTO):
    destinatario_id: StrictStr = Field(min_length=1, max_length=36)
    categoria: StrictStr = Field(min_length=2, max_length=48)
    motivo: StrictStr = Field(min_length=10, max_length=1000)


class PersonaDirectorioResponse(BaseModel):
    id: str
    nombre_completo: str


class ReconocimientoModeracion(StrictDTO):
    estado: Literal["aprobado", "rechazado"]


class ReconocimientoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    destinatario_id: str
    categoria: str
    motivo: str
    estado: str
    consentido: bool
    creado_en: datetime


class ConsentimientoRequest(StrictDTO):
    consentido: StrictBool


class NodoCreate(StrictDTO):
    nombre: StrictStr = Field(min_length=2, max_length=120)
    tipo: Literal["institucion", "area", "servicio", "cargo"]
    cargo: StrictStr | None = Field(default=None, max_length=120)
    padre_id: StrictStr | None = Field(default=None, max_length=36)
    orden: StrictInt = Field(default=0, ge=0, le=10000)


class NodoUpdate(StrictDTO):
    nombre: StrictStr | None = Field(default=None, min_length=2, max_length=120)
    tipo: Literal["institucion", "area", "servicio", "cargo"] | None = None
    cargo: StrictStr | None = Field(default=None, max_length=120)
    padre_id: StrictStr | None = Field(default=None, max_length=36)
    orden: StrictInt | None = Field(default=None, ge=0, le=10000)
    activo: StrictBool | None = None


class NodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    tipo: str
    cargo: str | None
    padre_id: str | None
    orden: int
    activo: bool


class EventoCreate(StrictDTO):
    titulo: StrictStr = Field(min_length=5, max_length=160)
    descripcion: StrictStr = Field(min_length=10, max_length=2000)
    inicio: AwareDatetime
    ubicacion: StrictStr = Field(min_length=2, max_length=160)
    audiencia: Literal["todos", "staff", "supervisores"] = "todos"
    cupo: StrictInt | None = Field(default=None, ge=1, le=10000)


class EventoUpdate(StrictDTO):
    titulo: StrictStr | None = Field(default=None, min_length=5, max_length=160)
    descripcion: StrictStr | None = Field(default=None, min_length=10, max_length=2000)
    inicio: AwareDatetime | None = None
    ubicacion: StrictStr | None = Field(default=None, min_length=2, max_length=160)
    audiencia: Literal["todos", "staff", "supervisores"] | None = None
    cupo: StrictInt | None = Field(default=None, ge=1, le=10000)
    estado: Literal["borrador", "publicado", "cancelado"] | None = None


class EventoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    descripcion: str
    inicio: datetime
    ubicacion: str
    audiencia: str
    cupo: int | None
    estado: str


class AsistenciaResponse(StrictDTO):
    evento_id: str
    confirmada: bool


class ComunicacionCreate(StrictDTO):
    titulo: StrictStr = Field(min_length=5, max_length=160)
    contenido: StrictStr = Field(min_length=10, max_length=5000)
    audiencia: Literal["todos", "staff", "supervisores"] = "todos"
    prioridad: Literal["normal", "alta", "urgente"] = "normal"
    vigente_desde: AwareDatetime | None = None
    vigente_hasta: AwareDatetime | None = None


class ComunicacionUpdate(StrictDTO):
    titulo: StrictStr | None = Field(default=None, min_length=5, max_length=160)
    contenido: StrictStr | None = Field(default=None, min_length=10, max_length=5000)
    audiencia: Literal["todos", "staff", "supervisores"] | None = None
    prioridad: Literal["normal", "alta", "urgente"] | None = None
    estado: Literal["borrador", "publicada", "archivada"] | None = None
    vigente_desde: AwareDatetime | None = None
    vigente_hasta: AwareDatetime | None = None


class ComunicacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    contenido: str
    audiencia: str
    prioridad: str
    estado: str
    vigente_desde: datetime | None
    vigente_hasta: datetime | None
    creado_en: datetime


class AuditoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str | None
    accion: str
    resultado: str
    recurso: str
    detalle: dict[str, object]
    creada_en: datetime
