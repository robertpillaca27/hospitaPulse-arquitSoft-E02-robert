"""Strict personnel management request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, StrictStr

from app.modulos.usuarios.dominio.rol_personal import RolPersonal


class CrearUsuarioRequest(BaseModel):
    """Administrator-provided attributes for a new staff account."""

    model_config = ConfigDict(extra="forbid")

    username: StrictStr = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9._-]+$",
    )
    nombre_completo: StrictStr = Field(min_length=3, max_length=160)
    email: EmailStr
    rol: RolPersonal = RolPersonal.STAFF


class CambiarRolRequest(BaseModel):
    """Role to assign to an existing account."""

    model_config = ConfigDict(extra="forbid")

    rol: RolPersonal


class CambiarEstadoRequest(BaseModel):
    """Activation state for an existing account."""

    model_config = ConfigDict(extra="forbid")

    activo: StrictBool


class UsuarioPersonalResponse(BaseModel):
    """Safe personnel representation; never contains a password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    nombre_completo: str
    email: str
    rol: RolPersonal
    activo: bool
    debe_cambiar_password: bool
    creado_en: datetime


class UsuarioCreadoResponse(BaseModel):
    """One-time credential delivery response for a newly created account."""

    usuario: UsuarioPersonalResponse
    password_temporal: str


class ImportacionUsuarioError(BaseModel):
    """A single Excel row that could not be imported."""

    fila: int
    nombre: str | None = None
    usuario: str | None = None
    error: str


class ImportacionUsuarioCreado(BaseModel):
    """One-time credential data for an imported account."""

    fila: int
    nombre: str
    usuario: str
    password_temporal: str


class ImportacionPersonalResponse(BaseModel):
    """Summary of a bulk personnel import."""

    procesados: int
    creados: int
    omitidos: int
    creados_detalle: list[ImportacionUsuarioCreado]
    errores: list[ImportacionUsuarioError]
