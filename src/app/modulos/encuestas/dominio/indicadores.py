"""Privacy-safe aggregate indicators for a monthly survey period."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndicadorDimension:
    """Aggregated Likert average for one survey dimension."""

    dimension: str
    promedio: float


@dataclass(frozen=True, slots=True)
class IndicadoresMensuales:
    """Monthly survey results, with sensitive values removed below the threshold."""

    anio: int
    mes: int
    enmascarado: bool
    total_respuestas: int | None
    promedio_general: float | None
    dimensiones: tuple[IndicadorDimension, ...]
