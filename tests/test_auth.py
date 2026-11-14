import time

import pytest

from app.extensions import db
from app.models import Rol, Usuario


@pytest.fixture
def account(app):
    role = Rol(name="WAITER")
    user = Usuario(username="alice", email="alice@example.test", rol=role)
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    return user


def token(client):
    return client.get("/auth/csrf").json["data"]["csrf_token"]


def login(client, **overrides):
    return client.post("/auth/login", json={
        "username": "alice", "password": "test-password", **overrides,
    }, headers={"X-CSRF-Token": token(client)})


def test_login_me_logout(client, account):
    old_token = token(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json["data"] == {
        "id": account.id, "username": "alice", "rol": "WAITER",
    }
    assert "password" not in response.get_data(as_text=True)
    assert client.get("/auth/me").json == response.json
    assert token(client) != old_token
    assert client.post("/auth/logout", headers={"X-CSRF-Token": old_token}).status_code == 400
    assert client.post("/auth/logout", headers={"X-CSRF-Token": token(client)}).status_code == 200
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("credentials", [
    {"password": "wrong"}, {"username": "missing"},
])
def test_bad_credentials(client, account, credentials):
    assert login(client, **credentials).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_inactive_account(client, account):
    account.is_active = False
    db.session.commit()
    assert login(client).status_code == 401


@pytest.mark.parametrize("data", [None, [], {}, {"username": 4, "password": "x"}])
def test_invalid_input(client, data):
    assert client.post("/auth/login", json=data,
                       headers={"X-CSRF-Token": token(client)}).status_code == 400


@pytest.mark.parametrize("csrf", [None, "incorrect", "ñ"])
def test_csrf_rejected(client, account, csrf):
    headers = {} if csrf is None else {"X-CSRF-Token": csrf}
    assert client.post("/auth/login", json={"username": "alice", "password": "test-password"},
                       headers=headers).status_code == 400


def test_absolute_expiry(client, account, monkeypatch):
    now = time.time()
    monkeypatch.setattr("app.auth.routes.time.time", lambda: now)
    assert login(client).status_code == 200
    monkeypatch.setattr("app.auth.service.time.time", lambda: now + 28799)
    assert client.get("/auth/me").status_code == 200
    client.get("/auth/csrf")
    monkeypatch.setattr("app.auth.service.time.time", lambda: now + 28800)
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("change", ["inactive", "deleted", "role"])
def test_current_database_state(client, account, change):
    login(client)
    if change == "inactive":
        account.is_active = False
    elif change == "deleted":
        db.session.delete(account)
    else:
        account.rol.name = "KITCHEN"
    db.session.commit()
    response = client.get("/auth/me")
    assert response.status_code == (200 if change == "role" else 401)
    if change == "role":
        assert response.json["data"]["rol"] == "KITCHEN"


def test_tampered_cookie(client, account, app):
    login(client)
    client.set_cookie(app.config["SESSION_COOKIE_NAME"], "invalid.signature")
    assert client.get("/auth/me").status_code == 401


def test_cookie_configuration(client, app):
    cookie = client.get("/auth/csrf").headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is False
    assert app.config["PERMANENT_SESSION_LIFETIME"].total_seconds() == 28800


def test_production_cookie(monkeypatch):
    from app import create_app
    from app.config import ProductionConfig
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "test-production-secret")
    app = create_app("production")
    assert "Secure" in app.test_client().get("/auth/csrf").headers["Set-Cookie"]


def test_production_rejects_default_secret(monkeypatch):
    from app import create_app
    from app.config import ProductionConfig
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "dev-secret-key-change-in-production")
    with pytest.raises(ValueError):
        create_app("production")
