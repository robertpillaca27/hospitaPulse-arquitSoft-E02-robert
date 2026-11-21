from datetime import timedelta
from types import SimpleNamespace

import jwt

from app.modulos.auth.infraestructura import credentials
from app.modulos.auth.presentacion import dependencies


def test_access_token_and_cookie_expire_after_ten_minutes(monkeypatch) -> None:
    secret = "test-secret-with-at-least-32-characters"
    monkeypatch.setattr(
        credentials,
        "get_settings",
        lambda: SimpleNamespace(jwt_secret=secret),
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(session_cookie_secure=False),
    )

    token = credentials.create_access_token(
        "staff-id",
        role="admin",
        must_change_password=False,
    )
    payload = jwt.decode(token, secret, algorithms=[credentials.JWT_ALGORITHM])
    cookie_options = dependencies.session_cookie_options()

    assert credentials.SESSION_DURATION == timedelta(minutes=10)
    assert payload["exp"] - payload["iat"] == 10 * 60
    assert payload["role"] == "admin"
    assert payload["must_change_password"] is False
    assert cookie_options["max_age"] == 10 * 60
