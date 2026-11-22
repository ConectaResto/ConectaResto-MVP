import pytest

from tests.test_servicios import autenticar


def test_admin_puede_reactivar_un_producto_sin_publicarlo_mientras_no_esta_disponible(app, client):
    _, headers = autenticar(client, "ADMIN")
    publico = app.test_client()
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers)
    assert category.status_code == 201
    payload = {"name": "Café", "price": "12.35", "categoria_id": category.json["data"]["id"]}
    response = client.post("/products", json=payload, headers=headers)
    assert response.status_code == 201
    product_id = response.json["data"]["id"]
    path = f"/products/{product_id}"

    for available in (True, False, True):
        response = client.patch(path, json={"is_available": available}, headers=headers)
        assert response.status_code == 200
        admin_products = client.get("/admin/products")
        assert admin_products.status_code == 200
        [product] = admin_products.json["data"]
        assert product["id"] == product_id
        assert product["is_available"] is available
        public_ids = [row["id"] for row in publico.get("/products").json["data"]]
        assert public_ids == ([product_id] if available else [])
        assert publico.get(path).status_code == (200 if available else 404)

    assert client.delete(path, headers=headers).status_code == 200
    assert client.get("/admin/products").json["data"] == []


@pytest.mark.parametrize("role, status", [(None, 401), ("WAITER", 403), ("KITCHEN", 403), ("CASHIER", 403)])
def test_catalogo_administrativo_y_disponibilidad_requieren_admin(client, role, status):
    if role:
        _, headers = autenticar(client, role)
    else:
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    assert client.get("/admin/products").status_code == status
    assert client.patch("/products/1", json={"is_available": False}, headers=headers).status_code == status
    assert client.get("/products").status_code == 200


@pytest.mark.parametrize("available", [False, True])
def test_reactivacion_catalogo_conserva_disponibilidad(app, client, available):
    _, headers = autenticar(client, "ADMIN")
    public = app.test_client()
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers).json["data"]
    cid = category["id"]
    product = client.post("/products", json={"name": "Cafe", "price": "5.25", "categoria_id": cid,
                                             "is_available": available}, headers=headers).json["data"]
    pid = product["id"]
    assert client.delete(f"/products/{pid}", headers=headers).status_code == 200
    assert client.delete(f"/categories/{cid}", headers=headers).status_code == 200
    assert public.get("/categories").json["data"] == []
    assert public.get("/products?include_inactive=true").json["data"] == []
    assert client.get("/categories?include_inactive=true").json["data"][0]["is_active"] is False
    assert client.get("/admin/products?include_inactive=true").json["data"][0]["is_active"] is False
    response = client.patch(f"/products/{pid}", json={"is_active": True}, headers=headers)
    assert response.status_code == 404
    assert client.get("/admin/products?include_inactive=true").json["data"][0]["is_active"] is False
    assert client.patch(f"/categories/{cid}", json={"is_active": True}, headers=headers).status_code == 200
    assert len(public.get("/categories").json["data"]) == 1
    assert public.get("/products").json["data"] == []
    response = client.patch(f"/products/{pid}", json={"is_active": True}, headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["is_available"] is available
    assert response.json["data"]["is_active"] is True
    assert len(public.get("/products").json["data"]) == int(available)
    assert public.get(f"/products/{pid}").status_code == (200 if available else 404)
    assert client.patch(f"/products/{pid}", json={"is_active": True}, headers=headers).status_code == 200


@pytest.mark.parametrize("role,status", [(None, 401), ("WAITER", 403), ("KITCHEN", 403), ("CASHIER", 403)])
def test_reactivacion_y_listados_inactivos_solo_admin(client, role, status):
    if role:
        _, headers = autenticar(client, role)
    else:
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    for path in ("/users/1", "/categories/1", "/products/1"):
        assert client.patch(path, json={"is_active": True}, headers=headers).status_code == status
    for path in ("/categories?include_inactive=true", "/admin/products?include_inactive=true"):
        assert client.get(path).status_code == status
    assert client.get("/categories").status_code == 200


@pytest.mark.parametrize("bad", [False, None, 0, 1, "true", "false", [], {}])
def test_reactivacion_rechaza_datos_y_no_aplica_cambios(app, client, bad):
    _, headers = autenticar(client, "ADMIN")
    uid = client.post("/users", json={"username": "cocinero1", "email": "c@example.test",
                                    "rol": "ADMIN", "password": "synthetic"}, headers=headers).json["data"]["id"]
    cid = client.post("/categories", json={"name": "Bebidas"}, headers=headers).json["data"]["id"]
    pid = client.post("/products", json={"name": "Cafe", "price": "5", "categoria_id": cid}, headers=headers).json["data"]["id"]
    for path, field, value in ((f"/users/{uid}", "username", "cocinero1"),
                               (f"/categories/{cid}", "name", "Bebidas"),
                               (f"/products/{pid}", "name", "Cafe")):
        assert client.patch(path, json={field: "Changed", "is_active": bad}, headers=headers).status_code == 400
        assert client.get(path).json["data"][field] == value
        assert client.patch(path, json={"is_active": True}).status_code == 400
    for path in ("/categories?include_inactive=invalid", "/admin/products?include_inactive=invalid"):
        assert client.get(path).status_code == 400


def test_reactivacion_usuario_preserva_password_y_rol(app, client):
    from app.extensions import db
    from app.users.models import Rol, Usuario
    _, headers = autenticar(client, "ADMIN")
    role = Rol(name="KITCHEN")
    user = Usuario(username="cocinero1", email="c@example.test", rol=role, is_active=False)
    user.set_password("synthetic-password")
    db.session.add(user)
    db.session.commit()
    uid, password_hash = user.id, user.password_hash
    response = client.patch(f"/users/{uid}", json={"is_active": True, "rol": "INVALID"}, headers=headers)
    assert response.status_code == 404
    db.session.refresh(user)
    assert user.is_active is False
    response = client.patch(f"/users/{uid}", json={"is_active": True}, headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["rol"] == "KITCHEN"
    assert "password_hash" not in response.json["data"]
    db.session.refresh(user)
    assert user.password_hash == password_hash
    assert client.patch(f"/users/{uid}", json={"is_active": True}, headers=headers).status_code == 200
    kitchen = app.test_client()
    csrf = kitchen.get("/auth/csrf").json["data"]["csrf_token"]
    assert kitchen.post("/auth/login", json={"username": "cocinero1", "password": "synthetic-password"},
                        headers={"X-CSRF-Token": csrf}).status_code == 200


@pytest.mark.parametrize("payload", [None, [], "true", 1])
def test_patch_catalogo_rechaza_cuerpos_no_objeto(client, payload):
    _, headers = autenticar(client, "ADMIN")
    for path in ("/categories/1", "/products/1"):
        assert client.patch(path, json=payload, headers=headers).status_code == 400


# ---------- Pruebas de navegación por pestañas en ADMIN ----------
