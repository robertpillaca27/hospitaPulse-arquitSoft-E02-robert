"""Redis adapter for privacy-safe monthly indicator caching."""

import json
from typing import Protocol

from redis.exceptions import RedisError

from app.modulos.encuestas.aplicacion.indicadores_cache import CacheUnavailableError
from app.modulos.encuestas.dominio.indicadores import (
    IndicadorDimension,
    IndicadoresMensuales,
)

_KEY_PREFIX = "hospitapulse:encuestas:indicadores"


class RedisCacheClient(Protocol):
    """Subset of Redis commands required by the indicator cache adapter."""

    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str, ex: int) -> bool | None: ...

    def delete(self, *names: str) -> int: ...


class RedisIndicadoresCache:
    """Store only privacy-filtered monthly aggregates with a bounded lifetime."""

    def __init__(self, client: RedisCacheClient, ttl_seconds: int) -> None:
        if ttl_seconds < 1:
            raise ValueError("El TTL del caché debe ser un entero positivo.")
        self._client = client
        self._ttl_seconds = ttl_seconds

    def obtener(self, anio: int, mes: int) -> IndicadoresMensuales | None:
        """Return a cached aggregate, or a cache miss if no value is present."""
        key = self._key(anio, mes)
        try:
            raw_value = self._client.get(key)
        except RedisError as error:
            raise CacheUnavailableError("No se pudo consultar el caché de indicadores.") from error
        if raw_value is None:
            return None
        try:
            value = json.loads(raw_value)
            dimensions = tuple(
                IndicadorDimension(
                    dimension=item["dimension"],
                    promedio=float(item["promedio"]),
                )
                for item in value["dimensiones"]
            )
            result = IndicadoresMensuales(
                anio=int(value["anio"]),
                mes=int(value["mes"]),
                enmascarado=bool(value["enmascarado"]),
                total_respuestas=value["total_respuestas"],
                promedio_general=value["promedio_general"],
                dimensiones=dimensions,
            )
            if (result.anio, result.mes) != (anio, mes):
                raise ValueError("El periodo del caché no coincide con su clave.")
            self._validate_privacy(result)
            return result
        except (KeyError, TypeError, ValueError) as error:
            try:
                self._client.delete(key)
            except RedisError as redis_error:
                raise CacheUnavailableError(
                    "El caché contiene un valor inválido y no pudo eliminarse."
                ) from redis_error
            raise CacheUnavailableError("El caché contiene un valor inválido.") from error

    def guardar(self, indicadores: IndicadoresMensuales) -> None:
        """Cache an aggregate only if it already satisfies the privacy threshold."""
        try:
            self._validate_privacy(indicadores)
            value = {
                "anio": indicadores.anio,
                "mes": indicadores.mes,
                "enmascarado": indicadores.enmascarado,
                "total_respuestas": indicadores.total_respuestas,
                "promedio_general": indicadores.promedio_general,
                "dimensiones": [
                    {"dimension": item.dimension, "promedio": item.promedio}
                    for item in indicadores.dimensiones
                ],
            }
            stored = self._client.set(
                self._key(indicadores.anio, indicadores.mes),
                json.dumps(value, separators=(",", ":"), allow_nan=False),
                ex=self._ttl_seconds,
            )
            if not stored:
                raise CacheUnavailableError("Redis no confirmó el almacenamiento del indicador.")
        except RedisError as error:
            raise CacheUnavailableError("No se pudo guardar el caché de indicadores.") from error
        except (TypeError, ValueError) as error:
            raise CacheUnavailableError("No se pudo serializar el indicador para el caché.") from error

    def invalidar(self, anio: int, mes: int) -> None:
        """Remove cached aggregates for the period after a new response is saved."""
        try:
            self._client.delete(self._key(anio, mes))
        except RedisError as error:
            raise CacheUnavailableError("No se pudo invalidar el caché de indicadores.") from error

    @staticmethod
    def _key(anio: int, mes: int) -> str:
        return f"{_KEY_PREFIX}:{anio}:{mes:02d}"

    @staticmethod
    def _validate_privacy(indicadores: IndicadoresMensuales) -> None:
        """Reject cached objects that could disclose a sample smaller than five."""
        if indicadores.enmascarado:
            if (
                indicadores.total_respuestas is not None
                or indicadores.promedio_general is not None
                or indicadores.dimensiones
            ):
                raise ValueError("Un indicador enmascarado no puede contener agregados.")
            return
        if indicadores.total_respuestas is None or indicadores.total_respuestas < 5:
            raise ValueError("No se puede cachear un indicador con una muestra menor que cinco.")
        if indicadores.promedio_general is None:
            raise ValueError("Un indicador no enmascarado debe incluir su promedio general.")
