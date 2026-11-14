import pytest

from app.extensions import db
from app.models import Rol, Usuario


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
def kitchen_role(app):
    with app.app_context():
        rol = Rol(name="KITCHEN", description="Personal de cocina")
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
def kitchen_user(app, kitchen_role):
    with app.app_context():
        user = Usuario(username="cocina1", email="cocina1@test.com", rol=kitchen_role)
        user.set_password("kitchen-pass")
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


# ---------- Rutas públicas ----------
def test_index_public(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ConectaResto" in html


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html


# ---------- Paneles requieren autenticación ----------
def test_admin_panel_requires_auth(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in (200, 302)
    html = response.get_data(as_text=True)
    assert "Debes iniciar sesión" in html or response.status_code == 302


def test_waiter_panel_requires_auth(client):
    response = client.get("/waiter", follow_redirects=False)
    assert response.status_code in (200, 302)


# ---------- Acceso por rol ----------
def test_admin_can_access_admin_panel(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel ADMIN" in html
    assert "admin1" in html
    assert "ADMIN" in html


def test_admin_can_access_waiter_panel_forbidden(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_can_access_waiter_panel(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Mesero" in html


def test_waiter_can_access_admin_panel_forbidden(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_can_access_kitchen_panel(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Cocina" in html


def test_cashier_can_access_cashier_panel(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Caja" in html


# ---------- Tarjetas por rol ----------
def test_admin_panel_shows_enabled_cards(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Endpoints existentes: habilitados
    assert "Usuarios" in html
    assert "Categorías" in html
    assert "Productos" in html
    assert "Mesas" in html
    # Endpoint inexistente: deshabilitado / pendiente
    assert "Pedidos" in html
    assert "Pendiente" in html


def test_waiter_panel_shows_mesas_and_pending_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Mesas" in html
    assert "Pedidos" in html
    assert "Pendiente" in html


def test_kitchen_panel_shows_pending_pedidos(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Pendiente" in html


def test_cashier_panel_shows_pending_items(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos para cobrar" in html
    assert "Cierre de caja" in html
    assert "Pendiente" in html


# ---------- Navegación por rol ----------
def test_nav_shows_user_and_logout_when_authenticated(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    html = response.get_data(as_text=True)
    assert "admin1" in html
    assert "ADMIN" in html
    assert "Cerrar sesión" in html


# ---------- Redirección de login si ya autenticado ----------
def test_login_redirects_if_authenticated(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302
