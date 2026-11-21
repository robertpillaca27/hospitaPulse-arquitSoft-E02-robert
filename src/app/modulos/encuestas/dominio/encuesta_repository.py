"""Persistence port for monthly surveys and anonymous responses."""

from typing import Protocol

from app.modulos.encuestas.dominio.encuesta import Encuesta, PreguntaPlantilla
from app.modulos.encuestas.dominio.respuesta_anonima import RespuestaAnonima


class EncuestaRepository(Protocol):
    """Port implemented by the PostgreSQL survey adapter."""

    def obtener_o_crear_mensual(
        self,
        anio: int,
        mes: int,
        titulo: str,
        descripcion: str,
        preguntas: tuple[PreguntaPlantilla, ...],
    ) -> Encuesta: ...

    def obtener_por_id(self, encuesta_id: str) -> Encuesta | None: ...

    def registrar_respuesta(
        self, encuesta_id: str, respuestas: tuple[RespuestaAnonima, ...]
    ) -> None: ...
