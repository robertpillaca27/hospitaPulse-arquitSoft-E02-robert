"""Read port for aggregated monthly survey indicators."""

from typing import Protocol

from app.modulos.encuestas.dominio.indicadores import IndicadoresMensuales


class IndicadoresRepository(Protocol):
    """Port implemented by the survey persistence adapter."""

    def obtener_indicadores_mensuales(self, anio: int, mes: int) -> IndicadoresMensuales: ...
