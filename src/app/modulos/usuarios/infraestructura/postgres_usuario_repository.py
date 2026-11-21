"""PostgreSQL adapter for personnel accounts and their authorization roles."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modulos.usuarios.aplicacion.gestionar_personal_use_case import (
    NuevoUsuarioPersonal,
    UsuarioDuplicadoError,
    UsuarioPersonal,
)
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.modulos.usuarios.infraestructura.models import UsuarioPersonalModel


class PostgresUsuarioPersonalRepository:
    """Persist staff account data and map it to safe application records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def listar(self) -> list[UsuarioPersonal]:
        """List personnel accounts ordered by name."""
        models = self._session.scalars(
            select(UsuarioPersonalModel).order_by(UsuarioPersonalModel.nombre_completo)
        ).all()
        return [self._to_domain(model) for model in models]

    def obtener(self, usuario_id: str) -> UsuarioPersonal | None:
        """Load a single account without its credential hash."""
        model = self._session.get(UsuarioPersonalModel, usuario_id)
        return self._to_domain(model) if model is not None else None

    def buscar_por_username(self, username: str) -> UsuarioPersonalModel | None:
        """Load a credential model for login verification."""
        return self._session.scalar(
            select(UsuarioPersonalModel).where(UsuarioPersonalModel.username == username)
        )

    def crear(
        self,
        id: str,
        datos: NuevoUsuarioPersonal,
        password_hash: str,
    ) -> UsuarioPersonal:
        """Insert a staff account, translating uniqueness violations to a conflict."""
        model = UsuarioPersonalModel(
            id=id,
            username=datos.username,
            nombre_completo=datos.nombre_completo,
            email=datos.email,
            rol=datos.rol,
            activo=True,
            password_hash=password_hash,
            debe_cambiar_password=True,
        )
        self._session.add(model)
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise UsuarioDuplicadoError(
                "El nombre de usuario o correo ya está registrado."
            ) from error
        self._session.refresh(model)
        return self._to_domain(model)

    def actualizar_rol(self, usuario_id: str, rol: RolPersonal) -> UsuarioPersonal:
        """Save the user's new role."""
        model = self._session.get(UsuarioPersonalModel, usuario_id)
        if model is None:
            raise LookupError("No se encontró la cuenta de personal.")
        model.rol = rol
        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    def actualizar_estado(self, usuario_id: str, activo: bool) -> UsuarioPersonal:
        """Save account activation state."""
        model = self._session.get(UsuarioPersonalModel, usuario_id)
        if model is None:
            raise LookupError("No se encontró la cuenta de personal.")
        model.activo = activo
        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    def restablecer_password(self, usuario_id: str, password_hash: str) -> UsuarioPersonal:
        """Save a temporary password hash and require a change after login."""
        model = self._session.get(UsuarioPersonalModel, usuario_id)
        if model is None:
            raise LookupError("No se encontró la cuenta de personal.")
        model.password_hash = password_hash
        model.debe_cambiar_password = True
        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    def contar_administradores_activos(self, excluir_id: str) -> int:
        """Count other active admin accounts while locking their rows for update."""
        query = (
            select(UsuarioPersonalModel.id)
            .where(
                UsuarioPersonalModel.rol == RolPersonal.ADMIN,
                UsuarioPersonalModel.activo.is_(True),
                UsuarioPersonalModel.id != excluir_id,
            )
            .with_for_update()
        )
        return len(self._session.scalars(query).all())

    @staticmethod
    def _to_domain(model: UsuarioPersonalModel) -> UsuarioPersonal:
        return UsuarioPersonal(
            id=model.id,
            username=model.username,
            nombre_completo=model.nombre_completo,
            email=model.email,
            rol=model.rol,
            activo=model.activo,
            debe_cambiar_password=model.debe_cambiar_password,
            creado_en=model.creado_en,
        )
