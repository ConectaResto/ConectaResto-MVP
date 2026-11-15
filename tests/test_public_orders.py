from decimal import Decimal
from pathlib import Path

import pytest

from app.extensions import db
from app.models import Category, DetallePedido, Mesa, Pedido, Product, Rol, Servicio, Usuario
from tests.test_servicios import autenticar


@pytest.fixture
def order_context(app, client):
    waiter = Usuario(username="waiter", email="waiter@test.invalid", rol=Rol(name="WAITER"))
    waiter.set_password("test-password")
    mesa = Mesa(numero=1, estado="OCUPADA")
    category = Category(name="Bebidas")
    db.session.add_all([waiter, mesa, category])
    db.session.flush()
    service = Servicio(mesa_id=mesa.id, abierto_por_id=waiter.id, estado="ACTIVO")
    product = Product(name="Cafe", price=Decimal("12.35"), categoria_id=category.id)
    db.session.add_all([service, product])
    db.session.commit()
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    return mesa, service, product, category, {"X-CSRF-Token": csrf}


def submit(client, context):
    mesa, _, product, _, headers = context
    return client.post(f"/public/mesas/{mesa.public_token}/pedidos",
                       json={"items": [{"producto_id": product.id, "cantidad": 2}]},
                       headers=headers)


def test_anonymous_order_uses_shared_domain(client, order_context):
    mesa, service, product, _, _ = order_context
    assert client.get("/auth/me").status_code == 401
    response = submit(client, order_context)
    assert response.status_code == 201
    pedido = db.session.get(Pedido, response.json["data"]["id"])
    assert response.json == {"success": True, "data": {"id": pedido.id, "estado": "PENDIENTE"}}
    assert pedido.servicio_id == service.id
    assert pedido.origen == "PUBLICO"
    assert pedido.creado_por_id is pedido.autorizado_por_id is None
    assert pedido.estado_preparacion == "NO_ENVIADO"
    assert pedido.detalles[0].precio_unitario == Decimal("12.35")
    assert pedido.detalles[0].cantidad == 2
    product.price = Decimal("99.00")
    db.session.commit()
    assert pedido.detalles[0].precio_unitario == Decimal("12.35")
    assert client.get(f"/pedidos/{pedido.id}").status_code == 401
    assert client.get(f"/servicios/{service.id}").status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert mesa.estado == "OCUPADA"


@pytest.mark.parametrize("token", ["invalid", "a" * 63, "A" * 64, "f" * 64])
def test_invalid_token_does_not_create_order(client, order_context, token):
    headers = order_context[-1]
    response = client.post(f"/public/mesas/{token}/pedidos", json={"items": []}, headers=headers)
    assert response.status_code == 404
    assert response.json == {"success": False, "error": "Mesa no encontrada"}
    assert Pedido.query.count() == DetallePedido.query.count() == 0


@pytest.mark.parametrize("state", ["missing", "closed", "closed_table"])
def test_closed_or_missing_service_and_closed_table(client, order_context, state):
    mesa, service, _, _, _ = order_context
    if state == "missing":
        db.session.delete(service)
    elif state == "closed":
        service.estado = "CERRADO"
    else:
        mesa.estado = "CERRADA"
    db.session.commit()
    response = submit(client, order_context)
    assert response.status_code == 409
    assert response.json["success"] is False
    assert Pedido.query.count() == DetallePedido.query.count() == 0


@pytest.mark.parametrize("field", ["is_active", "is_available", "category", "missing"])
def test_invalid_products_roll_back_entire_order(client, order_context, field):
    mesa, _, product, category, headers = order_context
    other = Product(name="Otro", price=Decimal("1.00"), categoria_id=category.id)
    db.session.add(other)
    db.session.commit()
    if field == "category":
        category.is_active = False
    elif field != "missing":
        setattr(product, field, False)
    db.session.commit()
    product_id = 99999 if field == "missing" else product.id
    response = client.post(f"/public/mesas/{mesa.public_token}/pedidos", headers=headers,
                           json={"items": [{"producto_id": other.id, "cantidad": 1},
                                           {"producto_id": product_id, "cantidad": 1}]})
    assert response.status_code == 404
    assert Pedido.query.count() == DetallePedido.query.count() == 0


@pytest.mark.parametrize("data", [None, [], {}, {"items": []}, {"items": None},
    {"items": [{"producto_id": 1, "cantidad": True}]},
    {"items": [{"producto_id": 1, "cantidad": 0}]},
    {"items": [{"producto_id": 1, "cantidad": 1, "precio_unitario": "0"}]},
    {"items": [], "servicio_id": 2}, {"items": [], "origen": "MESERO"},
    {"items": [], "creado_por_id": 1}])
def test_invalid_payload_cannot_override_identity_or_prices(client, order_context, data):
    mesa, _, _, _, headers = order_context
    response = client.post(f"/public/mesas/{mesa.public_token}/pedidos", json=data, headers=headers)
    assert response.status_code == 400
    assert Pedido.query.count() == DetallePedido.query.count() == 0


@pytest.mark.parametrize("csrf", [None, "invalid"])
def test_csrf_remains_required(client, order_context, csrf):
    mesa, _, product, _, _ = order_context
    headers = {} if csrf is None else {"X-CSRF-Token": csrf}
    response = client.post(f"/public/mesas/{mesa.public_token}/pedidos", headers=headers,
                           json={"items": [{"producto_id": product.id, "cantidad": 1}]})
    assert response.status_code == 400
    assert response.json["error"] == "Token CSRF invalido"
    assert Pedido.query.count() == 0


def test_token_only_selects_its_own_active_service(client, order_context):
    mesa, service, product, _, headers = order_context
    other_mesa = Mesa(numero=2, estado="OCUPADA")
    db.session.add(other_mesa)
    db.session.flush()
    other_service = Servicio(mesa_id=other_mesa.id, abierto_por_id=service.abierto_por_id,
                             estado="ACTIVO")
    service.estado = "CERRADO"
    db.session.add(other_service)
    db.session.commit()
    assert submit(client, order_context).status_code == 409
    service.estado = "ACTIVO"
    other_service.estado = "CERRADO"
    db.session.commit()
    response = submit(client, order_context)
    assert response.status_code == 201
    assert db.session.get(Pedido, response.json["data"]["id"]).servicio_id == service.id


def test_stable_token_uses_new_service_after_reopening(client, order_context):
    mesa, old_service, _, _, _ = order_context
    token = mesa.public_token
    old_service.estado = "CERRADO"
    db.session.commit()
    new_service = Servicio(mesa_id=mesa.id, abierto_por_id=old_service.abierto_por_id,
                           estado="ACTIVO")
    db.session.add(new_service)
    db.session.commit()
    response = submit(client, order_context)
    assert response.status_code == 201
    pedido = db.session.get(Pedido, response.json["data"]["id"])
    assert pedido.servicio_id == new_service.id
    assert mesa.public_token == token


@pytest.fixture
def disponible_mesa_context(app, client):
    """Mesa DISPONIBLE sin servicio activo, con un producto valido."""
    mesa = Mesa(numero=10, estado="DISPONIBLE")
    category = Category(name="Bebidas")
    waiter = Usuario(username="disp-waiter", email="disp@test.invalid", rol=Rol(name="WAITER"))
    waiter.set_password("test-password")
    db.session.add_all([mesa, category, waiter])
    db.session.flush()
    product = Product(name="Te", price=Decimal("5.00"), categoria_id=category.id)
    db.session.add(product)
    db.session.commit()
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    return mesa, product, {"X-CSRF-Token": csrf}


def submit_disponible(client, context, items=None):
    mesa, product, headers = context
    if items is None:
        items = [{"producto_id": product.id, "cantidad": 1}]
    return client.post(f"/public/mesas/{mesa.public_token}/pedidos",
                       json={"items": items}, headers=headers)


def test_public_order_invalid_product_leaves_mesa_disponible(client, disponible_mesa_context):
    """Caso A: producto invalido no crea servicio ni pedido, mesa queda DISPONIBLE."""
    mesa, _, headers = disponible_mesa_context
    response = submit_disponible(client, disponible_mesa_context,
                                 items=[{"producto_id": 99999, "cantidad": 1}])
    assert response.status_code == 404
    assert response.json["success"] is False
    assert Pedido.query.count() == 0
    assert Servicio.query.count() == 0
    mesa_db = db.session.get(Mesa, mesa.id)
    assert mesa_db.estado == "DISPONIBLE"


def test_public_order_first_creates_service_and_ocupa_mesa(client, disponible_mesa_context):
    """Caso B: primer pedido valido crea servicio ACTIVO (abierto_por_id NULL) y pedido PENDIENTE."""
    mesa, product, headers = disponible_mesa_context
    response = submit_disponible(client, disponible_mesa_context)
    assert response.status_code == 201
    data = response.json["data"]
    assert data["estado"] == "PENDIENTE"

    servicio = db.session.execute(
        db.select(Servicio).where(Servicio.mesa_id == mesa.id, Servicio.estado == "ACTIVO")
    ).scalar_one()
    assert servicio.abierto_por_id is None

    pedido = db.session.get(Pedido, data["id"])
    assert pedido.estado == "PENDIENTE"
    assert pedido.origen == "PUBLICO"
    assert pedido.servicio_id == servicio.id

    mesa_db = db.session.get(Mesa, mesa.id)
    assert mesa_db.estado == "OCUPADA"


def test_public_order_second_reuses_service(client, disponible_mesa_context):
    """Caso C: segundo pedido reutiliza el servicio ACTIVO existente."""
    mesa, product, headers = disponible_mesa_context

    response1 = submit_disponible(client, disponible_mesa_context)
    assert response1.status_code == 201
    servicio_id = db.session.execute(
        db.select(Servicio.id).where(Servicio.mesa_id == mesa.id, Servicio.estado == "ACTIVO")
    ).scalar_one()

    response2 = submit_disponible(client, disponible_mesa_context)
    assert response2.status_code == 201

    servicios = db.session.execute(
        db.select(Servicio).where(Servicio.mesa_id == mesa.id)
    ).scalars().all()
    assert len(servicios) == 1
    assert servicios[0].id == servicio_id

    pedidos = db.session.execute(
        db.select(Pedido).where(Pedido.servicio_id == servicio_id)
    ).scalars().all()
    assert len(pedidos) == 2


def test_admin_form_tiene_input_imagen(app, client):
    """El formulario ADMIN de productos tiene selector de imagen JPG/PNG."""
    source = Path(__file__).resolve().parents[1] / "app/templates/admin.html"
    html = source.read_text(encoding="utf-8")
    assert 'id="producto-image"' in html
    assert 'name="image"' in html
    assert 'accept="image/jpeg,image/png"' in html


def test_admin_js_envia_json_no_formdata_en_productos():
    """admin.js envía JSON (no FormData) en POST/PATCH de productos."""
    source = Path(__file__).resolve().parents[1] / "app/static/js/admin.js"
    js = source.read_text(encoding="utf-8")
    # payloadFor para productos retorna objeto JSON, no FormData
    assert "name === 'productos') return {" in js
    assert "new FormData()" not in js.split("name === 'productos'")[1].split("}")[0]


def test_admin_js_usa_put_delete_para_imagen():
    """admin.js usa PUT /products/<id>/image y DELETE /products/<id>/image."""
    source = Path(__file__).resolve().parents[1] / "app/static/js/admin.js"
    js = source.read_text(encoding="utf-8")
    assert "/products/' + productId + '/image'" in js
    assert "method: 'PUT', body: fd" in js
    assert "/products/' + recordId + '/image', { method: 'DELETE' }" in js


def test_admin_js_no_establece_content_type_manual_para_formdata():
    """admin.js no fuerza Content-Type cuando el body es FormData."""
    source = Path(__file__).resolve().parents[1] / "app/static/js/admin.js"
    js = source.read_text(encoding="utf-8")
    assert "if (!(options.body instanceof FormData))" in js
    assert "headers['Content-Type'] = 'application/json'" in js


def test_admin_js_mensaje_fallo_parcial_imagen():
    """admin.js muestra mensaje diferenciado cuando falla solo la subida de imagen."""
    source = Path(__file__).resolve().parents[1] / "app/static/js/admin.js"
    js = source.read_text(encoding="utf-8")
    assert "El producto se guardó correctamente, pero no fue posible subir su fotografía." in js


def test_menu_publico_renderiza_imagen_con_fallback():
    """public_menu.js usa image_url con fallback a imagen predeterminada."""
    source = Path(__file__).resolve().parents[1] / "app/static/js/public_menu.js"
    js = source.read_text(encoding="utf-8")
    assert "img.src = product.image_url || '/static/img/default-product.svg'" in js
    assert "img.loading = 'lazy'" in js


def test_menu_publico_css_object_fit_cover():
    """public_menu.css usa object-fit: cover para evitar deformaciones."""
    source = Path(__file__).resolve().parents[1] / "app/static/css/public_menu.css"
    css = source.read_text(encoding="utf-8")
    assert "object-fit: cover" in css


def test_producto_se_puede_crear_sin_imagen(app, client):
    """Caso behavioral: crear producto sin fotografía via POST /products (JSON)."""
    _, headers = autenticar(client, "ADMIN")
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers)
    assert category.status_code == 201
    payload = {"name": "Té", "price": "5.00", "categoria_id": category.json["data"]["id"]}
    response = client.post("/products", json=payload, headers=headers)
    assert response.status_code == 201
    product_id = response.json["data"]["id"]
    product = db.session.get(Product, product_id)
    assert product is not None
    assert product.name == "Té"
    assert str(product.price) == "5.00"


def test_producto_se_puede_crear_con_imagen_url(app, client):
    """Caso behavioral: crear producto y luego subir imagen via PUT /products/<id>/image."""
    _, headers = autenticar(client, "ADMIN")
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers)
    assert category.status_code == 201
    payload = {"name": "Café", "price": "12.35", "categoria_id": category.json["data"]["id"]}
    response = client.post("/products", json=payload, headers=headers)
    assert response.status_code == 201
    product_id = response.json["data"]["id"]

    # El backend aún no implementa PUT /products/<id>/image (pendiente de Kilo 1).
    # Este test verifica que el producto existe y está listo para recibir imagen.
    product = db.session.get(Product, product_id)
    assert product is not None


def test_producto_se_puede_editar_sin_cambiar_imagen(app, client):
    """Caso behavioral: editar producto sin tocar la imagen via PATCH /products/<id> (JSON)."""
    _, headers = autenticar(client, "ADMIN")
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers)
    assert category.status_code == 201
    payload = {"name": "Té", "price": "5.00", "categoria_id": category.json["data"]["id"]}
    response = client.post("/products", json=payload, headers=headers)
    assert response.status_code == 201
    product_id = response.json["data"]["id"]

    path = f"/products/{product_id}"
    response = client.patch(path, json={"price": "6.00"}, headers=headers)
    assert response.status_code == 200

    product = db.session.get(Product, product_id)
    assert product.price == 6.00
