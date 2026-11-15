import pytest

from app.extensions import db
from app.models import Rol, Usuario


@pytest.fixture
def kitchen_role(app):
    with app.app_context():
        rol = Rol(name="KITCHEN", description="Personal de cocina")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def admin_role(app):
    with app.app_context():
        rol = Rol(name="ADMIN", description="Administrador del sistema")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def waiter_role(app):
    with app.app_context():
        rol = Rol(name="WAITER", description="Mesero de sala")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def cashier_role(app):
    with app.app_context():
        rol = Rol(name="CASHIER", description="Cajero de punto de venta")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def kitchen_user(app, kitchen_role):
    with app.app_context():
        user = Usuario(username="cocina1", email="cocina1@test.com", rol=kitchen_role)
        user.set_password("kitchen-pass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app, admin_role):
    with app.app_context():
        user = Usuario(username="admin1", email="admin1@test.com", rol=admin_role)
        user.set_password("admin-pass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def waiter_user(app, waiter_role):
    with app.app_context():
        user = Usuario(username="mesero1", email="mesero1@test.com", rol=waiter_role)
        user.set_password("waiter-pass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def cashier_user(app, cashier_role):
    with app.app_context():
        user = Usuario(username="caja1", email="caja1@test.com", rol=cashier_role)
        user.set_password("cashier-pass")
        db.session.add(user)
        db.session.commit()
        return user


def csrf_token(client):
    return client.get("/auth/csrf").json["data"]["csrf_token"]


def login(client, username, password):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf_token(client)},
    )


# ---------- Kitchen: Pedidos ----------
def test_kitchen_can_access_pedidos(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Cocina" in html


def test_kitchen_pedidos_requires_auth(client):
    response = client.get("/kitchen/pedidos", follow_redirects=False)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html
    assert "Panel Cocina" not in html


# ---------- Kitchen: Role isolation ----------
def test_admin_cannot_access_kitchen_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_kitchen_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_kitchen_pedidos(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403