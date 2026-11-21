"""Login, current-session, and password-change HTTP endpoints."""

from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.auth.infraestructura.credentials import (
    PasswordHasher,
    create_access_token,
)
from app.modulos.auth.presentacion.auth_schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    UsuarioSesionResponse,
)
from app.modulos.auth.presentacion.dependencies import (
    AUTH_COOKIE_NAME,
    CurrentUser,
    session_cookie_options,
)
from app.modulos.usuarios.infraestructura.models import UsuarioPersonalModel
from app.shared.config import get_settings
from app.shared.database.session import get_db_session

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]


@router.post("/login", response_model=UsuarioSesionResponse, summary="Iniciar sesión")
def login(request: LoginRequest, response: Response, session: DbSession) -> UsuarioSesionResponse:
    """Authenticate an active staff account and set an HttpOnly session cookie."""
    settings = get_settings()
    if settings.jwt_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación no está configurada.",
        )
    user = session.scalar(
        select(UsuarioPersonalModel).where(UsuarioPersonalModel.username == request.username)
    )
    password_hash = user.password_hash if user is not None else bcrypt.hashpw(
        b"invalid-login-timing", bcrypt.gensalt(rounds=12)
    ).decode("ascii")
    password_valid = PasswordHasher.verify(request.password, password_hash)
    if user is None or not user.activo or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=create_access_token(
            user.id,
            role=user.rol.value,
            must_change_password=user.debe_cambiar_password,
        ),
        **session_cookie_options(),
    )
    return UsuarioSesionResponse.model_validate(user)


@router.get("/me", response_model=UsuarioSesionResponse, summary="Consultar sesión actual")
def get_session(current_user: CurrentUser) -> UsuarioSesionResponse:
    """Return the identity and role associated with the authenticated cookie."""
    return UsuarioSesionResponse.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def logout(response: Response) -> Response:
    """Clear the session cookie from the browser."""
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/api/v1",
        secure=get_settings().session_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.patch("/password", response_model=UsuarioSesionResponse, summary="Cambiar contraseña")
def change_password(
    request: CambiarPasswordRequest,
    current_user: CurrentUser,
    session: DbSession,
    response: Response,
) -> UsuarioSesionResponse:
    """Replace the account password, clear its temporary-password flag, and renew session."""
    if not PasswordHasher.verify(request.password_actual, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
    if request.password_actual == request.password_nueva:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña debe ser diferente a la actual.",
        )
    current_user.password_hash = PasswordHasher.hash(request.password_nueva)
    current_user.debe_cambiar_password = False
    session.commit()
    session.refresh(current_user)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=create_access_token(
            current_user.id,
            role=current_user.rol.value,
            must_change_password=current_user.debe_cambiar_password,
        ),
        **session_cookie_options(),
    )
    return UsuarioSesionResponse.model_validate(current_user)
