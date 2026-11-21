import pytest

from app.auth.decorators import roles_required
from app.extensions import db
from app.users.models import Rol, Usuario


@pytest.mark.parametrize("role", ["ADMIN", "WAITER", "KITCHEN", "CASHIER"])
@pytest.mark.parametrize("allowed", ["ADMIN", "WAITER", "KITCHEN", "CASHIER"])
def test_role_permissions(app, client, role, allowed):
    @app.route("/internal-test", methods=["GET", "POST"])
    @roles_required(allowed)
    def protected():
        return {"ok": True}

    assert client.get("/internal-test").status_code == 401
    assert client.post("/internal-test").status_code == 400
    anonymous_csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    assert client.post("/internal-test", headers={
        "X-CSRF-Token": anonymous_csrf,
    }).status_code == 401
    user = Usuario(username="test", email="test@example.test", rol=Rol(name=role))
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    assert client.post("/auth/login", json={"username": "test", "password": "password"},
                       headers={"X-CSRF-Token": csrf}).status_code == 200
    expected = 200 if role == allowed else 403
    assert client.get("/internal-test").status_code == expected
    assert client.post("/internal-test").status_code == 400
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    assert client.post("/internal-test", headers={"X-CSRF-Token": csrf}).status_code == expected


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_csrf_without_authenticated_session(app, client, method):
    calls = []

    @app.route("/write-test", methods=[method])
    def write():
        calls.append(True)
        return {"ok": True}

    assert client.open("/write-test", method=method).status_code == 400
    assert calls == []
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    assert client.open("/write-test", method=method, headers={
        "X-CSRF-Token": "invalid",
    }).status_code == 400
    assert calls == []
    assert client.open("/write-test", method=method, headers={
        "X-CSRF-Token": csrf,
    }).status_code == 200
    assert calls == [True]


def test_no_csrf_exemptions_enabled():
    from app.auth.csrf import CSRF_EXEMPT_ENDPOINTS
    assert CSRF_EXEMPT_ENDPOINTS == frozenset()
