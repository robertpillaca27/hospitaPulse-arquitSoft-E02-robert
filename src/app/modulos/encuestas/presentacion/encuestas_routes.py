"""HTTP routes for monthly surveys and anonymous response submission."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.modulos.auth.presentacion.dependencies import IndicatorViewer, SurveyParticipant
from app.modulos.encuestas.aplicacion.gestionar_encuesta_use_case import (
    EncuestaCerradaError,
    EncuestaNoEncontradaError,
    GestionarEncuestaUseCase,
)
from app.modulos.encuestas.aplicacion.obtener_indicadores_use_case import (
    ObtenerIndicadoresUseCase,
)
from app.modulos.encuestas.dominio.respuesta_anonima import RespuestaAnonima
from app.modulos.encuestas.infraestructura.postgres_encuesta_repository import (
    PostgresEncuestaRepository,
)
from app.modulos.encuestas.infraestructura.redis_indicadores_cache import (
    RedisIndicadoresCache,
)
from app.modulos.encuestas.presentacion.encuestas_schemas import (
    EncuestaResponse,
    IndicadoresResponse,
    RegistrarRespuestasRequest,
    RegistrarRespuestasResponse,
)
from app.shared.config import get_settings
from app.shared.database.session import get_db_session

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]


def _indicadores_cache(request: Request) -> RedisIndicadoresCache:
    """Build the Redis adapter around the application-scoped Redis client."""
    return RedisIndicadoresCache(
        request.app.state.redis,
        get_settings().redis_indicators_ttl_seconds,
    )


@router.get("/indicadores", response_model=IndicadoresResponse, summary="Consultar indicadores mensuales")
def obtener_indicadores(
    _: IndicatorViewer,
    session: DbSession,
    request: Request,
    anio: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
) -> IndicadoresResponse:
    """Return only aggregates whose monthly sample meets the N >= 5 rule."""
    resultado = ObtenerIndicadoresUseCase(
        PostgresEncuestaRepository(session),
        _indicadores_cache(request),
    ).ejecutar(anio, mes)
    return IndicadoresResponse(
        anio=resultado.anio,
        mes=resultado.mes,
        enmascarado=resultado.enmascarado,
        total_respuestas=resultado.total_respuestas,
        promedio_general=resultado.promedio_general,
        dimensiones=[
            {"dimension": item.dimension, "promedio": item.promedio}
            for item in resultado.dimensiones
        ],
    )


@router.get("/actual", response_model=EncuestaResponse, summary="Obtener o crear la encuesta mensual")
def obtener_encuesta_actual(
    _: SurveyParticipant,
    session: DbSession,
) -> EncuestaResponse:
    """Return this month's survey to an authenticated participant."""
    encuesta = GestionarEncuestaUseCase(
        PostgresEncuestaRepository(session)
    ).obtener_encuesta_actual()
    return EncuestaResponse.model_validate(encuesta, from_attributes=True)


@router.post(
    "/{encuesta_id}/respuestas",
    response_model=RegistrarRespuestasResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar respuestas anónimas",
)
def registrar_respuestas(
    encuesta_id: str,
    request: RegistrarRespuestasRequest,
    _: SurveyParticipant,
    session: DbSession,
    http_request: Request,
) -> RegistrarRespuestasResponse:
    """Store an anonymous Likert submission from an authenticated participant."""
    use_case = GestionarEncuestaUseCase(
        PostgresEncuestaRepository(session),
        _indicadores_cache(http_request),
    )
    respuestas = tuple(
        RespuestaAnonima(pregunta_id=item.pregunta_id, valor=item.valor)
        for item in request.respuestas
    )
    try:
        use_case.registrar_respuesta(encuesta_id, respuestas)
    except EncuestaNoEncontradaError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except EncuestaCerradaError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    return RegistrarRespuestasResponse(
        status="accepted",
        mensaje="Gracias. Tu respuesta anónima fue registrada.",
        anonima=True,
    )
