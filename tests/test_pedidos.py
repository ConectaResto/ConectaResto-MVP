from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Category, DetallePedido, Mesa, Pedido, Product, Servicio
from app.pedidos.service import PedidoError, actualizar_pedido, crear_pedido
from tests.test_servicios import autenticar


@pytest.fixture
def contexto(app, client):
    usuario, headers = autenticar(client)
    mesa = Mesa(numero=1)
    categoria = Category(name="Bebidas")
    db.session.add_all([mesa, categoria])
    db.session.flush()
    producto = Product(name="Cafe", price=Decimal("12.35"), categoria_id=categoria.id)
    db.session.add(producto)
    db.session.commit()
    response = client.post("/servicios", json={"mesa_id": mesa.id}, headers=headers)
    assert response.status_code == 201
    servicio_id = response.json["data"]["id"]
    return usuario, headers, producto, servicio_id


def pedir(client, contexto):
    _, headers, producto, servicio_id = contexto
    response = client.post(f"/servicios/{servicio_id}/pedidos", json={
        "items": [{"producto_id": producto.id, "cantidad": 2}],
    }, headers=headers)
    assert response.status_code == 201
    return response.json["data"]


@pytest.mark.parametrize("desactivar_catalogo", [False, True])
def test_precio_historico_y_agrupacion(client, contexto, desactivar_catalogo):
    usuario, headers, producto, servicio_id = contexto
    pedido = pedir(client, contexto)
    assert pedido["estado"] == "PENDIENTE"
    assert pedido["estado_preparacion"] == "NO_ENVIADO"
    assert pedido["autorizado_por_id"] is None
    assert pedido["creado_por_id"] == usuario.id
    assert pedido["total"] == "24.70"
    assert pedido["items"][0]["precio_unitario"] == "12.35"
    producto.price = Decimal("99.00")
    producto.is_available = False
    db.session.commit()
    if desactivar_catalogo:
        admin = client.application.test_client()
        _, admin_headers = autenticar(admin, "ADMIN", "administrador")
        assert admin.delete(f"/categories/{producto.categoria_id}", headers=admin_headers).status_code == 409
        assert admin.delete(f"/products/{producto.id}", headers=admin_headers).status_code == 200
        assert admin.delete(f"/categories/{producto.categoria_id}", headers=admin_headers).status_code == 200
        assert db.session.get(Product, producto.id) is not None
        assert db.session.get(Category, producto.categoria_id) is not None
        assert DetallePedido.query.filter_by(pedido_id=pedido["id"]).count() == 1
    assert client.get(f'/pedidos/{pedido["id"]}').json["data"] == pedido
    assert client.get(f"/servicios/{servicio_id}").json["data"]["pedidos"] == [pedido]
    assert client.post(f'/pedidos/{pedido["id"]}/autorizar', headers=headers).status_code == 200
    enviado = client.post(f'/pedidos/{pedido["id"]}/enviar-cocina', headers=headers)
    assert enviado.status_code == 200
    assert enviado.json["data"]["total"] == "24.70"


def test_flujo_completo_otro_mesero_y_cocina(client, contexto):
    pedido = pedir(client, contexto)
    path = f'/pedidos/{pedido["id"]}'
    _, headers, _, _ = contexto
    assert client.post(f"{path}/enviar-cocina", headers=headers).status_code == 409
    otro, headers = autenticar(client, nombre="otro")
    autorizado = client.post(f"{path}/autorizar", headers=headers)
    assert autorizado.json["data"]["autorizado_por_id"] == otro.id
    assert autorizado.json["data"]["autorizado_at"]
    assert client.post(f"{path}/autorizar", headers=headers).status_code == 409
    assert client.post(f"{path}/enviar-cocina", headers=headers).status_code == 200
    assert client.post(f"{path}/enviar-cocina", headers=headers).status_code == 409
    assert client.post(f"{path}/entregar", headers=headers).status_code == 409
    _, cocina_headers = autenticar(client, "KITCHEN", "cocinero")
    assert len(client.get("/pedidos").json["data"]) == 1
    assert client.patch(f"{path}/preparacion", json={"estado": "LISTO_PARA_SERVIR"},
                        headers=cocina_headers).status_code == 409
    for preparacion in ("EN_COCINA", "LISTO_PARA_SERVIR"):
        response = client.patch(f"{path}/preparacion", json={"estado": preparacion}, headers=cocina_headers)
        assert response.status_code == 200
        assert response.json["data"]["estado_preparacion"] == preparacion
    assert response.json["data"]["estado"] == "LISTO"
    assert client.patch(f"{path}/preparacion", json={"estado": "EN_COCINA"},
                        headers=cocina_headers).status_code == 409
    token = client.get("/auth/csrf").json["data"]["csrf_token"]
    assert client.post("/auth/login", json={"username": "otro", "password": "test-password"},
                       headers={"X-CSRF-Token": token}).status_code == 200
    headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    assert client.post(f"{path}/entregar", headers=headers).json["data"]["estado"] == "ENTREGADO"
    assert client.post(f"{path}/entregar", headers=headers).status_code == 409
    assert client.get("/pedidos?estado=ENTREGADO").json["data"][0]["id"] == pedido["id"]


@pytest.mark.parametrize("cantidad", [0, -1, True, False, "2", 1.5, None, [], {}, 2147483648])
def test_cantidades_invalidas(client, contexto, cantidad):
    _, headers, producto, servicio_id = contexto
    response = client.post(f"/servicios/{servicio_id}/pedidos", json={
        "items": [{"producto_id": producto.id, "cantidad": cantidad}],
    }, headers=headers)
    assert response.status_code == 400
    assert Pedido.query.count() == DetallePedido.query.count() == 0


@pytest.mark.parametrize("items", [None, [], {}, [None], [{}],
    [{"producto_id": True, "cantidad": 1}], [{"producto_id": "1", "cantidad": 1}],
    [{"producto_id": -1, "cantidad": 1}], [{"producto_id": 1, "cantidad": 1, "precio_unitario": "0"}]])
def test_items_invalidos(client, contexto, items):
    _, headers, _, servicio_id = contexto
    assert client.post(f"/servicios/{servicio_id}/pedidos", json={"items": items},
                       headers=headers).status_code == 400
    assert Pedido.query.count() == 0


@pytest.mark.parametrize("campo", ["is_active", "is_available", "categoria"])
def test_producto_no_disponible(client, contexto, campo):
    _, headers, producto, servicio_id = contexto
    if campo == "categoria":
        db.session.get(Category, producto.categoria_id).is_active = False
    else:
        setattr(producto, campo, False)
    db.session.commit()
    assert client.post(f"/servicios/{servicio_id}/pedidos", json={
        "items": [{"producto_id": producto.id, "cantidad": 1}],
    }, headers=headers).status_code == 404
    assert Pedido.query.count() == 0


def test_item_invalido_no_guarda_pedido_parcial(client, contexto):
    usuario, _, producto, servicio_id = contexto
    with pytest.raises(PedidoError) as error:
        crear_pedido(servicio_id, [{"producto_id": producto.id, "cantidad": 1},
                                  {"producto_id": 999, "cantidad": 1}],
                     origen="MESERO", creado_por_id=usuario.id)
    assert error.value.status_code == 404
    assert Pedido.query.count() == DetallePedido.query.count() == 0
    pedir(client, contexto)


def test_fallo_persistencia_revierte_pedido_y_detalles(client, contexto, monkeypatch):
    usuario, _, producto, servicio_id = contexto
    def fallar():
        db.session.flush()
        raise RuntimeError("fallo de persistencia")
    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fallar)
        with pytest.raises(RuntimeError):
            crear_pedido(servicio_id, [{"producto_id": producto.id, "cantidad": 1}],
                         origen="MESERO", creado_por_id=usuario.id)
    assert Pedido.query.count() == DetallePedido.query.count() == 0
    pedir(client, contexto)


def test_funcion_compartida_publica(client, contexto):
    _, _, producto, servicio_id = contexto
    pedido = crear_pedido(servicio_id, [{"producto_id": producto.id, "cantidad": 1}], origen="PUBLICO")
    assert pedido.creado_por_id is None
    assert pedido.autorizado_por_id is None
    assert pedido.origen == "PUBLICO"
    assert pedido.estado == "PENDIENTE"


def test_varios_pedidos_y_precio_cero(client, contexto):
    primero = pedir(client, contexto)
    _, _, producto, servicio_id = contexto
    producto.price = Decimal("0.00")
    db.session.commit()
    segundo = pedir(client, contexto)
    assert segundo["total"] == "0.00"
    pedidos = client.get(f"/servicios/{servicio_id}").json["data"]["pedidos"]
    assert {p["id"] for p in pedidos} == {primero["id"], segundo["id"]}
    assert next(p for p in pedidos if p["id"] == primero["id"])["total"] == "24.70"


@pytest.mark.parametrize("servicio_id,origen,creador", [
    (True, "MESERO", None), (0, "MESERO", None), (2147483648, "PUBLICO", None),
    (1, "INVALIDO", None), (1, "MESERO", None), (1, "PUBLICO", 1),
])
def test_contrato_funcion_compartida(client, contexto, servicio_id, origen, creador):
    _, _, producto, _ = contexto
    with pytest.raises(PedidoError):
        crear_pedido(servicio_id, [{"producto_id": producto.id, "cantidad": 1}],
                     origen=origen, creado_por_id=creador)
    assert Pedido.query.count() == 0


@pytest.mark.parametrize("rol", [None, "ADMIN", "CASHIER", "KITCHEN"])
def test_permisos_acciones_mesero(client, contexto, rol):
    pedido = pedir(client, contexto)
    if rol:
        _, headers = autenticar(client, rol, "otra_sesion")
    else:
        with client.session_transaction() as session:
            session.clear()
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    expected = 403 if rol else 401
    for accion in ("autorizar", "enviar-cocina", "entregar"):
        assert client.post(f'/pedidos/{pedido["id"]}/{accion}', headers=headers).status_code == expected
    if rol in (None, "ADMIN", "CASHIER"):
        assert client.get("/pedidos").status_code == expected
        assert client.get(f'/pedidos/{pedido["id"]}').status_code == expected


@pytest.mark.parametrize("rol", ["WAITER", "ADMIN", "CASHIER"])
def test_solo_cocina_actualiza_preparacion(client, contexto, rol):
    pedido = pedir(client, contexto)
    _, headers = autenticar(client, rol, "otra_sesion")
    assert client.patch(f'/pedidos/{pedido["id"]}/preparacion', json={"estado": "EN_COCINA"},
                        headers=headers).status_code == 403


def test_cocina_no_ve_pendientes_y_valida_preparacion(client, contexto):
    pedido = pedir(client, contexto)
    _, headers = autenticar(client, "KITCHEN", "cocinero")
    assert client.get("/pedidos").json["data"] == []
    assert client.get(f'/pedidos/{pedido["id"]}').status_code == 404
    for data in (None, [], {}, {"estado": "INVALIDO"}, {"estado": []}, {"estado": "EN_COCINA", "extra": 1}):
        assert client.patch(f'/pedidos/{pedido["id"]}/preparacion', json=data, headers=headers).status_code == 400
    assert client.patch(f'/pedidos/{pedido["id"]}/preparacion', json={"estado": "EN_COCINA"},
                        headers=headers).status_code == 409


def test_errores_y_csrf(client, contexto):
    _, headers, _, servicio_id = contexto
    pedido = pedir(client, contexto)
    assert client.get("/pedidos/999").status_code == 404
    assert client.get("/pedidos?estado=INVALIDO").status_code == 400
    assert client.post("/pedidos/999/autorizar", headers=headers).status_code == 404
    for data in (None, [], {}, {"items": [], "estado": "LISTO"}):
        assert client.post(f"/servicios/{servicio_id}/pedidos", json=data, headers=headers).status_code == 400
    assert client.post(f'/pedidos/{pedido["id"]}/autorizar', json={"autorizado_por_id": 99},
                       headers=headers).status_code == 400
    for path in (f'/pedidos/{pedido["id"]}/autorizar', f'/pedidos/{pedido["id"]}/enviar-cocina',
                 f'/pedidos/{pedido["id"]}/entregar', f"/servicios/{servicio_id}/pedidos"):
        assert client.post(path, json={}).status_code == 400
    assert client.patch(f'/pedidos/{pedido["id"]}/preparacion', json={"estado": "EN_COCINA"}).status_code == 400


@pytest.mark.parametrize("rol", ["WAITER", "KITCHEN"])
@pytest.mark.parametrize("pedido_id", [
    "0", "-1", "abc", "1.5", "2147483648", "9223372036854775807",
    "9223372036854775808", str(10 ** 100),
])
def test_consulta_pedido_id_invalido_devuelve_404(client, pedido_id, rol, monkeypatch):
    autenticar(client, rol)

    def consultar_no_permitido(*args, **kwargs):
        pytest.fail("Un ID invalido no debe llegar a la consulta de base de datos")

    monkeypatch.setattr(db, "get_or_404", consultar_no_permitido)
    response = client.get(f"/pedidos/{pedido_id}")
    assert response.status_code == 404
    assert response.json["success"] is False


def test_servicio_cerrado_y_sin_detalles(client, contexto):
    usuario, headers, producto, servicio_id = contexto
    pedido = pedir(client, contexto)
    almacenado = db.session.get(Pedido, pedido["id"])
    for detalle in almacenado.detalles:
        db.session.delete(detalle)
    db.session.commit()
    assert client.post(f'/pedidos/{pedido["id"]}/autorizar', headers=headers).status_code == 200
    assert client.post(f'/pedidos/{pedido["id"]}/enviar-cocina', headers=headers).status_code == 409
    db.session.get(Servicio, servicio_id).estado = "CERRADO"
    db.session.commit()
    with pytest.raises(PedidoError) as error:
        crear_pedido(servicio_id, [{"producto_id": producto.id, "cantidad": 1}],
                     origen="MESERO", creado_por_id=usuario.id)
    assert error.value.status_code == 409
    assert client.post(f'/pedidos/{pedido["id"]}/enviar-cocina', headers=headers).status_code == 409


def test_transicion_revierte_fallo_de_commit(client, contexto, monkeypatch):
    usuario, _, _, _ = contexto
    pedido = pedir(client, contexto)
    def fallar():
        db.session.flush()
        raise RuntimeError("fallo de persistencia")
    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fallar)
        with pytest.raises(RuntimeError):
            actualizar_pedido(pedido["id"], "autorizar", actor=usuario)
    almacenado = db.session.get(Pedido, pedido["id"])
    assert almacenado.autorizado_por_id is None
    assert almacenado.autorizado_at is None
    assert almacenado.estado == "PENDIENTE"


def test_cocina_conserva_historial_despues_de_entrega_pago_y_cierre(app, client, contexto):
    pedido = pedir(client, contexto)
    _, headers, _, servicio_id = contexto
    path = f"/pedidos/{pedido['id']}"
    assert client.post(path + "/autorizar", headers=headers).status_code == 200
    assert client.post(path + "/enviar-cocina", headers=headers).status_code == 200
    cocina = app.test_client()
    _, cocina_headers = autenticar(cocina, "KITCHEN", "cocinero_historial")
    for estado in ("EN_COCINA", "LISTO_PARA_SERVIR"):
        assert cocina.patch(path + "/preparacion", json={"estado": estado},
                            headers=cocina_headers).status_code == 200
    assert client.post(path + "/entregar", headers=headers).status_code == 200
    caja = app.test_client()
    _, caja_headers = autenticar(caja, "CASHIER", "cajero_historial")
    for accion, expected in (("pago-simulado", 201), ("cerrar", 200)):
        assert caja.post(f"/servicios/{servicio_id}/{accion}", headers=caja_headers).status_code == expected
        response = cocina.get("/pedidos")
        assert response.status_code == 200
        assert [(p["id"], p["estado"], p["estado_preparacion"]) for p in response.json["data"]] == [
            (pedido["id"], "ENTREGADO", "LISTO_PARA_SERVIR")
        ]
        assert cocina.get(path).json["data"]["items"] == pedido["items"]
