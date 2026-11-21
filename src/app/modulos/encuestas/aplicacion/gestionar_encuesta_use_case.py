"""Use cases for automatically creating monthly surveys and accepting answers."""

import logging
from datetime import date

from app.modulos.encuestas.aplicacion.indicadores_cache import (
    CacheUnavailableError,
    IndicadoresCache,
)
from app.modulos.encuestas.dominio.encuesta import (
    Encuesta,
    PLANTILLA_PULSO_MENSUAL,
)
from app.modulos.encuestas.dominio.encuesta_repository import EncuestaRepository
from app.modulos.encuestas.dominio.respuesta_anonima import RespuestaAnonima

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
logger = logging.getLogger(__name__)


class EncuestaNoEncontradaError(LookupError):
    """Raised when a requested survey does not exist."""


class EncuestaCerradaError(ValueError):
    """Raised when a response is submitted for a closed survey."""


class GestionarEncuestaUseCase:
    """Coordinate monthly survey creation and anonymous answer submission."""

    def __init__(
        self,
        repository: EncuestaRepository,
        indicadores_cache: IndicadoresCache | None = None,
    ) -> None:
        self._repository = repository
        self._indicadores_cache = indicadores_cache

    def obtener_encuesta_actual(self, hoy: date | None = None) -> Encuesta:
        """Return this month's survey, creating it once if it does not exist."""
        periodo = hoy or date.today()
        mes = _MESES[periodo.month - 1]
        return self._repository.obtener_o_crear_mensual(
            anio=periodo.year,
            mes=periodo.month,
            titulo=f"Pulso de bienestar · {mes.capitalize()} {periodo.year}",
            descripcion="Cuéntanos cómo ha sido tu experiencia en el hospital este mes.",
            preguntas=PLANTILLA_PULSO_MENSUAL,
        )

    def registrar_respuesta(
        self, encuesta_id: str, respuestas: tuple[RespuestaAnonima, ...]
    ) -> None:
        """Validate a complete response and persist it without respondent identity."""
        encuesta = self._repository.obtener_por_id(encuesta_id)
        if encuesta is None:
            raise EncuestaNoEncontradaError("La encuesta solicitada no existe.")
        if encuesta.estado != "abierta":
            raise EncuestaCerradaError("Esta encuesta ya no recibe respuestas.")

        pregunta_ids = {pregunta.id for pregunta in encuesta.preguntas}
        respuesta_ids = [respuesta.pregunta_id for respuesta in respuestas]
        if len(respuesta_ids) != len(set(respuesta_ids)):
            raise ValueError("No se permiten respuestas duplicadas para una pregunta.")
        if set(respuesta_ids) != pregunta_ids:
            raise ValueError("Debes responder todas las preguntas de la encuesta.")
        if any(not 1 <= respuesta.valor <= 5 for respuesta in respuestas):
            raise ValueError("El valor de cada respuesta debe estar entre 1 y 5.")

        self._repository.registrar_respuesta(encuesta_id, respuestas)
        if self._indicadores_cache is not None:
            try:
                self._indicadores_cache.invalidar(encuesta.anio, encuesta.mes)
            except CacheUnavailableError:
                logger.warning(
                    "Redis no disponible al invalidar indicadores tras registrar respuesta.",
                    exc_info=True,
                )
