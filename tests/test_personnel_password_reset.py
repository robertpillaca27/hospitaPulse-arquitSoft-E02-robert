from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.modulos.auth.infraestructura.credentials import PasswordHasher
from app.modulos.auth.presentacion.dependencies import require_admin
from app.modulos.usuarios.dominio.rol_personal import RolPersonal
from app.modulos.usuarios.infraestructura.models import UsuarioPersonalModel
from app.modulos.usuarios.presentacion.usuarios_routes import router
from app.shared.database.session import get_db_session


@pytest.fixture
def personnel_client() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    UsuarioPersonalModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            UsuarioPersonalModel(
                id="target-id",
                username="target",
                nombre_completo="Personal de prueba",
                email="target@example.test",
                rol=RolPersonal.STAFF,
                activo=True,
                password_hash="old-hash",
                debe_cambiar_password=False,
            )
        )
        session.commit()

    def database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(router, prefix="/personal")
    app.dependency_overrides[get_db_session] = database_session
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id="admin-id")

    with TestClient(app) as client:
        yield client, factory

    app.dependency_overrides.clear()
    engine.dispose()


def test_admin_password_reset_returns_temporary_password_and_stores_only_hash(
    personnel_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = personnel_client

    response = client.post("/personal/target-id/restablecer-password")

    assert response.status_code == 200
    payload = response.json()
    temporary_password = payload["password_temporal"]
    assert payload["usuario"]["debe_cambiar_password"] is True
    assert temporary_password
    with factory() as session:
        user = session.get(UsuarioPersonalModel, "target-id")
        assert user is not None
        assert user.password_hash != temporary_password
        assert PasswordHasher.verify(temporary_password, user.password_hash)
        assert user.debe_cambiar_password is True


def test_admin_cannot_reset_own_password(
    personnel_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = personnel_client

    response = client.post("/personal/admin-id/restablecer-password")

    assert response.status_code == 409
    assert response.json()["detail"] == "No puedes restablecer tu propia contraseña desde esta acción."
