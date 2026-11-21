"""Administrator-only endpoints for personnel account access management."""

from typing import Annotated
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import ValidationError
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.modulos.auth.infraestructura.credentials import PasswordHasher
from app.modulos.auth.presentacion.dependencies import AdminUser
from app.modulos.usuarios.aplicacion.gestionar_personal_use_case import (
    GestionarPersonalUseCase,
    NuevoUsuarioPersonal,
    UltimoAdministradorError,
    UsuarioDuplicadoError,
    UsuarioNoEncontradoError,
)
from app.modulos.usuarios.infraestructura.postgres_usuario_repository import (
    PostgresUsuarioPersonalRepository,
)
from app.modulos.usuarios.presentacion.usuarios_schemas import (
    CambiarEstadoRequest,
    CambiarRolRequest,
    CrearUsuarioRequest,
    ImportacionPersonalResponse,
    ImportacionUsuarioCreado,
    ImportacionUsuarioError,
    UsuarioCreadoResponse,
    UsuarioPersonalResponse,
)
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.shared.database.session import get_db_session

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]


def _use_case(session: Session) -> GestionarPersonalUseCase:
    return GestionarPersonalUseCase(
        PostgresUsuarioPersonalRepository(session),
        PasswordHasher(),
    )


@router.get("", response_model=list[UsuarioPersonalResponse], summary="Listar personal y roles")
def listar_personal(_: AdminUser, session: DbSession) -> list[UsuarioPersonalResponse]:
    """Return staff accounts for administrator role management."""
    return [UsuarioPersonalResponse.model_validate(user) for user in _use_case(session).listar()]


@router.post(
    "",
    response_model=UsuarioCreadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cuenta de personal",
)
def crear_personal(
    request: CrearUsuarioRequest,
    _: AdminUser,
    session: DbSession,
) -> UsuarioCreadoResponse:
    """Create a staff account with a one-time temporary password."""
    use_case = _use_case(session)
    try:
        user, temporary_password = use_case.crear(
            NuevoUsuarioPersonal(
                username=request.username,
                nombre_completo=request.nombre_completo,
                email=str(request.email),
                rol=request.rol,
            )
        )
    except UsuarioDuplicadoError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return UsuarioCreadoResponse(
        usuario=UsuarioPersonalResponse.model_validate(user),
        password_temporal=temporary_password,
    )


@router.post(
    "/importar",
    response_model=ImportacionPersonalResponse,
    summary="Importar cuentas desde Excel",
)
async def importar_personal(
    _: AdminUser,
    session: DbSession,
    archivo: UploadFile = File(...),
) -> ImportacionPersonalResponse:
    """Import personnel rows from an XLSX workbook without storing file contents."""
    if not archivo.filename or not archivo.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecciona un archivo Excel .xlsx.",
        )

    content = await archivo.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo Excel no puede superar 5 MB.",
        )

    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es un libro Excel .xlsx válido.",
        )

    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    try:
        headers = [str(value).strip().lower() if value is not None else "" for value in next(rows)]
    except StopIteration:
        workbook.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo no contiene filas.",
        )

    header_aliases = {
        "nombre": "nombre",
        "nombre completo": "nombre",
        "nombre_completo": "nombre",
        "dni": "dni",
        "documento": "dni",
        "telefono": "telefono",
        "teléfono": "telefono",
        "numero": "telefono",
        "número": "telefono",
        "email": "email",
        "correo": "email",
        "usuario": "usuario",
        "username": "usuario",
        "rol": "rol",
    }
    normalized_headers = [
        header_aliases.get(header.replace("_", " ").strip(), header.replace("_", " ").strip())
        for header in headers
    ]
    if "nombre" not in normalized_headers:
        workbook.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El Excel debe incluir una columna Nombre o Nombre completo.",
        )

    use_case = _use_case(session)
    created: list[ImportacionUsuarioCreado] = []
    errors: list[ImportacionUsuarioError] = []
    processed = 0

    for row_number, values in enumerate(rows, start=2):
        if not any(value is not None and str(value).strip() for value in values):
            continue
        processed += 1
        row = {
            normalized_headers[index]: str(value).strip()
            if value is not None
            else ""
            for index, value in enumerate(values)
            if index < len(normalized_headers)
        }
        nombre = row.get("nombre", "")
        dni = row.get("dni", "")
        usuario = row.get("usuario", "") or dni
        email = row.get("email", "")
        rol_text = row.get("rol", "staff").strip().lower()
        rol = {
            "personal": RolPersonal.STAFF,
            "staff": RolPersonal.STAFF,
            "supervisor": RolPersonal.SUPERVISOR,
            "administrador": RolPersonal.ADMIN,
            "admin": RolPersonal.ADMIN,
        }.get(rol_text)

        if not nombre:
            errors.append(ImportacionUsuarioError(fila=row_number, nombre=nombre or None, usuario=usuario or None, error="Nombre completo vacío."))
            continue
        if not usuario:
            errors.append(ImportacionUsuarioError(fila=row_number, nombre=nombre, usuario=None, error="Debe indicar Usuario o DNI."))
            continue
        if rol is None:
            errors.append(ImportacionUsuarioError(fila=row_number, nombre=nombre, usuario=usuario, error="Rol inválido. Use Personal, Supervisor o Administrador."))
            continue
        if not email:
            email = f"{usuario}@hospitapulse.local"

        try:
            request = CrearUsuarioRequest(
                username=usuario,
                nombre_completo=nombre,
                email=email,
                rol=rol,
            )
            user, temporary_password = use_case.crear(
                NuevoUsuarioPersonal(
                    username=request.username,
                    nombre_completo=request.nombre_completo,
                    email=str(request.email),
                    rol=request.rol,
                )
            )
            created.append(
                ImportacionUsuarioCreado(
                    fila=row_number,
                    nombre=user.nombre_completo,
                    usuario=user.username,
                    password_temporal=temporary_password,
                )
            )
        except ValidationError as error:
            errors.append(ImportacionUsuarioError(fila=row_number, nombre=nombre, usuario=usuario, error="Datos inválidos: " + "; ".join(item["msg"] for item in error.errors())))
        except UsuarioDuplicadoError as error:
            errors.append(ImportacionUsuarioError(fila=row_number, nombre=nombre, usuario=usuario, error=str(error)))

    workbook.close()
    return ImportacionPersonalResponse(
        procesados=processed,
        creados=len(created),
        omitidos=len(errors),
        creados_detalle=created,
        errores=errors,
    )


@router.patch("/{usuario_id}/rol", response_model=UsuarioPersonalResponse, summary="Cambiar rol")
def cambiar_rol(
    usuario_id: str,
    request: CambiarRolRequest,
    _: AdminUser,
    session: DbSession,
) -> UsuarioPersonalResponse:
    """Update an account role without allowing the last active admin to be removed."""
    try:
        user = _use_case(session).actualizar_rol(usuario_id, request.rol)
    except UltimoAdministradorError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UsuarioNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return UsuarioPersonalResponse.model_validate(user)


@router.patch(
    "/{usuario_id}/estado",
    response_model=UsuarioPersonalResponse,
    summary="Activar o desactivar cuenta",
)
def cambiar_estado(
    usuario_id: str,
    request: CambiarEstadoRequest,
    _: AdminUser,
    session: DbSession,
) -> UsuarioPersonalResponse:
    """Enable or disable access, preserving at least one active administrator."""
    try:
        user = _use_case(session).actualizar_estado(usuario_id, request.activo)
    except UltimoAdministradorError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UsuarioNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return UsuarioPersonalResponse.model_validate(user)


@router.post(
    "/{usuario_id}/restablecer-password",
    response_model=UsuarioCreadoResponse,
    summary="Restablecer contraseña temporal",
)
def restablecer_password(
    usuario_id: str,
    current_admin: AdminUser,
    session: DbSession,
) -> UsuarioCreadoResponse:
    """Issue a one-time credential to an administrator-authorized account."""
    if usuario_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes restablecer tu propia contraseña desde esta acción.",
        )
    try:
        user, temporary_password = _use_case(session).restablecer_password(usuario_id)
    except UsuarioNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return UsuarioCreadoResponse(
        usuario=UsuarioPersonalResponse.model_validate(user),
        password_temporal=temporary_password,
    )
