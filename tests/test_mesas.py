import re
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.catalog.models import Category, Product
from app.extensions import db
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.servicios.models import Pago, Servicio
from app.users.models import Rol, Usuario


def csrf_headers(client):
    token = client.get("/auth/csrf").json["data"]["csrf_token"]
    return {"X-CSRF-Token": token}


def authenticate(client, role):
    username = f"tables-{role.lower()}"
    user = Usuario(username=username, email=f"{username}@example.test", rol=Rol(name=role))
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    response = client.post("/auth/login", json={
        "username": user.username, "password": "test-password",
    }, headers=csrf_headers(client))
    assert response.status_code == 200
    return csrf_headers(client)


@pytest.fixture
def admin_headers(client):
    return authenticate(client, "ADMIN")


def test_create_read_update_without_delete(client, admin_headers):
    assert client.get("/admin/mesas").json == {"success": True, "data": []}
    response = client.post("/admin/mesas", json={"numero": 2}, headers=admin_headers)
    assert response.status_code == 201
    mesa = response.json["data"]
    assert mesa["numero"] == 2
    assert mesa["estado"] == "DISPONIBLE"
    assert re.fullmatch(r"[0-9a-f]{64}", mesa["public_token"])
    path = f'/admin/mesas/{mesa["id"]}'
    assert client.get(path).json["data"] == mesa
    for estado in ("OCUPADA", "CERRADA", "DISPONIBLE"):
        updated = client.patch(path, json={"numero": 3, "estado": estado}, headers=admin_headers)
        assert updated.status_code == 200
        assert updated.json["data"] == {**mesa, "numero": 3, "estado": estado}
    response = client.post("/admin/mesas", json={"numero": 1, "estado": "CERRADA"}, headers=admin_headers)
    assert response.status_code == 201
    assert response.json["data"]["public_token"] != mesa["public_token"]
    assert [m["numero"] for m in client.get("/admin/mesas").json["data"]] == [3]
    assert client.delete(path, headers=admin_headers).status_code == 405
    assert client.get(path).status_code == 200


def test_soft_delete_and_reactivation_preserve_history_and_qr(app, client, admin_headers, monkeypatch):
    monkeypatch.setitem(app.config, "PUBLIC_BASE_URL", "https://resto.example.test")
    mesa = Mesa(numero=1)
    other = Mesa(numero=2)
    category = Category(name="Bebidas")
    db.session.add(category)
    db.session.flush()
    product = Product(name="Cafe", price=Decimal("10.00"), categoria_id=category.id)
    service = Servicio(mesa=mesa, estado="CERRADO")
    order = Pedido(servicio=service, origen="PUBLICO", estado="ENTREGADO")
    detail = DetallePedido(pedido=order, producto=product, precio_unitario=product.price)
    cashier = Usuario(username="cashier", email="cashier@example.test", rol=Rol(name="CASHIER"))
    cashier.set_password("test-password")
    payment = Pago(servicio=service, registrado_por=cashier, importe=product.price)
    db.session.add_all([mesa, other, detail, payment])
    db.session.commit()
    mesa_id, other_id = mesa.id, other.id
    token, other_token = mesa.public_token, other.public_token
    service_id, order_id, detail_id, payment_id = service.id, order.id, detail.id, payment.id
    order_data = {"items": [{"producto_id": product.id, "cantidad": 1}]}

    response = client.patch(f"/admin/mesas/{mesa_id}", json={"estado": "CERRADA"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json["data"]["estado"] == "CERRADA"
    assert [row["id"] for row in client.get("/admin/mesas").json["data"]] == [other_id]

    forbidden = client.patch(
        f"/admin/mesas/{mesa_id}", json={"numero": 99, "estado": "OCUPADA"},
        headers=admin_headers,
    )
    assert forbidden.status_code == 409

    db.session.remove()
    stored = db.session.get(Mesa, mesa_id)
    assert (stored.numero, stored.estado, stored.public_token) == (1, "CERRADA", token)
    assert (stored.servicios[0].id, stored.servicios[0].estado) == (service_id, "CERRADO")
    assert stored.servicios[0].pedidos[0].id == order_id
    assert stored.servicios[0].pedidos[0].detalles[0].id == detail_id
    assert stored.servicios[0].pago.id == payment_id

    waiter = app.test_client()
    waiter_headers = authenticate(waiter, "WAITER")
    assert [row["id"] for row in waiter.get("/mesas").json["data"]] == [other_id]
    assert waiter.get(f"/mesas?id={mesa_id}").json["data"] == []
    assert waiter.get(f"/mesas?id={mesa_id}&estado=CERRADA").json["data"] == [
        {"id": mesa_id, "numero": 1, "estado": "CERRADA"},
    ]
    assert waiter.post("/servicios", json={"mesa_id": mesa_id}, headers=waiter_headers).status_code == 409

    public = app.test_client()
    public_headers = csrf_headers(public)
    assert public.get(f"/public/mesas/{token}").status_code == 200
    blocked = public.post(f"/public/mesas/{token}/pedidos", json=order_data, headers=public_headers)
    assert blocked.status_code == 409
    assert Servicio.query.count() == Pedido.query.count() == 1
    assert client.get(f"/admin/mesas/{other_id}/qr.svg").status_code == 200
    assert public.get(f"/public/mesas/{other_token}/menu").status_code == 302
    assert public.post(
        f"/public/mesas/{other_token}/pedidos", json=order_data, headers=public_headers,
    ).status_code == 201
    assert db.session.get(Mesa, other_id).estado == "OCUPADA"

    history = waiter.get(f"/servicios/{service_id}").json["data"]
    assert history["mesa_numero"] == 1
    assert history["estado"] == "CERRADO"
    assert history["pedidos"][0]["id"] == order_id
    assert history["pedidos"][0]["items"][0]["producto_id"] == order_data["items"][0]["producto_id"]
    assert history["pago"]["id"] == payment_id

    reactivated = client.post("/admin/mesas", json={"numero": 1}, headers=admin_headers)
    assert reactivated.status_code == 200
    assert reactivated.json["data"] == {
        "id": mesa_id, "numero": 1, "estado": "DISPONIBLE", "public_token": token,
    }
    db.session.remove()
    assert Mesa.query.count() == 2
    assert db.session.get(Mesa, mesa_id).estado == "DISPONIBLE"
    assert waiter.get(f"/servicios/{service_id}").json["data"] == history
    assert waiter.get("/servicios?estado=CERRADO").json["data"] == [history]
    assert waiter.get(f"/mesas?id={mesa_id}").json["data"] == [
        {"id": mesa_id, "numero": 1, "estado": "DISPONIBLE"},
    ]
    assert public.post(
        f"/public/mesas/{token}/pedidos", json=order_data, headers=public_headers,
    ).status_code == 201
    assert waiter.get(f"/servicios/{service_id}").json["data"] == history


def test_reactivation_rejects_closed_table_with_active_service(client, admin_headers):
    mesa = Mesa(numero=1, estado="CERRADA")
    servicio = Servicio(mesa=mesa)
    db.session.add(servicio)
    db.session.commit()
    mesa_id, token, servicio_id = mesa.id, mesa.public_token, servicio.id

    response = client.post("/admin/mesas", json={"numero": 1}, headers=admin_headers)
    assert response.status_code == 409
    assert response.json["error"] == "La mesa tiene un servicio activo"

    db.session.remove()
    assert Mesa.query.count() == 1
    stored = db.session.get(Mesa, mesa_id)
    assert (stored.estado, stored.public_token) == ("CERRADA", token)
    assert db.session.get(Servicio, servicio_id).estado == "ACTIVO"


@pytest.mark.parametrize("estado", ["OCUPADA", "CERRADA"])
def test_reactivation_requires_available_state(client, admin_headers, estado):
    original = client.post(
        "/admin/mesas", json={"numero": 1, "estado": "CERRADA"}, headers=admin_headers,
    ).json["data"]
    response = client.post("/admin/mesas", json={"numero": 1, "estado": estado}, headers=admin_headers)
    assert response.status_code == 409
    assert client.get(f"/admin/mesas/{original['id']}").json["data"] == original

    response = client.post(
        "/admin/mesas", json={"numero": 1, "estado": "DISPONIBLE"}, headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json["data"] == {**original, "estado": "DISPONIBLE"}


@pytest.mark.parametrize("extra", [{}, {"numero": 99}])
def test_closed_table_requires_available_reactivation(client, admin_headers, extra):
    response = client.post(
        "/admin/mesas", json={"numero": 10, "estado": "CERRADA"}, headers=admin_headers,
    )
    assert response.status_code == 201
    original = response.json["data"]
    path = f"/admin/mesas/{original['id']}"

    forbidden = client.patch(path, json={**extra, "estado": "OCUPADA"}, headers=admin_headers)
    assert forbidden.status_code == 409
    assert forbidden.json == {
        "success": False,
        "error": "Una mesa cerrada no puede pasar directamente a ocupada",
    }
    db.session.remove()
    stored = db.session.get(Mesa, original["id"])
    assert (stored.numero, stored.estado, stored.public_token) == (
        original["numero"], "CERRADA", original["public_token"],
    )
    assert client.get(path).json["data"] == original
    assert client.get("/admin/mesas").json["data"] == []

    reactivated = client.patch(path, json={"estado": "DISPONIBLE"}, headers=admin_headers)
    assert reactivated.status_code == 200
    assert reactivated.json["data"] == {**original, "estado": "DISPONIBLE"}
    assert client.get("/admin/mesas").json["data"] == [reactivated.json["data"]]


@pytest.mark.parametrize("estado", ["CERRADA", "DISPONIBLE"])
def test_active_service_blocks_incompatible_table_update(client, admin_headers, estado):
    mesa = Mesa(numero=1, estado="OCUPADA")
    service = Servicio(mesa=mesa)
    db.session.add(service)
    db.session.commit()
    path = f"/admin/mesas/{mesa.id}"

    response = client.patch(path, json={"numero": 2, "estado": estado}, headers=admin_headers)
    assert response.status_code == 409
    assert response.json["error"] == "La mesa tiene un servicio activo"
    assert (mesa.numero, mesa.estado, service.estado) == (1, "OCUPADA", "ACTIVO")
    assert [row["id"] for row in client.get("/admin/mesas").json["data"]] == [mesa.id]
    assert client.patch(path, json={"numero": 2, "estado": "OCUPADA"}, headers=admin_headers).status_code == 200


@pytest.mark.parametrize("method,path", [("GET", "/admin/mesas/999"), ("PATCH", "/admin/mesas/999")])
def test_missing_table(client, admin_headers, method, path):
    response = client.open(path, method=method, json={"estado": "CERRADA"}, headers=admin_headers)
    assert response.status_code == 404
    assert response.json["success"] is False


@pytest.mark.parametrize("data", [
    None, [], {}, {"estado": "OCUPADA"},
    *[{"numero": n} for n in (0, -1, True, False, "1", 1.5, None, 2147483648)],
    *[{"numero": 1, "estado": s} for s in ("INVALIDO", "disponible", None, [], 1)],
    {"numero": 1, "public_token": "client-token"}, {"numero": 1, "id": 99},
])
def test_invalid_create(client, admin_headers, data):
    response = client.post("/admin/mesas", json=data, headers=admin_headers)
    assert response.status_code == 400
    assert response.json["success"] is False
    assert client.get("/admin/mesas").json["data"] == []


@pytest.mark.parametrize("data", [
    None, [], {}, {"numero": 0}, {"numero": True}, {"numero": "2"},
    {"estado": []}, {"estado": "INVALIDO"}, {"public_token": "replacement"},
    {"numero": 9, "estado": "INVALIDO"}, {"id": 5},
])
def test_invalid_patch_is_atomic(client, admin_headers, data):
    mesa = client.post("/admin/mesas", json={"numero": 1}, headers=admin_headers).json["data"]
    path = f'/admin/mesas/{mesa["id"]}'
    response = client.patch(path, json=data, headers=admin_headers)
    assert response.status_code == 400
    assert client.get(path).json["data"] == mesa


@pytest.mark.parametrize("estado", ["DISPONIBLE", "OCUPADA"])
def test_duplicate_number_rolls_back(client, admin_headers, estado):
    first = client.post(
        "/admin/mesas", json={"numero": 1, "estado": estado}, headers=admin_headers,
    ).json["data"]
    second = client.post("/admin/mesas", json={"numero": 2}, headers=admin_headers).json["data"]
    assert client.post("/admin/mesas", json={"numero": 1}, headers=admin_headers).status_code == 409
    path = f'/admin/mesas/{second["id"]}'
    assert client.patch(path, json={"numero": 1, "estado": "CERRADA"}, headers=admin_headers).status_code == 409
    assert client.get(path).json["data"] == second
    assert client.patch(path, json={"numero": 2}, headers=admin_headers).status_code == 200
    assert client.get(f'/admin/mesas/{first["id"]}').json["data"] == first


@pytest.mark.parametrize("role", [None, "WAITER", "KITCHEN", "CASHIER"])
def test_permissions_for_every_endpoint(app, client, role):
    mesa = Mesa(numero=1)
    db.session.add(mesa)
    db.session.commit()
    headers = authenticate(client, role) if role else csrf_headers(client)
    expected = 403 if role else 401
    for method, path, data in (
        ("GET", "/admin/mesas", None),
        ("GET", f"/admin/mesas/{mesa.id}", None),
        ("POST", "/admin/mesas", {"numero": 2}),
        ("PATCH", f"/admin/mesas/{mesa.id}", {"estado": "CERRADA"}),
    ):
        response = client.open(path, method=method, json=data, headers=headers)
        assert response.status_code == expected
        assert response.json["success"] is False
    db.session.refresh(mesa)
    assert mesa.estado == "DISPONIBLE"
    assert db.session.execute(db.select(db.func.count()).select_from(Mesa)).scalar_one() == 1


@pytest.mark.parametrize("supplied", [None, "invalid", "ñ"])
@pytest.mark.parametrize("logged_in", [False, True])
def test_write_requires_csrf(app, client, supplied, logged_in):
    mesa = Mesa(numero=1)
    db.session.add(mesa)
    db.session.commit()
    if logged_in:
        authenticate(client, "ADMIN")
    else:
        csrf_headers(client)
    headers = {} if supplied is None else {"X-CSRF-Token": supplied}
    assert client.post("/admin/mesas", json={"numero": 2}, headers=headers).status_code == 400
    assert client.patch(f"/admin/mesas/{mesa.id}", json={"estado": "CERRADA"}, headers=headers).status_code == 400
    db.session.refresh(mesa)
    assert mesa.estado == "DISPONIBLE"
    assert db.session.execute(db.select(db.func.count()).select_from(Mesa)).scalar_one() == 1


@pytest.mark.parametrize("values", [
    {"numero": 0}, {"numero": -1}, {"numero": 1, "estado": "INVALIDO"},
])
def test_database_constraints(app, values):
    db.session.add(Mesa(**values))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize("field", ["numero", "public_token"])
def test_database_uniqueness(app, field):
    first = Mesa(numero=1)
    db.session.add(first)
    db.session.commit()
    second = Mesa(numero=2)
    setattr(second, field, getattr(first, field))
    db.session.add(second)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_token_collision_returns_conflict(client, admin_headers, monkeypatch):
    monkeypatch.setattr("app.mesas.models.secrets.token_hex", lambda size: "a" * (size * 2))
    assert client.post("/admin/mesas", json={"numero": 1}, headers=admin_headers).status_code == 201
    assert client.post("/admin/mesas", json={"numero": 2}, headers=admin_headers).status_code == 409
    assert len(client.get("/admin/mesas").json["data"]) == 1


def test_listar_mesas_waiter_listado_ordenado_sin_public_token(client):
    waiter_headers = authenticate(client, "WAITER")
    from app.mesas.models import Mesa
    db.session.add_all([Mesa(numero=3), Mesa(numero=1), Mesa(numero=2)])
    db.session.commit()
    response = client.get("/mesas", headers=waiter_headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 3
    assert [m["numero"] for m in data] == [1, 2, 3]
    for m in data:
        assert set(m.keys()) == {"id", "numero", "estado"}
        assert "public_token" not in m


def test_listar_mesas_waiter_filtros(client):
    waiter_headers = authenticate(client, "WAITER")
    from app.mesas.models import Mesa
    db.session.add_all([
        Mesa(numero=1, estado="DISPONIBLE"),
        Mesa(numero=2, estado="OCUPADA"),
        Mesa(numero=3, estado="OCUPADA"),
    ])
    db.session.commit()
    response = client.get("/mesas?estado=OCUPADA", headers=waiter_headers)
    assert response.status_code == 200
    assert [m["numero"] for m in response.json["data"]] == [2, 3]
    response = client.get("/mesas?numero=2", headers=waiter_headers)
    assert response.status_code == 200
    assert len(response.json["data"]) == 1
    assert response.json["data"][0]["numero"] == 2
    response = client.get("/mesas?estado=OCUPADA&numero=3", headers=waiter_headers)
    assert response.status_code == 200
    assert len(response.json["data"]) == 1
    assert response.json["data"][0]["numero"] == 3


@pytest.mark.parametrize("params", [
    {"id": "0"}, {"id": "-1"}, {"id": "abc"}, {"id": "2147483648"},
    {"numero": "0"}, {"numero": "-1"}, {"numero": "abc"}, {"numero": "2147483648"},
    {"estado": "INVALIDO"},
])
def test_listar_mesas_waiter_filtros_invalidos_devuelven_400(client, params):
    waiter_headers = authenticate(client, "WAITER")
    response = client.get("/mesas", query_string=params, headers=waiter_headers)
    assert response.status_code == 400


def test_listar_mesas_waiter_sin_coincidencias_devuelve_200_vacio(client):
    waiter_headers = authenticate(client, "WAITER")
    response = client.get("/mesas?estado=OCUPADA", headers=waiter_headers)
    assert response.status_code == 200
    assert response.json["data"] == []


@pytest.mark.parametrize("rol", [None, "ADMIN", "KITCHEN", "CASHIER"])
def test_listar_mesas_waiter_permisos(client, rol):
    if rol:
        headers = authenticate(client, rol)
    else:
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    expected = 403 if rol else 401
    response = client.get("/mesas", headers=headers)
    assert response.status_code == expected
    assert response.json["success"] is False
