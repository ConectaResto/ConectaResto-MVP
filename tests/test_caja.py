from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Category, DetallePedido, Mesa, Pago, Pedido, Product, Rol, Servicio, Usuario
from app.pedidos.service import PedidoError, crear_pedido
from app.servicios.service import calcular_total_servicio, procesar_caja
from tests.test_servicios import autenticar


@pytest.fixture
def caja(app, client):
    mesero, headers = autenticar(client)
    mesa = Mesa(numero=1)
    categoria = Category(name="Bebidas")
    db.session.add_all([mesa, categoria])
    db.session.flush()
    producto = Product(name="Cafe", price=Decimal("12.35"), categoria_id=categoria.id)
    db.session.add(producto)
    db.session.commit()
    servicio_id = client.post("/servicios", json={"mesa_id": mesa.id}, headers=headers).json["data"]["id"]
    pedido = crear_pedido(servicio_id, [{"producto_id": producto.id, "cantidad": 2}],
                         origen="MESERO", creado_por_id=mesero.id)
    pedido.estado = "ENTREGADO"
    pedido.estado_preparacion = "LISTO_PARA_SERVIR"
    db.session.commit()
    cajero, headers = autenticar(client, "CASHIER", "cajero")
    return {"servicio_id": servicio_id, "mesa_id": mesa.id, "pedido_id": pedido.id,
            "producto_id": producto.id, "cajero_id": cajero.id, "headers": headers}


def test_pago_total_historico_cierre_y_reapertura(client, caja):
    servicio_id = caja["servicio_id"]
    producto = db.session.get(Product, caja["producto_id"])
    producto.price = Decimal("90.00")
    producto.is_available = False
    db.session.commit()
    assert client.get(f"/servicios/{servicio_id}").json["data"]["total"] == "24.70"
    response = client.post(f"/servicios/{servicio_id}/pago-simulado", headers=caja["headers"])
    assert response.status_code == 201
    pago = response.json["data"]["pago"]
    assert pago["importe"] == "24.70"
    assert pago["registrado_por_id"] == caja["cajero_id"]
    assert pago["fecha_registro"]
    assert client.get(f"/servicios/{servicio_id}").json["data"]["pago"] == pago
    assert client.post(f"/servicios/{servicio_id}/pago-simulado", headers=caja["headers"]).status_code == 409
    assert Pago.query.count() == 1
    response = client.post(f"/servicios/{servicio_id}/cerrar", headers=caja["headers"])
    assert response.status_code == 200
    assert response.json["data"]["estado"] == "CERRADO"
    assert db.session.get(Mesa, caja["mesa_id"]).estado == "DISPONIBLE"
    assert db.session.get(Pedido, caja["pedido_id"]).estado == "ENTREGADO"
    assert client.post(f"/servicios/{servicio_id}/cerrar", headers=caja["headers"]).status_code == 409
    _, headers = autenticar(client, nombre="mesero_reapertura")
    response = client.post("/servicios", json={"mesa_id": caja["mesa_id"]}, headers=headers)
    assert response.status_code == 201
    assert response.json["data"]["id"] != servicio_id


def test_total_agrupa_todos_los_pedidos_sin_mezclar_servicios(client, caja):
    servicio = db.session.get(Servicio, caja["servicio_id"])
    segundo = Pedido(servicio_id=servicio.id, origen="PUBLICO", estado="ENTREGADO")
    segundo.detalles = [DetallePedido(producto_id=caja["producto_id"], cantidad=3,
                                     precio_unitario=Decimal("0.10"))]
    otra_mesa = Mesa(numero=2, estado="OCUPADA")
    otro = Servicio(mesa=otra_mesa, abierto_por_id=servicio.abierto_por_id)
    pedido_ajeno = Pedido(servicio=otro, origen="PUBLICO", estado="ENTREGADO")
    pedido_ajeno.detalles = [DetallePedido(producto_id=caja["producto_id"], cantidad=1,
                                          precio_unitario=Decimal("500.00"))]
    db.session.add_all([segundo, pedido_ajeno])
    db.session.commit()
    response = client.post(f'/servicios/{servicio.id}/pago-simulado', headers=caja["headers"])
    assert response.status_code == 201
    assert response.json["data"]["total"] == response.json["data"]["pago"]["importe"] == "25.00"


def test_servicio_vacio_cierra_sin_pago(client, caja):
    servicio = Servicio(mesa=Mesa(numero=2, estado="OCUPADA"),
                        abierto_por_id=db.session.get(Servicio, caja["servicio_id"]).abierto_por_id)
    db.session.add(servicio)
    db.session.commit()
    path = f"/servicios/{servicio.id}"
    assert client.post(f"{path}/pago-simulado", headers=caja["headers"]).status_code == 409
    response = client.post(f"{path}/cerrar", headers=caja["headers"])
    assert response.status_code == 200
    assert response.json["data"]["total"] == "0.00"
    assert response.json["data"]["pago"] is None
    assert db.session.get(Mesa, servicio.mesa_id).estado == "DISPONIBLE"


@pytest.mark.parametrize("estado", ["PENDIENTE", "EN_PREPARACION", "LISTO"])
@pytest.mark.parametrize("accion", ["pago-simulado", "cerrar"])
def test_pedidos_sin_entregar_bloquean_caja(client, caja, estado, accion):
    db.session.get(Pedido, caja["pedido_id"]).estado = estado
    db.session.commit()
    assert client.post(f'/servicios/{caja["servicio_id"]}/{accion}', headers=caja["headers"]).status_code == 409
    assert Pago.query.count() == 0
    assert db.session.get(Servicio, caja["servicio_id"]).estado == "ACTIVO"


@pytest.mark.parametrize("importe", [None, Decimal("1.00"), Decimal("25.00")])
def test_cierre_requiere_pago_completo(client, caja, importe):
    if importe is not None:
        db.session.add(Pago(servicio_id=caja["servicio_id"], importe=importe,
                            registrado_por_id=caja["cajero_id"]))
        db.session.commit()
    assert client.post(f'/servicios/{caja["servicio_id"]}/cerrar', headers=caja["headers"]).status_code == 409
    assert db.session.get(Mesa, caja["mesa_id"]).estado == "OCUPADA"


@pytest.mark.parametrize("precio,cantidad", [(Decimal("0.00"), 2), (Decimal("99999999.99"), 2)])
def test_importe_cero_o_fuera_de_capacidad(client, caja, precio, cantidad):
    detalle = db.session.get(Pedido, caja["pedido_id"]).detalles[0]
    detalle.precio_unitario = precio
    detalle.cantidad = cantidad
    db.session.commit()
    assert client.post(f'/servicios/{caja["servicio_id"]}/pago-simulado', headers=caja["headers"]).status_code == 409
    assert Pago.query.count() == 0


@pytest.mark.parametrize("canal", ["MESERO", "PUBLICO"])
def test_pago_bloquea_pedidos_en_ambos_endpoints(app, client, caja, canal):
    servicio_id = caja["servicio_id"]
    assert client.post(f"/servicios/{servicio_id}/pago-simulado", headers=caja["headers"]).status_code == 201
    if canal == "MESERO":
        _, headers = autenticar(client, nombre="mesero_nuevo")
        path = f"/servicios/{servicio_id}/pedidos"
    else:
        client = app.test_client()
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
        token = db.session.get(Mesa, caja["mesa_id"]).public_token
        path = f"/public/mesas/{token}/pedidos"
    response = client.post(path, headers=headers, json={
        "items": [{"producto_id": caja["producto_id"], "cantidad": 1}],
    })
    assert response.status_code == 409
    assert Pedido.query.count() == 1
    assert Pago.query.one().importe == Decimal("24.70")


@pytest.mark.parametrize("rol", [None, "WAITER", "ADMIN", "KITCHEN"])
def test_solo_cashier_paga_y_cierra(client, caja, rol):
    if rol is None:
        with client.session_transaction() as session:
            session.clear()
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    else:
        _, headers = autenticar(client, rol, "otro_usuario")
    for accion in ("pago-simulado", "cerrar"):
        assert client.post(f'/servicios/{caja["servicio_id"]}/{accion}', headers=headers).status_code == (401 if rol is None else 403)
    assert Pago.query.count() == 0


@pytest.mark.parametrize("rol,codigo", [(None, 401), ("WAITER", 200), ("CASHIER", 200),
                                       ("ADMIN", 403), ("KITCHEN", 403)])
def test_permisos_consulta_servicio(client, caja, rol, codigo):
    if rol is None:
        with client.session_transaction() as session:
            session.clear()
    else:
        autenticar(client, rol, "consulta")
    response = client.get(f'/servicios/{caja["servicio_id"]}')
    assert response.status_code == codigo
    if codigo == 200:
        assert response.json["data"]["total"] == "24.70"
        assert response.json["data"]["pago"] is None


@pytest.mark.parametrize("accion", ["pago-simulado", "cerrar"])
@pytest.mark.parametrize("token", [None, "invalido"])
def test_csrf_caja(client, caja, accion, token):
    headers = {} if token is None else {"X-CSRF-Token": token}
    assert client.post(f'/servicios/{caja["servicio_id"]}/{accion}', headers=headers).status_code == 400
    assert Pago.query.count() == 0


@pytest.mark.parametrize("accion", ["pago-simulado", "cerrar"])
@pytest.mark.parametrize("data", [None, [], {"importe": "0.01"}, {"medio": "inventado"}])
def test_caja_rechaza_campos_del_cliente(client, caja, accion, data):
    if data is None:
        response = client.post(f'/servicios/{caja["servicio_id"]}/{accion}', data="null",
                               headers=caja["headers"], content_type="application/json")
    else:
        response = client.post(f'/servicios/{caja["servicio_id"]}/{accion}', json=data,
                               headers=caja["headers"], content_type="application/json")
    assert response.status_code == 400


@pytest.mark.parametrize("accion", ["pago-simulado", "cerrar"])
@pytest.mark.parametrize("servicio_id", [0, 999, 2147483648, 9223372036854775808])
def test_caja_ids_invalidos(client, caja, accion, servicio_id):
    assert client.post(f"/servicios/{servicio_id}/{accion}", headers=caja["headers"]).status_code == 404


@pytest.mark.parametrize("accion", ["pago-simulado", "cerrar"])
def test_servicio_cerrado_rechaza_operaciones(client, caja, accion):
    db.session.get(Servicio, caja["servicio_id"]).estado = "CERRADO"
    db.session.commit()
    assert client.post(f'/servicios/{caja["servicio_id"]}/{accion}', headers=caja["headers"]).status_code == 409


@pytest.mark.parametrize("estado", ["DISPONIBLE", "CERRADA"])
def test_cierre_no_sobrescribe_estado_incompatible_de_mesa(client, caja, estado):
    client.post(f'/servicios/{caja["servicio_id"]}/pago-simulado', headers=caja["headers"])
    db.session.get(Mesa, caja["mesa_id"]).estado = estado
    db.session.commit()
    assert client.post(f'/servicios/{caja["servicio_id"]}/cerrar', headers=caja["headers"]).status_code == 409
    assert db.session.get(Servicio, caja["servicio_id"]).estado == "ACTIVO"
    assert db.session.get(Mesa, caja["mesa_id"]).estado == estado


@pytest.mark.parametrize("accion", ["pago-simulado", "cerrar"])
def test_rollback_caja_despues_de_flush(client, caja, accion, monkeypatch):
    if accion == "cerrar":
        assert client.post(f'/servicios/{caja["servicio_id"]}/pago-simulado', headers=caja["headers"]).status_code == 201
    actor = db.session.get(Usuario, caja["cajero_id"])

    def fallar():
        db.session.flush()
        raise RuntimeError("fallo tras persistir cambios")

    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fallar)
        with pytest.raises(RuntimeError):
            procesar_caja(caja["servicio_id"], accion, actor=actor)
    assert db.session.get(Servicio, caja["servicio_id"]).estado == "ACTIVO"
    assert db.session.get(Mesa, caja["mesa_id"]).estado == "OCUPADA"
    assert Pago.query.count() == (1 if accion == "cerrar" else 0)
    assert client.post(f'/servicios/{caja["servicio_id"]}/{accion}', headers=caja["headers"]).status_code == (200 if accion == "cerrar" else 201)


@pytest.mark.parametrize("acciones,con_pedido,pagado", [
    (("pago-simulado", "pago-simulado"), True, False),
    (("cerrar", "cerrar"), True, True),
    (("pago-simulado", "pedido"), True, False),
    (("cerrar", "pedido"), False, False),
    (("cerrar", "publico"), True, True),
])
def test_concurrencia_caja_y_pedidos(tmp_path, monkeypatch, acciones, con_pedido, pagado):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path / 'caja.db'}")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        mesero = Usuario(username="mesero", email="mesero@test.invalid", password_hash="test", rol=Rol(name="WAITER"))
        cajero = Usuario(username="cajero", email="cajero@test.invalid", password_hash="test", rol=Rol(name="CASHIER"))
        mesa = Mesa(numero=1, estado="OCUPADA")
        categoria = Category(name="Bebidas")
        db.session.add_all([mesero, cajero, mesa, categoria])
        db.session.flush()
        servicio = Servicio(mesa=mesa, abierto_por_id=mesero.id)
        producto = Product(name="Cafe", price=Decimal("12.35"), categoria_id=categoria.id)
        db.session.add_all([servicio, producto])
        db.session.flush()
        if con_pedido:
            pedido = Pedido(servicio=servicio, origen="MESERO", creado_por_id=mesero.id,
                            estado="ENTREGADO", estado_preparacion="LISTO_PARA_SERVIR")
            pedido.detalles = [DetallePedido(producto=producto, cantidad=2, precio_unitario=producto.price)]
            db.session.add(pedido)
        if pagado:
            db.session.add(Pago(servicio=servicio, registrado_por_id=cajero.id, importe=Decimal("24.70")))
        db.session.commit()
        servicio_id, producto_id, mesa_id = servicio.id, producto.id, mesa.id
        mesero_id, cajero_id, token = mesero.id, cajero.id, mesa.public_token
    barrera = Barrier(2)

    def ejecutar(accion):
        with app.app_context():
            if accion == "publico":
                client = app.test_client()
                csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
                barrera.wait(timeout=10)
                return client.post(f"/public/mesas/{token}/pedidos", headers={"X-CSRF-Token": csrf},
                                   json={"items": [{"producto_id": producto_id, "cantidad": 1}]}).status_code
            actor = db.session.get(Usuario, mesero_id if accion == "pedido" else cajero_id)
            barrera.wait(timeout=10)
            try:
                if accion == "pedido":
                    crear_pedido(servicio_id, [{"producto_id": producto_id, "cantidad": 1}],
                                 origen="MESERO", creado_por_id=actor.id)
                    return 201
                procesar_caja(servicio_id, accion, actor=actor)
                return 201 if accion == "pago-simulado" else 200
            except PedidoError as error:
                return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(ejecutar, acciones))
        with app.app_context():
            servicio = db.session.get(Servicio, servicio_id)
            pago = Pago.query.filter_by(servicio_id=servicio_id).one_or_none()
            if acciones == ("cerrar", "publico"):
                assert resultados == [200, 409]
            elif acciones == ("cerrar", "pedido"):
                assert resultados in ([200, 409], [409, 201])
            elif acciones == ("cerrar", "cerrar"):
                assert sorted(resultados) == [200, 409]
            else:
                assert sorted(resultados) == [201, 409]
            if pago is not None:
                assert pago.importe == calcular_total_servicio(servicio_id)
                assert all(p.estado == "ENTREGADO" for p in servicio.pedidos)
            if servicio.estado == "CERRADO":
                assert db.session.get(Mesa, mesa_id).estado == "DISPONIBLE"
                assert all(p.estado == "ENTREGADO" for p in servicio.pedidos)
            else:
                assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
