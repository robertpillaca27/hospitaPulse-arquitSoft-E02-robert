"""FastAPI dependencies that enforce session and administrator authorization."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.modulos.auth.infraestructura.credentials import SESSION_DURATION, decode_access_token
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.modulos.usuarios.infraestructura.models import UsuarioPersonalModel
from app.shared.config import get_settings
from app.shared.database.session import get_db_session

AUTH_COOKIE_NAME = "hospitapulse_session"
DbSession = Annotated[Session, Depends(get_db_session)]


def get_current_user(request: Request, session: DbSession) -> UsuarioPersonalModel:
    """Require a valid cookie token and an active account."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación no está configurada.",
        ) from error
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida o expiró.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión no válida.")
    user = session.get(UsuarioPersonalModel, user_id)
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta está inactiva o no existe.",
        )
    return user


CurrentUser = Annotated[UsuarioPersonalModel, Depends(get_current_user)]


def require_admin(current_user: CurrentUser) -> UsuarioPersonalModel:
    """Restrict account administration to an administrator with a completed password setup."""
    if current_user.rol != RolPersonal.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede gestionar accesos del personal.",
        )
    if current_user.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambia tu contraseña temporal antes de gestionar personal.",
        )
    return current_user


def require_indicator_viewer(current_user: CurrentUser) -> UsuarioPersonalModel:
    """Allow only admins and supervisors to view aggregate climate indicators."""
    if current_user.rol not in {RolPersonal.ADMIN, RolPersonal.SUPERVISOR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu rol no tiene permiso para consultar indicadores.",
        )
    if current_user.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambia tu contraseña temporal antes de consultar indicadores.",
        )
    return current_user


def _indicator_token_payload(request: Request) -> dict[str, object] | None:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación no está configurada.",
        ) from error
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida o expiró.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return payload if "role" in payload else None


def require_indicator_token_viewer(request: Request, session: DbSession) -> object:
    """Authorize current JWT claims without a database lookup on every indicator read."""
    payload = _indicator_token_payload(request)
    if payload is None:
        return require_indicator_viewer(get_current_user(request, session))

    if payload.get("role") not in {RolPersonal.ADMIN, RolPersonal.SUPERVISOR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu rol no tiene permiso para consultar indicadores.",
        )
    if payload.get("must_change_password") is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambia tu contraseña temporal antes de consultar indicadores.",
        )
    return payload


def require_survey_participant(current_user: CurrentUser) -> UsuarioPersonalModel:
    """Allow only staff accounts with a completed password setup to answer surveys."""
    if current_user.rol != RolPersonal.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La encuesta está habilitada únicamente para cuentas de personal.",
        )
    if current_user.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambia tu contraseña temporal antes de responder la encuesta.",
        )
    return current_user


AdminUser = Annotated[UsuarioPersonalModel, Depends(require_admin)]
IndicatorViewer = Annotated[object, Depends(require_indicator_token_viewer)]
SurveyParticipant = Annotated[UsuarioPersonalModel, Depends(require_survey_participant)]


def session_cookie_options() -> dict[str, object]:
    """Return cookie flags appropriate for the configured local/production scheme."""
    return {
        "httponly": True,
        "secure": get_settings().session_cookie_secure,
        "samesite": "strict",
        "path": "/api/v1",
        "max_age": int(SESSION_DURATION.total_seconds()),
    }
