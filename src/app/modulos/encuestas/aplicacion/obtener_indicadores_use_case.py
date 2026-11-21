"""Application use case for privacy-safe monthly survey indicators."""

import logging

from app.modulos.encuestas.dominio.indicadores import IndicadoresMensuales
from app.modulos.encuestas.dominio.indicadores_repository import IndicadoresRepository
from app.modulos.encuestas.aplicacion.indicadores_cache import (
    CacheUnavailableError,
    IndicadoresCache,
)

MUESTRA_MINIMA = 5
logger = logging.getLogger(__name__)


class ObtenerIndicadoresUseCase:
    """Hide all aggregate values until the monthly sample reaches five responses."""

    def __init__(
        self,
        repository: IndicadoresRepository,
        cache: IndicadoresCache | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache

    def ejecutar(self, anio: int, mes: int) -> IndicadoresMensuales:
        """Return period indicators, masking values when fewer than five replied."""
        if self._cache is not None:
            try:
                cached = self._cache.obtener(anio, mes)
                if cached is not None:
                    return cached
            except CacheUnavailableError:
                logger.warning(
                    "Redis no disponible al consultar indicadores; se usará PostgreSQL.",
                    exc_info=True,
                )

        resultado = self._repository.obtener_indicadores_mensuales(anio, mes)
        if resultado.total_respuestas is None:
            resultado_seguro = resultado
        elif resultado.total_respuestas < MUESTRA_MINIMA:
            resultado_seguro = IndicadoresMensuales(
                anio=resultado.anio,
                mes=resultado.mes,
                enmascarado=True,
                total_respuestas=None,
                promedio_general=None,
                dimensiones=(),
            )
        else:
            resultado_seguro = resultado

        if self._cache is not None:
            try:
                self._cache.guardar(resultado_seguro)
            except CacheUnavailableError:
                logger.warning(
                    "Redis no disponible al guardar indicadores; se responderá desde PostgreSQL.",
                    exc_info=True,
                )
        return resultado_seguro
