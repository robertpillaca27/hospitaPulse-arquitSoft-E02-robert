"""Protected API routes for the institutional management modules."""

from datetime import date, datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modulos.auth.presentacion.dependencies import CurrentUser, DbSession
from app.modulos.institucional.infraestructura.models import (
    AsistenciaEventoModel,
    ComunicacionModel,
    EventoAuditoriaModel,
    EventoModel,
    NodoOrganigramaModel,
    PlanMejoraModel,
    ReconocimientoModel,
    SugerenciaModel,
)
from app.modulos.institucional.presentacion.schemas import (
    AsistenciaResponse,
    AuditoriaResponse,
    ComunicacionCreate,
    ComunicacionResponse,
    ComunicacionUpdate,
    ConsentimientoRequest,
    EventoCreate,
    EventoResponse,
    EventoUpdate,
    NodoCreate,
    NodoResponse,
    NodoUpdate,
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    PersonaDirectorioResponse,
    ReconocimientoCreate,
    ReconocimientoModeracion,
    ReconocimientoResponse,
    SugerenciaCreate,
    SugerenciaModeracion,
    SugerenciaResponse,
)
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.modulos.usuarios.infraestructura.models import UsuarioPersonalModel

router = APIRouter()


def _ready_user(user: CurrentUser) -> UsuarioPersonalModel:
    if user.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambia tu contraseña temporal antes de usar esta función.",
        )
    return user


def _manager(user: CurrentUser) -> UsuarioPersonalModel:
    user = _ready_user(user)
    if user.rol not in {RolPersonal.ADMIN, RolPersonal.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para esta acción.")
    return user


def _staff(user: CurrentUser) -> UsuarioPersonalModel:
    user = _ready_user(user)
    if user.rol != RolPersonal.STAFF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta acción está disponible para personal.")
    return user


def _admin(user: CurrentUser) -> UsuarioPersonalModel:
    user = _ready_user(user)
    if user.rol != RolPersonal.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un administrador puede realizar esta acción.")
    return user


def _audit(
    session: Session,
    actor_id: str | None,
    accion: str,
    recurso: str,
    *,
    resultado: str = "exito",
    detalle: dict[str, object] | None = None,
) -> None:
    session.add(
        EventoAuditoriaModel(
            id=str(uuid4()),
            actor_id=actor_id,
            accion=accion,
            recurso=recurso,
            resultado=resultado,
            detalle=detalle or {},
        )
    )


def _commit(session: Session, actor: UsuarioPersonalModel, accion: str, recurso: str) -> None:
    _audit(session, actor.id, accion, recurso)
    session.commit()


def _iso_utc(value: datetime) -> str:
    """Normalize aware timestamps for the existing ISO-8601 text columns."""
    return value.astimezone(timezone.utc).isoformat()


@router.post(
    "/sugerencias",
    response_model=SugerenciaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar sugerencia anónima",
)
def crear_sugerencia(
    body: SugerenciaCreate,
    user: CurrentUser,
    session: DbSession,
) -> SugerenciaResponse:
    """Persist suggestion text without retaining submitter, session, or network identity."""
    _staff(user)
    record = SugerenciaModel(
        id=str(uuid4()),
        categoria=body.categoria,
        titulo=body.titulo,
        detalle=body.detalle,
        estado="recibida",
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return SugerenciaResponse.model_validate(record)


@router.get("/sugerencias", response_model=list[SugerenciaResponse], summary="Listar sugerencias para moderación")
def listar_sugerencias(
    user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[SugerenciaResponse]:
    _manager(user)
    rows = session.scalars(select(SugerenciaModel).order_by(SugerenciaModel.creada_en.desc()).limit(limit))
    return [SugerenciaResponse.model_validate(item) for item in rows]


@router.patch(
    "/sugerencias/{sugerencia_id}",
    response_model=SugerenciaResponse,
    summary="Actualizar estado y respuesta de sugerencia",
)
def moderar_sugerencia(
    sugerencia_id: str,
    body: SugerenciaModeracion,
    user: CurrentUser,
    session: DbSession,
) -> SugerenciaResponse:
    _manager(user)
    record = session.get(SugerenciaModel, sugerencia_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró la sugerencia.")
    record.estado = body.estado
    if body.categoria is not None:
        record.categoria = body.categoria
    record.respuesta_publica = body.respuesta_publica
    _commit(session, user, "moderar_sugerencia", "sugerencias")
    session.refresh(record)
    return SugerenciaResponse.model_validate(record)


@router.get("/planes-mejora", response_model=list[PlanResponse], summary="Consultar planes de mejora")
def listar_planes_mejora(user: CurrentUser, session: DbSession) -> list[PlanResponse]:
    _ready_user(user)
    statement = select(PlanMejoraModel).order_by(PlanMejoraModel.creado_en.desc())
    if user.rol == RolPersonal.STAFF:
        statement = statement.where(PlanMejoraModel.estado != "borrador")
    rows = session.scalars(statement)
    return [PlanResponse.model_validate(item) for item in rows]


@router.post(
    "/planes-mejora",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear plan de mejora",
)
def crear_plan(
    body: PlanCreate,
    user: CurrentUser,
    session: DbSession,
) -> PlanResponse:
    _manager(user)
    try:
        inicio = date.fromisoformat(body.fecha_inicio)
        fin = date.fromisoformat(body.fecha_fin)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Las fechas no son válidas.") from error
    if fin < inicio:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La fecha final debe ser posterior al inicio.")
    record = PlanMejoraModel(
        id=str(uuid4()),
        titulo=body.titulo,
        objetivo=body.objetivo,
        dimension=body.dimension,
        responsable=body.responsable,
        acciones=body.acciones,
        fecha_inicio=body.fecha_inicio,
        fecha_fin=body.fecha_fin,
        progreso=0,
        estado="borrador",
        creado_por=user.id,
    )
    session.add(record)
    _commit(session, user, "crear_plan_mejora", "planes_mejora")
    session.refresh(record)
    return PlanResponse.model_validate(record)


@router.patch("/planes-mejora/{plan_id}", response_model=PlanResponse, summary="Actualizar plan de mejora")
def actualizar_plan(
    plan_id: str,
    body: PlanUpdate,
    user: CurrentUser,
    session: DbSession,
) -> PlanResponse:
    _manager(user)
    record = session.get(PlanMejoraModel, plan_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el plan.")
    changes = body.model_dump(exclude_unset=True)
    inicio = changes.get("fecha_inicio", record.fecha_inicio)
    fin = changes.get("fecha_fin", record.fecha_fin)
    try:
        if date.fromisoformat(fin) < date.fromisoformat(inicio):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La fecha final debe ser posterior al inicio.")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Las fechas no son válidas.") from error
    for field, value in changes.items():
        setattr(record, field, value)
    _commit(session, user, "actualizar_plan_mejora", "planes_mejora")
    session.refresh(record)
    return PlanResponse.model_validate(record)


@router.get("/reconocimientos", response_model=list[ReconocimientoResponse], summary="Consultar reconocimientos")
def listar_reconocimientos(user: CurrentUser, session: DbSession) -> list[ReconocimientoResponse]:
    _ready_user(user)
    if user.rol in {RolPersonal.ADMIN, RolPersonal.SUPERVISOR}:
        statement = select(ReconocimientoModel).where(ReconocimientoModel.estado != "rechazado")
    else:
        statement = select(ReconocimientoModel).where(
            ReconocimientoModel.destinatario_id == user.id,
            or_(
                ReconocimientoModel.estado == "pendiente",
                ReconocimientoModel.estado == "aprobado",
            ),
        )
    rows = session.scalars(statement.order_by(ReconocimientoModel.creado_en.desc()))
    return [ReconocimientoResponse.model_validate(item) for item in rows]


@router.get(
    "/directorio",
    response_model=list[PersonaDirectorioResponse],
    summary="Consultar directorio institucional para nominaciones",
)
def listar_directorio(user: CurrentUser, session: DbSession) -> list[PersonaDirectorioResponse]:
    _ready_user(user)
    people = session.scalars(
        select(UsuarioPersonalModel)
        .where(
            UsuarioPersonalModel.activo.is_(True),
            UsuarioPersonalModel.id != user.id,
        )
        .order_by(UsuarioPersonalModel.nombre_completo)
    )
    return [
        PersonaDirectorioResponse(id=person.id, nombre_completo=person.nombre_completo)
        for person in people
    ]


@router.post(
    "/reconocimientos",
    response_model=ReconocimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nominar a un compañero",
)
def crear_reconocimiento(
    body: ReconocimientoCreate,
    user: CurrentUser,
    session: DbSession,
) -> ReconocimientoResponse:
    _ready_user(user)
    recipient = session.get(UsuarioPersonalModel, body.destinatario_id)
    if recipient is None or not recipient.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró a la persona destinataria.")
    if recipient.id == user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No puedes nominarte a ti mismo.")
    record = ReconocimientoModel(
        id=str(uuid4()),
        destinatario_id=recipient.id,
        nominador_id=user.id,
        categoria=body.categoria,
        motivo=body.motivo,
        estado="pendiente",
        consentido=False,
    )
    session.add(record)
    _commit(session, user, "crear_reconocimiento", "reconocimientos")
    session.refresh(record)
    return ReconocimientoResponse.model_validate(record)


@router.post("/reconocimientos/{reconocimiento_id}/consentimiento", summary="Gestionar consentimiento de publicación")
def responder_consentimiento(
    reconocimiento_id: str,
    body: ConsentimientoRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict[str, str]:
    _ready_user(user)
    record = session.get(ReconocimientoModel, reconocimiento_id)
    if record is None or record.destinatario_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el reconocimiento.")
    if record.estado == "rechazado":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El reconocimiento no está disponible.")
    record.consentido = body.consentido
    _commit(session, user, "actualizar_consentimiento_reconocimiento", "reconocimientos")
    return {"estado": "consentido" if body.consentido else "no_consentido"}


@router.patch(
    "/reconocimientos/{reconocimiento_id}",
    response_model=ReconocimientoResponse,
    summary="Moderar reconocimiento",
)
def moderar_reconocimiento(
    reconocimiento_id: str,
    body: ReconocimientoModeracion,
    user: CurrentUser,
    session: DbSession,
) -> ReconocimientoResponse:
    _manager(user)
    record = session.get(ReconocimientoModel, reconocimiento_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el reconocimiento.")
    record.estado = body.estado
    record.moderado_por = user.id
    _commit(session, user, "moderar_reconocimiento", "reconocimientos")
    session.refresh(record)
    return ReconocimientoResponse.model_validate(record)


@router.get("/organigrama", response_model=list[NodoResponse], summary="Consultar organigrama institucional")
def listar_organigrama(user: CurrentUser, session: DbSession) -> list[NodoResponse]:
    _ready_user(user)
    rows = session.scalars(
        select(NodoOrganigramaModel)
        .where(NodoOrganigramaModel.activo.is_(True))
        .order_by(NodoOrganigramaModel.orden, NodoOrganigramaModel.nombre)
    )
    return [NodoResponse.model_validate(item) for item in rows]


@router.post(
    "/organigrama",
    response_model=NodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear unidad organizacional",
)
def crear_nodo(
    body: NodoCreate,
    user: CurrentUser,
    session: DbSession,
) -> NodoResponse:
    _admin(user)
    if body.padre_id and session.get(NodoOrganigramaModel, body.padre_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La unidad superior no existe.")
    record = NodoOrganigramaModel(id=str(uuid4()), **body.model_dump(), activo=True)
    session.add(record)
    _commit(session, user, "crear_nodo_organigrama", "organigrama")
    session.refresh(record)
    return NodoResponse.model_validate(record)


@router.patch("/organigrama/{nodo_id}", response_model=NodoResponse, summary="Actualizar unidad organizacional")
def actualizar_nodo(
    nodo_id: str,
    body: NodoUpdate,
    user: CurrentUser,
    session: DbSession,
) -> NodoResponse:
    _admin(user)
    record = session.get(NodoOrganigramaModel, nodo_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró la unidad.")
    changes = body.model_dump(exclude_unset=True)
    parent_id = changes.get("padre_id", record.padre_id)
    if parent_id == nodo_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Una unidad no puede depender de sí misma.")
    if parent_id and session.get(NodoOrganigramaModel, parent_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La unidad superior no existe.")
    ancestor_id = parent_id
    while ancestor_id:
        if ancestor_id == nodo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La jerarquía no puede contener ciclos.")
        ancestor = session.get(NodoOrganigramaModel, ancestor_id)
        ancestor_id = ancestor.padre_id if ancestor else None
    for field, value in changes.items():
        setattr(record, field, value)
    _commit(session, user, "actualizar_nodo_organigrama", "organigrama")
    session.refresh(record)
    return NodoResponse.model_validate(record)


@router.get("/eventos", response_model=list[EventoResponse], summary="Consultar eventos institucionales")
def listar_eventos(user: CurrentUser, session: DbSession) -> list[EventoResponse]:
    _ready_user(user)
    if user.rol in {RolPersonal.ADMIN, RolPersonal.SUPERVISOR}:
        statement = select(EventoModel)
    else:
        statement = select(EventoModel).where(
            EventoModel.estado == "publicado",
            EventoModel.inicio >= _iso_utc(datetime.now(timezone.utc)),
            EventoModel.audiencia.in_(["todos", "staff"]),
        )
    rows = session.scalars(statement.order_by(EventoModel.inicio))
    return [EventoResponse.model_validate(item) for item in rows]


@router.post(
    "/eventos",
    response_model=EventoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear evento institucional",
)
def crear_evento(
    body: EventoCreate,
    user: CurrentUser,
    session: DbSession,
) -> EventoResponse:
    _manager(user)
    record = EventoModel(
        id=str(uuid4()),
        **body.model_dump(),
        estado="borrador",
        creado_por=user.id,
    )
    record.inicio = _iso_utc(body.inicio)
    session.add(record)
    _commit(session, user, "crear_evento", "eventos")
    session.refresh(record)
    return EventoResponse.model_validate(record)


@router.post("/eventos/{evento_id}/publicar", response_model=EventoResponse, summary="Publicar evento")
def publicar_evento(
    evento_id: str,
    user: CurrentUser,
    session: DbSession,
) -> EventoResponse:
    _manager(user)
    record = session.get(EventoModel, evento_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el evento.")
    record.estado = "publicado"
    _commit(session, user, "publicar_evento", "eventos")
    session.refresh(record)
    return EventoResponse.model_validate(record)


@router.patch("/eventos/{evento_id}", response_model=EventoResponse, summary="Actualizar o cancelar evento")
def actualizar_evento(
    evento_id: str,
    body: EventoUpdate,
    user: CurrentUser,
    session: DbSession,
) -> EventoResponse:
    _manager(user)
    record = session.get(EventoModel, evento_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el evento.")
    changes = body.model_dump(exclude_unset=True)
    if "inicio" in changes and changes["inicio"] is not None:
        changes["inicio"] = _iso_utc(changes["inicio"])
    for field, value in changes.items():
        setattr(record, field, value)
    _commit(session, user, "actualizar_evento", "eventos")
    session.refresh(record)
    return EventoResponse.model_validate(record)


@router.put("/eventos/{evento_id}/asistencia", response_model=AsistenciaResponse, summary="Confirmar asistencia")
def confirmar_asistencia(
    evento_id: str,
    user: CurrentUser,
    session: DbSession,
) -> AsistenciaResponse:
    _ready_user(user)
    event = session.scalar(
        select(EventoModel).where(EventoModel.id == evento_id).with_for_update()
    )
    if event is None or event.estado != "publicado":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el evento disponible.")
    record = session.scalar(
        select(AsistenciaEventoModel).where(
            AsistenciaEventoModel.evento_id == evento_id,
            AsistenciaEventoModel.usuario_id == user.id,
        )
    )
    if record is None:
        attendance_count = session.scalar(
            select(func.count()).select_from(AsistenciaEventoModel).where(
                AsistenciaEventoModel.evento_id == evento_id,
                AsistenciaEventoModel.confirmada.is_(True),
            )
        ) or 0
        if event.cupo is not None and attendance_count >= event.cupo:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El evento alcanzó su cupo.")
        record = AsistenciaEventoModel(
            id=str(uuid4()), evento_id=evento_id, usuario_id=user.id, confirmada=True
        )
        session.add(record)
    else:
        record.confirmada = True
    _audit(session, user.id, "confirmar_asistencia", "eventos")
    session.commit()
    return AsistenciaResponse(evento_id=evento_id, confirmada=True)


@router.delete("/eventos/{evento_id}/asistencia", status_code=status.HTTP_204_NO_CONTENT, summary="Cancelar asistencia")
def cancelar_asistencia(
    evento_id: str,
    user: CurrentUser,
    session: DbSession,
) -> None:
    _ready_user(user)
    record = session.scalar(
        select(AsistenciaEventoModel).where(
            AsistenciaEventoModel.evento_id == evento_id,
            AsistenciaEventoModel.usuario_id == user.id,
        )
    )
    if record is not None:
        session.delete(record)
        _audit(session, user.id, "cancelar_asistencia", "eventos")
        session.commit()


@router.get("/comunicaciones", response_model=list[ComunicacionResponse], summary="Consultar comunicaciones vigentes")
def listar_comunicaciones(user: CurrentUser, session: DbSession) -> list[ComunicacionResponse]:
    _ready_user(user)
    now = datetime.now(timezone.utc)
    if user.rol == RolPersonal.ADMIN:
        statement = select(ComunicacionModel)
    elif user.rol == RolPersonal.SUPERVISOR:
        statement = select(ComunicacionModel).where(
            or_(
                ComunicacionModel.estado == "publicada",
                ComunicacionModel.autor_id == user.id,
            )
        )
    else:
        statement = select(ComunicacionModel).where(
            ComunicacionModel.estado == "publicada",
            ComunicacionModel.audiencia.in_(["todos", "staff"]),
        )
    statement = statement.where(
        or_(ComunicacionModel.estado != "publicada", ComunicacionModel.vigente_desde.is_(None), ComunicacionModel.vigente_desde <= _iso_utc(now)),
        or_(ComunicacionModel.estado != "publicada", ComunicacionModel.vigente_hasta.is_(None), ComunicacionModel.vigente_hasta >= _iso_utc(now)),
    )
    if user.rol == RolPersonal.SUPERVISOR:
        statement = statement.where(
            or_(
                ComunicacionModel.estado != "publicada",
                ComunicacionModel.audiencia.in_(["todos", "supervisores"]),
            )
        )
    rows = session.scalars(statement.order_by(ComunicacionModel.creado_en.desc()))
    return [ComunicacionResponse.model_validate(item) for item in rows]


@router.post(
    "/comunicaciones",
    response_model=ComunicacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Redactar comunicación institucional",
)
def crear_comunicacion(
    body: ComunicacionCreate,
    user: CurrentUser,
    session: DbSession,
) -> ComunicacionResponse:
    _manager(user)
    if body.vigente_desde and body.vigente_hasta and body.vigente_hasta < body.vigente_desde:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La vigencia final debe ser posterior al inicio.")
    record = ComunicacionModel(
        id=str(uuid4()),
        **body.model_dump(),
        estado="borrador",
        autor_id=user.id,
    )
    record.vigente_desde = _iso_utc(body.vigente_desde) if body.vigente_desde else None
    record.vigente_hasta = _iso_utc(body.vigente_hasta) if body.vigente_hasta else None
    session.add(record)
    _commit(session, user, "crear_comunicacion", "comunicaciones")
    session.refresh(record)
    return ComunicacionResponse.model_validate(record)


@router.post(
    "/comunicaciones/{comunicacion_id}/publicar",
    response_model=ComunicacionResponse,
    summary="Aprobar y publicar comunicación",
)
def publicar_comunicacion(
    comunicacion_id: str,
    user: CurrentUser,
    session: DbSession,
) -> ComunicacionResponse:
    _admin(user)
    record = session.get(ComunicacionModel, comunicacion_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró la comunicación.")
    record.estado = "publicada"
    record.aprobado_por = user.id
    _commit(session, user, "publicar_comunicacion", "comunicaciones")
    session.refresh(record)
    return ComunicacionResponse.model_validate(record)


@router.patch(
    "/comunicaciones/{comunicacion_id}",
    response_model=ComunicacionResponse,
    summary="Editar o archivar comunicación",
)
def actualizar_comunicacion(
    comunicacion_id: str,
    body: ComunicacionUpdate,
    user: CurrentUser,
    session: DbSession,
) -> ComunicacionResponse:
    _manager(user)
    record = session.get(ComunicacionModel, comunicacion_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró la comunicación.")
    changes = body.model_dump(exclude_unset=True)
    if user.rol == RolPersonal.SUPERVISOR:
        if record.autor_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes gestionar tus propios borradores.")
        if record.estado != "borrador" or changes.get("estado") not in {None, "borrador"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un administrador puede publicar o archivar comunicaciones.")
    desde = changes.get("vigente_desde", record.vigente_desde)
    hasta = changes.get("vigente_hasta", record.vigente_hasta)
    if desde and hasta and hasta < desde:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La vigencia final debe ser posterior al inicio.")
    for field in ("vigente_desde", "vigente_hasta"):
        if field in changes and changes[field] is not None:
            changes[field] = _iso_utc(changes[field])
    for field, value in changes.items():
        setattr(record, field, value)
    if changes.get("estado") == "publicada":
        record.aprobado_por = user.id
    _commit(session, user, "actualizar_comunicacion", "comunicaciones")
    session.refresh(record)
    return ComunicacionResponse.model_validate(record)


@router.get("/auditoria", response_model=list[AuditoriaResponse], summary="Consultar registro de auditoría")
def listar_auditoria(
    user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    accion: Annotated[str | None, Query(max_length=64)] = None,
    resultado: Annotated[str | None, Query(max_length=24)] = None,
    actor_id: Annotated[str | None, Query(max_length=36)] = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[AuditoriaResponse]:
    _admin(user)
    statement = select(EventoAuditoriaModel)
    if accion:
        statement = statement.where(EventoAuditoriaModel.accion == accion)
    if resultado:
        statement = statement.where(EventoAuditoriaModel.resultado == resultado)
    if actor_id:
        statement = statement.where(EventoAuditoriaModel.actor_id == actor_id)
    if desde:
        statement = statement.where(EventoAuditoriaModel.creada_en >= desde)
    if hasta:
        statement = statement.where(EventoAuditoriaModel.creada_en <= hasta)
    rows = session.scalars(statement.order_by(EventoAuditoriaModel.creada_en.desc()).limit(limit))
    return [AuditoriaResponse.model_validate(item) for item in rows]
