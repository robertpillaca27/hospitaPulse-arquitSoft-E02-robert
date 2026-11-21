"""SQLAlchemy models for surveys and identity-free answer submissions."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base


class EncuestaModel(Base):
    """A single monthly hospital-wide survey."""

    __tablename__ = "encuestas"
    __table_args__ = (
        UniqueConstraint("anio", "mes", name="uq_encuesta_periodo"),
        CheckConstraint("mes >= 1 AND mes <= 12", name="ck_encuesta_mes"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="abierta")
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    preguntas: Mapped[list["PreguntaEncuestaModel"]] = relationship(
        back_populates="encuesta", cascade="all, delete-orphan", order_by="PreguntaEncuestaModel.orden"
    )


class PreguntaEncuestaModel(Base):
    """A Likert question belonging to a monthly survey."""

    __tablename__ = "preguntas_encuesta"
    __table_args__ = (
        UniqueConstraint("encuesta_id", "orden", name="uq_pregunta_encuesta_orden"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    encuesta_id: Mapped[str] = mapped_column(
        ForeignKey("encuestas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    texto: Mapped[str] = mapped_column(String(300), nullable=False)
    encuesta: Mapped[EncuestaModel] = relationship(back_populates="preguntas")


class RespuestaEncuestaModel(Base):
    """An anonymous submission; it deliberately stores no user or service ID."""

    __tablename__ = "respuestas_encuesta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    encuesta_id: Mapped[str] = mapped_column(
        ForeignKey("encuestas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enviada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    respuestas: Mapped[list["RespuestaLikertModel"]] = relationship(
        back_populates="respuesta", cascade="all, delete-orphan"
    )


class RespuestaLikertModel(Base):
    """A Likert value linked only to its anonymous submission and question."""

    __tablename__ = "respuestas_likert"
    __table_args__ = (
        CheckConstraint("valor >= 1 AND valor <= 5", name="ck_respuesta_likert_valor"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    respuesta_id: Mapped[str] = mapped_column(
        ForeignKey("respuestas_encuesta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pregunta_id: Mapped[str] = mapped_column(
        ForeignKey("preguntas_encuesta.id", ondelete="RESTRICT"), nullable=False
    )
    valor: Mapped[int] = mapped_column(Integer, nullable=False)
    respuesta: Mapped[RespuestaEncuestaModel] = relationship(back_populates="respuestas")
