from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.modulos.auth.presentacion.dependencies import get_current_user
from app.modulos.institucional.infraestructura.models import (
    AsistenciaEventoModel,
    EventoAuditoriaModel,
    EventoModel,
    SugerenciaModel,
)
from app.modulos.institucional.presentacion.institucional_routes import router
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.shared.database.base import Base
from app.shared.database.session import get_db_session


@pytest.fixture
def institutional_client() -> Iterator[tuple[TestClient, SimpleNamespace, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    active_user = SimpleNamespace(
        id="staff-user-id",
        rol=RolPersonal.STAFF,
        debe_cambiar_password=False,
    )

    def database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(router, prefix="/institucional")
    app.dependency_overrides[get_db_session] = database_session
    app.dependency_overrides[get_current_user] = lambda: active_user

    with TestClient(app) as client:
        yield client, active_user, factory

    app.dependency_overrides.clear()
    engine.dispose()


def test_suggestion_submission_does_not_store_or_return_submitter(
    institutional_client: tuple[TestClient, SimpleNamespace, sessionmaker[Session]],
) -> None:
    client, _, factory = institutional_client
    response = client.post(
        "/institucional/sugerencias",
        json={
            "categoria": "bienestar",
            "titulo": "Mejoras para el equipo",
            "detalle": "Propongo establecer espacios regulares de coordinación.",
        },
    )

    assert response.status_code == 201
    assert "usuario_id" not in response.json()
    assert "actor_id" not in response.json()
    with factory() as session:
        stored = session.scalar(select(SugerenciaModel))
        assert stored is not None
        assert not hasattr(stored, "usuario_id")
        assert not hasattr(stored, "actor_id")
        assert stored.detalle == "Propongo establecer espacios regulares de coordinación."


def test_suggestion_moderation_is_restricted_and_does_not_expose_sender(
    institutional_client: tuple[TestClient, SimpleNamespace, sessionmaker[Session]],
) -> None:
    client, active_user, _ = institutional_client
    created = client.post(
        "/institucional/sugerencias",
        json={"categoria": "procesos", "detalle": "Propongo mejorar la coordinación entre turnos."},
    )
    assert created.status_code == 201

    forbidden = client.get("/institucional/sugerencias")
    assert forbidden.status_code == 403

    active_user.rol = RolPersonal.SUPERVISOR
    listed = client.get("/institucional/sugerencias")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "usuario_id" not in listed.json()[0]


def test_suggestion_contract_rejects_unexpected_identity_fields(
    institutional_client: tuple[TestClient, SimpleNamespace, sessionmaker[Session]],
) -> None:
    client, _, _ = institutional_client
    response = client.post(
        "/institucional/sugerencias",
        json={
            "categoria": "bienestar",
            "detalle": "Propongo una actividad de bienestar para el personal.",
            "usuario_id": "should-not-be-accepted",
        },
    )

    assert response.status_code == 422


def test_event_attendance_is_idempotent_and_audited_separately_from_survey_data(
    institutional_client: tuple[TestClient, SimpleNamespace, sessionmaker[Session]],
) -> None:
    client, active_user, factory = institutional_client
    active_user.rol = RolPersonal.SUPERVISOR
    created = client.post(
        "/institucional/eventos",
        json={
            "titulo": "Jornada institucional",
            "descripcion": "Actividad para fortalecer el trabajo colaborativo.",
            "inicio": "2099-01-01T10:00:00Z",
            "ubicacion": "Auditorio principal",
            "audiencia": "todos",
            "cupo": 10,
        },
    )
    assert created.status_code == 201
    event_id = created.json()["id"]
    published = client.post(f"/institucional/eventos/{event_id}/publicar")
    assert published.status_code == 200

    active_user.rol = RolPersonal.STAFF
    first = client.put(f"/institucional/eventos/{event_id}/asistencia")
    second = client.put(f"/institucional/eventos/{event_id}/asistencia")
    assert first.status_code == 200
    assert second.status_code == 200

    with factory() as session:
        attendance = session.scalars(select(AsistenciaEventoModel)).all()
        audit_events = session.scalars(
            select(EventoAuditoriaModel).where(EventoAuditoriaModel.accion == "confirmar_asistencia")
        ).all()
        assert len(attendance) == 1
        assert attendance[0].usuario_id == active_user.id
        assert len(audit_events) == 2
        assert session.get(EventoModel, event_id) is not None


def test_communications_list_filters_iso_timestamp_columns(
    institutional_client: tuple[TestClient, SimpleNamespace, sessionmaker[Session]],
) -> None:
    client, active_user, _ = institutional_client
    active_user.rol = RolPersonal.SUPERVISOR
    created = client.post(
        "/institucional/comunicaciones",
        json={
            "titulo": "Aviso de prueba",
            "contenido": "Información institucional para el personal.",
            "audiencia": "todos",
            "prioridad": "normal",
            "vigente_desde": "2000-01-01T10:00:00Z",
            "vigente_hasta": "2099-01-01T10:00:00Z",
        },
    )
    assert created.status_code == 201
    communication_id = created.json()["id"]
    active_user.rol = RolPersonal.ADMIN
    published = client.post(f"/institucional/comunicaciones/{communication_id}/publicar")
    assert published.status_code == 200

    active_user.rol = RolPersonal.STAFF
    listed = client.get("/institucional/comunicaciones")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [communication_id]
