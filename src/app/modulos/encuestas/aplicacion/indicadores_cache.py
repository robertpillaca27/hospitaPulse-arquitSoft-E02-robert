"""Application port for caching privacy-safe aggregate indicators."""

from typing import Protocol

from app.modulos.encuestas.dominio.indicadores import IndicadoresMensuales


class CacheUnavailableError(RuntimeError):
    """Raised when an indicator cache operation cannot be completed."""


class IndicadoresCache(Protocol):
    """Cache port used by application use cases without Redis coupling."""

    def obtener(self, anio: int, mes: int) -> IndicadoresMensuales | None: ...

    def guardar(self, indicadores: IndicadoresMensuales) -> None: ...

    def invalidar(self, anio: int, mes: int) -> None: ...
