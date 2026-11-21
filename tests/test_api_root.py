from fastapi.testclient import TestClient

from app.main import app


def test_api_root_returns_discovery_links() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "hospitaPulse-api",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }


def test_api_v1_root_returns_discovery_links() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"
