"""Business logic for category administration.

All operations are prepared to be protected by the A-02 authorization
mechanism once it is integrated. Until then, this module is intentionally
not registered in the Flask application (see app/__init__.py) so that no
administrative endpoint is exposed unprotected.
"""

import os
import uuid
from decimal import Decimal, InvalidOperation
from flask import current_app
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


def _parse_decimal_price(value) -> Decimal:
    """Convierte un valor de entrada a Decimal sin pasar por float.

    Rechaza valores que no sean numericos validos, incluyendo NaN,
    Infinity y -Infinity.
    """
    if value is None or value == "":
        raise ValueError("El precio es obligatorio")
    try:
        price_decimal = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("El precio debe ser un numero valido")
    if not price_decimal.is_finite():
        raise ValueError("El precio debe ser un valor finito")
    return price_decimal


def _parse_bool(value, field_name: str) -> bool:
    """Valida un booleano estrictamente.

    Acepta True/False, 1/0, "true"/"false" (case-insensitive).
    Rechaza cualquier otro valor, incluido "false" como string no vacio.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise ValueError(f"{field_name} debe ser un booleano valido")
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in ("true", "1", "yes", "on"):
            return True
        if lower in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"{field_name} debe ser un booleano valido")
    raise ValueError(f"{field_name} debe ser un booleano valido")


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
        raise CategoryAlreadyExists("Ya existe una categoria con ese nombre")

    category = Category(name=name, description=description, is_active=True)
    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if _is_duplicate_category_name_error(exc):
            raise CategoryAlreadyExists("Ya existe una categoria con ese nombre")
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
    if "is_active" in data and data["is_active"] is not True:
        raise ValueError("is_active solo admite true; use DELETE para desactivar")
    category = get_category(category_id, include_inactive=include_inactive or data.get("is_active") is True)
    if category is None:
        raise CategoryNotFound("Categoria no encontrada")

    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise CategoryAlreadyExists("El nombre es obligatorio")
        existing = Category.find_by_name_case_insensitive(
            name, exclude_id=category.id
        )
        if existing is not None:
            raise CategoryAlreadyExists("Ya existe una categoria con ese nombre")
        category.name = name

    if "description" in data:
        category.description = data["description"]
    if "is_active" in data:
        category.is_active = True

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if _is_duplicate_category_name_error(exc):
            raise CategoryAlreadyExists("Ya existe una categoria con ese nombre")
        raise
    return category


def deactivate_category(category_id: int):
    """Soft-delete a category by setting is_active = False.

    Returns None if the category does not exist or is already inactive.
    Blocks deactivation if the category has active products, regardless of availability.
    """
    category = Category.query.filter(Category.id == category_id).first()
    if category is None:
        raise CategoryNotFound("Categoria no encontrada")
    if not category.is_active:
        return None
    # Bloquear desactivacion si hay productos activos (is_active=True)
    # independientemente de is_available
    active_products = (
        Product.query.filter(Product.categoria_id == category_id)
        .filter(Product.is_active.is_(True))
        .count()
    )
    if active_products > 0:
        raise CategoryHasActiveProducts(
            "No se puede desactivar la categoria: tiene productos activos asociados"
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


def list_products(
    include_inactive: bool = False,
    categoria_id: int | None = None,
    *,
    include_unavailable: bool = False,
):
    """Return products, optionally including inactive ones.

    By default, return only products that are:
    - is_active = True (not logically deleted)
    - is_available = True (temporarily available)
    - associated with an active category (Category.is_active = True)

    include_unavailable lets ADMIN list temporarily unavailable products
    while keeping the active product and category filters.
    If categoria_id is provided, only products of that category are returned.
    """
    query = Product.query.join(Category, Product.categoria_id == Category.id)
    if not include_inactive:
        query = query.filter(
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
        if not include_unavailable:
            query = query.filter(Product.is_available.is_(True))
    if categoria_id is not None:
        query = query.filter(Product.categoria_id == categoria_id)
    return query.order_by(Product.created_at.asc()).all()


def create_product(data: dict) -> Product:
    """Create a new active and available product.

    Validates that the category exists and is active.
    Name uniqueness within a category is validated ignoring case.
    Price is handled as Decimal to preserve monetary precision.
    """
    name = data.get("name")
    description = data.get("description")
    price = data.get("price")
    categoria_id = data.get("categoria_id")
    is_available = data.get("is_available", True)

    if not name or not str(name).strip():
        raise ProductAlreadyExists("El nombre es obligatorio")

    name = str(name).strip()

    if price is None:
        raise ProductAlreadyExists("El precio es obligatorio")

    try:
        price_decimal = _parse_decimal_price(price)
    except ValueError as exc:
        raise ProductAlreadyExists(str(exc))

    if price_decimal < 0:
        raise ProductAlreadyExists("El precio no puede ser negativo")

    try:
        is_available_bool = _parse_bool(is_available, "is_available")
    except ValueError as exc:
        raise ProductAlreadyExists(str(exc))

    categoria = Category.query.filter(Category.id == categoria_id).first()
    if categoria is None:
        raise ProductNotFound("La categoria especificada no existe")
    if not categoria.is_active:
        raise ProductNotFound("La categoria especificada no esta activa")

    existing = (
        Product.query.filter(Product.categoria_id == categoria_id)
        .filter(db.func.lower(Product.name) == db.func.lower(name))
        .first()
    )
    if existing is not None:
        raise ProductAlreadyExists(
            "Ya existe un producto con ese nombre en esta categoria"
        )

    product = Product(
        name=name,
        description=description,
        price=price_decimal,
        categoria_id=categoria_id,
        is_active=True,
        is_available=is_available_bool,
    )
    db.session.add(product)
    db.session.commit()
    return product


def get_product(product_id: int, include_inactive: bool = False):
    """Return a product by id. Returns None if not found (or inactive
    or unavailable when include_inactive is False).

    Public queries also require the associated category to be active.
    """
    query = Product.query.join(Category, Product.categoria_id == Category.id)
    query = query.filter(Product.id == product_id)
    if not include_inactive:
        query = query.filter(
            Product.is_active.is_(True),
            Product.is_available.is_(True),
            Category.is_active.is_(True),
        )
    return query.first()


def update_product(product_id: int, data: dict, include_inactive: bool = False):
    """Update an existing product's fields.

    Updatable fields: name, description, price, categoria_id, is_available.
    Validates name uniqueness within category ignoring case.
    Price is handled as Decimal.

    For administrative updates (include_inactive=False), the product is
    located regardless of is_available, so an ADMIN can reactivate
    availability on a product that is temporarily unavailable. Public
    queries still filter by is_available=True via get_product().

    is_active=true permite reactivar sin cambiar is_available; DELETE desactiva.
    """
    if "is_active" in data and data["is_active"] is not True:
        raise ValueError("is_active solo admite true; use DELETE para desactivar")
    reactivating = data.get("is_active") is True
    query = Product.query.join(Category, Product.categoria_id == Category.id)
    query = query.filter(Product.id == product_id)
    if not include_inactive and not reactivating:
        query = query.filter(Product.is_active.is_(True), Category.is_active.is_(True))
    product = query.first()
    if product is None:
        raise ProductNotFound("Producto no encontrado")

    # Fase 1: validar todos los campos antes de aplicar cualquier cambio.
    # Esto evita cambios parciales en la sesion si alguna validacion falla.
    changes = {}

    # Determinar la categoria de destino para la comprobacion de unicidad
    # de nombre. Si se cambia la categoria, validar que exista y este activa.
    target_categoria_id = product.categoria_id
    if "categoria_id" in data and data["categoria_id"] is not None:
        nueva_categoria = Category.query.filter(
            Category.id == data["categoria_id"]
        ).first()
        if nueva_categoria is None:
            raise ProductNotFound("La categoria especificada no existe")
        if not nueva_categoria.is_active:
            raise ProductNotFound("La categoria especificada no esta activa")
        target_categoria_id = nueva_categoria.id

    if reactivating:
        category = db.session.get(Category, target_categoria_id)
        if category is None or not category.is_active:
            raise ProductNotFound("La categoria especificada no esta activa")

    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise ProductAlreadyExists("El nombre es obligatorio")
        existing = (
            Product.query.filter(Product.categoria_id == target_categoria_id)
            .filter(db.func.lower(Product.name) == db.func.lower(name))
            .filter(Product.id != product.id)
            .first()
        )
        if existing is not None:
            raise ProductAlreadyExists(
                "Ya existe un producto con ese nombre en esta categoria"
            )
        changes["name"] = name

    if "description" in data:
        changes["description"] = data["description"]

    if "price" in data and data["price"] is not None:
        try:
            price_decimal = _parse_decimal_price(data["price"])
        except ValueError as exc:
            raise ProductAlreadyExists(str(exc))
        if price_decimal < 0:
            raise ProductAlreadyExists("El precio no puede ser negativo")
        changes["price"] = price_decimal

    if "categoria_id" in data and data["categoria_id"] is not None:
        changes["categoria_id"] = target_categoria_id

    if reactivating:
        changes["is_active"] = True

    if "is_available" in data:
        try:
            changes["is_available"] = _parse_bool(
                data["is_available"], "is_available"
            )
        except ValueError as exc:
            raise ProductAlreadyExists(str(exc))

    # Fase 2: aplicar todos los cambios validados de una vez.
    for field, value in changes.items():
        setattr(product, field, value)

    db.session.commit()
    return product


def deactivate_product(product_id: int):
    """Soft-delete a product by setting is_active = False.

    This is logical deactivation, not a change of temporary availability.
    Returns None if the product does not exist or is already inactive.
    """
    product = Product.query.filter(Product.id == product_id).first()
    if product is None:
        raise ProductNotFound("Producto no encontrado")
    if not product.is_active:
        return None
    product.is_active = False
    db.session.commit()
    return product


# ---------------------------------------------------------------------------
# Product image operations
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS = frozenset({"jpg", "jpeg", "png"})
_MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MiB


class ProductImageError(ValueError):
    """Raised for product image validation errors."""


def _upload_dir() -> str:
    """Return the absolute path to the product image upload directory."""
    base = current_app.instance_path
    upload_dir = os.path.join(base, "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _validate_image_file(file_storage) -> str:
    """Validate uploaded image file and return its lowercase extension.

    Raises ProductImageError if the file is missing, has a bad extension,
    or exceeds the maximum size.
    """
    if file_storage is None or not file_storage.filename:
        raise ProductImageError("No se proporciono archivo de imagen")

    filename = file_storage.filename
    if "." not in filename:
        raise ProductImageError("El archivo debe tener una extension valida")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ProductImageError(
            f"Formato no permitido. Formatos validos: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )

    # Validate size by reading the stream (without consuming it permanently)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > _MAX_IMAGE_SIZE:
        raise ProductImageError(
            f"El archivo excede el tamano maximo de 2 MiB ({size} bytes)"
        )
    if size == 0:
        raise ProductImageError("El archivo esta vacio")

    return ext


def _unique_filename(ext: str) -> str:
    """Generate a unique server-side filename."""
    return f"{uuid.uuid4().hex}.{ext}"


def upload_product_image(product_id: int, file_storage) -> tuple[Product, dict]:
    """Upload or replace an image for a product.

    Saves the file to instance/uploads/products/ with a unique name,
    updates product.image_filename, and returns the product plus cleanup info.
    The caller is responsible for committing the transaction.
    File deletion of the previous image must happen after a successful commit.
    If the commit fails, the new file must be removed by the caller.
    """
    ext = _validate_image_file(file_storage)
    product = db.session.get(Product, product_id)
    if product is None:
        raise ProductImageError("Producto no encontrado")

    old_filename = product.image_filename
    new_filename = _unique_filename(ext)
    upload_dir = _upload_dir()
    new_path = os.path.join(upload_dir, new_filename)

    try:
        file_storage.save(new_path)
    except OSError as exc:
        raise ProductImageError(f"No se pudo guardar la imagen: {exc}")

    product.image_filename = new_filename
    db.session.add(product)

    cleanup = {
        "old_filename": old_filename,
        "new_path": new_path,
        "upload_dir": upload_dir,
    }
    return product, cleanup


def delete_product_image(product_id: int) -> tuple[Product, dict]:
    """Remove the image from a product and delete the file.

    Does not deactivate the product. Returns the product plus cleanup info.
    The caller is responsible for committing the transaction.
    File deletion must happen after a successful commit.
    If the commit fails, the file remains on disk (no data loss).
    """
    product = db.session.get(Product, product_id)
    if product is None:
        raise ProductImageError("Producto no encontrado")

    old_filename = product.image_filename
    cleanup = {
        "old_filename": old_filename,
        "upload_dir": _upload_dir() if old_filename else None,
    }

    if old_filename:
        product.image_filename = None
        db.session.add(product)

    return product, cleanup


def get_product_image_filename(product_id: int) -> str | None:
    """Return the image filename for a product, or None if no image."""
    product = db.session.get(Product, product_id)
    if product is None:
        return None
    return product.image_filename
