"""Composition of public version 1 API routes."""

from fastapi import APIRouter

from app.modulos.asistente.presentacion.asistente_routes import router as asistente_router
from app.modulos.auth.presentacion.auth_routes import router as auth_router
from app.modulos.encuestas.presentacion.encuestas_routes import router as encuestas_router
from app.modulos.institucional.presentacion.institucional_routes import router as institucional_router
from app.modulos.usuarios.presentacion.usuarios_routes import router as usuarios_router

api_router = APIRouter()
api_router.include_router(asistente_router, prefix="/asistente", tags=["asistente"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(encuestas_router, prefix="/encuestas", tags=["encuestas"])
api_router.include_router(institucional_router, prefix="/institucional", tags=["institucional"])
api_router.include_router(usuarios_router, prefix="/personal", tags=["personal"])


@api_router.get("/health", tags=["health"], summary="Check API availability")
def health_check() -> dict[str, str]:
    """Return liveness information without implying dependency availability."""
    return {"status": "ok", "service": "hospitaPulse-api"}


@api_router.get("/", tags=["health"], summary="API root information")
def api_v1_root() -> dict[str, str]:
    """Return links to API discovery and liveness endpoints."""
    return {
        "status": "ok",
        "service": "hospitaPulse-api",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }
