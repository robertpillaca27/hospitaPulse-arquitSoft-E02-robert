"""Environment-backed settings for the API process."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings required by the API composition root."""

    cors_allowed_origins: tuple[str, ...]
    database_url: str | None
    redis_url: str
    redis_indicators_ttl_seconds: int
    jwt_secret: str | None
    admin_username: str | None
    admin_password: str | None
    admin_full_name: str
    admin_email: str
    session_cookie_secure: bool
    gemini_api_key: str | None
    gemini_model: str


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment variables with local-development defaults."""
    raw_origins = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    if not origins:
        raise ValueError("CORS_ALLOWED_ORIGINS debe incluir al menos un origen.")
    database_url = os.getenv("DATABASE_URL", "").strip() or None
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    if not redis_url:
        raise ValueError("REDIS_URL no puede estar vacío.")
    try:
        redis_indicators_ttl_seconds = int(
            os.getenv("REDIS_INDICATORS_TTL_SECONDS", "60").strip()
        )
    except ValueError as error:
        raise ValueError("REDIS_INDICATORS_TTL_SECONDS debe ser un entero positivo.") from error
    if redis_indicators_ttl_seconds < 1:
        raise ValueError("REDIS_INDICATORS_TTL_SECONDS debe ser un entero positivo.")
    jwt_secret = os.getenv("JWT_SECRET", "").strip() or None
    if jwt_secret is not None and len(jwt_secret) < 32:
        raise ValueError("JWT_SECRET debe tener al menos 32 caracteres.")
    admin_username = os.getenv("ADMIN_USERNAME", "").strip() or None
    admin_password = os.getenv("ADMIN_PASSWORD", "") or None
    if bool(admin_username) != bool(admin_password):
        raise ValueError("ADMIN_USERNAME y ADMIN_PASSWORD deben configurarse juntos.")
    if (admin_username or admin_password) and not jwt_secret:
        raise ValueError("JWT_SECRET es obligatorio para habilitar el administrador inicial.")
    if admin_password and (len(admin_password) < 12 or len(admin_password.encode("utf-8")) > 72):
        raise ValueError("ADMIN_PASSWORD debe tener entre 12 y 72 bytes UTF-8.")
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip() or None
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    if not gemini_model:
        raise ValueError("GEMINI_MODEL no puede estar vacío.")
    return Settings(
        cors_allowed_origins=origins,
        database_url=database_url,
        redis_url=redis_url,
        redis_indicators_ttl_seconds=redis_indicators_ttl_seconds,
        jwt_secret=jwt_secret,
        admin_username=admin_username,
        admin_password=admin_password,
        admin_full_name=os.getenv("ADMIN_FULL_NAME", "Administrador HospitaPulse").strip(),
        admin_email=os.getenv("ADMIN_EMAIL", "admin@hospitapulse.local").strip(),
        session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() == "true",
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
    )
