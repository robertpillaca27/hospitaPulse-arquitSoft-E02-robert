from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.modulos.asistente.presentacion import asistente_routes
from app.modulos.asistente.presentacion.asistente_routes import (
    _RATE_LIMIT_REQUESTS,
    _enforce_rate_limit,
    router,
)
from app.shared.config import get_settings


class FakeGemini:
    """Gemini client double that records only the request under test."""

    instances: list["FakeGemini"] = []
    response: object = SimpleNamespace(text="Respuesta generada.")
    provider_error: Exception | None = None

    def __init__(self, *, api_key: str, http_options: object) -> None:
        self.api_key = api_key
        self.http_options = http_options
        self.aio = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=AsyncMock(
                    return_value=self.response,
                    side_effect=self.provider_error,
                )
            ),
            aclose=AsyncMock(),
        )
        self.instances.append(self)


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    get_settings.cache_clear()
    FakeGemini.instances.clear()
    FakeGemini.response = SimpleNamespace(text="Respuesta generada.")
    FakeGemini.provider_error = None
    monkeypatch.setattr(asistente_routes.genai, "Client", FakeGemini)
    asistente_routes._requests_by_client.clear()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/asistente")
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
    asistente_routes._requests_by_client.clear()


def test_chat_sends_only_current_question_and_returns_gemini_answer(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/asistente/chat",
        json={"pregunta": "¿Qué es la arquitectura limpia?"},
    )

    assert response.status_code == 200
    assert response.json() == {"respuesta": "Respuesta generada."}
    gemini_client = FakeGemini.instances[0]
    request_arguments = gemini_client.aio.models.generate_content.call_args.kwargs
    assert request_arguments["model"] == "test-model"
    assert request_arguments["contents"] == "¿Qué es la arquitectura limpia?"
    assert request_arguments["config"].system_instruction == (
        asistente_routes._SYSTEM_INSTRUCTIONS
    )
    assert "respuestas de encuestas" in request_arguments["config"].system_instruction
    gemini_client.aio.aclose.assert_awaited_once()


def test_chat_rejects_empty_question(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/asistente/chat", json={"pregunta": "   "})

    assert response.status_code == 422
    assert FakeGemini.instances == []


def test_chat_rejects_conversation_history(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/asistente/chat",
        json={
            "pregunta": "¿Qué es la arquitectura limpia?",
            "historial": [{"role": "user", "content": "previous message"}],
        },
    )

    assert response.status_code == 422
    assert FakeGemini.instances == []


def test_chat_returns_service_unavailable_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/asistente")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/asistente/chat",
            json={"pregunta": "Una pregunta abierta"},
        )

    get_settings.cache_clear()
    assert response.status_code == 503


def test_chat_reports_provider_quota_without_exposing_provider_details(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRateLimitError(Exception):
        code = 429

    monkeypatch.setattr(asistente_routes.errors, "APIError", FakeRateLimitError)
    FakeGemini.provider_error = FakeRateLimitError("provider details")

    response = api_client.post(
        "/api/v1/asistente/chat",
        json={"pregunta": "Una pregunta abierta"},
    )

    assert response.status_code == 503
    assert "cuota" in response.json()["detail"]
    assert "provider details" not in response.json()["detail"]
    FakeGemini.instances[0].aio.aclose.assert_awaited_once()


def test_chat_explains_unavailable_gemini_model_without_provider_details(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeNotFoundError(Exception):
        code = 404

    monkeypatch.setattr(asistente_routes.errors, "APIError", FakeNotFoundError)
    FakeGemini.provider_error = FakeNotFoundError("provider details")

    response = api_client.post(
        "/api/v1/asistente/chat",
        json={"pregunta": "Una pregunta abierta"},
    )

    assert response.status_code == 503
    assert "modelo Gemini configurado" in response.json()["detail"]
    assert "provider details" not in response.json()["detail"]
    FakeGemini.instances[0].aio.aclose.assert_awaited_once()


def test_rate_limit_rejects_requests_after_configured_window_limit() -> None:
    asistente_routes._requests_by_client.clear()
    for request_index in range(_RATE_LIMIT_REQUESTS):
        _enforce_rate_limit("test-client", now=float(request_index))

    with pytest.raises(HTTPException) as error:
        _enforce_rate_limit("test-client", now=float(_RATE_LIMIT_REQUESTS))

    assert error.value.status_code == 429
    asistente_routes._requests_by_client.clear()
