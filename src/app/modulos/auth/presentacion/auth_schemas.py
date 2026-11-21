"""Strict request and response schemas for session management."""

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from app.modulos.usuarios.dominio.rol_personal import RolPersonal


class LoginRequest(BaseModel):
    """Username and password submitted to establish a session."""

    model_config = ConfigDict(extra="forbid")

    username: StrictStr = Field(min_length=1, max_length=64)
    password: StrictStr = Field(min_length=1, max_length=128)


class CambiarPasswordRequest(BaseModel):
    """Current and replacement credentials."""

    model_config = ConfigDict(extra="forbid")

    password_actual: StrictStr = Field(min_length=1, max_length=128)
    password_nueva: StrictStr = Field(min_length=12, max_length=72)

    @field_validator("password_nueva")
    @classmethod
    def validate_password_bytes(cls, password: str) -> str:
        """Ensure bcrypt can safely process the UTF-8 encoded password."""
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La nueva contraseña no puede superar 72 bytes UTF-8.")
        return password


class UsuarioSesionResponse(BaseModel):
    """Safe identity and authorization data for the current session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    nombre_completo: str
    email: str
    rol: RolPersonal
    activo: bool
    debe_cambiar_password: bool
