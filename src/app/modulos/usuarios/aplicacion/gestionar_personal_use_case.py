"""Role and account management use cases for hospital personnel."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from app.modulos.usuarios.dominio.rol_personal import RolPersonal


class UsuarioDuplicadoError(ValueError):
    """Raised when a username or email is already registered."""


class UltimoAdministradorError(ValueError):
    """Raised when a change would remove the last active administrator."""


class UsuarioNoEncontradoError(LookupError):
    """Raised when a personnel account cannot be found."""


@dataclass(frozen=True, slots=True)
class UsuarioPersonal:
    """Personnel data safe to return to the management interface."""

    id: str
    username: str
    nombre_completo: str
    email: str
    rol: RolPersonal
    activo: bool
    debe_cambiar_password: bool
    creado_en: datetime


@dataclass(frozen=True, slots=True)
class NuevoUsuarioPersonal:
    """Validated attributes for creating a staff account."""

    username: str
    nombre_completo: str
    email: str
    rol: RolPersonal


class PersonalRepositoryPort(Protocol):
    """Persistence operations required by personnel management."""

    def listar(self) -> list[UsuarioPersonal]: ...

    def obtener(self, usuario_id: str) -> UsuarioPersonal | None: ...

    def crear(
        self, id: str, datos: NuevoUsuarioPersonal, password_hash: str
    ) -> UsuarioPersonal: ...

    def actualizar_rol(self, usuario_id: str, rol: RolPersonal) -> UsuarioPersonal: ...

    def actualizar_estado(self, usuario_id: str, activo: bool) -> UsuarioPersonal: ...

    def restablecer_password(
        self, usuario_id: str, password_hash: str
    ) -> UsuarioPersonal: ...

    def contar_administradores_activos(self, excluir_id: str) -> int: ...


class PasswordHasherPort(Protocol):
    """Password-hashing operation required by personnel creation."""

    def hash(self, password: str) -> str: ...


class GestionarPersonalUseCase:
    """Orchestrate staff account administration through its repository port."""

    def __init__(
        self,
        repository: PersonalRepositoryPort,
        password_hasher: PasswordHasherPort,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher

    def listar(self) -> list[UsuarioPersonal]:
        """Return personnel accounts without password hashes."""
        return self._repository.listar()

    def crear(self, datos: NuevoUsuarioPersonal) -> tuple[UsuarioPersonal, str]:
        """Create an account and return its one-time temporary password."""
        from secrets import token_urlsafe

        temporary_password = token_urlsafe(18)
        password_hash = self._password_hasher.hash(temporary_password)
        user = self._repository.crear(
            id=str(uuid4()),
            datos=datos,
            password_hash=password_hash,
        )
        return user, temporary_password

    def actualizar_rol(self, usuario_id: str, rol: RolPersonal) -> UsuarioPersonal:
        """Assign a role while preserving an active administrator."""
        user = self._require_user(usuario_id)
        if user.rol == RolPersonal.ADMIN and user.activo and rol != RolPersonal.ADMIN:
            if self._repository.contar_administradores_activos(excluir_id=usuario_id) == 0:
                raise UltimoAdministradorError(
                    "No se puede quitar el rol del único administrador activo."
                )
        return self._repository.actualizar_rol(usuario_id, rol)

    def actualizar_estado(self, usuario_id: str, activo: bool) -> UsuarioPersonal:
        """Activate or deactivate an account without locking out all admins."""
        user = self._require_user(usuario_id)
        if user.rol == RolPersonal.ADMIN and user.activo and not activo:
            if self._repository.contar_administradores_activos(excluir_id=usuario_id) == 0:
                raise UltimoAdministradorError(
                    "No se puede desactivar al único administrador activo."
                )
        return self._repository.actualizar_estado(usuario_id, activo)

    def restablecer_password(self, usuario_id: str) -> tuple[UsuarioPersonal, str]:
        """Set a random one-time password and require replacement on next login."""
        self._require_user(usuario_id)
        from secrets import token_urlsafe

        temporary_password = token_urlsafe(18)
        password_hash = self._password_hasher.hash(temporary_password)
        user = self._repository.restablecer_password(usuario_id, password_hash)
        return user, temporary_password

    def _require_user(self, usuario_id: str) -> UsuarioPersonal:
        user = self._repository.obtener(usuario_id)
        if user is None:
            raise UsuarioNoEncontradoError("No se encontró la cuenta de personal.")
        return user
