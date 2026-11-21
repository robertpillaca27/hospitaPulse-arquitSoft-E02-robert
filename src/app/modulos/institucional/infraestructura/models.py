"""Persistence models for institutional workflows and security audit events."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SugerenciaModel(Base):
    """Suggestion content without sender, session, or network identifiers."""

    __tablename__ = "sugerencias"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    categoria: Mapped[str] = mapped_column(String(48), nullable=False)
    titulo: Mapped[str | None] = mapped_column(String(160), nullable=True)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="recibida")
    respuesta_publica: Mapped[str | None] = mapped_column(Text, nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PlanMejoraModel(Base):
    """Institutional improvement plan with aggregate-only outcome tracking."""

    __tablename__ = "planes_mejora"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    objetivo: Mapped[str] = mapped_column(Text, nullable=False)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False)
    responsable: Mapped[str] = mapped_column(String(120), nullable=False)
    acciones: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    progreso: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="borrador")
    fecha_inicio: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_fin: Mapped[str] = mapped_column(String(10), nullable=False)
    creado_por: Mapped[str] = mapped_column(String(36), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReconocimientoModel(Base):
    """Voluntary recognition with recipient consent gating publication."""

    __tablename__ = "reconocimientos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    destinatario_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    nominador_id: Mapped[str] = mapped_column(String(36), nullable=False)
    categoria: Mapped[str] = mapped_column(String(48), nullable=False)
    motivo: Mapped[str] = mapped_column(String(1000), nullable=False)
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="pendiente")
    consentido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    moderado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NodoOrganigramaModel(Base):
    """Authorized organizational unit, service, or role in a hierarchy."""

    __tablename__ = "nodos_organigrama"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    cargo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    padre_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodos_organigrama.id", ondelete="SET NULL"), nullable=True, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EventoModel(Base):
    """Institutional event with published audience and optional capacity."""

    __tablename__ = "eventos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    inicio: Mapped[str] = mapped_column(String(32), nullable=False)
    ubicacion: Mapped[str] = mapped_column(String(160), nullable=False)
    audiencia: Mapped[str] = mapped_column(String(24), nullable=False, default="todos")
    cupo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="borrador")
    creado_por: Mapped[str] = mapped_column(String(36), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AsistenciaEventoModel(Base):
    """Voluntary event attendance, isolated from survey responses."""

    __tablename__ = "asistencias_eventos"
    __table_args__ = (
        UniqueConstraint("evento_id", "usuario_id", name="uq_asistencia_evento_usuario"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evento_id: Mapped[str] = mapped_column(ForeignKey("eventos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    confirmada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actualizada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ComunicacionModel(Base):
    """Institutional announcement with approval, audience, and validity."""

    __tablename__ = "comunicaciones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    audiencia: Mapped[str] = mapped_column(String(24), nullable=False, default="todos")
    prioridad: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="borrador")
    autor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    aprobado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    vigente_desde: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vigente_hasta: Mapped[str | None] = mapped_column(String(32), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventoAuditoriaModel(Base):
    """Read-only security audit record that excludes secrets and survey content."""

    __tablename__ = "eventos_auditoria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    accion: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resultado: Mapped[str] = mapped_column(String(24), nullable=False)
    recurso: Mapped[str] = mapped_column(String(64), nullable=False)
    detalle: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
