"""API pública del módulo de encuestas.

Los consumidores deben importar desde este archivo los casos de uso y
contratos publicados por Encuestas, no desde sus adaptadores internos.
"""

from app.modulos.encuestas.aplicacion.gestionar_encuesta_use_case import (
    GestionarEncuestaUseCase,
)
from app.modulos.encuestas.dominio.encuesta import Encuesta, PreguntaEncuesta
from app.modulos.encuestas.dominio.encuesta_repository import EncuestaRepository
from app.modulos.encuestas.dominio.indicadores import (
    IndicadorDimension,
    IndicadoresMensuales,
)
from app.modulos.encuestas.aplicacion.obtener_indicadores_use_case import (
    ObtenerIndicadoresUseCase,
)
from app.modulos.encuestas.dominio.respuesta_anonima import RespuestaAnonima

__all__ = [
    "Encuesta",
    "EncuestaRepository",
    "GestionarEncuestaUseCase",
    "IndicadorDimension",
    "IndicadoresMensuales",
    "ObtenerIndicadoresUseCase",
    "PreguntaEncuesta",
    "RespuestaAnonima",
]
