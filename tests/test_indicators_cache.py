"""Unit tests for indicator caching and privacy-preserving cache behavior."""

import json
import unittest

from app.modulos.encuestas.aplicacion.obtener_indicadores_use_case import (
    ObtenerIndicadoresUseCase,
)
from app.modulos.encuestas.aplicacion.gestionar_encuesta_use_case import (
    GestionarEncuestaUseCase,
)
from app.modulos.encuestas.aplicacion.indicadores_cache import CacheUnavailableError
from app.modulos.encuestas.dominio.encuesta import Encuesta, PreguntaEncuesta
from app.modulos.encuestas.dominio.indicadores import (
    IndicadorDimension,
    IndicadoresMensuales,
)
from app.modulos.encuestas.dominio.respuesta_anonima import RespuestaAnonima
from app.modulos.encuestas.infraestructura.redis_indicadores_cache import (
    RedisIndicadoresCache,
)


class FakeRedis:
    """Minimal Redis test double that records values, TTLs, and invalidations."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.deleted: list[str] = []

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str, ex: int) -> bool:
        self.values[name] = value
        self.ttls[name] = ex
        return True

    def delete(self, *names: str) -> int:
        self.deleted.extend(names)
        return sum(self.values.pop(name, None) is not None for name in names)


class FakeIndicatorsRepository:
    """Return one configured aggregate and track database reads."""

    def __init__(self, result: IndicadoresMensuales) -> None:
        self.result = result
        self.calls = 0
        self.last_query: tuple[int, int] | None = None

    def obtener_indicadores_mensuales(self, anio: int, mes: int) -> IndicadoresMensuales:
        self.calls += 1
        self.last_query = (anio, mes)
        return self.result


class FakeIndicatorsCache:
    """Record application-level indicator cache writes and reads."""

    def __init__(self) -> None:
        self.value: IndicadoresMensuales | None = None
        self.invalidated: list[tuple[int, int]] = []
        self.requested: list[tuple[int, int]] = []
        self.failed_queries: list[tuple[int, int]] = []
        self.failed_saves: list[IndicadoresMensuales] = []

    def obtener(self, anio: int, mes: int) -> IndicadoresMensuales | None:
        self.requested.append((anio, mes))
        return self.value

    def guardar(self, indicadores: IndicadoresMensuales) -> None:
        self.value = indicadores

    def invalidar(self, anio: int, mes: int) -> None:
        self.requested.append((anio, mes))
        self.invalidated.append((anio, mes))
        self.value = None


class FakeSurveyRepository:
    """Provide an open survey and record persisted submissions."""

    def __init__(self) -> None:
        self.survey = Encuesta(
            id="survey-1",
            anio=2026,
            mes=11,
            titulo="Encuesta",
            descripcion="",
            estado="abierta",
            preguntas=(PreguntaEncuesta("question-1", 1, "clima", "Pregunta"),),
        )
        self.registered = False
        self.last_submission: tuple[str, tuple[RespuestaAnonima, ...]] | None = None

    def obtener_por_id(self, encuesta_id: str) -> Encuesta | None:
        return self.survey if encuesta_id == self.survey.id else None

    def registrar_respuesta(
        self, encuesta_id: str, respuestas: tuple[RespuestaAnonima, ...]
    ) -> None:
        self.registered = True
        self.last_submission = (encuesta_id, respuestas)


class IndicatorCacheTests(unittest.TestCase):
    def test_redis_adapter_round_trips_safe_aggregates_with_ttl(self) -> None:
        redis = FakeRedis()
        cache = RedisIndicadoresCache(redis, ttl_seconds=60)
        indicators = IndicadoresMensuales(
            anio=2026,
            mes=11,
            enmascarado=False,
            total_respuestas=5,
            promedio_general=3.8,
            dimensiones=(IndicadorDimension("Clima", 4.0),),
        )

        cache.guardar(indicators)

        key = "hospitapulse:encuestas:indicadores:2026:11"
        self.assertEqual(redis.ttls[key], 60)
        stored = json.loads(redis.values[key])
        self.assertEqual(
            set(stored),
            {
                "anio",
                "mes",
                "enmascarado",
                "total_respuestas",
                "promedio_general",
                "dimensiones",
            },
        )
        self.assertEqual(cache.obtener(2026, 11), indicators)

    def test_redis_adapter_refuses_to_cache_subthreshold_aggregates(self) -> None:
        cache = RedisIndicadoresCache(FakeRedis(), ttl_seconds=60)
        unsafe_indicators = IndicadoresMensuales(
            anio=2026,
            mes=11,
            enmascarado=False,
            total_respuestas=4,
            promedio_general=3.8,
            dimensiones=(),
        )

        with self.assertRaises(CacheUnavailableError):
            cache.guardar(unsafe_indicators)

    def test_use_case_masks_small_samples_before_caching(self) -> None:
        repository = FakeIndicatorsRepository(
            IndicadoresMensuales(
                anio=2026,
                mes=11,
                enmascarado=True,
                total_respuestas=4,
                promedio_general=None,
                dimensiones=(),
            )
        )
        cache = FakeIndicatorsCache()

        result = ObtenerIndicadoresUseCase(repository, cache).ejecutar(2026, 11)

        self.assertTrue(result.enmascarado)
        self.assertIsNone(result.total_respuestas)
        self.assertIsNone(result.promedio_general)
        self.assertEqual(result.dimensiones, ())
        self.assertEqual(cache.value, result)

    def test_cache_hit_skips_database_read(self) -> None:
        expected = IndicadoresMensuales(
            anio=2026,
            mes=11,
            enmascarado=False,
            total_respuestas=5,
            promedio_general=3.8,
            dimensiones=(),
        )
        repository = FakeIndicatorsRepository(expected)
        cache = FakeIndicatorsCache()
        cache.value = expected

        result = ObtenerIndicadoresUseCase(repository, cache).ejecutar(2026, 11)

        self.assertEqual(result, expected)
        self.assertEqual(repository.calls, 0)

    def test_cache_unavailability_falls_back_to_database(self) -> None:
        class UnavailableCache(FakeIndicatorsCache):
            def obtener(self, anio: int, mes: int) -> IndicadoresMensuales | None:
                self.failed_queries.append((anio, mes))
                raise CacheUnavailableError("Redis unavailable")

            def guardar(self, indicadores: IndicadoresMensuales) -> None:
                self.failed_saves.append(indicadores)
                raise CacheUnavailableError("Redis unavailable")

        expected = IndicadoresMensuales(
            anio=2026,
            mes=11,
            enmascarado=True,
            total_respuestas=None,
            promedio_general=None,
            dimensiones=(),
        )
        repository = FakeIndicatorsRepository(expected)

        with self.assertLogs(
            "app.modulos.encuestas.aplicacion.obtener_indicadores_use_case",
            level="WARNING",
        ):
            result = ObtenerIndicadoresUseCase(repository, UnavailableCache()).ejecutar(
                2026, 11
            )

        self.assertEqual(result, expected)
        self.assertEqual(repository.calls, 1)
        self.assertEqual(repository.last_query, (2026, 11))

    def test_submission_invalidates_its_period_cache_after_persistence(self) -> None:
        repository = FakeSurveyRepository()
        cache = FakeIndicatorsCache()

        GestionarEncuestaUseCase(repository, cache).registrar_respuesta(
            "survey-1",
            (RespuestaAnonima(pregunta_id="question-1", valor=4),),
        )

        self.assertTrue(repository.registered)
        self.assertEqual(cache.invalidated, [(2026, 11)])


if __name__ == "__main__":
    unittest.main()
