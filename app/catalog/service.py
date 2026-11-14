"""Business logic for category administration.

All operations are prepared to be protected by the A-02 authorization
mechanism once it is integrated. Until then, this module is intentionally
not registered in the Flask application (see app/__init__.py) so that no
administrative endpoint is exposed unprotected.
"""

from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.category import Category
from app.models.product import Product


def _is_duplicate_category_name_error(exc: IntegrityError) -> bool:
    """Determina si un IntegrityError es por violación de UNIQUE en categories.name.

    Distingue la violación de unicidad de nombre de otros errores de integridad
    (FK, NOT NULL, check) usando el código o mensaje del driver subyacente.
    """
    orig = getattr(exc, "orig", None)
    if orig is None:
        return False

    args = getattr(orig, "args", None)
    if args and len(args) > 0:
        # PyMySQL / MySQL: código 1062 (ER_DUP_ENTRY)
        if isinstance(args[0], int) and args[0] == 1062:
            return True
        # Mensaje de texto: MySQL "Duplicate entry ... for key 'categories.name'"
        # y SQLite "UNIQUE constraint failed: categories.name"
        msg = str(args[0]).lower()
        if "duplicate entry" in msg and "categories.name" in msg:
            return True
        if "unique constraint failed" in msg and "categories.name" in msg:
            return True

    return False


class CategoryAlreadyExists(ValueError):
    """Raised when a category name already exists (case-insensitive)."""


class CategoryNotFound(ValueError):
    """Raised when a category does not exist."""


def list_categories(include_inactive: bool = False):
    """Return categories, optionally including inactive ones.

    Public queries must pass include_inactive=False so only active
    categories are visible.
    """
    query = Category.query
    if not include_inactive:
        query = query.filter(Category.is_active.is_(True))
    return query.order_by(Category.created_at.asc()).all()


def create_category(data: dict) -> Category:
    """Create a new active category.

    Validates that the name is unique ignoring case.
    """
    name = data.get("name")
    description = data.get("description")

    if not name or not str(name).strip():
        raise CategoryAlreadyExists("El nombre es obligatorio")

    name = str(name).strip()

    existing = Category.find_by_name_case_insensitive(name)
    if existing is not None:
        raise CategoryAlreadyExists("Ya existe una categoría con ese nombre")

    category = Category(name=name, description=description, is_active=True)
    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if _is_duplicate_category_name_error(exc):
            raise CategoryAlreadyExists("Ya existe una categoría con ese nombre")
        raise
    return category


def get_category(category_id: int, include_inactive: bool = False):
    """Return a category by id. Returns None if not found (or inactive
    when include_inactive is False)."""
    query = Category.query.filter(Category.id == category_id)
    if not include_inactive:
        query = query.filter(Category.is_active.is_(True))
    return query.first()


def update_category(category_id: int, data: dict, include_inactive: bool = False):
    """Update an existing category's name and/or description.

    Validates name uniqueness ignoring case, excluding the current
    category from the check.
    """
    category = get_category(category_id, include_inactive=include_inactive)
    if category is None:
        raise CategoryNotFound("Categoría no encontrada")

    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise CategoryAlreadyExists("El nombre es obligatorio")
        existing = Category.find_by_name_case_insensitive(
            name, exclude_id=category.id
        )
        if existing is not None:
            raise CategoryAlreadyExists("Ya existe una categoría con ese nombre")
        category.name = name

    if "description" in data:
        category.description = data["description"]

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if _is_duplicate_category_name_error(exc):
            raise CategoryAlreadyExists("Ya existe una categoría con ese nombre")
        raise
    return category


def deactivate_category(category_id: int):
    """Soft-delete a category by setting is_active = False.

    Returns None if the category does not exist or is already inactive.
    """
    category = Category.query.filter(Category.id == category_id).first()
    if category is None:
        raise CategoryNotFound("Categoría no encontrada")
    if not category.is_active:
        return None
    # Bloquear desactivación si hay productos activos (regla de B-01.2)
    active_products = (
        Product.query.filter(Product.categoria_id == category_id)
        .filter(Product.disponible.is_(True))
        .count()
    )
    if active_products > 0:
        raise CategoryHasActiveProducts(
            "No se puede desactivar la categoría: tiene productos activos asociados"
        )

    category.is_active = False
    db.session.commit()
    return category


class CategoryHasActiveProducts(ValueError):
    """Raised when trying to deactivate a category that has active products."""


# ---------------------------------------------------------------------------
# Product operations
# ---------------------------------------------------------------------------


class ProductAlreadyExists(ValueError):
    """Raised when a product name already exists within a category."""


class ProductNotFound(ValueError):
    """Raised when a product does not exist."""


def list_products(include_inactive: bool = False, categoria_id: int | None = None):
    """Return products, optionally including inactive ones.

    If categoria_id is provided, only products of that category are returned.
    Public queries must pass include_inactive=False so only available
    products are visible.
    """
    query = Product.query
    if not include_inactive:
        query = query.filter(Product.disponible.is_(True))
    if categoria_id is not None:
        query = query.filter(Product.categoria_id == categoria_id)
    return query.order_by(Product.created_at.asc()).all()


def create_product(data: dict) -> Product:
    """Create a new available product.

    Validates that the category exists and is active.
    Name uniqueness within a category is validated ignoring case.
    """
    name = data.get("name")
    description = data.get("description")
    price = data.get("price")
    categoria_id = data.get("categoria_id")
    disponible = data.get("disponible", True)

    if not name or not str(name).strip():
        raise ProductAlreadyExists("El nombre es obligatorio")

    name = str(name).strip()

    if price is None:
        raise ProductAlreadyExists("El precio es obligatorio")

    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ProductAlreadyExists("El precio debe ser un número válido")

    if price < 0:
        raise ProductAlreadyExists("El precio no puede ser negativo")

    categoria = Category.query.filter(Category.id == categoria_id).first()
    if categoria is None:
        raise ProductNotFound("La categoría especificada no existe")
    if not categoria.is_active:
        raise ProductNotFound("La categoría especificada no está activa")

    existing = (
        Product.query.filter(Product.categoria_id == categoria_id)
        .filter(db.func.lower(Product.name) == db.func.lower(name))
        .first()
    )
    if existing is not None:
        raise ProductAlreadyExists(
            "Ya existe un producto con ese nombre en esta categoría"
        )

    product = Product(
        name=name,
        description=description,
        price=price,
        categoria_id=categoria_id,
        disponible=bool(disponible),
    )
    db.session.add(product)
    db.session.commit()
    return product


def get_product(product_id: int, include_inactive: bool = False):
    """Return a product by id. Returns None if not found (or inactive
    when include_inactive is False)."""
    query = Product.query.filter(Product.id == product_id)
    if not include_inactive:
        query = query.filter(Product.disponible.is_(True))
    return query.first()


def update_product(product_id: int, data: dict, include_inactive: bool = False):
    """Update an existing product's fields.

    Updatable fields: name, description, price, categoria_id, disponible.
    Validates name uniqueness within category ignoring case.
    """
    product = get_product(product_id, include_inactive=include_inactive)
    if product is None:
        raise ProductNotFound("Producto no encontrado")

    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise ProductAlreadyExists("El nombre es obligatorio")
        existing = (
            Product.query.filter(Product.categoria_id == product.categoria_id)
            .filter(db.func.lower(Product.name) == db.func.lower(name))
            .filter(Product.id != product.id)
            .first()
        )
        if existing is not None:
            raise ProductAlreadyExists(
                "Ya existe un producto con ese nombre en esta categoría"
            )
        product.name = name

    if "description" in data:
        product.description = data["description"]

    if "price" in data and data["price"] is not None:
        try:
            price = float(data["price"])
        except (TypeError, ValueError):
            raise ProductAlreadyExists("El precio debe ser un número válido")
        if price < 0:
            raise ProductAlreadyExists("El precio no puede ser negativo")
        product.price = price

    if "categoria_id" in data and data["categoria_id"] is not None:
        nueva_categoria = Category.query.filter(
            Category.id == data["categoria_id"]
        ).first()
        if nueva_categoria is None:
            raise ProductNotFound("La categoría especificada no existe")
        if not nueva_categoria.is_active:
            raise ProductNotFound("La categoría especificada no está activa")
        product.categoria_id = nueva_categoria.id

    if "disponible" in data:
        product.disponible = bool(data["disponible"])

    db.session.commit()
    return product


def deactivate_product(product_id: int):
    """Soft-delete a product by setting disponible = False.

    Returns None if the product does not exist or is already inactive.
    """
    product = Product.query.filter(Product.id == product_id).first()
    if product is None:
        raise ProductNotFound("Producto no encontrado")
    if not product.disponible:
        return None
    product.disponible = False
    db.session.commit()
    return product
