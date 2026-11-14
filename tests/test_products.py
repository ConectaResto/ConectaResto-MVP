import pytest
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.catalog.service import (
    CategoryAlreadyExists,
    CategoryNotFound,
    CategoryHasActiveProducts,
    ProductAlreadyExists,
    ProductNotFound,
    create_category,
    create_product,
    deactivate_category,
    deactivate_product,
    get_category,
    get_product,
    list_categories,
    list_products,
    update_category,
    update_product,
)


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# ---------- Product creation ----------

def test_create_product(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas", "description": "Refrescos"})
        product = create_product({
            "name": "Coca Cola",
            "description": "Refresco de cola",
            "price": "25.50",
            "categoria_id": categoria.id,
        })
        assert product.id is not None
        assert product.name == "Coca Cola"
        assert product.description == "Refresco de cola"
        assert product.price == Decimal("25.50")
        assert product.categoria_id == categoria.id
        assert product.is_active is True
        assert product.is_available is True


def test_new_products_are_active_and_available(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        product = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        assert product.is_active is True
        assert product.is_available is True


def test_create_product_invalid_categoria(app):
    with app.app_context():
        with pytest.raises(ProductNotFound):
            create_product({
                "name": "Coca Cola",
                "price": "10.00",
                "categoria_id": 99999,
            })


def test_create_product_inactive_categoria(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        deactivate_category(categoria.id)
        with pytest.raises(ProductNotFound):
            create_product({
                "name": "Coca Cola",
                "price": "10.00",
                "categoria_id": categoria.id,
            })


def test_create_product_price_required(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "Coca Cola",
                "categoria_id": categoria.id,
            })


def test_create_product_negative_price(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "Coca Cola",
                "price": "-5.00",
                "categoria_id": categoria.id,
            })


def test_create_product_invalid_price(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "Coca Cola",
                "price": "abc",
                "categoria_id": categoria.id,
            })


def test_create_product_without_name(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "",
                "price": "10.00",
                "categoria_id": categoria.id,
            })


# ---------- Product name uniqueness within category ----------

def test_product_name_unique_within_category_case_insensitive(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "coca cola",
                "price": "12.00",
                "categoria_id": categoria.id,
            })


def test_product_name_can_repeat_across_categories(app):
    with app.app_context():
        cat1 = create_category({"name": "Bebidas"})
        cat2 = create_category({"name": "Entradas"})
        create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": cat1.id,
        })
        product = create_product({
            "name": "Coca Cola",
            "price": "12.00",
            "categoria_id": cat2.id,
        })
        assert product.id is not None


# ---------- Product retrieval ----------

def test_get_product_by_id(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        fetched = get_product(created.id, include_inactive=False)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Coca Cola"


def test_get_inactive_product_returns_none(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        deactivate_product(created.id)
        fetched = get_product(created.id, include_inactive=False)
        assert fetched is None


def test_get_unavailable_product_returns_none(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
            "is_available": False,
        })
        fetched = get_product(created.id, include_inactive=False)
        assert fetched is None


def test_list_products_only_active_and_available(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({"name": "Producto 1", "price": "10.00", "categoria_id": categoria.id})
        create_product({"name": "Producto 2", "price": "12.00", "categoria_id": categoria.id})
        products = list_products(include_inactive=False)
        assert len(products) == 2

        # Deactivate one (sets is_active=False)
        p2 = Product.query.filter(Product.name == "Producto 2").first()
        deactivate_product(p2.id)

        active = list_products(include_inactive=False)
        assert len(active) == 1
        assert active[0].name == "Producto 1"

        all_prods = list_products(include_inactive=True)
        assert len(all_prods) == 2


def test_list_products_unavailable_not_returned_publicly(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({"name": "Producto 1", "price": "10.00", "categoria_id": categoria.id, "is_available": True})
        create_product({"name": "Producto 2", "price": "12.00", "categoria_id": categoria.id, "is_available": False})

        active = list_products(include_inactive=False)
        assert len(active) == 1
        assert active[0].name == "Producto 1"


def test_list_products_filtered_by_categoria(app):
    with app.app_context():
        cat1 = create_category({"name": "Bebidas"})
        cat2 = create_category({"name": "Entradas"})
        create_product({"name": "Coca Cola", "price": "10.00", "categoria_id": cat1.id})
        create_product({"name": "Papas", "price": "8.00", "categoria_id": cat2.id})

        products_cat1 = list_products(include_inactive=False, categoria_id=cat1.id)
        assert len(products_cat1) == 1
        assert products_cat1[0].name == "Coca Cola"

        products_cat2 = list_products(include_inactive=False, categoria_id=cat2.id)
        assert len(products_cat2) == 1
        assert products_cat2[0].name == "Papas"


def test_public_products_exclude_inactive_category(app):
    """Productos de categoria inactiva no deben aparecer en consultas publicas."""
    with app.app_context():
        cat_inactive = create_category({"name": "Inactiva"})
        cat_active = create_category({"name": "Activa"})

        # Crear productos mientras las categorias estan activas
        create_product({
            "name": "Prod Inactiva Cat",
            "price": "10.00",
            "categoria_id": cat_inactive.id,
        })
        create_product({"name": "Prod Activa Cat", "price": "12.00", "categoria_id": cat_active.id})

        # Desactivar el producto de la categoria inactiva primero
        prod_inactiva = Product.query.filter(Product.name == "Prod Inactiva Cat").first()
        deactivate_product(prod_inactiva.id)

        # Ahora desactivar la categoria (no tiene productos activos y disponibles)
        deactivate_category(cat_inactive.id)

        products = list_products(include_inactive=False)
        assert len(products) == 1
        assert products[0].name == "Prod Activa Cat"


# ---------- Product update ----------

def test_update_product(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "description": "Desc vieja",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        updated = update_product(
            created.id,
            {"name": "Coca Cola Zero", "description": "Desc nueva", "price": "15.00"},
            include_inactive=False,
        )
        assert updated.name == "Coca Cola Zero"
        assert updated.description == "Desc nueva"
        assert updated.price == Decimal("15.00")


def test_update_product_change_categoria(app):
    with app.app_context():
        cat1 = create_category({"name": "Bebidas"})
        cat2 = create_category({"name": "Entradas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": cat1.id,
        })
        updated = update_product(
            created.id,
            {"categoria_id": cat2.id},
            include_inactive=False,
        )
        assert updated.categoria_id == cat2.id


def test_update_product_is_available(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
            "is_available": True,
        })
        updated = update_product(
            created.id,
            {"is_available": False},
            include_inactive=False,
        )
        assert updated.is_active is True
        assert updated.is_available is False


def test_update_product_is_active_manually(app):
    """is_active puede actualizarse directamente via PATCH (para administracion)."""
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
            "is_active": True,
        })
        updated = update_product(
            created.id,
            {"is_active": False},
            include_inactive=True,
        )
        assert updated.is_active is False
        assert updated.is_available is True  # disponible no se toca


# ---------- Product deactivation ----------

def test_deactivate_product_sets_is_active_false(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        assert created.is_active is True
        result = deactivate_product(created.id)
        assert result is not None
        assert result.is_active is False
        # is_available no debe cambiar por desactivacion logica
        assert result.is_available is True


def test_deactivate_already_inactive_product_returns_none(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        deactivate_product(created.id)
        result = deactivate_product(created.id)
        assert result is None


def test_deactivate_nonexistent_product_raises(app):
    with app.app_context():
        with pytest.raises(ProductNotFound):
            deactivate_product(99999)


# ---------- Category deactivation blocked by active products ----------

def test_deactivate_category_blocked_by_active_products(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        with pytest.raises(CategoryHasActiveProducts):
            deactivate_category(categoria.id)


def test_deactivate_category_allowed_when_no_products(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        result = deactivate_category(categoria.id)
        assert result is not None
        assert result.is_active is False


def test_deactivate_category_allowed_when_only_inactive_products(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        producto = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        deactivate_product(producto.id)
        result = deactivate_category(categoria.id)
        assert result is not None
        assert result.is_active is False


def test_deactivate_category_blocked_by_available_but_not_inactive_products(app):
    """Producto inactivo (is_active=False) no bloquea aunque is_available=True."""
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        producto = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        # Producto inactivo logico pero disponible
        deactivate_product(producto.id)
        assert producto.is_active is False
        assert producto.is_available is True
        result = deactivate_category(categoria.id)
        assert result is not None
        assert result.is_active is False


def test_deactivate_category_blocked_by_active_but_unavailable_product(app):
    """Producto activo (is_active=True) pero no disponible (is_available=False)
    bloquea la desactivacion de la categoria."""
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
            "is_available": False,
        })
        with pytest.raises(CategoryHasActiveProducts):
            deactivate_category(categoria.id)


# ---------- Strict boolean validation ----------

def test_create_product_invalid_is_available(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "Coca Cola",
                "price": "10.00",
                "categoria_id": categoria.id,
                "is_available": "maybe",
            })


def test_create_product_is_available_false_string(app):
    """String "false" debe interpretarse como False, no como True."""
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        product = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
            "is_available": "false",
        })
        assert product.is_available is False


def test_update_product_invalid_is_active(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": "10.00",
            "categoria_id": categoria.id,
        })
        with pytest.raises(ProductAlreadyExists):
            update_product(
                created.id,
                {"is_active": "maybe"},
                include_inactive=True,
            )


# ---------- Price serialization ----------

def test_product_to_dict_price_is_string(app):
    """El precio se serializa como string para preservar precision de Decimal."""
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        product = create_product({
            "name": "Coca Cola",
            "price": "25.50",
            "categoria_id": categoria.id,
        })
        data = product.to_dict()
        assert data["price"] == "25.50"
        assert isinstance(data["price"], str)


# ---------- Endpoint-level tests: authentication and authorization ----------

@pytest.fixture
def admin_user(app, client):
    """Crea roles y un usuario ADMIN para pruebas de endpoints."""
    with app.app_context():
        from app.models import Rol, Usuario
        for nombre in ["ADMIN", "WAITER"]:
            rol = Rol(name=nombre, description=f"Rol {nombre}")
            db.session.add(rol)
        db.session.commit()
        admin_rol = db.session.execute(
            db.select(Rol).filter_by(name="ADMIN")
        ).scalar_one()
        waiter_rol = db.session.execute(
            db.select(Rol).filter_by(name="WAITER")
        ).scalar_one()
        admin = Usuario(username="admin1", email="admin1@test.com", rol_id=admin_rol.id)
        admin.set_password("admin-pass")
        waiter = Usuario(username="mesero1", email="mesero1@test.com", rol_id=waiter_rol.id)
        waiter.set_password("waiter-pass")
        db.session.add(admin)
        db.session.add(waiter)
        db.session.commit()
    return {"admin": "admin1", "waiter": "mesero1"}


def csrf_token(client):
    return client.get("/auth/csrf").json["data"]["csrf_token"]


def login(client, username, password):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf_token(client)},
    )


# ---- Category admin routes require authentication ----

def test_category_post_requires_auth(client):
    resp = client.post(
        "/categories",
        json={"name": "Test"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 401


def test_category_patch_requires_auth(client):
    resp = client.patch(
        "/categories/1",
        json={"name": "Test"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 401


def test_category_delete_requires_auth(client):
    resp = client.delete(
        "/categories/1",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 401


# ---- Category admin routes require ADMIN role ----

def test_category_post_requires_admin(client, admin_user):
    login(client, "mesero1", "waiter-pass")
    resp = client.post(
        "/categories",
        json={"name": "Test"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 403


def test_category_patch_requires_admin(client, admin_user):
    login(client, "mesero1", "waiter-pass")
    resp = client.patch(
        "/categories/1",
        json={"name": "Test"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 403


def test_category_delete_requires_admin(client, admin_user):
    login(client, "mesero1", "waiter-pass")
    resp = client.delete(
        "/categories/1",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 403


# ---- Category public routes accessible without auth ----

def test_category_get_public(client):
    resp = client.get("/categories")
    assert resp.status_code == 200


def test_category_get_by_id_public(client):
    resp = client.get("/categories/1")
    assert resp.status_code in (200, 404)


# ---- Product admin routes require authentication ----

def test_product_post_requires_auth(client):
    resp = client.post(
        "/products",
        json={"name": "Test", "price": "10.00"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 401


def test_product_patch_requires_auth(client):
    resp = client.patch(
        "/products/1",
        json={"name": "Test"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 401


def test_product_delete_requires_auth(client):
    resp = client.delete(
        "/products/1",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 401


# ---- Product admin routes require ADMIN role ----

def test_product_post_requires_admin(client, admin_user):
    login(client, "mesero1", "waiter-pass")
    resp = client.post(
        "/products",
        json={"name": "Test", "price": "10.00"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 403


def test_product_patch_requires_admin(client, admin_user):
    login(client, "mesero1", "waiter-pass")
    resp = client.patch(
        "/products/1",
        json={"name": "Test"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 403


def test_product_delete_requires_admin(client, admin_user):
    login(client, "mesero1", "waiter-pass")
    resp = client.delete(
        "/products/1",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert resp.status_code == 403


# ---- Product public routes accessible without auth ----

def test_product_get_public(client):
    resp = client.get("/products")
    assert resp.status_code == 200


def test_product_get_by_id_public(client):
    resp = client.get("/products/1")
    assert resp.status_code in (200, 404)


# ---- CSRF protection on mutating endpoints ----

def test_category_post_requires_csrf(client, admin_user):
    login(client, "admin1", "admin-pass")
    resp = client.post("/categories", json={"name": "Test"})
    assert resp.status_code == 400  # CSRF rejected


def test_product_post_requires_csrf(client, admin_user):
    login(client, "admin1", "admin-pass")
    resp = client.post("/products", json={"name": "Test", "price": "10.00"})
    assert resp.status_code == 400  # CSRF rejected


def test_category_post_with_csrf_succeeds(client, admin_user):
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    resp = client.post(
        "/categories",
        json={"name": "Bebidas"},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 201
