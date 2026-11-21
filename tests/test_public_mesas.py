import pytest

from app.extensions import db
from app.catalog.models import Category, Product
from app.mesas.models import Mesa


@pytest.fixture
def public_client(app):
    # Exercise the actual factory registration; do not register routes in tests.
    assert "public_mesas" in app.blueprints
    return app.test_client()


@pytest.mark.parametrize("estado", ["DISPONIBLE", "OCUPADA", "CERRADA"])
def test_resolve_table_without_login(public_client, estado):
    mesa = Mesa(numero=7, estado=estado)
    other = Mesa(numero=8)
    db.session.add_all([mesa, other])
    db.session.commit()
    token = mesa.public_token
    response = public_client.get(f"/public/mesas/{token}")
    assert response.status_code == 200
    assert response.json == {"success": True, "data": {
        "numero": 7,
        "menu": {"categories": "/categories", "products": "/products"},
    }}
    assert "Set-Cookie" not in response.headers
    assert token not in response.get_data(as_text=True)
    assert other.public_token not in response.get_data(as_text=True)
    assert public_client.get("/auth/me").status_code == 401
    assert public_client.get(f"/admin/mesas/{mesa.id}").status_code == 401
    db.session.refresh(mesa)
    assert mesa.estado == estado
    assert mesa.public_token == token


@pytest.mark.parametrize("token", [
    "invalid", "a" * 63, "a" * 65, "g" * 64, "A" * 64,
    "a" * 64, "1", "null", "' OR 1=1 --",
])
def test_invalid_or_unknown_token(public_client, token):
    db.session.add(Mesa(numero=1))
    db.session.commit()
    response = public_client.get(f"/public/mesas/{token}")
    assert response.status_code == 404
    assert response.json == {"success": False, "error": "Mesa no encontrada"}


def test_lookup_links_reuse_filtered_catalog(public_client):
    active = Category(name="Publica")
    inactive = Category(name="Oculta", is_active=False)
    db.session.add_all([active, inactive])
    db.session.flush()
    visible = Product(name="Visible", price="12.50", categoria_id=active.id)
    db.session.add_all([
        visible,
        Product(name="Agotado", price="1.00", categoria_id=active.id,
                is_available=False),
        Product(name="Eliminado", price="1.00", categoria_id=active.id,
                is_active=False),
        Product(name="Oculto", price="1.00", categoria_id=inactive.id),
    ])
    mesa = Mesa(numero=1)
    db.session.add(mesa)
    db.session.commit()
    links = public_client.get(f"/public/mesas/{mesa.public_token}").json["data"]["menu"]
    categories = public_client.get(links["categories"])
    products = public_client.get(links["products"])
    assert categories.status_code == products.status_code == 200
    assert [c["id"] for c in categories.json["data"]] == [active.id]
    assert [p["id"] for p in products.json["data"]] == [visible.id]


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
def test_token_does_not_allow_writes(public_client, method):
    mesa = Mesa(numero=1, estado="CERRADA")
    db.session.add(mesa)
    db.session.commit()
    token = mesa.public_token
    csrf = public_client.get("/auth/csrf").json["data"]["csrf_token"]
    response = public_client.open(f"/public/mesas/{token}", method=method,
                                 json={"estado": "OCUPADA"},
                                 headers={"X-CSRF-Token": csrf})
    assert response.status_code == 405
    db.session.refresh(mesa)
    assert mesa.estado == "CERRADA"
    assert mesa.public_token == token
