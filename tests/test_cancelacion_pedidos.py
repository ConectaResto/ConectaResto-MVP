from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from app import create_app
from app.catalog.models import Category, Product
from app.config import TestingConfig
from app.extensions import db
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.pedidos.service import PedidoError, actualizar_pedido
from app.servicios.models import Pago, Servicio
from app.servicios.service import calcular_total_servicio, procesar_caja
from app.users.models import Rol, Usuario
from tests.test_pedidos import contexto, pedir
from tests.test_servicios import autenticar


@pytest.mark.parametrize("autorizado", [False, True])
def test_cancelacion_terminal_conserva_historico(app, client, contexto, autorizado):
    _, headers, producto, servicio_id = contexto
    pedido = pedir(client, contexto)
    path = f'/pedidos/{pedido["id"]}'
    if autorizado:
        respuesta = client.post(f"{path}/autorizar", headers=headers)
        assert respuesta.status_code == 200
        pedido = respuesta.json["data"]
        assert pedido["autorizado_por_id"] and pedido["autorizado_at"]

    producto.price = Decimal("99.00")
    db.session.commit()
    argumentos = {"json": {}} if autorizado else {}
    respuesta = client.post(f"{path}/cancelar", headers=headers, **argumentos)
    assert respuesta.status_code == 200
    historico = {**pedido, "estado": "CANCELADO"}
    assert respuesta.json["data"] == historico
    assert client.get(path).json["data"] == historico
    assert client.get("/pedidos?estado=CANCELADO").json["data"] == [historico]
    assert client.get("/pedidos?estado=PENDIENTE").json["data"] == []
    servicio = client.get(f"/servicios/{servicio_id}").json["data"]
    assert servicio["pedidos"] == [historico]
    assert servicio["total"] == "0.00"
    assert calcular_total_servicio(servicio_id) == Decimal("24.70")
    for accion in ("cancelar", "autorizar", "enviar-cocina", "entregar"):
        assert client.post(f"{path}/{accion}", headers=headers).status_code == 409

    cocina = app.test_client()
    _, csrf = autenticar(cocina, "KITCHEN", "cocinero_cancelacion")
    assert cocina.get("/pedidos").json["data"] == []
    assert cocina.get("/pedidos?estado=CANCELADO").json["data"] == []
    assert cocina.get(path).status_code == 404
    assert cocina.patch(f"{path}/preparacion", json={"estado": "EN_COCINA"},
                        headers=csrf).status_code == 409


def test_cancelacion_permisos_body_csrf_y_404(app, client, contexto):
    _, headers, _, _ = contexto
    pedido = pedir(client, contexto)
    path = f'/pedidos/{pedido["id"]}/cancelar'
    assert client.post(path).status_code == 400
    for datos in ({"estado": "CANCELADO"}, [], "cancelar"):
        assert client.post(path, json=datos, headers=headers).status_code == 400
    assert client.post(path, data="{", content_type="application/json", headers=headers).status_code == 400
    for pedido_id in (0, pedido["id"] + 1, 2147483648):
        assert client.post(f"/pedidos/{pedido_id}/cancelar", headers=headers).status_code == 404
    anonimo = app.test_client()
    csrf = anonimo.get("/auth/csrf").json["data"]["csrf_token"]
    assert anonimo.post(path, headers={"X-CSRF-Token": csrf}).status_code == 401
    for rol in ("ADMIN", "KITCHEN", "CASHIER"):
        otro = app.test_client()
        _, csrf = autenticar(otro, rol, rol.lower())
        assert otro.post(path, headers=csrf).status_code == 403
    assert client.get(f'/pedidos/{pedido["id"]}').json["data"] == pedido


@pytest.mark.parametrize("estado,preparacion,cerrado", [
    ("PENDIENTE", "RECIBIDO", False),
    ("EN_PREPARACION", "RECIBIDO", False),
    ("LISTO", "LISTO_PARA_SERVIR", False),
    ("ENTREGADO", "LISTO_PARA_SERVIR", False),
    ("PENDIENTE", "NO_ENVIADO", True),
])
def test_cancelacion_rechaza_pedido_enviado_o_servicio_cerrado(
    client, contexto, estado, preparacion, cerrado,
):
    _, headers, _, _ = contexto
    pedido = db.session.get(Pedido, pedir(client, contexto)["id"])
    pedido.estado = estado
    pedido.estado_preparacion = preparacion
    if cerrado:
        pedido.servicio.estado = "CERRADO"
    db.session.commit()
    assert client.post(f"/pedidos/{pedido.id}/cancelar", headers=headers).status_code == 409
    assert (pedido.estado, pedido.estado_preparacion) == (estado, preparacion)


def test_cancelacion_rechaza_pago_registrado_y_conserva_historico(app, client, contexto):
    _, headers, _, servicio_id = contexto
    path = f'/pedidos/{pedir(client, contexto)["id"]}'
    autorizado = client.post(f"{path}/autorizar", headers=headers)
    assert autorizado.status_code == 200
    pedido = autorizado.json["data"]
    assert (pedido["estado"], pedido["estado_preparacion"]) == ("PENDIENTE", "NO_ENVIADO")

    cajero, _ = autenticar(app.test_client(), "CASHIER", "caja_pago_previo")
    # Simula un registro histórico inconsistente que la API de caja hoy rechaza.
    db.session.add(Pago(servicio_id=servicio_id, importe=Decimal(pedido["total"]),
                        registrado_por_id=cajero.id))
    db.session.commit()

    servicio_path = f"/servicios/{servicio_id}"
    servicio_antes = client.get(servicio_path).json["data"]
    assert servicio_antes["pago"]["importe"] == pedido["total"]
    assert client.post(f"{path}/cancelar", headers=headers).status_code == 409
    assert client.get(path).json["data"] == pedido
    assert client.get(servicio_path).json["data"] == servicio_antes


@pytest.mark.parametrize("entregado", [None, Decimal("0.00"), Decimal("0.07")])
def test_caja_con_cancelados(app, client, contexto, entregado):
    _, headers, _, servicio_id = contexto
    cancelado = pedir(client, contexto)
    assert client.post(f'/pedidos/{cancelado["id"]}/cancelar', headers=headers).status_code == 200
    if entregado is not None:
        pedido = db.session.get(Pedido, pedir(client, contexto)["id"])
        pedido.detalles[0].precio_unitario = entregado
        pedido.estado = "ENTREGADO"
        pedido.estado_preparacion = "LISTO_PARA_SERVIR"
        db.session.commit()
    caja = app.test_client()
    _, csrf = autenticar(caja, "CASHIER", "caja_cancelacion")
    path = f"/servicios/{servicio_id}"
    total = (entregado or Decimal("0.00")) * 2
    if total > 0:
        assert caja.post(f"{path}/cerrar", headers=csrf).status_code == 409
        pago = caja.post(f"{path}/pago-simulado", headers=csrf)
        assert pago.status_code == 201
        assert pago.json["data"]["pago"]["importe"] == "0.14"
    assert caja.post(f"{path}/pago-simulado", headers=csrf).status_code == 409
    cerrado = caja.post(f"{path}/cerrar", headers=csrf)
    assert cerrado.status_code == 200
    datos = cerrado.json["data"]
    assert datos["estado"] == "CERRADO"
    assert datos["total"] == format(total, ".2f")
    assert Pago.query.count() == int(total > 0)
    assert db.session.get(Mesa, datos["mesa_id"]).estado == "DISPONIBLE"
    historico = next(p for p in datos["pedidos"] if p["id"] == cancelado["id"])
    assert historico == {**cancelado, "estado": "CANCELADO"}


@pytest.mark.parametrize("competidor", ["enviar-cocina", "cerrar", "pago-simulado"])
def test_carrera_cancelacion_con_cocina_y_caja(tmp_path, monkeypatch, competidor):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path / 'cancelacion.db'}")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        mesero = Usuario(username="mesero", email="mesero@test.invalid",
                         password_hash="test", rol=Rol(name="WAITER"))
        cajero = Usuario(username="cajero", email="cajero@test.invalid",
                         password_hash="test", rol=Rol(name="CASHIER"))
        servicio = Servicio(mesa=Mesa(numero=1, estado="OCUPADA"), abierto_por=mesero)
        categoria = Category(name="Bebidas")
        db.session.add(categoria)
        db.session.flush()
        producto = Product(name="Cafe", price=Decimal("1.23"), categoria_id=categoria.id)
        pendiente = Pedido(servicio=servicio, origen="MESERO", autorizado_por=mesero)
        pendiente.detalles = [DetallePedido(producto=producto, cantidad=1, precio_unitario=producto.price)]
        db.session.add_all([pendiente, cajero])
        if competidor == "pago-simulado":
            entregado = Pedido(servicio=servicio, origen="PUBLICO", estado="ENTREGADO",
                               estado_preparacion="LISTO_PARA_SERVIR")
            entregado.detalles = [DetallePedido(producto=producto, cantidad=2, precio_unitario=producto.price)]
            db.session.add(entregado)
        db.session.commit()
        pedido_id, servicio_id = pendiente.id, servicio.id
        mesero_id, cajero_id = mesero.id, cajero.id

    barrera = Barrier(2)

    def ejecutar(accion):
        with app.app_context():
            es_caja = accion in ("cerrar", "pago-simulado")
            actor = db.session.get(Usuario, cajero_id if es_caja else mesero_id)
            barrera.wait(timeout=10)
            try:
                if es_caja:
                    procesar_caja(servicio_id, accion, actor=actor)
                else:
                    actualizar_pedido(pedido_id, accion, actor=actor)
                return 200
            except PedidoError as error:
                return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(ejecutar, ("cancelar", competidor)))
        with app.app_context():
            pedido = db.session.get(Pedido, pedido_id)
            servicio = db.session.get(Servicio, servicio_id)
            if competidor == "enviar-cocina":
                assert sorted(resultados) == [200, 409]
                esperado = ("CANCELADO", "NO_ENVIADO") if resultados[0] == 200 else ("EN_PREPARACION", "RECIBIDO")
                assert (pedido.estado, pedido.estado_preparacion) == esperado
            else:
                assert resultados in ([200, 200], [200, 409])
                assert pedido.estado == "CANCELADO"
                if resultados[1] == 409:
                    procesar_caja(servicio_id, competidor, actor=db.session.get(Usuario, cajero_id))
                if competidor == "cerrar":
                    assert servicio.estado == "CERRADO"
                    assert servicio.pago is None
                else:
                    assert servicio.pago.importe == Decimal("2.46")
    finally:
        with app.app_context():
            db.engine.dispose()
