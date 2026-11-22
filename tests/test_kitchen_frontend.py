from app.catalog.models import Category, Product
from app.extensions import db
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.servicios.models import Servicio
from tests.test_servicios import autenticar


def test_kitchen_clasificacion_y_transiciones(client):
    waiter, _ = autenticar(client, "WAITER", "mesero_cocina")
    category = Category(name="Cocina")
    mesa = Mesa(numero=77, estado="OCUPADA")
    db.session.add_all([category, mesa])
    db.session.flush()
    products = [Product(name=name, price="12.35", categoria_id=category.id,
                        is_available=available) for name, available in (
        ("Cafe <img src=x onerror=alert(1)>", True), ("Sopa", True), ("Retirado", False),
    )]
    db.session.add_all(products)
    service = Servicio(mesa_id=mesa.id, abierto_por_id=waiter.id, estado="ACTIVO")
    db.session.add(service)
    db.session.flush()
    orders = []
    # Deliberately interleave history, active and hidden orders to catch index drift.
    for prep, state, product_index, quantity in (
        ("LISTO_PARA_SERVIR", "ENTREGADO", 1, 3),
        ("RECIBIDO", "EN_PREPARACION", 0, 2),
        ("EN_COCINA", "EN_PREPARACION", 2, 4),
        ("NO_ENVIADO", "PENDIENTE", 0, 1),
    ):
        order = Pedido(servicio_id=service.id, origen="MESERO", estado=state,
                       estado_preparacion=prep,
                       autorizado_por_id=waiter.id if prep != "NO_ENVIADO" else None)
        order.detalles = [DetallePedido(producto_id=products[product_index].id,
                                       cantidad=quantity, precio_unitario="12.35")]
        db.session.add(order)
        orders.append(order)
    db.session.commit()
    ids = [p.id for p in orders]
    _, headers = autenticar(client, "KITCHEN", "cocinero")
    response = client.get("/pedidos")
    assert response.status_code == 200
    assert {pedido["id"] for pedido in response.json["data"]} == set(ids[:3])
    assert client.get(f"/pedidos/{ids[3]}").status_code == 404

    for order_id, transitions in (
        (ids[1], ("EN_COCINA", "LISTO_PARA_SERVIR")),
        (ids[2], ("LISTO_PARA_SERVIR",)),
    ):
        for preparation in transitions:
            response = client.patch(f"/pedidos/{order_id}/preparacion",
                                    json={"estado": preparation}, headers=headers)
            assert response.status_code == 200
            assert response.json["data"]["estado_preparacion"] == preparation

    db.session.expire_all()
    assert db.session.get(Pedido, ids[1]).estado_preparacion == "LISTO_PARA_SERVIR"
    assert db.session.get(Pedido, ids[2]).estado_preparacion == "LISTO_PARA_SERVIR"
    assert db.session.get(Pedido, ids[3]).estado_preparacion == "NO_ENVIADO"
