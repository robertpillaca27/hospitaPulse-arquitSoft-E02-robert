"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import Engine

from app.api.v1.router import api_router
from app.modulos.encuestas.infraestructura.postgres_encuesta_repository import (
    ensure_current_survey,
)
from app.modulos.usuarios.infraestructura.bootstrap import ensure_initial_admin
from app.shared.config import get_settings
from app.shared.database.base import Base
from app.shared.database.session import get_engine


def create_app() -> FastAPI:
    """Create the API and configure its versioned routes and browser origins."""
    settings = get_settings()
    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=50,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.redis = redis_client
        try:
            engine: Engine | None = get_engine()
            if engine is not None:
                Base.metadata.create_all(engine)
                ensure_initial_admin(engine)
                ensure_current_survey(engine)
            yield
        finally:
            redis_client.close()

    application = FastAPI(
        title="HospitaPulse API",
        version="1.0.0",
        description="API del sistema de clima organizacional HospitaPulse.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.get("/", include_in_schema=False)
    def api_root() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "hospitaPulse-api",
            "documentation": "/docs",
            "health": "/api/v1/health",
        }

    return application


app = create_app()
