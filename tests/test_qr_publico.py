"""Pruebas del generador QR de mesa y del menú público (Portátil Codex 2)."""

from xml.etree import ElementTree

import pytest

from app import create_app
from app.extensions import db
from app.models import Mesa, Rol, Usuario


def csrf_headers(client):
    token = client.get("/auth/csrf").json["data"]["csrf_token"]
    return {"X-CSRF-Token": token}


def login_admin(client, app):
    with app.app_context():
        user = Usuario(username="qr-admin", email="qr-admin@example.test",
                       rol=Rol(name="ADMIN"))
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    response = client.post("/auth/login", json={
        "username": "qr-admin", "password": "password",
    }, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    return csrf_headers(client)


@pytest.fixture
def admin_headers(client):
    return login_admin(client, client.application)


def authenticate(client, role):
    user = Usuario(username="qr-user", email="qr-user@example.test",
                   rol=Rol(name=role))
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    response = client.post("/auth/login", json={
        "username": user.username, "password": "test-password",
    }, headers=csrf_headers(client))
    assert response.status_code == 200
    return csrf_headers(client)


@pytest.fixture
def mesa_token(client):
    mesa = Mesa(numero=5)
    db.session.add(mesa)
    db.session.commit()
    return mesa.id, mesa.public_token


@pytest.mark.parametrize("role,expected", [
    (None, 401), ("WAITER", 403), ("KITCHEN", 403), ("CASHIER", 403),
])
def test_qr_svg_permisos_solo_admin(client, mesa_token, role, expected):
    mesa_id, _ = mesa_token
    headers = authenticate(client, role) if role else csrf_headers(client)
    response = client.get(f"/admin/mesas/{mesa_id}/qr.svg", headers=headers)
    assert response.status_code == expected
    assert response.json["success"] is False


def test_qr_mesa_inexistente(client, admin_headers):
    response = client.get("/admin/mesas/99999/qr.svg", headers=admin_headers)
    assert response.status_code == 404
    assert response.json["success"] is False


def test_qr_svg_sin_public_base_url_devuelve_error(client, mesa_token,
                                                   admin_headers):
    mesa_id, _ = mesa_token
    response = client.get(f"/admin/mesas/{mesa_id}/qr.svg", headers=admin_headers)
    assert response.status_code == 500
    assert response.json["success"] is False
    assert "PUBLIC_BASE_URL" in response.json["error"]


def _qr_svg(monkeypatch, base_url, numero, token=None):
    monkeypatch.setenv("PUBLIC_BASE_URL", base_url)
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        kwargs = {"numero": numero}
        if token is not None:
            kwargs["public_token"] = token
        mesa = Mesa(**kwargs)
        db.session.add(mesa)
        db.session.commit()
        mesa_id = mesa.id
    client = app.test_client()
    login_admin(client, app)
    response = client.get(f"/admin/mesas/{mesa_id}/qr.svg")
    with app.app_context():
        db.drop_all()
        db.session.remove()
    return response


def test_qr_con_public_base_url_devuelve_svg(monkeypatch):
    response = _qr_svg(monkeypatch, "https://resto.example.com", 8)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("image/svg+xml")
    root = ElementTree.fromstring(response.get_data())
    assert root.tag == "{http://www.w3.org/2000/svg}svg"


def test_qr_contenido_depende_de_url_y_token(monkeypatch):
    svg_a = _qr_svg(monkeypatch, "https://resto.example.com", 1).get_data()
    svg_b = _qr_svg(monkeypatch, "https://otro.example.com", 1).get_data()
    svg_c = _qr_svg(monkeypatch, "https://resto.example.com", 2,
                    token="a" * 64).get_data()
    for svg in (svg_a, svg_b, svg_c):
        assert b"<svg" in svg
    assert svg_a != svg_b
    assert svg_a != svg_c


@pytest.mark.parametrize("token", [
    "invalid", "a" * 63, "a" * 65, "g" * 64, "A" * 64,
])
def test_menu_publico_token_invalido_404(client, token):
    db.session.add(Mesa(numero=1))
    db.session.commit()
    response = client.get(f"/public/mesas/{token}/menu")
    assert response.status_code == 404
    assert response.json == {"success": False, "error": "Mesa no encontrada"}


@pytest.mark.parametrize("estado", ["DISPONIBLE", "OCUPADA", "CERRADA"])
def test_menu_publico_html(client, estado):
    mesa = Mesa(numero=3, estado=estado)
    db.session.add(mesa)
    db.session.commit()
    token = mesa.public_token
    response = client.get(f"/public/mesas/{token}/menu")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("Content-Type", "")
    body = response.get_data(as_text=True)
    assert "Mesa" in body and "3" in body
    assert token not in body
    assert 'data-categories-url="/categories"' in body
    assert 'data-products-url="/products"' in body
    assert 'action="pedidos"' in body
    assert 'public_menu.js' in body
    assert "Set-Cookie" not in response.headers


def test_menu_publico_no_crea_sesion(client):
    mesa = Mesa(numero=3)
    db.session.add(mesa)
    db.session.commit()
    client.get(f"/public/mesas/{mesa.public_token}/menu")
    with client.session_transaction() as session:
        assert not session
