"""HTTP endpoint for general questions answered by Gemini."""

from __future__ import annotations

import logging
import time
from collections import deque
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, status
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.modulos.asistente.presentacion.asistente_schemas import (
    PreguntaAsistenteRequest,
    RespuestaAsistenteResponse,
)
from app.shared.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_REQUESTS = 12
_MAX_ANSWER_LENGTH = 6000
_rate_limit_lock = Lock()
_requests_by_client: dict[str, deque[float]] = {}

_SYSTEM_INSTRUCTIONS = (
    "Eres el asistente de HospitaPulse. Responde en español, de forma clara, "
    "amable y útil, a preguntas abiertas. No tienes acceso a cuentas, datos "
    "personales, respuestas de encuestas ni indicadores internos. No afirmes "
    "haber consultado información privada o del hospital. Si una pregunta trata "
    "sobre privacidad de HospitaPulse, explica que las respuestas son anónimas "
    "y que los indicadores de grupos con menos de cinco respuestas se ocultan. "
    "Si no conoces una política específica de la institución, dilo claramente "
    "y recomienda consultar al administrador."
)


def _enforce_rate_limit(client_key: str, now: float | None = None) -> None:
    """Limit unauthenticated assistant calls per client in this API process."""
    current_time = time.monotonic() if now is None else now
    cutoff = current_time - _RATE_LIMIT_WINDOW_SECONDS
    with _rate_limit_lock:
        for key, requests in tuple(_requests_by_client.items()):
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if not requests:
                _requests_by_client.pop(key, None)
        if client_key not in _requests_by_client and len(_requests_by_client) >= 4096:
            _requests_by_client.pop(next(iter(_requests_by_client)))
        client_requests = _requests_by_client.setdefault(client_key, deque())
        if len(client_requests) >= _RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Se alcanzó el límite temporal de preguntas. Inténtalo más tarde.",
                headers={"Retry-After": str(_RATE_LIMIT_WINDOW_SECONDS)},
            )
        client_requests.append(current_time)


@router.post(
    "/chat",
    response_model=RespuestaAsistenteResponse,
    summary="Responder una pregunta abierta",
)
async def responder_pregunta(
    pregunta: PreguntaAsistenteRequest,
    request: Request,
) -> RespuestaAsistenteResponse:
    """Answer one question without sending chat history or application data."""
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El asistente de IA no está configurado. Define GEMINI_API_KEY en el backend.",
        )

    client_key = request.client.host if request.client is not None else "unknown"
    _enforce_rate_limit(client_key)
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=30_000),
    )
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=pregunta.pregunta,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTIONS,
                max_output_tokens=700,
            )
        )
    except errors.APIError as error:
        provider_status = getattr(error, "code", "no disponible")
        logger.warning(
            "El proveedor del asistente no pudo responder "
            "(tipo=%s, estado=%s).",
            type(error).__name__,
            provider_status,
        )
        if provider_status == 429 or provider_status == "429":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Gemini alcanzó su límite de uso o cuota. Revisa la cuota "
                    "del proyecto de Google AI Studio e inténtalo más tarde."
                ),
            ) from error
        if provider_status == 404 or provider_status == "404":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "El modelo Gemini configurado no está disponible. "
                    "Actualiza GEMINI_MODEL en el backend."
                ),
            ) from error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini no pudo responder en este momento. Inténtalo nuevamente.",
        ) from error
    finally:
        await client.aio.aclose()

    try:
        answer = response.text
    except (AttributeError, TypeError) as error:
        logger.error("Gemini devolvió una respuesta inválida.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El asistente devolvió una respuesta no válida.",
        ) from error

    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini devolvió una respuesta vacía.",
        )

    try:
        return RespuestaAsistenteResponse(respuesta=answer.strip()[:_MAX_ANSWER_LENGTH])
    except ValidationError as error:
        logger.error("La respuesta del asistente no cumplió el esquema esperado.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El asistente devolvió una respuesta no válida.",
        ) from error
