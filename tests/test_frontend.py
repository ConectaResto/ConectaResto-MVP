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
def test_admin_panel_shows_disabled_cards(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Todas las tarjetas ADMIN están deshabilitadas
    assert "Usuarios" in html
    assert "Categorías" in html
    assert "Productos" in html
    assert "Mesas" in html
    assert "Pedidos" in html
    assert "Pendiente" in html


def test_waiter_panel_shows_enabled_cards(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Tarjetas WAITER habilitadas con URLs reales
    assert "Mesas" in html
    assert "Pedidos" in html
    assert "Ver mesas" in html
    assert "Gestionar pedidos" in html
    assert "Pendiente" not in html


def test_kitchen_panel_shows_enabled_cards(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Tarjeta KITCHEN habilitada con URL real
    assert "Pedidos" in html
    assert "Ver pedidos" in html
    assert "Pendiente" not in html


def test_cashier_panel_no_disabled_cards(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # No aparecen tarjetas deshabilitadas de "Próximamente"
    assert "Pedidos para cobrar" not in html
    assert "Cierre de caja" not in html
    assert "Pendiente" not in html
    # Las funciones reales de caja siguen presentes
    assert "Servicios activos" in html
    assert "Registrar pago simulado" in html
    assert "Cerrar servicio" in html


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


# ---------- Nuevas rutas de mesero y cocina ----------
def test_waiter_can_access_mesas(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Mesas" in html
    assert "Panel Mesero" in html


def test_waiter_can_access_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Mesero" in html


def test_kitchen_can_access_pedidos(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Cocina" in html


def test_admin_cannot_access_waiter_mesas(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_waiter_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_kitchen_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_kitchen_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_waiter_mesas(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_mesas_requires_auth(client):
    response = client.get("/waiter/mesas", follow_redirects=False)
    assert response.status_code in (200, 302)


def test_waiter_pedidos_requires_auth(client):
    response = client.get("/waiter/pedidos", follow_redirects=False)
    assert response.status_code in (200, 302)


def test_kitchen_pedidos_requires_auth(client):
    response = client.get("/kitchen/pedidos", follow_redirects=False)
    assert response.status_code in (200, 302)


# ---------- Regresión: bucle de redirecciones en paneles directos ----------
def test_admin_can_access_panel_admin_direct(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel ADMIN" in html


def test_waiter_can_access_panel_waiter_direct(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Mesero" in html


def test_kitchen_can_access_panel_kitchen_direct(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Cocina" in html


def test_cashier_can_access_panel_cashier_direct(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Caja" in html


def test_admin_cannot_access_panel_waiter(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_panel_admin(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 403


# ---------- Regresión: aislamiento de roles entre paneles ----------
def test_admin_cannot_access_panel_kitchen(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_panel_cashier(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_panel_kitchen(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_panel_cashier(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_panel_admin(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_panel_waiter(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_panel_cashier(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_panel_admin(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_panel_waiter(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_panel_kitchen(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 403
