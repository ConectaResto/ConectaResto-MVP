"""Category administration blueprint.

Administrative endpoints are protected with
roles_required("ADMIN") from the A-02 authorization module.
Public GET endpoints remain unprotected.
"""

from flask import Blueprint, request

from app.auth.decorators import roles_required
from app.auth.service import current_user
from app.catalog.service import (
    _parse_bool,
    CategoryAlreadyExists,
    CategoryNotFound,
    CategoryHasActiveProducts,
    create_category,
    deactivate_category,
    get_category,
    list_categories,
    update_category,
    create_product,
    deactivate_product,
    get_product,
    list_products,
    update_product,
    ProductAlreadyExists,
    ProductNotFound,
)
from app.common.responses import error_response, success_response

categories_bp = Blueprint("categories", __name__)
products_bp = Blueprint("products", __name__)


@categories_bp.get("/categories")
def list_all():
    """List active categories (public query)."""
    try:
        include_inactive = _parse_bool(request.args.get("include_inactive", False), "include_inactive")
    except ValueError as exc:
        return error_response(str(exc), 400)
    if include_inactive:
        user = current_user()
        if user is None:
            return error_response("No autorizado", 401)
        if user.rol.name != "ADMIN":
            return error_response("Prohibido", 403)
    categories = list_categories(include_inactive=include_inactive)
    return success_response(data=[c.to_dict() for c in categories])


@categories_bp.post("/categories")
@roles_required("ADMIN")
def create():
    """Create a new active category."""
    data = request.get_json(silent=True) or {}
    try:
        category = create_category(data)
    except CategoryAlreadyExists as exc:
        return error_response(str(exc), 409)
    return success_response(data=category.to_dict(), message="Categoria creada", status_code=201)


@categories_bp.get("/categories/<int:category_id>")
def get_one(category_id):
    """Get a single active category by id."""
    category = get_category(category_id, include_inactive=False)
    if category is None:
        return error_response("Categoria no encontrada", 404)
    return success_response(data=category.to_dict())


@categories_bp.patch("/categories/<int:category_id>")
@roles_required("ADMIN")
def update_one(category_id):
    """Update a category's name and/or description."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("Cuerpo JSON invalido", 400)
    try:
        category = update_category(category_id, data, include_inactive=False)
    except CategoryNotFound as exc:
        return error_response(str(exc), 404)
    except CategoryAlreadyExists as exc:
        return error_response(str(exc), 409)
    except ValueError as exc:
        return error_response(str(exc), 400)
    return success_response(data=category.to_dict())


@categories_bp.delete("/categories/<int:category_id>")
@roles_required("ADMIN")
def deactivate_one(category_id):
    """Soft-delete a category (sets is_active = False)."""
    try:
        category = deactivate_category(category_id)
    except CategoryNotFound as exc:
        return error_response(str(exc), 404)
    except CategoryHasActiveProducts as exc:
        return error_response(str(exc), 409)
    if category is None:
        return error_response("Categoria no encontrada o ya inactiva", 404)
    return success_response(message="Categoria desactivada")


@products_bp.get("/products")
def list_all_products():
    """List available products (public query). Optional filter ?categoria_id=."""
    categoria_id = request.args.get("categoria_id", type=int)
    products = list_products(include_inactive=False, categoria_id=categoria_id)
    return success_response(data=[p.to_dict() for p in products])


@products_bp.get("/admin/products")
@roles_required("ADMIN")
def list_admin_products():
    """List active products from active categories regardless of availability."""
    try:
        include_inactive = _parse_bool(request.args.get("include_inactive", False), "include_inactive")
    except ValueError as exc:
        return error_response(str(exc), 400)
    products = list_products(include_inactive=include_inactive, include_unavailable=True)
    return success_response(data=[p.to_dict() for p in products])


@products_bp.post("/products")
@roles_required("ADMIN")
def create_product_route():
    """Create a new active and available product."""
    data = request.get_json(silent=True) or {}
    try:
        product = create_product(data)
    except ProductAlreadyExists as exc:
        return error_response(str(exc), 409)
    except ProductNotFound as exc:
        return error_response(str(exc), 404)
    return success_response(data=product.to_dict(), message="Producto creado", status_code=201)


@products_bp.get("/products/<int:product_id>")
def get_one_product(product_id):
    """Get a single available product by id."""
    product = get_product(product_id, include_inactive=False)
    if product is None:
        return error_response("Producto no encontrado", 404)
    return success_response(data=product.to_dict())


@products_bp.patch("/products/<int:product_id>")
@roles_required("ADMIN")
def update_one_product(product_id):
    """Update a product's fields."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("Cuerpo JSON invalido", 400)
    try:
        product = update_product(product_id, data, include_inactive=False)
    except ProductNotFound as exc:
        return error_response(str(exc), 404)
    except ProductAlreadyExists as exc:
        return error_response(str(exc), 409)
    except ValueError as exc:
        return error_response(str(exc), 400)
    return success_response(data=product.to_dict())


@products_bp.delete("/products/<int:product_id>")
@roles_required("ADMIN")
def deactivate_one_product(product_id):
    """Soft-delete a product (sets is_active = False)."""
    try:
        product = deactivate_product(product_id)
    except ProductNotFound as exc:
        return error_response(str(exc), 404)
    if product is None:
        return error_response("Producto no encontrado o ya inactivo", 404)
    return success_response(message="Producto desactivado")
