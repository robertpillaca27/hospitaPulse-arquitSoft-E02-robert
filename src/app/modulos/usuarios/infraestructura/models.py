"""SQLAlchemy persistence model for staff accounts and access roles."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.shared.database.base import Base


class UsuarioPersonalModel(Base):
    """A staff account; this table intentionally stores no survey answers."""

    __tablename__ = "usuarios_personal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    rol: Mapped[RolPersonal] = mapped_column(
        Enum(RolPersonal, name="rol_personal", native_enum=False),
        nullable=False,
        default=RolPersonal.STAFF,
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
