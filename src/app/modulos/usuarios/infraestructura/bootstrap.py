"""Initialize the environment-configured administrator account."""

from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.modulos.auth.infraestructura.credentials import PasswordHasher
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.modulos.usuarios.infraestructura.models import UsuarioPersonalModel
from app.shared.config import get_settings


def ensure_initial_admin(engine: Engine) -> None:
    """Create the initial admin once when bootstrap credentials are configured."""
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        return

    with Session(engine) as session:
        existing_admin = session.scalar(
            select(UsuarioPersonalModel).where(
                UsuarioPersonalModel.username == settings.admin_username
            )
        )
        if existing_admin is not None:
            return

        session.add(
            UsuarioPersonalModel(
                id=str(uuid4()),
                username=settings.admin_username,
                nombre_completo=settings.admin_full_name,
                email=settings.admin_email,
                rol=RolPersonal.ADMIN,
                activo=True,
                password_hash=PasswordHasher.hash(settings.admin_password),
                debe_cambiar_password=False,
            )
        )
        session.commit()
