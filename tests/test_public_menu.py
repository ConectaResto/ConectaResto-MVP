"""Public catalog and stable table-token integration guarantees."""

import pytest

from app.extensions import db
from app.models import Category, Mesa, Product


@pytest.fixture
def public_catalog(app):
    active = Category(name="Bebidas")
    inactive = Category(name="Retirada", is_active=False)
    empty = Category(name="Sin productos")
    db.session.add_all([active, inactive, empty])
    db.session.flush()
    products = [
        Product(name="Visible", price="12.50", categoria_id=active.id),
        Product(name="Eliminado", price="4.00", categoria_id=active.id,
                is_active=False),
        Product(name="Agotado", price="5.00", categoria_id=active.id,
                is_available=False),
        Product(name="Categoria retirada", price="6.00", categoria_id=inactive.id),
    ]
    db.session.add_all(products)
    db.session.commit()
    return active, inactive, empty, products


def test_public_menu_reuses_catalog_without_auth(client, public_catalog):
    active, inactive, empty, products = public_catalog
    categories = client.get("/categories")
    assert categories.status_code == 200
    assert {c["id"] for c in categories.json["data"]} == {active.id, empty.id}
    response = client.get("/products")
    assert response.status_code == 200
    assert [p["id"] for p in response.json["data"]] == [products[0].id]
    assert response.json["data"][0]["price"] == "12.50"
    assert client.get(f"/categories/{active.id}").status_code == 200
    assert client.get(f"/products/{products[0].id}").status_code == 200


@pytest.mark.parametrize("index", [1, 2, 3])
def test_hidden_product_is_not_public_by_id(client, public_catalog, index):
    product = public_catalog[3][index]
    response = client.get(f"/products/{product.id}")
    assert response.status_code == 404
    assert response.json["success"] is False


def test_inactive_category_is_not_public_by_id(client, public_catalog):
    response = client.get(f"/categories/{public_catalog[1].id}")
    assert response.status_code == 404
    assert response.json["success"] is False


@pytest.mark.parametrize("category_index", [0, 1, 2])
def test_public_menu_category_filter(client, public_catalog, category_index):
    category = public_catalog[category_index]
    response = client.get(f"/products?categoria_id={category.id}")
    assert response.status_code == 200
    expected = [public_catalog[3][0].id] if category_index == 0 else []
    assert [p["id"] for p in response.json["data"]] == expected


def test_public_queries_cannot_include_hidden_resources(client, public_catalog):
    response = client.get("/products?include_inactive=true&is_available=false")
    assert [p["id"] for p in response.json["data"]] == [public_catalog[3][0].id]
    response = client.get("/categories?include_inactive=true")
    assert public_catalog[1].id not in {c["id"] for c in response.json["data"]}


@pytest.mark.parametrize("path", ["/categories/99999", "/products/99999"])
def test_missing_public_resource(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json["success"] is False


@pytest.mark.parametrize("exists", [True, False])
def test_public_client_cannot_read_admin_table_or_token(client, exists):
    mesa = Mesa(numero=1)
    db.session.add(mesa)
    db.session.commit()
    mesa_id = mesa.id if exists else 99999
    for path in ("/admin/mesas", f"/admin/mesas/{mesa_id}"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.json["success"] is False
        assert mesa.public_token not in response.get_data(as_text=True)


@pytest.mark.parametrize("method,path", [
    ("POST", "/products"), ("PATCH", "/products/1"),
    ("DELETE", "/products/1"), ("POST", "/categories"),
    ("PATCH", "/categories/1"), ("DELETE", "/categories/1"),
    ("POST", "/admin/mesas"), ("PATCH", "/admin/mesas/1"),
])
def test_public_menu_does_not_grant_write_access(client, method, path):
    token = client.get("/auth/csrf").json["data"]["csrf_token"]
    response = client.open(path, method=method, json={},
                           headers={"X-CSRF-Token": token})
    assert response.status_code == 401
    assert response.json["success"] is False


def test_table_token_survives_close_and_reopen(app):
    mesa = Mesa(numero=1)
    db.session.add(mesa)
    db.session.commit()
    mesa_id, token = mesa.id, mesa.public_token
    for estado in ("OCUPADA", "CERRADA", "DISPONIBLE", "OCUPADA"):
        mesa.estado = estado
        db.session.commit()
        db.session.remove()
        mesa = db.session.get(Mesa, mesa_id)
        assert mesa.public_token == token


@pytest.mark.parametrize("path", ["/categories", "/products"])
def test_menu_read_does_not_create_authenticated_session(client, public_catalog, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "Set-Cookie" not in response.headers
    with client.session_transaction() as session:
        assert not session
