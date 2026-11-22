import pytest

from app.extensions import db
from app.catalog.models import Category, Product
from app.mesas.models import Mesa
from app.pedidos.models import Pedido
from app.servicios.models import Servicio
from app.users.models import Rol, Usuario


@pytest.fixture
def menu_context(app):
    mesa = Mesa(numero=7, estado="OCUPADA", public_token="a" * 64)
    inactive = Mesa(numero=8, public_token="b" * 64)
    closed = Mesa(numero=9, estado="CERRADA", public_token="c" * 64)
    category = Category(name="Bebidas")
    food = Category(name="Comida")
    waiter = Usuario(username="menu-waiter", email="menu@test.invalid", rol=Rol(name="WAITER"))
    waiter.set_password("test-password")
    db.session.add_all([mesa, inactive, closed, category, food, waiter])
    db.session.flush()
    product = Product(name="Café", description="Recién preparado", price="12.35", categoria_id=category.id)
    snack = Product(name="Pan", description='<img src=x onerror="window.badContent=true">', price="0.10", categoria_id=food.id)
    hidden = Product(name="No disponible", price="1.00", categoria_id=category.id, is_available=False)
    db.session.add_all([product, snack, hidden, Servicio(mesa_id=mesa.id, abierto_por_id=waiter.id)])
    db.session.commit()
    return mesa, product


def test_imagen_predeterminada_publica(client):
    response = client.get("/static/img/default-product.svg")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"


def test_order_contract_preserves_csrf_and_empty_cart_validation(client, menu_context):
    mesa, _ = menu_context
    path = f"/public/mesas/{mesa.public_token}/pedidos"
    assert client.post(path, json={"items": []}).status_code == 400
    csrf = client.get('/auth/csrf').json['data']['csrf_token']
    assert client.post(path, json={"items": []}, headers={'X-CSRF-Token': csrf}).status_code == 400
    assert Pedido.query.count() == 0


def test_pedidos_publicos_por_estado_de_mesa(client, menu_context):
    _, producto = menu_context
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    payload = {"items": [{"producto_id": producto.id, "cantidad": 1}]}
    for token, expected in (("a" * 64, 201), ("b" * 64, 201), ("c" * 64, 409)):
        response = client.post(f"/public/mesas/{token}/pedidos", json=payload, headers=headers)
        assert response.status_code == expected
        if expected == 201:
            assert response.json["data"]["estado"] == "PENDIENTE"
    assert Pedido.query.count() == 2
    assert client.get("/auth/me").status_code == 401
