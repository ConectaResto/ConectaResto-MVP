import pytest
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
            "price": 25.50,
            "categoria_id": categoria.id,
        })
        assert product.id is not None
        assert product.name == "Coca Cola"
        assert product.description == "Refresco de cola"
        assert float(product.price) == 25.50
        assert product.categoria_id == categoria.id
        assert product.disponible is True


def test_new_products_are_disponible(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        product = create_product({
            "name": "Coca Cola",
            "price": 10.00,
            "categoria_id": categoria.id,
        })
        assert product.disponible is True


def test_create_product_invalid_categoria(app):
    with app.app_context():
        with pytest.raises(ProductNotFound):
            create_product({
                "name": "Coca Cola",
                "price": 10.00,
                "categoria_id": 99999,
            })


def test_create_product_inactive_categoria(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        deactivate_category(categoria.id)
        with pytest.raises(ProductNotFound):
            create_product({
                "name": "Coca Cola",
                "price": 10.00,
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
                "price": -5.00,
                "categoria_id": categoria.id,
            })


def test_create_product_without_name(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "",
                "price": 10.00,
                "categoria_id": categoria.id,
            })


# ---------- Product name uniqueness within category ----------

def test_product_name_unique_within_category_case_insensitive(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({
            "name": "Coca Cola",
            "price": 10.00,
            "categoria_id": categoria.id,
        })
        with pytest.raises(ProductAlreadyExists):
            create_product({
                "name": "coca cola",
                "price": 12.00,
                "categoria_id": categoria.id,
            })


def test_product_name_can_repeat_across_categories(app):
    with app.app_context():
        cat1 = create_category({"name": "Bebidas"})
        cat2 = create_category({"name": "Entradas"})
        create_product({
            "name": "Coca Cola",
            "price": 10.00,
            "categoria_id": cat1.id,
        })
        # Same name in different category should be allowed
        product = create_product({
            "name": "Coca Cola",
            "price": 12.00,
            "categoria_id": cat2.id,
        })
        assert product.id is not None


# ---------- Product retrieval ----------

def test_get_product_by_id(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": 10.00,
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
            "price": 10.00,
            "categoria_id": categoria.id,
        })
        deactivate_product(created.id)
        fetched = get_product(created.id, include_inactive=False)
        assert fetched is None


def test_list_products_only_disponible(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        create_product({"name": "Producto 1", "price": 10.00, "categoria_id": categoria.id})
        create_product({"name": "Producto 2", "price": 12.00, "categoria_id": categoria.id})
        products = list_products(include_inactive=False)
        assert len(products) == 2

        # Deactivate one
        p2 = Product.query.filter(Product.name == "Producto 2").first()
        deactivate_product(p2.id)

        active = list_products(include_inactive=False)
        assert len(active) == 1
        assert active[0].name == "Producto 1"

        all_prods = list_products(include_inactive=True)
        assert len(all_prods) == 2


def test_list_products_filtered_by_categoria(app):
    with app.app_context():
        cat1 = create_category({"name": "Bebidas"})
        cat2 = create_category({"name": "Entradas"})
        create_product({"name": "Coca Cola", "price": 10.00, "categoria_id": cat1.id})
        create_product({"name": "Papas", "price": 8.00, "categoria_id": cat2.id})

        products_cat1 = list_products(include_inactive=False, categoria_id=cat1.id)
        assert len(products_cat1) == 1
        assert products_cat1[0].name == "Coca Cola"

        products_cat2 = list_products(include_inactive=False, categoria_id=cat2.id)
        assert len(products_cat2) == 1
        assert products_cat2[0].name == "Papas"


# ---------- Product update ----------

def test_update_product(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "description": "Desc vieja",
            "price": 10.00,
            "categoria_id": categoria.id,
        })
        updated = update_product(
            created.id,
            {"name": "Coca Cola Zero", "description": "Desc nueva", "price": 15.00},
            include_inactive=False,
        )
        assert updated.name == "Coca Cola Zero"
        assert updated.description == "Desc nueva"
        assert float(updated.price) == 15.00


def test_update_product_change_categoria(app):
    with app.app_context():
        cat1 = create_category({"name": "Bebidas"})
        cat2 = create_category({"name": "Entradas"})
        created = create_product({
            "name": "Coca Cola",
            "price": 10.00,
            "categoria_id": cat1.id,
        })
        updated = update_product(
            created.id,
            {"categoria_id": cat2.id},
            include_inactive=False,
        )
        assert updated.categoria_id == cat2.id


# ---------- Product deactivation ----------

def test_deactivate_product_sets_disponible_false(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": 10.00,
            "categoria_id": categoria.id,
        })
        assert created.disponible is True
        result = deactivate_product(created.id)
        assert result is not None
        assert result.disponible is False


def test_deactivate_already_inactive_product_returns_none(app):
    with app.app_context():
        categoria = create_category({"name": "Bebidas"})
        created = create_product({
            "name": "Coca Cola",
            "price": 10.00,
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
            "price": 10.00,
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
            "price": 10.00,
            "categoria_id": categoria.id,
        })
        deactivate_product(producto.id)
        result = deactivate_category(categoria.id)
        assert result is not None
        assert result.is_active is False
