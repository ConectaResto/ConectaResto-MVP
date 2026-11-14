import pytest

from app.extensions import db
from app.models import Rol, Usuario


@pytest.fixture
def all_roles(app):
    """Crea los cuatro roles estándar antes de cada prueba que los necesite."""
    with app.app_context():
        for nombre, descripcion in [
            ("ADMIN", "Administrador del sistema"),
            ("WAITER", "Mesero de sala"),
            ("KITCHEN", "Personal de cocina"),
            ("CASHIER", "Cajero de punto de venta"),
        ]:
            rol = Rol(name=nombre, description=descripcion)
            db.session.add(rol)
        db.session.commit()


@pytest.fixture
def admin_id(app, all_roles):
    with app.app_context():
        rol = db.session.execute(db.select(Rol).filter_by(name="ADMIN")).scalar_one()
        user = Usuario(username="admin1", email="admin1@test.com", rol_id=rol.id)
        user.set_password("admin-pass")
        db.session.add(user)
        db.session.commit()
        uid = user.id
    return uid


@pytest.fixture
def waiter_id(app, all_roles):
    with app.app_context():
        rol = db.session.execute(db.select(Rol).filter_by(name="WAITER")).scalar_one()
        user = Usuario(username="mesero1", email="mesero1@test.com", rol_id=rol.id)
        user.set_password("waiter-pass")
        db.session.add(user)
        db.session.commit()
        uid = user.id
    return uid


def csrf_token(client):
    return client.get("/auth/csrf").json["data"]["csrf_token"]


def login(client, username, password):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf_token(client)},
    )


# ---------- List ----------
def test_list_users_requires_authentication(client):
    token = csrf_token(client)
    assert client.get("/users", headers={"X-CSRF-Token": token}).status_code == 401


def test_list_users_requires_admin_role(client, waiter_id):
    login(client, "mesero1", "waiter-pass")
    token = csrf_token(client)
    assert client.get("/users", headers={"X-CSRF-Token": token}).status_code == 403


def test_list_users_as_admin(client, admin_id):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.get("/users", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    data = response.json["data"]["users"]
    usernames = [u["username"] for u in data]
    assert "admin1" in usernames
    for u in data:
        assert "password_hash" not in u


# ---------- Get ----------
def test_get_user_requires_authentication(client):
    token = csrf_token(client)
    assert client.get("/users/1", headers={"X-CSRF-Token": token}).status_code == 401


def test_get_user_not_found(client, admin_id):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    assert client.get("/users/9999", headers={"X-CSRF-Token": token}).status_code == 404


def test_get_user_success(client, admin_id, waiter_id):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.get(f"/users/{waiter_id}", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    data = response.json["data"]
    assert data["username"] == "mesero1"
    assert data["email"] == "mesero1@test.com"
    assert data["rol"] == "WAITER"
    assert data["is_active"] is True
    assert "password_hash" not in data


# ---------- Create ----------
def test_create_user_requires_authentication(client):
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={"username": "nuevo", "email": "nuevo@test.com", "password": "Pass123", "rol": "WAITER"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401


def test_create_user_requires_admin_role(client, waiter_id):
    login(client, "mesero1", "waiter-pass")
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={"username": "nuevo", "email": "nuevo@test.com", "password": "Pass123", "rol": "WAITER"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 403


def test_create_user_requires_csrf(client, admin_id):
    login(client, "admin1", "admin-pass")
    response = client.post(
        "/users",
        json={"username": "nuevo", "email": "nuevo@test.com", "password": "Pass123", "rol": "WAITER"},
    )
    assert response.status_code == 400


def test_create_user_missing_fields(client, admin_id):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={"username": "nuevo"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400


def test_create_user_success(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={
            "username": "cajero1",
            "email": "cajero1@test.com",
            "password": "CajeroPass123",
            "rol": "CASHIER",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 201
    data = response.json["data"]
    assert data["username"] == "cajero1"
    assert data["email"] == "cajero1@test.com"
    assert data["rol"] == "CASHIER"
    assert data["is_active"] is True
    assert "password_hash" not in data


def test_create_user_duplicate_username(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={
            "username": "mesero1",
            "email": "otro@test.com",
            "password": "Pass123",
            "rol": "WAITER",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 409


def test_create_user_duplicate_email(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={
            "username": "otro",
            "email": "mesero1@test.com",
            "password": "Pass123",
            "rol": "WAITER",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 409


def test_create_user_unknown_rol(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.post(
        "/users",
        json={
            "username": "otro",
            "email": "otro@test.com",
            "password": "Pass123",
            "rol": "INEXISTENTE",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 404


# ---------- Update ----------
def test_update_user_requires_authentication(client):
    token = csrf_token(client)
    assert client.patch("/users/1", json={}, headers={"X-CSRF-Token": token}).status_code == 401


def test_update_user_success(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.patch(
        f"/users/{waiter_id}",
        json={"username": "mesero-nuevo", "email": "mesero-nuevo@test.com"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert data["username"] == "mesero-nuevo"
    assert data["email"] == "mesero-nuevo@test.com"
    assert "password_hash" not in data


def test_update_user_change_rol(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.patch(
        f"/users/{waiter_id}",
        json={"rol": "ADMIN"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    assert response.json["data"]["rol"] == "ADMIN"


def test_update_user_change_last_admin_rol_prohibited(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.patch(
        f"/users/{admin_id}",
        json={"rol": "WAITER"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 409


def test_update_user_duplicate_username(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.patch(
        f"/users/{waiter_id}",
        json={"username": "admin1"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 409


def test_update_user_unknown_rol(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.patch(
        f"/users/{waiter_id}",
        json={"rol": "INEXISTENTE"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 404


def test_update_user_not_found(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    assert client.patch("/users/9999", json={"username": "x"}, headers={"X-CSRF-Token": token}).status_code == 404


# ---------- Delete (deactivate) ----------
def test_deactivate_user_requires_authentication(client):
    token = csrf_token(client)
    assert client.delete("/users/1", headers={"X-CSRF-Token": token}).status_code == 401


def test_deactivate_user_success(client, app, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.delete(f"/users/{waiter_id}", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    with app.app_context():
        from app.extensions import db

        user = db.session.get(Usuario, waiter_id)
        assert user.is_active is False


def test_deactivate_self_prohibited(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.delete(f"/users/{admin_id}", headers={"X-CSRF-Token": token})
    assert response.status_code == 409


def test_deactivate_last_active_admin_prohibited(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    response = client.delete(f"/users/{admin_id}", headers={"X-CSRF-Token": token})
    assert response.status_code == 409


def test_deactivate_not_found(client, admin_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    assert client.delete("/users/9999", headers={"X-CSRF-Token": token}).status_code == 404


def test_deactivate_then_cannot_login(client, admin_id, waiter_id, all_roles):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    client.delete(f"/users/{waiter_id}", headers={"X-CSRF-Token": token})
    assert login(client, "mesero1", "waiter-pass").status_code == 401
